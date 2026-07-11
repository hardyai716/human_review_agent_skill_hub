#!/usr/bin/env python3
"""Validate Aeolus semantic-field contracts in analysis scenario docs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


HUMAN_REVIEW_OPS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = HUMAN_REVIEW_OPS_ROOT.parent
ANALYSIS_ROOT = HUMAN_REVIEW_OPS_ROOT / "skills" / "analysis"
CACHE_PATH = Path(__file__).with_name("aeolus_dataset_fields_cache.json")

FIELD_RE = re.compile(r"\[([^\]\n]+)\]")
BACKTICK_FIELD_RE = re.compile(r"`\[([^\]\n]+)\]`")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
ALLOWED_FIELD_TABLE_HEADERS = {
    ("概念", "aeolus query 使用字段", "说明"),
    ("概念", "aeolus query 使用字段", "口径", "说明"),
}
FORBIDDEN_FIELD_TABLE_HEADERS = {
    "metric_id",
    "逻辑 `metric_id`",
    "逻辑字段",
    "默认 Name",
    "默认 Name / expr",
    "数据集字段 / 指标",
}
IGNORED_FIELDS = {
    "Name",
    "数据集字段名",
}
IGNORED_LINE_MARKERS = {
    "Dataset 名称",
    "数据集名称",
}

SCENARIOS = {
    "efficiency-label-rate": {
        "dataset_id": "3888816",
        "region": "cn",
        "doc": ANALYSIS_ROOT
        / "references"
        / "scenarios"
        / "efficiency-label-rate.md",
        "scripts": [
            {
                "path": ANALYSIS_ROOT / "scripts" / "label_rate_analysis.py",
                "args": ["--dry-run"],
            }
        ],
    },
    "efficiency-auto-disposal-accuracy": {
        "dataset_id": "3945965",
        "region": "cn",
        "doc": ANALYSIS_ROOT
        / "references"
        / "scenarios"
        / "efficiency-auto-disposal-accuracy.md",
        "scripts": [],
    },
    "quality-inspection-accuracy": {
        "dataset_id": "3533559",
        "region": "cn",
        "doc": ANALYSIS_ROOT
        / "references"
        / "scenarios"
        / "quality-inspection-accuracy.md",
        "scripts": [
            {
                "path": ANALYSIS_ROOT / "scripts" / "quality_inspection_accuracy_query.py",
                "args": ["--current-date", "2026-07-08", "--format", "sql"],
            }
        ],
    },
}


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def iter_markdown_tables(text: str) -> list[tuple[int, list[list[str]]]]:
    lines = text.splitlines()
    tables: list[tuple[int, list[list[str]]]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.lstrip().startswith("|"):
            index += 1
            continue
        if index + 1 >= len(lines) or not TABLE_SEPARATOR_RE.match(lines[index + 1]):
            index += 1
            continue

        start_line = index + 1
        rows = [split_markdown_row(line), split_markdown_row(lines[index + 1])]
        index += 2
        while index < len(lines) and lines[index].lstrip().startswith("|"):
            rows.append(split_markdown_row(lines[index]))
            index += 1
        tables.append((start_line, rows))
    return tables


def extract_fields_from_text(text: str) -> set[str]:
    fields: set[str] = set()
    for line in text.splitlines():
        if any(marker in line for marker in IGNORED_LINE_MARKERS):
            continue
        for match in FIELD_RE.finditer(line):
            field = match.group(1).strip()
            if field and field not in IGNORED_FIELDS and "{" not in field and "}" not in field:
                fields.add(field)
    return fields


def extract_backtick_fields_from_text(text: str) -> set[str]:
    fields: set[str] = set()
    for line in text.splitlines():
        if any(marker in line for marker in IGNORED_LINE_MARKERS):
            continue
        for match in BACKTICK_FIELD_RE.finditer(line):
            field = match.group(1).strip()
            if field and field not in IGNORED_FIELDS and "{" not in field and "}" not in field:
                fields.add(field)
    return fields


def load_cache() -> dict[str, set[str]]:
    payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    datasets = payload.get("datasets")
    if not isinstance(datasets, dict):
        raise ValueError(f"{rel(CACHE_PATH)} missing datasets object.")

    result: dict[str, set[str]] = {}
    for dataset_id, entry in datasets.items():
        if not isinstance(entry, dict):
            raise ValueError(f"{rel(CACHE_PATH)} dataset {dataset_id} must be object.")
        fields = entry.get("fields")
        if not isinstance(fields, list) or not all(isinstance(item, str) for item in fields):
            raise ValueError(f"{rel(CACHE_PATH)} dataset {dataset_id}.fields must be strings.")
        result[str(dataset_id)] = set(fields)
    return result


def collect_names(payload: Any) -> set[str]:
    names: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            name = value.get("name") or value.get("fieldName") or value.get("title")
            if isinstance(name, str) and name:
                names.add(name)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    return names


def refresh_cache() -> None:
    datasets: dict[str, dict[str, Any]] = {}
    for scenario in SCENARIOS.values():
        dataset_id = scenario["dataset_id"]
        region = scenario["region"]
        command = [
            "bytedcli",
            "-j",
            "aeolus",
            "dataset-fields",
            "-r",
            region,
            dataset_id,
        ]
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise SystemExit(
                f"Failed to refresh dataset {dataset_id}: {result.stderr or result.stdout}"
            )
        payload = json.loads(result.stdout)
        data = payload.get("data", payload)
        datasets[dataset_id] = {
            "region": region,
            "fields": sorted(collect_names(data)),
        }

    CACHE_PATH.write_text(
        json.dumps(
            {"schema_version": "aeolus_dataset_fields_cache.v1", "datasets": datasets},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def validate_field_tables(
    *,
    scenario_key: str,
    doc_path: Path,
    text: str,
    issues: list[str],
) -> set[str]:
    registered_fields: set[str] = set()
    for start_line, rows in iter_markdown_tables(text):
        header = tuple(rows[0])
        forbidden = FORBIDDEN_FIELD_TABLE_HEADERS.intersection(header)
        if forbidden:
            issues.append(
                f"{rel(doc_path)}:{start_line} {scenario_key} field table contains "
                f"forbidden column(s): {sorted(forbidden)}"
            )

        if "aeolus query 使用字段" not in header:
            continue

        if header not in ALLOWED_FIELD_TABLE_HEADERS:
            issues.append(
                f"{rel(doc_path)}:{start_line} {scenario_key} unsupported Aeolus field "
                f"table header: {list(header)}"
            )
            continue

        field_index = header.index("aeolus query 使用字段")
        for row_offset, row in enumerate(rows[2:], start=2):
            if field_index >= len(row):
                issues.append(
                    f"{rel(doc_path)}:{start_line + row_offset} {scenario_key} "
                    "field row is shorter than header."
                )
                continue
            cell = row[field_index]
            if cell == "无":
                continue
            cell_fields = extract_fields_from_text(cell)
            if not cell_fields:
                issues.append(
                    f"{rel(doc_path)}:{start_line + row_offset} {scenario_key} "
                    f"field cell must use `[数据集字段名]` or `无`: {cell!r}"
                )
            registered_fields.update(cell_fields)
    return registered_fields


def validate_doc_fields(
    *,
    scenario_key: str,
    dataset_id: str,
    doc_path: Path,
    text: str,
    cache_fields: set[str],
    registered_fields: set[str],
    issues: list[str],
) -> None:
    used_fields = extract_fields_from_text(text)
    missing_from_dataset = sorted(field for field in used_fields if field not in cache_fields)
    if missing_from_dataset:
        issues.append(
            f"{rel(doc_path)} {scenario_key} field(s) missing from dataset {dataset_id} "
            f"cache: {missing_from_dataset}"
        )

    missing_registration = sorted(
        field
        for field in used_fields
        if field in cache_fields and field not in registered_fields
    )
    if missing_registration:
        issues.append(
            f"{rel(doc_path)} {scenario_key} field(s) used in doc but not registered "
            f"in Aeolus field tables: {missing_registration}"
        )


def script_outputs(script_path: Path, args: list[str]) -> str:
    text = script_path.read_text(encoding="utf-8")
    if not args:
        return text
    result = subprocess.run(
        [sys.executable, str(script_path), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{rel(script_path)} failed during dry-run: {result.stderr or result.stdout}"
        )
    return text + "\n" + result.stdout


def validate_script_fields(
    *,
    scenario_key: str,
    dataset_id: str,
    script_path: Path,
    script_args: list[str],
    cache_fields: set[str],
    registered_fields: set[str],
    issues: list[str],
) -> None:
    text = script_outputs(script_path, script_args)
    used_fields = extract_backtick_fields_from_text(text)
    missing_from_dataset = sorted(field for field in used_fields if field not in cache_fields)
    if missing_from_dataset:
        issues.append(
            f"{rel(script_path)} {scenario_key} field(s) missing from dataset "
            f"{dataset_id} cache: {missing_from_dataset}"
        )

    missing_registration = sorted(
        field for field in used_fields if field in cache_fields and field not in registered_fields
    )
    if missing_registration:
        issues.append(
            f"{rel(script_path)} {scenario_key} field(s) used by script but not "
            f"registered in scenario doc: {missing_registration}"
        )


def run_validation() -> list[str]:
    cache = load_cache()
    issues: list[str] = []

    for scenario_key, scenario in SCENARIOS.items():
        dataset_id = scenario["dataset_id"]
        doc_path = scenario["doc"]
        if dataset_id not in cache:
            issues.append(f"{scenario_key} dataset {dataset_id} missing from cache.")
            continue
        if not doc_path.exists():
            issues.append(f"{scenario_key} missing scenario doc: {rel(doc_path)}")
            continue

        text = doc_path.read_text(encoding="utf-8")
        registered_fields = validate_field_tables(
            scenario_key=scenario_key,
            doc_path=doc_path,
            text=text,
            issues=issues,
        )
        validate_doc_fields(
            scenario_key=scenario_key,
            dataset_id=dataset_id,
            doc_path=doc_path,
            text=text,
            cache_fields=cache[dataset_id],
            registered_fields=registered_fields,
            issues=issues,
        )

        for script in scenario["scripts"]:
            validate_script_fields(
                scenario_key=scenario_key,
                dataset_id=dataset_id,
                script_path=script["path"],
                script_args=list(script.get("args", [])),
                cache_fields=cache[dataset_id],
                registered_fields=registered_fields,
                issues=issues,
            )

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate Aeolus field references in analysis scenario docs and scripts."
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Refresh dataset field cache via bytedcli dataset-fields before validating.",
    )
    args = parser.parse_args()

    if args.refresh_cache:
        refresh_cache()

    try:
        issues = run_validation()
    except Exception as error:  # noqa: BLE001
        print(f"Aeolus field contract validation FAILED: {error}")
        raise SystemExit(1)

    if issues:
        print("Aeolus field contract validation FAILED")
        for issue in issues:
            print(f"- {issue}")
        raise SystemExit(1)

    print("Aeolus field contract validation OK")


if __name__ == "__main__":
    main()
