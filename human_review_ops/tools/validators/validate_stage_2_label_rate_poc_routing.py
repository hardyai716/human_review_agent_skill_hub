#!/usr/bin/env python3
"""Validate stage 2 label-rate POC routing artifacts."""

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
LEVEL_ORDER = ["notice", "P2", "P1", "P0"]
EXPECTED_RULES = {
    "notice": {
        "target_roles": ["群内同步策略明细和数据链接"],
        "action_required": "周知明细，纳入观察。",
    },
    "P2": {
        "target_roles": ["治理 BP", "审核 VOC POC", "人审运营"],
        "action_required": "请相关 POC 说明低打标原因和后续处理计划。",
    },
    "P1": {
        "target_roles": [
            "治理 BP",
            "审核 VOC POC",
            "人审运营",
            "治理 BP +1",
            "VOC 负责人",
            "人审运营负责人",
        ],
        "action_required": "要求负责人关注，并推动原因说明和处理计划。",
    },
    "P0": {
        "target_roles": [
            "治理 BP",
            "审核 VOC POC",
            "人审运营",
            "治理 BP +1",
            "VOC 负责人",
            "人审运营负责人",
            "治理负责人",
        ],
        "action_required": "高优先级周知，要求重点关注和处理。",
    },
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", nargs="?", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    validate(output_dir)
    print(f"Stage 2 label-rate POC routing OK: {output_dir}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(output_dir: Path) -> None:
    plan_path = output_dir / "poc_routing_plan.json"
    if not plan_path.exists():
        raise AssertionError("Missing artifact: poc_routing_plan.json")

    plan = load_json(plan_path)
    assert_plan_header(plan)
    assert_level_rules(plan)
    assert_no_group_send(plan)
    assert_no_online_write(plan)


def assert_plan_header(plan: dict[str, Any]) -> None:
    if plan.get("schema_version") != "stage_2_poc_routing_plan.v1":
        raise AssertionError("schema_version mismatch.")
    if plan.get("scenario_key") != "efficiency-label-rate":
        raise AssertionError("scenario_key mismatch.")
    if plan.get("report_type") != "low_efficiency_grading":
        raise AssertionError("report_type mismatch.")
    if plan.get("routing_mode") != "mach_root_label_mapping":
        raise AssertionError("routing_mode must be mach_root_label_mapping.")
    if plan.get("routing_key") != "mach_root_label_name":
        raise AssertionError("routing_key must be mach_root_label_name.")
    if plan.get("default_recipient") != "self":
        raise AssertionError("default_recipient must be self.")
    if plan.get("real_poc_mapping_used") is not True:
        raise AssertionError("real POC mapping must be used.")
    if plan.get("contact_resolution_status") != "name_only":
        raise AssertionError("contact_resolution_status must be name_only.")
    if not isinstance(plan.get("poc_summary"), list):
        raise AssertionError("poc_summary must be a list.")
    if plan.get("mapped_row_count", 0) + plan.get("unmapped_row_count", 0) + plan.get(
        "missing_route_dimension_count", 0
    ) != plan.get("comprehensive_strategy_group_count", plan.get("comprehensive_reason_count")):
        raise AssertionError("POC mapping counts must equal comprehensive group count.")
    assert_level_counts(plan)


def assert_level_counts(plan: dict[str, Any]) -> None:
    level_counts = plan.get("level_counts")
    if set(level_counts or {}) != set(LEVEL_ORDER):
        raise AssertionError("level_counts must contain notice/P2/P1/P0 only.")
    for level, count in level_counts.items():
        if not isinstance(count, int) or count < 0:
            raise AssertionError(f"{level} level_count must be a non-negative integer.")
    comprehensive_group_count = plan.get(
        "comprehensive_strategy_group_count",
        plan.get("comprehensive_reason_count"),
    )
    if not isinstance(comprehensive_group_count, int) or comprehensive_group_count < 0:
        raise AssertionError("comprehensive strategy group count must be non-negative.")
    if comprehensive_group_count > level_counts.get("notice", 0):
        raise AssertionError("comprehensive group count cannot exceed notice count.")


def assert_level_rules(plan: dict[str, Any]) -> None:
    routing_rules = plan.get("routing_rules")
    if set(routing_rules or {}) != set(LEVEL_ORDER):
        raise AssertionError("routing_rules must contain notice/P2/P1/P0 only.")
    for level in LEVEL_ORDER:
        actual = routing_rules[level]
        expected = EXPECTED_RULES[level]
        if actual.get("severity_level") != level:
            raise AssertionError(f"{level} severity_level mismatch.")
        if actual.get("target_roles") != expected["target_roles"]:
            raise AssertionError(f"{level} target_roles mismatch.")
        if actual.get("action_required") != expected["action_required"]:
            raise AssertionError(f"{level} action_required mismatch.")
        if actual.get("default_recipient") != "self":
            raise AssertionError(f"{level} default_recipient must be self.")
        if actual.get("requires_human_confirmation_before_real_send") is not True:
            raise AssertionError(f"{level} must require confirmation before real send.")
        resolution = actual.get("recipient_resolution", {})
        if resolution.get("mode") != "mach_root_label_mapping":
            raise AssertionError(f"{level} recipient resolution mode mismatch.")
        if resolution.get("routing_key") != "mach_root_label_name":
            raise AssertionError(f"{level} recipient routing_key mismatch.")
        if actual.get("reason_count") > 0 and resolution.get("real_poc_count", 0) <= 0:
            raise AssertionError(f"{level} must contain name-level POCs when rows exist.")
        if actual.get("reason_count") > 0 and not actual.get("poc_names"):
            raise AssertionError(f"{level} poc_names missing.")
        if actual.get("reason_count") != plan["level_counts"][level]:
            raise AssertionError(f"{level} reason_count mismatch.")
        if actual.get("strategy_group_count") != plan["level_counts"][level]:
            raise AssertionError(f"{level} strategy_group_count mismatch.")


def assert_no_group_send(plan: dict[str, Any]) -> None:
    constraints = plan.get("routing_constraints", {})
    if constraints.get("group_send_blocked") is not True:
        raise AssertionError("group_send_blocked must be true.")
    if constraints.get("group_send_allowed") is not False:
        raise AssertionError("group_send_allowed must be false.")
    if constraints.get("group_recipients") != []:
        raise AssertionError("group_recipients must be empty.")
    if constraints.get("real_notification_executed") is not False:
        raise AssertionError("real_notification_executed must be false.")
    for level, rule in plan.get("routing_rules", {}).items():
        if rule.get("group_send_blocked") is not True:
            raise AssertionError(f"{level} group_send_blocked must be true.")


def assert_no_online_write(plan: dict[str, Any]) -> None:
    constraints = plan.get("routing_constraints", {})
    if constraints.get("online_write_executed") is not False:
        raise AssertionError("online_write_executed must be false.")
    if constraints.get("online_state_write_allowed") is not False:
        raise AssertionError("online_state_write_allowed must be false.")
    for level, rule in plan.get("routing_rules", {}).items():
        if rule.get("online_write_executed") is not False:
            raise AssertionError(f"{level} online_write_executed must be false.")


if __name__ == "__main__":
    main()
