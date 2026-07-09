#!/usr/bin/env python3
"""Smoke-validate label-rate perception dry-run scripts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


HUMAN_REVIEW_OPS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = HUMAN_REVIEW_OPS_ROOT.parent
SCRIPT_PATH = (
    HUMAN_REVIEW_OPS_ROOT
    / "skills"
    / "perception"
    / "scripts"
    / "label_rate_perception.py"
)
REQUIRED_TOP_LEVEL_FIELDS = {
    "scenario_key",
    "task_type",
    "run_mode",
    "metric_ids",
    "retrieval_policy",
    "readiness",
}


def main() -> None:
    validate_ready_case()
    validate_needs_clarification_case()
    print("Label-rate perception scripts OK")


def run_dry_run(request: str) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--dry-run",
            "--request",
            request,
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Dry-run stdout is not JSON: {completed.stdout}") from exc
    if not isinstance(payload, dict):
        raise AssertionError("Dry-run payload must be a JSON object.")
    return payload


def validate_ready_case() -> None:
    payload = run_dry_run(
        "请判断这个需求属于哪个人审运营场景：帮我看近 7 天低打标率策略，"
        "按机审一级标签、策略 ID、策略名称、送审原因拆解，并分 P0/P1/P2/notice。"
    )
    assert_common_contract(payload)

    if payload["scenario_key"] != "efficiency-label-rate":
        raise AssertionError("Ready case scenario_key mismatch.")
    if payload["task_type"] != "low_label_rate_grading":
        raise AssertionError("Ready case task_type mismatch.")
    if payload["run_mode"] != "debug_only":
        raise AssertionError("Ready case run_mode mismatch.")
    if "label_rate" not in payload["metric_ids"]:
        raise AssertionError("Ready case must include label_rate metric.")
    if payload.get("time_window") != "近 7 天":
        raise AssertionError("Ready case time_window should be extracted.")

    expected_dimensions = {
        "mach_root_label_name",
        "strategy_id",
        "strategy_name",
        "reason",
    }
    if set(payload.get("dimensions", [])) != expected_dimensions:
        raise AssertionError("Ready case dimensions mismatch.")

    readiness = payload["readiness"]
    if readiness.get("status") != "ready":
        raise AssertionError(f"Ready case status mismatch: {readiness}")
    if readiness.get("blocking_reasons") != []:
        raise AssertionError("Ready case should not have blocking reasons.")
    if readiness.get("clarification_fields") != []:
        raise AssertionError("Ready case should not require clarification.")
    if payload.get("handoff", {}).get("next_skill") != "analysis":
        raise AssertionError("Ready case should hand off to analysis.")
    assert_no_side_effects(payload)


def validate_needs_clarification_case() -> None:
    payload = run_dry_run("看下低打标率问题。")
    assert_common_contract(payload)

    if payload["scenario_key"] != "efficiency-label-rate":
        raise AssertionError("Clarification case scenario_key mismatch.")
    if payload["task_type"] != "low_label_rate_grading":
        raise AssertionError("Clarification case task_type mismatch.")

    readiness = payload["readiness"]
    if readiness.get("status") != "needs_clarification":
        raise AssertionError(f"Clarification case status mismatch: {readiness}")
    if "missing_time_window" not in readiness.get("blocking_reasons", []):
        raise AssertionError("Clarification case must report missing_time_window.")
    if "time_window" not in readiness.get("clarification_fields", []):
        raise AssertionError("Clarification case must ask for time_window.")
    if payload.get("handoff", {}).get("next_skill") is not None:
        raise AssertionError("Clarification case must not hand off yet.")
    assert_no_side_effects(payload)


def assert_common_contract(payload: dict[str, Any]) -> None:
    missing = REQUIRED_TOP_LEVEL_FIELDS - set(payload)
    if missing:
        raise AssertionError(f"Missing top-level fields: {sorted(missing)}")
    policy = payload["retrieval_policy"]
    for field in (
        "reference_first",
        "semantic_layer_first",
        "allow_readonly_query_after_query_plan",
        "forbid_sql_execution_in_perception",
        "forbid_notification",
        "forbid_online_write",
    ):
        if policy.get(field) is not True:
            raise AssertionError(f"retrieval_policy.{field} must be true.")
    readiness = payload["readiness"]
    for field in ("status", "blocking_reasons", "clarification_fields"):
        if field not in readiness:
            raise AssertionError(f"readiness.{field} missing.")


def assert_no_side_effects(payload: dict[str, Any]) -> None:
    safety = payload.get("safety", {})
    expected = {
        "sql_executed": False,
        "notification_sent": False,
        "online_write_executed": False,
        "sensitive_detail_exported": False,
    }
    if safety != expected:
        raise AssertionError(f"Unexpected side effects: {safety}")


if __name__ == "__main__":
    main()
