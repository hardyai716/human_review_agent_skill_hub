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
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*```([A-Za-z0-9_-]*)\s*$")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
ALLOWED_FIELD_TABLE_HEADERS = {
    ("概念", "aeolus query 使用字段", "说明"),
    ("概念", "aeolus query 使用字段", "口径", "说明"),
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
        "doc": ANALYSIS_ROOT
        / "references"
        / "scenarios"
        / "efficiency-label-rate.md",
        "profiles": {
            "manual_review_detail": {
                "dataset_id": "3888816",
                "region": "cn",
                "scripts": [
                    {
                        "path": ANALYSIS_ROOT / "scripts" / "label_rate_analysis.py",
                        "args": [
                            "--dry-run",
                            "--data-direction",
                            "manual_review_detail",
                        ],
                    }
                ],
            },
            "report_flow": {
                "dataset_id": "3952594",
                "region": "cn",
                "scripts": [
                    {
                        "path": ANALYSIS_ROOT / "scripts" / "label_rate_analysis.py",
                        "args": ["--dry-run", "--data-direction", "report_flow"],
                    }
                ],
            },
        },
    },
    "efficiency-auto-disposal-accuracy": {
        "doc": ANALYSIS_ROOT
        / "references"
        / "scenarios"
        / "efficiency-auto-disposal-accuracy.md",
        "profiles": {
            "default": {
                "dataset_id": "3945965",
                "region": "cn",
                "scripts": [],
            }
        },
    },
    "quality-inspection-accuracy": {
        "doc": ANALYSIS_ROOT
        / "references"
        / "scenarios"
        / "quality-inspection-accuracy.md",
        "profiles": {
            "default": {
                "dataset_id": "3533559",
                "region": "cn",
                "scripts": [
                    {
                        "path": ANALYSIS_ROOT
                        / "scripts"
                        / "quality_inspection_accuracy_query.py",
                        "args": ["--current-date", "2026-07-08", "--format", "sql"],
                    }
                ],
            }
        },
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


def normalize_field(raw_field: str) -> str | None:
    field = raw_field.strip()
    if not field:
        return None
    if field in IGNORED_FIELDS:
        return None
    if "{" in field or "}" in field:
        return None
    return field


def extract_bracket_fields_from_text(text: str) -> set[str]:
    fields: set[str] = set()
    for line in text.splitlines():
        if any(marker in line for marker in IGNORED_LINE_MARKERS):
            continue
        for match in FIELD_RE.finditer(line):
            field = normalize_field(match.group(1))
            if field:
                fields.add(field)
    return fields


def extract_backtick_fields_from_text(text: str) -> set[str]:
    fields: set[str] = set()
    for line in text.splitlines():
        if any(marker in line for marker in IGNORED_LINE_MARKERS):
            continue
        for match in BACKTICK_FIELD_RE.finditer(line):
            field = normalize_field(match.group(1))
            if field:
                fields.add(field)
    return fields


def extract_named_fields_from_cell(cell: str) -> set[str]:
    fields: set[str] = set()
    if cell.strip() == "无":
        return fields
    for code in INLINE_CODE_RE.findall(cell):
        code = code.strip()
        if not code or code == "无":
            continue
        bracket_fields = extract_bracket_fields_from_text(code)
        if bracket_fields:
            fields.update(bracket_fields)
            continue
        field = normalize_field(code)
        if field:
            fields.add(field)
    return fields


def markdown_headings(text: str) -> list[tuple[int, str]]:
    headings: list[tuple[int, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = HEADING_RE.match(line)
        if match:
            headings.append((line_number, match.group(1).strip()))
    return headings


def heading_before_line(headings: list[tuple[int, str]], line_number: int) -> str:
    current = ""
    for heading_line, heading in headings:
        if heading_line >= line_number:
            break
        current = heading
    return current


def profile_key_for_line(
    *,
    scenario_key: str,
    profiles: dict[str, dict[str, Any]],
    headings: list[tuple[int, str]],
    line_number: int,
) -> str:
    if len(profiles) == 1:
        return next(iter(profiles))

    heading = heading_before_line(headings, line_number)
    if scenario_key == "efficiency-label-rate":
        if "举报" in heading or "report_flow" in heading:
            return "report_flow"
        return "manual_review_detail"

    return next(iter(profiles))


def iter_markdown_field_references(text: str) -> list[tuple[int, str]]:
    references: list[tuple[int, str]] = []
    lines = text.splitlines()
    in_fence = False
    is_sql_fence = False

    for line_number, line in enumerate(lines, start=1):
        fence = FENCE_RE.match(line)
        if fence:
            if in_fence:
                in_fence = False
                is_sql_fence = False
            else:
                in_fence = True
                is_sql_fence = fence.group(1).lower() == "sql"
            continue

        if any(marker in line for marker in IGNORED_LINE_MARKERS):
            continue

        pattern = FIELD_RE if in_fence and is_sql_fence else BACKTICK_FIELD_RE
        for match in pattern.finditer(line):
            field = normalize_field(match.group(1))
            if field:
                references.append((line_number, field))
    return references


def collect_markdown_fields_by_profile(
    *,
    scenario_key: str,
    text: str,
    profiles: dict[str, dict[str, Any]],
) -> dict[str, set[str]]:
    headings = markdown_headings(text)
    fields_by_profile = {profile_key: set() for profile_key in profiles}
    for line_number, field in iter_markdown_field_references(text):
        profile_key = profile_key_for_line(
            scenario_key=scenario_key,
            profiles=profiles,
            headings=headings,
            line_number=line_number,
        )
        fields_by_profile.setdefault(profile_key, set()).add(field)
    return fields_by_profile


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
        for profile in scenario["profiles"].values():
            dataset_id = profile["dataset_id"]
            if dataset_id in datasets:
                continue
            region = profile["region"]
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
    profiles: dict[str, dict[str, Any]],
    issues: list[str],
) -> dict[str, set[str]]:
    registered_fields = {profile_key: set() for profile_key in profiles}
    headings = markdown_headings(text)
    for start_line, rows in iter_markdown_tables(text):
        header = tuple(rows[0])
        field_index: int | None = None
        field_column_kind = ""

        if "aeolus query 使用字段" in header:
            if header not in ALLOWED_FIELD_TABLE_HEADERS:
                issues.append(
                    f"{rel(doc_path)}:{start_line} {scenario_key} unsupported Aeolus field "
                    f"table header: {list(header)}"
                )
                continue
            field_index = header.index("aeolus query 使用字段")
            field_column_kind = "bracket"
        elif "默认 Name" in header:
            field_index = header.index("默认 Name")
            field_column_kind = "name"
        else:
            continue

        profile_key = profile_key_for_line(
            scenario_key=scenario_key,
            profiles=profiles,
            headings=headings,
            line_number=start_line,
        )
        if profile_key not in registered_fields:
            issues.append(
                f"{rel(doc_path)}:{start_line} {scenario_key} field table maps to "
                f"unknown profile: {profile_key}"
            )
            continue

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
            if field_column_kind == "bracket":
                cell_fields = extract_bracket_fields_from_text(cell)
                expected_format = "`[数据集字段名]` / `[数据集字段名]` or `无`"
            else:
                cell_fields = extract_named_fields_from_cell(cell)
                expected_format = "`数据集字段名` or `无`"
            if not cell_fields:
                issues.append(
                    f"{rel(doc_path)}:{start_line + row_offset} {scenario_key} "
                    f"field cell must use {expected_format}: {cell!r}"
                )
            registered_fields[profile_key].update(cell_fields)

            for index, column_name in enumerate(header):
                if index >= len(row):
                    continue
                if "口径" in column_name or "expr" in column_name:
                    registered_fields[profile_key].update(
                        extract_bracket_fields_from_text(row[index])
                    )
    return registered_fields


def validate_registered_fields(
    *,
    scenario_key: str,
    profile_key: str,
    dataset_id: str,
    doc_path: Path,
    cache_fields: set[str],
    registered_fields: set[str],
    issues: list[str],
) -> None:
    missing_from_dataset = sorted(
        field for field in registered_fields if field not in cache_fields
    )
    if missing_from_dataset:
        issues.append(
            f"{rel(doc_path)} {scenario_key}/{profile_key} registered field(s) missing "
            f"from dataset {dataset_id} cache: {missing_from_dataset}"
        )


def validate_doc_fields(
    *,
    scenario_key: str,
    profile_key: str,
    dataset_id: str,
    doc_path: Path,
    used_fields: set[str],
    cache_fields: set[str],
    registered_fields: set[str],
    issues: list[str],
) -> None:
    missing_from_dataset = sorted(field for field in used_fields if field not in cache_fields)
    if missing_from_dataset:
        issues.append(
            f"{rel(doc_path)} {scenario_key}/{profile_key} field(s) missing from "
            f"dataset {dataset_id} cache: {missing_from_dataset}"
        )

    missing_registration = sorted(
        field
        for field in used_fields
        if field in cache_fields and field not in registered_fields
    )
    if missing_registration:
        issues.append(
            f"{rel(doc_path)} {scenario_key}/{profile_key} field(s) used in doc but "
            f"not registered in Aeolus field tables: {missing_registration}"
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
    return result.stdout


def validate_script_fields(
    *,
    scenario_key: str,
    profile_key: str,
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
            f"{rel(script_path)} {scenario_key}/{profile_key} field(s) missing from "
            f"dataset {dataset_id} cache: {missing_from_dataset}"
        )

    missing_registration = sorted(
        field for field in used_fields if field in cache_fields and field not in registered_fields
    )
    if missing_registration:
        issues.append(
            f"{rel(script_path)} {scenario_key}/{profile_key} field(s) used by script "
            f"but not registered in scenario doc: {missing_registration}"
        )


def run_validation() -> list[str]:
    cache = load_cache()
    issues: list[str] = []

    for scenario_key, scenario in SCENARIOS.items():
        doc_path = scenario["doc"]
        if not doc_path.exists():
            issues.append(f"{scenario_key} missing scenario doc: {rel(doc_path)}")
            continue

        profiles = scenario["profiles"]
        for profile_key, profile in profiles.items():
            dataset_id = profile["dataset_id"]
            if dataset_id not in cache:
                issues.append(
                    f"{scenario_key}/{profile_key} dataset {dataset_id} missing from cache."
                )

        text = doc_path.read_text(encoding="utf-8")
        registered_fields_by_profile = validate_field_tables(
            scenario_key=scenario_key,
            doc_path=doc_path,
            text=text,
            profiles=profiles,
            issues=issues,
        )
        doc_fields_by_profile = collect_markdown_fields_by_profile(
            scenario_key=scenario_key,
            text=text,
            profiles=profiles,
        )

        for profile_key, profile in profiles.items():
            dataset_id = profile["dataset_id"]
            if dataset_id not in cache:
                continue
            registered_fields = registered_fields_by_profile.get(profile_key, set())
            validate_registered_fields(
                scenario_key=scenario_key,
                profile_key=profile_key,
                dataset_id=dataset_id,
                doc_path=doc_path,
                cache_fields=cache[dataset_id],
                registered_fields=registered_fields,
                issues=issues,
            )
            validate_doc_fields(
                scenario_key=scenario_key,
                profile_key=profile_key,
                dataset_id=dataset_id,
                doc_path=doc_path,
                used_fields=doc_fields_by_profile.get(profile_key, set()),
                cache_fields=cache[dataset_id],
                registered_fields=registered_fields,
                issues=issues,
            )

            for script in profile["scripts"]:
                validate_script_fields(
                    scenario_key=scenario_key,
                    profile_key=profile_key,
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
