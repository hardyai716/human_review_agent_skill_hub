#!/usr/bin/env python3
"""Validate local manual tracking for stage 2 label-rate outputs."""

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
    / "20260709_low_label_rate_grading_min_review_in_draft"
)
STATE_MACHINE_PATH = (
    ROOT / "references" / "scenarios" / "efficiency-label-rate" / "state_machine.md"
)
EXPECTED_LEVELS = {"notice", "P2", "P1", "P0"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", nargs="?", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    validate(output_dir)
    print(f"Stage 2 label-rate manual tracking OK: {output_dir}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(output_dir: Path) -> None:
    manual_tracking_path = output_dir / "manual_tracking.json"
    notification_draft_path = output_dir / "notification_draft.json"
    send_plan_path = output_dir / "send_plan.json"

    for path in (manual_tracking_path, notification_draft_path, send_plan_path):
        if not path.exists():
            raise AssertionError(f"Missing artifact: {path.name}")

    state_machine_text = STATE_MACHINE_PATH.read_text(encoding="utf-8")
    if "MANUAL_TRACKING_RECORDED" not in state_machine_text:
        raise AssertionError("state_machine.md missing MANUAL_TRACKING_RECORDED.")

    manual_tracking = load_json(manual_tracking_path)
    notification_draft = load_json(notification_draft_path)
    send_plan = load_json(send_plan_path)

    assert_header(manual_tracking)
    assert_state_machine(manual_tracking)
    assert_required_fields(manual_tracking)
    assert_tracking_records(manual_tracking)
    assert_safety(manual_tracking, send_plan, notification_draft)


def assert_header(manual_tracking: dict[str, Any]) -> None:
    if manual_tracking.get("schema_version") != "stage_2_manual_tracking.v1":
        raise AssertionError("manual_tracking schema_version mismatch.")
    if manual_tracking.get("scenario_key") != "efficiency-label-rate":
        raise AssertionError("manual_tracking scenario_key mismatch.")
    if manual_tracking.get("report_type") != "low_efficiency_grading":
        raise AssertionError("manual_tracking report_type mismatch.")
    if manual_tracking.get("tracking_mode") != "local_debug_only":
        raise AssertionError("manual_tracking tracking_mode mismatch.")


def assert_state_machine(manual_tracking: dict[str, Any]) -> None:
    state_machine = manual_tracking.get("state_machine", {})
    if state_machine.get("previous_state") != "NOTIFICATION_DRAFTED":
        raise AssertionError("manual_tracking previous_state mismatch.")
    if state_machine.get("current_state") != "MANUAL_TRACKING_RECORDED":
        raise AssertionError("manual_tracking current_state mismatch.")
    if not state_machine.get("state_machine_ref", "").endswith("state_machine.md"):
        raise AssertionError("manual_tracking state_machine_ref missing.")


def assert_required_fields(manual_tracking: dict[str, Any]) -> None:
    for field in ("evidence_refs", "operator_note", "next_action"):
        value = manual_tracking.get(field)
        if not value:
            raise AssertionError(f"manual_tracking {field} missing.")
    if manual_tracking.get("continue_observation") is not True:
        raise AssertionError("manual_tracking continue_observation must be true.")

    closure_check = manual_tracking.get("closure_check", {})
    if closure_check.get("can_close") is not False:
        raise AssertionError("manual_tracking must not be closable yet.")
    if not closure_check.get("missing_before_close"):
        raise AssertionError("manual_tracking closure missing_before_close missing.")


def assert_tracking_records(manual_tracking: dict[str, Any]) -> None:
    records = manual_tracking.get("tracking_records", [])
    if {record.get("severity_level") for record in records} != EXPECTED_LEVELS:
        raise AssertionError("manual_tracking records must cover notice/P2/P1/P0.")
    for record in records:
        level = record["severity_level"]
        if record.get("status") != "pending_manual_follow_up":
            raise AssertionError(f"{level} status mismatch.")
        if record.get("continue_observation") is not True:
            raise AssertionError(f"{level} continue_observation must be true.")
        for field in ("evidence_refs", "operator_note", "next_action"):
            if not record.get(field):
                raise AssertionError(f"{level} {field} missing.")
        resolution = record.get("recipient_resolution", {})
        if resolution.get("mode") != "mach_root_label_mapping":
            raise AssertionError(f"{level} recipient resolution must be mach_root_label_mapping.")
        if resolution.get("routing_key") != "mach_root_label_name":
            raise AssertionError(f"{level} recipient routing_key mismatch.")
        if record.get("reason_count", 0) > 0 and resolution.get("real_poc_count", 0) <= 0:
            raise AssertionError(f"{level} must contain name-level POCs when rows exist.")


def assert_safety(
    manual_tracking: dict[str, Any],
    send_plan: dict[str, Any],
    notification_draft: dict[str, Any],
) -> None:
    safety = manual_tracking.get("safety", {})
    if safety.get("requires_confirmation") is not True:
        raise AssertionError("manual_tracking must require confirmation.")
    if safety.get("group_send_blocked") is not True:
        raise AssertionError("manual_tracking group_send_blocked must be true.")
    if safety.get("group_send_sent") is not False:
        raise AssertionError("manual_tracking group_send_sent must be false.")
    if safety.get("real_group_send_executed") is not False:
        raise AssertionError("manual_tracking must not execute real group send.")
    if safety.get("online_write_executed") is not False:
        raise AssertionError("manual_tracking online_write_executed must be false.")
    if safety.get("online_state_write_allowed") is not False:
        raise AssertionError("manual_tracking online_state_write_allowed must be false.")

    if send_plan.get("sent") is not False:
        raise AssertionError("send_plan sent must remain false.")
    if notification_draft.get("send_safety", {}).get("online_write_executed") is not False:
        raise AssertionError("notification_draft online_write_executed must remain false.")


if __name__ == "__main__":
    main()
