#!/usr/bin/env python3
"""Validate label-rate mach-root-label POC mapping and optional routing plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ROOT_MAPPING = (
    ROOT
    / "references"
    / "scenarios"
    / "efficiency-label-rate"
    / "mach_root_label_poc_mapping.json"
)
SKILL_MAPPING = (
    ROOT
    / "skills"
    / "notification"
    / "assets"
    / "efficiency-label-rate"
    / "mach_root_label_poc_mapping.json"
)
DEFAULT_ROUTING_PLAN = (
    ROOT
    / "evals"
    / "efficiency-label-rate"
    / "stage_2_runs"
    / "20260709_custom_label_rate_breakdown_rerun_20260629_20260705"
    / "poc_routing_plan.json"
)
EXPECTED_MAPPING = {
    "国家安全": "杜衡",
    "领导人": "宋诗慧",
    "指令舆情相关": "张发奇",
    "偏激社会情绪和涉外言论": "张发奇",
    "党和国家形象负面": "齐思蕾",
    "举报": "韩晶晶",
    "不良行为或争议价值观": "陈雅静",
    "色情性化": "刘小楷",
    "高热": "闫秦河",
    "侵犯未成年权益": "张宇轩",
    "引人不适": "陈思乔",
    "短期策略迁移": "陈思乔",
    "危险行为": "陈雅静",
    "政媒": "杜衡",
    "违法违规": "叶健",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--routing-plan", default=str(DEFAULT_ROUTING_PLAN))
    parser.add_argument("--skip-routing-plan", action="store_true")
    args = parser.parse_args()

    root_mapping = load_json(ROOT_MAPPING)
    skill_mapping = load_json(SKILL_MAPPING)
    assert_mapping(root_mapping)
    if root_mapping != skill_mapping:
        raise AssertionError("Root mapping and notification Skill asset mapping must match.")

    routing_plan = Path(args.routing_plan)
    if not args.skip_routing_plan and routing_plan.exists():
        assert_routing_plan(load_json(routing_plan))
    elif not args.skip_routing_plan:
        raise AssertionError(f"Missing routing plan: {routing_plan}")

    print("Label-rate POC mapping OK")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_mapping(mapping: dict[str, Any]) -> None:
    if mapping.get("schema_version") != "label_rate_mach_root_label_poc_mapping.v1":
        raise AssertionError("mapping schema_version mismatch.")
    if mapping.get("scenario_key") != "efficiency-label-rate":
        raise AssertionError("mapping scenario_key mismatch.")
    if mapping.get("routing_key") != "mach_root_label_name":
        raise AssertionError("mapping routing_key mismatch.")
    if mapping.get("contact_resolution_status") != "name_only":
        raise AssertionError("mapping must be name_only before open_id resolution.")
    source = mapping.get("source", {})
    if source.get("url") != "https://bytedance.larkoffice.com/sheets/TpxwsA8zohUZkVtJ4J9cDcXUnbg?sheet=HKdm9w":
        raise AssertionError("mapping source URL mismatch.")

    entries = mapping.get("entries", [])
    actual = {entry.get("mach_root_label_name"): entry.get("poc_name") for entry in entries}
    if actual != EXPECTED_MAPPING:
        raise AssertionError(f"mapping entries mismatch: {actual}")
    for entry in entries:
        if entry.get("poc_open_id") is not None:
            raise AssertionError("poc_open_id must remain null until contact resolution is implemented.")


def assert_routing_plan(plan: dict[str, Any]) -> None:
    if plan.get("schema_version") != "label_rate_mach_label_poc_routing_plan.v1":
        raise AssertionError("routing plan schema_version mismatch.")
    if plan.get("routing_mode") != "mach_root_label_mapping":
        raise AssertionError("routing plan mode mismatch.")
    if plan.get("routing_key") != "mach_root_label_name":
        raise AssertionError("routing key mismatch.")
    if plan.get("real_poc_mapping_used") is not True:
        raise AssertionError("routing plan must use real name-level POC mapping.")
    if plan.get("contact_resolution_status") != "name_only":
        raise AssertionError("routing plan contact_resolution_status mismatch.")
    if plan.get("row_count", 0) <= 0:
        raise AssertionError("routing plan row_count must be positive.")
    if plan.get("mapped_row_count", 0) <= 0:
        raise AssertionError("routing plan mapped_row_count must be positive.")
    if plan.get("missing_route_dimension_count") != 0:
        raise AssertionError("custom breakdown rows must contain mach_root_label_name.")
    constraints = plan.get("routing_constraints", {})
    if constraints.get("requires_contact_resolution_before_real_send") is not True:
        raise AssertionError("contact resolution gate must be enabled.")
    if constraints.get("requires_human_confirmation_before_real_send") is not True:
        raise AssertionError("human confirmation gate must be enabled.")
    if constraints.get("group_send_blocked") is not True:
        raise AssertionError("group_send_blocked must remain true.")
    if constraints.get("real_notification_executed") is not False:
        raise AssertionError("routing plan must not execute notification.")
    if not plan.get("poc_summary"):
        raise AssertionError("poc_summary must be non-empty.")
    poc_names = {item.get("poc_name") for item in plan.get("poc_summary", [])}
    for name in ("杜衡", "宋诗慧", "张发奇", "陈雅静"):
        if name not in poc_names:
            raise AssertionError(f"Expected POC missing from summary: {name}")


if __name__ == "__main__":
    main()
