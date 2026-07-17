#!/usr/bin/env python3
"""Validate runtime artifacts against the repository contract subset."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_ref(root_schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"Only local schema refs are supported: {ref}")
    value: Any = root_schema
    for part in ref[2:].split("/"):
        value = value[part]
    if not isinstance(value, dict):
        raise ValueError(f"Schema ref does not resolve to object: {ref}")
    return value


def validate_value(
    value: Any,
    schema: dict[str, Any],
    *,
    root_schema: dict[str, Any],
    path: str = "$",
) -> list[str]:
    if "$ref" in schema:
        return validate_value(
            value,
            resolve_ref(root_schema, schema["$ref"]),
            root_schema=root_schema,
            path=path,
        )
    issues: list[str] = []
    if "const" in schema and value != schema["const"]:
        issues.append(f"{path}: expected const {schema['const']!r}, got {value!r}")
        return issues
    expected_type = schema.get("type")
    if expected_type is not None and not matches_type(value, expected_type):
        issues.append(f"{path}: expected type {expected_type!r}, got {type(value).__name__}")
        return issues
    if "enum" in schema and value not in schema["enum"]:
        issues.append(f"{path}: value {value!r} not in enum {schema['enum']!r}")
    if isinstance(value, dict):
        required = schema.get("required", [])
        for field in required:
            if field not in value:
                issues.append(f"{path}: missing required field {field!r}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for field in value:
                if field not in properties:
                    issues.append(f"{path}: unexpected field {field!r}")
        for field, field_schema in properties.items():
            if field in value:
                issues.extend(
                    validate_value(
                        value[field],
                        field_schema,
                        root_schema=root_schema,
                        path=f"{path}.{field}",
                    )
                )
    if isinstance(value, list):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            issues.append(f"{path}: expected at least {min_items} items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                issues.extend(
                    validate_value(
                        item,
                        item_schema,
                        root_schema=root_schema,
                        path=f"{path}[{index}]",
                    )
                )
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            issues.append(f"{path}: value below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            issues.append(f"{path}: value above maximum {schema['maximum']}")
    return issues


def matches_type(value: Any, expected: str | list[str]) -> bool:
    expected_types = [expected] if isinstance(expected, str) else expected
    return any(matches_single_type(value, item) for item in expected_types)


def matches_single_type(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "null": value is None,
    }.get(expected, True)


def validate_artifact(schema_name: str, artifact: Any) -> list[str]:
    schema = load_json(SCHEMAS / schema_name)
    return validate_value(artifact, schema, root_schema=schema)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("schema", nargs="?")
    parser.add_argument("artifact", nargs="?")
    args = parser.parse_args()
    if not args.schema and not args.artifact:
        run_repository_smoke()
        print("Runtime contracts smoke OK")
        return
    if not args.schema or not args.artifact:
        parser.error("schema and artifact must be provided together")
    issues = validate_artifact(args.schema, load_json(Path(args.artifact)))
    if issues:
        raise SystemExit("Runtime contract validation failed:\n- " + "\n- ".join(issues))
    print("Runtime contract OK")


def run_repository_smoke() -> None:
    skills = ROOT / "skills"
    with tempfile.TemporaryDirectory(prefix="runtime-contract-smoke-") as tmp:
        tmp_path = Path(tmp)
        perception_path = tmp_path / "perception.json"
        analysis_path = tmp_path / "analysis.json"
        notification_dir = tmp_path / "notification"
        resolution_path = tmp_path / "resolution.json"

        run_json_command(
            [
                sys.executable,
                str(skills / "perception" / "scripts" / "label_rate_perception.py"),
                "--dry-run",
                "--request",
                "帮我看近7天低打标率策略，按P0/P1/P2/notice分级。",
            ],
            perception_path,
        )
        run_json_command(
            [
                sys.executable,
                str(skills / "analysis" / "scripts" / "label_rate_analysis.py"),
                "--dry-run",
            ],
            analysis_path,
        )
        subprocess.run(
            [
                sys.executable,
                str(
                    skills
                    / "notification"
                    / "scripts"
                    / "label_rate_notification_artifacts.py"
                ),
                "--source",
                str(analysis_path),
                "--output-dir",
                str(notification_dir),
            ],
            cwd=ROOT.parent,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                sys.executable,
                str(
                    skills
                    / "resolution"
                    / "scripts"
                    / "build_label_rate_manual_tracking.py"
                ),
                "--notification-draft",
                str(notification_dir / "notification_draft.json"),
                "--send-plan",
                str(notification_dir / "send_plan.json"),
                "--output",
                str(resolution_path),
            ],
            cwd=ROOT.parent,
            check=True,
            capture_output=True,
            text=True,
        )

        artifacts = [
            (
                "perception_result.schema.json",
                load_json(perception_path),
            ),
            (
                "analysis_artifact.schema.json",
                load_json(analysis_path),
            ),
            (
                "analysis_result.schema.json",
                load_json(analysis_path)["analysis_result"],
            ),
            (
                "notification_artifact.schema.json",
                load_json(notification_dir / "notification_draft.json"),
            ),
            (
                "resolution_result.schema.json",
                load_json(resolution_path),
            ),
        ]
        issues: list[str] = []
        for schema_name, artifact in artifacts:
            issues.extend(
                f"{schema_name}: {issue}"
                for issue in validate_artifact(schema_name, artifact)
            )
        if issues:
            raise AssertionError("\n".join(issues))


def run_json_command(command: list[str], output_path: Path) -> None:
    completed = subprocess.run(
        command,
        cwd=ROOT.parent,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
