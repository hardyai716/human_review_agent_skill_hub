#!/usr/bin/env python3
"""Build local manual tracking records for label-rate stage 2 outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


LEVEL_ORDER = ["notice", "P2", "P1", "P0"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--notification-draft", required=True)
    parser.add_argument("--send-plan", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--state-machine-ref",
        default="human_review_ops/references/scenarios/efficiency-label-rate/state_machine.md",
    )
    args = parser.parse_args()

    notification_draft = load_json(Path(args.notification_draft))
    send_plan = load_json(Path(args.send_plan))
    tracking = build_manual_tracking(
        notification_draft=notification_draft,
        send_plan=send_plan,
        state_machine_ref=args.state_machine_ref,
    )
    write_json(Path(args.output), tracking)
    print(f"Manual tracking wrote {args.output}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_manual_tracking(
    *,
    notification_draft: dict[str, Any],
    send_plan: dict[str, Any],
    state_machine_ref: str,
) -> dict[str, Any]:
    routing_rules = notification_draft.get("poc_routing", {}).get("routing_rules", {})
    records = [
        build_tracking_record(level, routing_rules.get(level, {}))
        for level in LEVEL_ORDER
    ]
    return {
        "schema_version": "stage_2_manual_tracking.v1",
        "scenario_key": "efficiency-label-rate",
        "report_type": "low_efficiency_grading",
        "tracking_mode": "local_debug_only",
        "state_machine": {
            "state_machine_ref": state_machine_ref,
            "previous_state": "NOTIFICATION_DRAFTED",
            "current_state": "MANUAL_TRACKING_RECORDED",
            "next_state": "DEBUG_CLOSED_AFTER_MANUAL_REVIEW",
        },
        "source_refs": {
            "notification_draft": send_plan.get("content_source", {}).get(
                "notification_draft"
            ),
            "send_plan": "send_plan.json",
            "poc_routing_plan": notification_draft.get("poc_routing", {}).get(
                "poc_routing_plan"
            ),
            "card_json": send_plan.get("content_source", {}).get("card_json"),
            "sheet_url": notification_draft.get("data_link", {}).get("sheet_url"),
        },
        "overall_status": "pending_manual_confirmation",
        "operator_note": (
            "开发验证阶段仅记录本地人工处理状态；真实 POC 映射、群推送和线上状态写入均未启用。"
        ),
        "next_action": (
            "补充真实 reason/strategy -> POC 映射后，由人工确认是否执行群推送或继续观察。"
        ),
        "continue_observation": True,
        "evidence_refs": build_evidence_refs(notification_draft, records),
        "tracking_records": records,
        "closure_check": {
            "can_close": False,
            "reason": "Stage 2 uses placeholder routing and still requires manual confirmation.",
            "missing_before_close": [
                "real_poc_mapping",
                "human_confirmation",
                "manual_response_or_resolution_note",
            ],
        },
        "safety": {
            "requires_confirmation": send_plan.get("requires_confirmation", True),
            "group_send_blocked": send_plan.get("group_send_blocked", True),
            "group_send_sent": send_plan.get("sent", False),
            "real_group_send_executed": send_plan.get(
                "real_group_send_executed", False
            ),
            "online_write_executed": False,
            "online_state_write_allowed": False,
        },
    }


def build_tracking_record(level: str, rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "severity_level": level,
        "status": "pending_manual_follow_up",
        "reason_count": int(rule.get("reason_count", 0)),
        "target_roles": rule.get("target_roles", []),
        "action_required": rule.get("action_required"),
        "recipient_resolution": rule.get("recipient_resolution", {}),
        "operator_note": "当前 POC 解析为占位逻辑，默认仅本人预览。",
        "next_action": "等待真实 POC 映射和人工确认。",
        "continue_observation": True,
        "evidence_refs": [
            {
                "source": "poc_routing_rule",
                "severity_level": level,
                "field": field,
                "value": rule.get(field),
            }
            for field in ("target_roles", "action_required", "reason_count")
        ],
    }


def build_evidence_refs(
    notification_draft: dict[str, Any],
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "source": "notification_draft",
            "field": "level_counts",
            "value": notification_draft.get("level_counts"),
        },
        {
            "source": "notification_draft",
            "field": "data_link.sheet_url",
            "value": notification_draft.get("data_link", {}).get("sheet_url"),
        },
        {
            "source": "manual_tracking_records",
            "field": "covered_levels",
            "value": [record["severity_level"] for record in records],
        },
    ]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
