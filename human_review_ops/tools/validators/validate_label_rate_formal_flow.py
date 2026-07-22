#!/usr/bin/env python3
"""Validate formal label-rate Skill-first flow artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REQUIRED_FILES = [
    "perception_notification_request.json",
    "perception_analysis_request.json",
    "analysis_query_plan.json",
    "analysis_summary.json",
    "notification_draft.json",
    "send_plan.json",
    "summary.json",
    "publish/low_efficiency_grading.card.json",
    "publish/card_hash_check.json",
    "publish/low_efficiency_grading.publish_summary.json",
    "formal_flow_summary.json",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir")
    parser.add_argument("--expect-sent", action="store_true")
    args = parser.parse_args()
    validate(Path(args.output_dir), expect_sent=args.expect_sent)
    print(f"Label-rate formal flow OK: {args.output_dir}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(output_dir: Path, *, expect_sent: bool) -> None:
    for relative in REQUIRED_FILES:
        if not (output_dir / relative).exists():
            raise AssertionError(f"Missing formal flow artifact: {relative}")

    notification_perception = load_json(output_dir / "perception_notification_request.json")
    analysis_perception = load_json(output_dir / "perception_analysis_request.json")
    query_plan = load_json(output_dir / "analysis_query_plan.json")
    analysis_summary = load_json(output_dir / "analysis_summary.json")
    summary = load_json(output_dir / "summary.json")
    hash_check = load_json(output_dir / "publish" / "card_hash_check.json")
    publish = load_json(output_dir / "publish" / "low_efficiency_grading.publish_summary.json")
    formal_summary = load_json(output_dir / "formal_flow_summary.json")

    assert_notification_perception(notification_perception)
    assert_analysis_perception(analysis_perception)
    assert_query_plan(query_plan)
    assert_analysis_summary(analysis_summary)
    assert_notification_summary(summary, hash_check, expect_sent=expect_sent)
    assert_formal_summary(formal_summary, analysis_summary)
    if expect_sent:
        assert_dispatch(output_dir, publish, formal_summary)


def assert_notification_perception(payload: dict[str, Any]) -> None:
    if payload.get("scenario_key") != "efficiency-label-rate":
        raise AssertionError("notification perception scenario mismatch.")
    workflow = payload.get("workflow_plan", {})
    if payload.get("task_type") == "low_label_rate_grading":
        if workflow.get("intent_type") != "analysis":
            raise AssertionError("analysis-only workflow_plan intent mismatch.")
        if workflow.get("next_action") != "analysis":
            raise AssertionError("analysis-only workflow_plan next_action mismatch.")
        return
    if payload.get("task_type") != "notification_request":
        raise AssertionError("notification perception task_type mismatch.")
    if workflow.get("intent_type") != "analysis_then_notification":
        raise AssertionError("workflow_plan must identify analysis_then_notification.")
    if workflow.get("next_action") != "run_analysis_prerequisite":
        raise AssertionError("workflow_plan next_action mismatch.")
    if workflow.get("requires_host_send_confirmation") is not True:
        raise AssertionError("workflow_plan must require host send confirmation.")
    prerequisites = workflow.get("prerequisites", [])
    if not any(item.get("skill") == "analysis" for item in prerequisites):
        raise AssertionError("workflow_plan must require analysis prerequisite.")


def assert_analysis_perception(payload: dict[str, Any]) -> None:
    if payload.get("scenario_key") != "efficiency-label-rate":
        raise AssertionError("analysis perception scenario mismatch.")
    if payload.get("task_type") != "low_label_rate_grading":
        raise AssertionError("analysis perception task mismatch.")
    if payload.get("readiness", {}).get("status") != "ready":
        raise AssertionError("analysis perception must be ready.")
    if payload.get("handoff", {}).get("next_skill") != "analysis":
        raise AssertionError("analysis perception must hand off to analysis.")


def assert_query_plan(query_plan: dict[str, Any]) -> None:
    if query_plan.get("scenario_key") != "efficiency-label-rate":
        raise AssertionError("QueryPlan scenario mismatch.")
    if query_plan.get("metric_id") not in {
        "label_rate",
        "report_label_rate",
        "combined_label_rate",
    }:
        raise AssertionError("QueryPlan metric mismatch.")
    if set(query_plan.get("levels", [])) != {"notice", "P2", "P1", "P0"}:
        raise AssertionError("QueryPlan levels mismatch.")
    if not query_plan.get("sql_by_level"):
        raise AssertionError("QueryPlan must include sql_by_level.")


def assert_analysis_summary(summary: dict[str, Any]) -> None:
    counts = summary.get("level_counts", {})
    if set(counts) != {"notice", "P2", "P1", "P0"}:
        raise AssertionError("analysis_summary level_counts mismatch.")
    if summary.get("row_count", 0) < max(counts.values()):
        raise AssertionError("analysis_summary row_count is inconsistent.")
    source_footer = summary.get("source_footer", {})
    if source_footer.get("metric_id") not in {
        "label_rate",
        "report_label_rate",
        "combined_label_rate",
    }:
        raise AssertionError("source_footer metric mismatch.")


def assert_notification_summary(
    summary: dict[str, Any],
    hash_check: dict[str, Any],
    *,
    expect_sent: bool,
) -> None:
    if expect_sent:
        if not summary.get("sheet_url"):
            raise AssertionError("formal flow summary requires sheet_url.")
        if summary.get("publish", {}).get("sent") is not True:
            raise AssertionError("summary publish.sent must be true.")
    if hash_check.get("ok") is not True:
        raise AssertionError("card hash check must pass.")


def assert_formal_summary(
    formal_summary: dict[str, Any],
    analysis_summary: dict[str, Any],
) -> None:
    if formal_summary.get("level_counts") != analysis_summary.get("level_counts"):
        raise AssertionError("formal summary level_counts mismatch.")
    if not formal_summary.get("stage1_result"):
        raise AssertionError("formal summary stage1_result missing.")
    if not formal_summary.get("stage2_output_dir"):
        raise AssertionError("formal summary stage2_output_dir missing.")


def assert_dispatch(
    output_dir: Path,
    publish: dict[str, Any],
    formal_summary: dict[str, Any],
) -> None:
    dispatch_path = output_dir / "host_dispatch_record.json"
    if not dispatch_path.exists():
        raise AssertionError("host_dispatch_record.json missing.")
    dispatch = load_json(dispatch_path)
    if dispatch.get("schema_version") != "formal_flow_host_dispatch.v1":
        raise AssertionError("host dispatch schema mismatch.")
    if dispatch.get("confirmed_by_user") is not True:
        raise AssertionError("host dispatch confirmation missing.")
    if dispatch.get("message_id") != publish.get("message_id"):
        raise AssertionError("host dispatch message_id mismatch.")
    if dispatch.get("message_id") != formal_summary.get("message_id"):
        raise AssertionError("formal summary message_id mismatch.")
    checks = dispatch.get("pre_send_checks", [])
    if not checks or any(item.get("status") != "pass" for item in checks):
        raise AssertionError(f"pre_send_checks failed: {checks}")
    if dispatch.get("online_write_executed") is not False:
        raise AssertionError("host dispatch must not write online state.")
    if not (output_dir / "lark_send_dry_run.txt").exists():
        raise AssertionError("lark dry-run record missing.")


if __name__ == "__main__":
    main()
