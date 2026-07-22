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
    validate_report_flow_case()
    validate_weekly_comparison_notification_case()
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
        "默认按机审一级标签、策略 ID、策略名称分 P0/P1/P2/notice。"
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


def validate_report_flow_case() -> None:
    payload = run_dry_run(
        "举报场景近七天打标率小于10%的enpool_reason有哪些？"
        "输出日均人审完结量、日均打标量和打标率。"
    )
    assert_common_contract(payload)

    if payload["scenario_key"] != "efficiency-label-rate":
        raise AssertionError("Report-flow case scenario_key mismatch.")
    if payload["task_type"] != "low_label_rate_grading":
        raise AssertionError(f"Report-flow case task_type mismatch: {payload['task_type']}")
    if payload.get("data_direction") != "report_flow":
        raise AssertionError("Report-flow case must set data_direction=report_flow.")
    if payload.get("source_profile") != "report_flow_review":
        raise AssertionError("Report-flow case source_profile mismatch.")
    if payload.get("time_window") != "近七天":
        raise AssertionError("Report-flow case should support Chinese numeric time window.")
    if set(payload.get("dimensions", [])) != {"enpool_reason"}:
        raise AssertionError(f"Report-flow dimensions mismatch: {payload.get('dimensions')}")
    expected_metrics = {
        "report_label_rate",
        "report_review_done_cnt",
        "report_label_cnt",
    }
    if not expected_metrics.issubset(set(payload.get("metric_ids", []))):
        raise AssertionError(f"Report-flow metric_ids mismatch: {payload.get('metric_ids')}")
    readiness = payload["readiness"]
    if readiness.get("status") != "ready":
        raise AssertionError(f"Report-flow case status mismatch: {readiness}")
    if payload.get("handoff", {}).get("next_skill") != "analysis":
        raise AssertionError("Report-flow case should hand off to analysis.")
    assert_no_side_effects(payload)


def validate_weekly_comparison_notification_case() -> None:
    payload = run_dry_run(
        "对比 2026-07-06 至 2026-07-12 和 2026-07-13 至 2026-07-19 "
        "的汇总统计_剔除+1同意，按截图样式生成飞书表格并在确认后推送。"
    )
    assert_common_contract(payload)

    if payload["scenario_key"] != "efficiency-label-rate":
        raise AssertionError("Weekly comparison scenario_key mismatch.")
    if payload["task_type"] != "notification_request":
        raise AssertionError("Weekly comparison must route as notification_request.")
    workflow = payload.get("workflow_plan", {})
    if workflow.get("intent_type") != "analysis_then_notification":
        raise AssertionError(
            "Weekly comparison must require analysis before notification."
        )
    if workflow.get("requires_host_send_confirmation") is not True:
        raise AssertionError(
            "Weekly comparison must require host send confirmation."
        )
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
