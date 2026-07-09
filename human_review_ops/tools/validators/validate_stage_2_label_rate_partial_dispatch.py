#!/usr/bin/env python3
"""Validate stage 2 partial-dispatch regression records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = (
    ROOT
    / "evals"
    / "efficiency-label-rate"
    / "stage_2_runs"
    / "20260709_low_label_rate_grading_notification_draft"
)
TASK_TYPES = {"owner_lookup_only", "notification_only", "resolution_only"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", nargs="?", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    validate(output_dir)
    print(f"Stage 2 label-rate partial dispatch OK: {output_dir}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate(output_dir: Path) -> None:
    required_artifacts = [
        "poc_routing_plan.json",
        "notification_draft.json",
        "send_plan.json",
        "manual_tracking.json",
        "owner_lookup_only_results.jsonl",
        "notification_only_results.jsonl",
        "resolution_only_results.jsonl",
        "partial_dispatch_results.jsonl",
    ]
    for relative in required_artifacts:
        if not (output_dir / relative).exists():
            raise AssertionError(f"Missing artifact: {relative}")

    poc_routing = load_json(output_dir / "poc_routing_plan.json")
    notification_draft = load_json(output_dir / "notification_draft.json")
    send_plan = load_json(output_dir / "send_plan.json")
    manual_tracking = load_json(output_dir / "manual_tracking.json")

    combined_records = load_jsonl(output_dir / "partial_dispatch_results.jsonl")
    if {record.get("task_type") for record in combined_records} != TASK_TYPES:
        raise AssertionError("partial dispatch must cover all task types.")

    for task_type in TASK_TYPES:
        records = load_jsonl(output_dir / f"{task_type}_results.jsonl")
        if len(records) != 1:
            raise AssertionError(f"{task_type} must contain one result record.")
        assert_record_safety(records[0], task_type)

    for record in combined_records:
        assert_record_safety(record, record.get("task_type"))

    assert_owner_lookup(combined_records, poc_routing)
    assert_notification(combined_records, notification_draft, send_plan)
    assert_resolution(combined_records, manual_tracking)


def assert_record_safety(record: dict[str, Any], task_type: str | None) -> None:
    if record.get("record_type") != "partial_dispatch_result":
        raise AssertionError(f"{task_type} record_type mismatch.")
    if record.get("schema_version") != "stage_2_partial_dispatch_result.v1":
        raise AssertionError(f"{task_type} schema_version mismatch.")
    if record.get("scenario_key") != "efficiency-label-rate":
        raise AssertionError(f"{task_type} scenario_key mismatch.")
    if record.get("task_type") != task_type:
        raise AssertionError(f"{task_type} task_type mismatch.")
    if record.get("result_status") != "ok":
        raise AssertionError(f"{task_type} result_status mismatch.")
    if record.get("real_query_executed") is not False:
        raise AssertionError(f"{task_type} must not execute real query.")
    if record.get("stage_1_query_reused") is not True:
        raise AssertionError(f"{task_type} must reuse stage 1 query outputs.")
    if record.get("external_cli_calls") != []:
        raise AssertionError(f"{task_type} must not call external CLI.")
    if record.get("group_send_blocked") is not True:
        raise AssertionError(f"{task_type} group_send_blocked must be true.")
    if record.get("group_send_sent") is not False:
        raise AssertionError(f"{task_type} group_send_sent must be false.")
    if record.get("real_group_send_executed") is not False:
        raise AssertionError(f"{task_type} must not execute group send.")
    if record.get("online_write_executed") is not False:
        raise AssertionError(f"{task_type} online_write_executed must be false.")
    if record.get("online_state_write_allowed") is not False:
        raise AssertionError(f"{task_type} online_state_write_allowed must be false.")


def record_by_type(records: list[dict[str, Any]], task_type: str) -> dict[str, Any]:
    matches = [record for record in records if record.get("task_type") == task_type]
    if len(matches) != 1:
        raise AssertionError(f"Expected one {task_type} record.")
    return matches[0]


def assert_owner_lookup(
    records: list[dict[str, Any]],
    poc_routing: dict[str, Any],
) -> None:
    record = record_by_type(records, "owner_lookup_only")
    if record.get("semantic_task_type") != "poc_routing_only":
        raise AssertionError("owner_lookup_only semantic_task_type mismatch.")
    if record.get("result_artifacts") != ["poc_routing_plan.json"]:
        raise AssertionError("owner_lookup_only artifacts mismatch.")
    summary = record.get("summary", {})
    if summary.get("routing_mode") != "mach_root_label_mapping":
        raise AssertionError("owner_lookup_only routing_mode mismatch.")
    if summary.get("default_recipient") != "self":
        raise AssertionError("owner_lookup_only default_recipient mismatch.")
    if poc_routing.get("real_poc_mapping_used") is not True:
        raise AssertionError("POC routing must use name-level mapping.")


def assert_notification(
    records: list[dict[str, Any]],
    notification_draft: dict[str, Any],
    send_plan: dict[str, Any],
) -> None:
    record = record_by_type(records, "notification_only")
    if record.get("semantic_task_type") != "notification_draft_only":
        raise AssertionError("notification_only semantic_task_type mismatch.")
    result_artifacts = set(record.get("result_artifacts", []))
    if "notification_draft.json" not in result_artifacts:
        raise AssertionError("notification_only missing notification draft artifact.")
    if "send_plan.json" not in result_artifacts:
        raise AssertionError("notification_only missing send plan artifact.")
    if notification_draft.get("send_safety", {}).get("group_send_blocked") is not True:
        raise AssertionError("notification draft must block group send.")
    if send_plan.get("requires_confirmation") is not True:
        raise AssertionError("send plan must require confirmation.")
    if send_plan.get("sent") is not False:
        raise AssertionError("send plan sent must remain false.")


def assert_resolution(
    records: list[dict[str, Any]],
    manual_tracking: dict[str, Any],
) -> None:
    record = record_by_type(records, "resolution_only")
    if record.get("semantic_task_type") != "manual_tracking_only":
        raise AssertionError("resolution_only semantic_task_type mismatch.")
    if record.get("result_artifacts") != ["manual_tracking.json"]:
        raise AssertionError("resolution_only artifacts mismatch.")
    summary = record.get("summary", {})
    if summary.get("current_state") != "MANUAL_TRACKING_RECORDED":
        raise AssertionError("resolution_only current_state mismatch.")
    if summary.get("continue_observation") is not True:
        raise AssertionError("resolution_only continue_observation mismatch.")
    if manual_tracking.get("safety", {}).get("online_write_executed") is not False:
        raise AssertionError("manual tracking must not write online state.")


if __name__ == "__main__":
    main()
