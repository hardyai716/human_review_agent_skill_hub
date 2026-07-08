#!/usr/bin/env python3
"""Validate TRAE stage 0.5 debug records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_KEY = "efficiency-auto-disposal-accuracy"
EVAL_DIR = ROOT / "evals" / SCENARIO_KEY
SCENARIO_DIR = ROOT / "references" / "scenarios" / SCENARIO_KEY
SKILLS = ("perception", "analysis", "notification", "resolution")


def load_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {error}") from error
    return records


def assert_stage_assets() -> None:
    if not SCENARIO_DIR.exists():
        raise AssertionError(f"Missing root scenario package: {SCENARIO_DIR}")

    for skill in SKILLS:
        snapshot_dir = ROOT / "skills" / skill / "references" / "scenarios"
        if not snapshot_dir.exists():
            raise AssertionError(f"Missing Skill snapshot directory: {snapshot_dir}")


def assert_environment(record: dict | None) -> None:
    if not record:
        raise AssertionError("Missing environment record.")

    required_true_fields = [
        "custom_agent_visible_in_trae",
        "root_package_read",
        "skill_snapshot_available",
        "real_notification_blocked",
        "online_write_blocked",
    ]
    for field in required_true_fields:
        if record.get(field) is not True:
            raise AssertionError(f"Environment check failed: {field} must be true.")

    if record.get("run_mode") != "debug_only":
        raise AssertionError("Environment run_mode must be debug_only.")
    if record.get("result") != "pass":
        raise AssertionError("Environment result must be pass.")


def assert_sample(sample: dict, expected: dict) -> None:
    if sample.get("result") != "pass":
        raise AssertionError(f"{sample.get('id')} did not pass.")

    if expected.get("type") == "positive":
        if sample.get("actual_scenario_key") != expected["expected_scenario_key"]:
            raise AssertionError(f"{sample['id']} scenario mismatch.")
        if sample.get("actual_task_type") != expected["expected_task_type"]:
            raise AssertionError(f"{sample['id']} task_type mismatch.")
        outputs = set(sample.get("outputs", []))
        missing_outputs = set(expected.get("must_output", [])) - outputs
        if missing_outputs:
            raise AssertionError(f"{sample['id']} missing outputs: {sorted(missing_outputs)}")
        if not sample.get("root_package_read"):
            raise AssertionError(f"{sample['id']} should read root scenario package.")

    if expected.get("type") == "negative":
        rejected = expected["expected_reject_scenario_key"]
        if sample.get("actual_scenario_key") == rejected:
            raise AssertionError(f"{sample['id']} incorrectly matched rejected scenario.")
        outputs = set(sample.get("outputs", []))
        if "reject_or_ask_clarification" not in outputs:
            raise AssertionError(f"{sample['id']} must reject or ask clarification.")

    if expected.get("type") == "low_context":
        if sample.get("must_not_query") is not True:
            raise AssertionError(f"{sample['id']} must not query data.")
        outputs = set(sample.get("outputs", []))
        if "ask_more_info" not in outputs:
            raise AssertionError(f"{sample['id']} must ask for more information.")

    permission_checks = sample.get("permission_checks", {})
    if permission_checks.get("read_only") is not True:
        raise AssertionError(f"{sample['id']} must stay read-only.")
    if permission_checks.get("real_notification_blocked") is not True:
        raise AssertionError(f"{sample['id']} must block real notification.")
    if permission_checks.get("online_write_blocked") is not True:
        raise AssertionError(f"{sample['id']} must block online writes.")


def validate(results_path: Path) -> None:
    assert_stage_assets()

    eval_records = load_jsonl(EVAL_DIR / "eval_samples.jsonl")
    expected_by_id = {record["id"]: record for record in eval_records}
    result_records = load_jsonl(results_path)

    environment = next(
        (record for record in result_records if record.get("record_type") == "environment"),
        None,
    )
    assert_environment(environment)

    samples = {
        record["id"]: record
        for record in result_records
        if record.get("record_type") == "sample"
    }
    missing = set(expected_by_id) - set(samples)
    if missing:
        raise AssertionError(f"Missing sample results: {sorted(missing)}")

    for sample_id, expected in expected_by_id.items():
        assert_sample(samples[sample_id], expected)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "results_path",
        nargs="?",
        default=str(EVAL_DIR / "trae_debug_runs" / "20260708_stage_0_5_results.jsonl"),
    )
    args = parser.parse_args()
    validate(Path(args.results_path))
    print(f"TRAE stage 0.5 records OK: {args.results_path}")


if __name__ == "__main__":
    main()
