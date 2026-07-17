#!/usr/bin/env python3
"""Build validated local resolution tracking for label-rate artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LEVEL_ORDER = ["notice", "P2", "P1", "P0"]
SCENARIO_KEY = "efficiency-label-rate"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--notification-draft", required=True)
    parser.add_argument("--send-plan", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--state-machine-ref",
        default="references/scenarios/efficiency-label-rate.md#状态机",
    )
    parser.add_argument("--current-state", default="NOTIFICATION_DRAFTED")
    parser.add_argument("--manual-action")
    parser.add_argument("--manual-response")
    parser.add_argument("--resolution-note")
    parser.add_argument("--evidence-ref", action="append", default=[])
    parser.add_argument("--follow-up-due")
    parser.add_argument("--operator")
    parser.add_argument("--operator-confirmed", action="store_true")
    args = parser.parse_args()

    notification_draft_path = Path(args.notification_draft)
    send_plan_path = Path(args.send_plan)
    tracking = build_manual_tracking(
        notification_draft=load_json(notification_draft_path),
        send_plan=load_json(send_plan_path),
        state_machine_ref=args.state_machine_ref,
        current_state=args.current_state,
        manual_action=args.manual_action,
        manual_response=args.manual_response,
        resolution_note=args.resolution_note,
        evidence_refs=args.evidence_ref,
        follow_up_due=args.follow_up_due,
        operator=args.operator,
        operator_confirmation=args.operator_confirmed,
        source_paths={
            "notification_draft": str(notification_draft_path),
            "send_plan": str(send_plan_path),
        },
    )
    write_json(Path(args.output), tracking)
    print(f"Manual tracking wrote {args.output}")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def build_manual_tracking(
    *,
    notification_draft: dict[str, Any],
    send_plan: dict[str, Any],
    state_machine_ref: str,
    current_state: str = "NOTIFICATION_DRAFTED",
    manual_action: str | None = None,
    manual_response: str | None = None,
    resolution_note: str | None = None,
    evidence_refs: list[Any] | None = None,
    follow_up_due: str | None = None,
    operator: str | None = None,
    operator_confirmation: bool = False,
    source_paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    validate_inputs(notification_draft, send_plan, current_state)
    safety = build_safety(send_plan)
    routing_rules = notification_draft.get("poc_routing", {}).get("routing_rules", {})
    records = [
        build_tracking_record(level, routing_rules.get(level, {}))
        for level in LEVEL_ORDER
    ]
    collected_evidence = build_evidence_refs(
        notification_draft,
        records,
        evidence_refs or [],
    )
    closure_check = build_closure_check(
        manual_action=manual_action,
        manual_response=manual_response,
        resolution_note=resolution_note,
        evidence_refs=collected_evidence,
        operator_confirmation=operator_confirmation,
    )
    can_close = closure_check["can_close"]
    now = datetime.now(timezone.utc).isoformat()
    event_id = str(
        notification_draft.get("event_id")
        or notification_draft.get("source_stage_1_result")
        or "ELR-LOCAL-TRACKING"
    )
    source_refs = build_source_refs(
        notification_draft,
        send_plan,
        source_paths or {},
    )
    follow_up = build_follow_up(
        can_close=can_close,
        due=follow_up_due,
        operator=operator,
        missing=closure_check["missing_before_close"],
    )
    overall_status = "debug_closed" if can_close else "pending_manual_confirmation"
    manual_tracking = {
        "tracking_mode": "local_debug_only",
        "overall_status": overall_status,
        "tracking_records": records,
        "continue_observation": not can_close,
        "operator": operator,
        "manual_action": manual_action,
        "manual_response": manual_response,
        "resolution_note": resolution_note,
    }
    actions = [
        {
            "action_id": f"ACT-{event_id}",
            "action_type": "record",
            "executor": "human" if manual_action else "agent",
            "requires_confirmation": not operator_confirmation,
            "status": "done" if manual_action else "pending",
            "created_at": now,
            "result_summary": manual_action or "等待人工处理动作",
        }
    ]
    closure = {
        "action_completed": bool(manual_action),
        "evidence_confirmed": bool(collected_evidence),
        "conclusion_recorded": bool(resolution_note or manual_response),
        "root_cause": resolution_note or "",
        "impact_scope": str(notification_draft.get("level_counts") or {}),
        "final_conclusion": resolution_note or manual_response or "",
        "evidence_refs": [evidence_ref_label(item) for item in collected_evidence],
        "closed_by": operator or "",
        "closed_at": now if can_close else "",
    }
    return {
        "schema_version": "stage_2_manual_tracking.v1",
        "resolution_id": f"RES-{event_id}",
        "event_id": event_id,
        "scenario_key": SCENARIO_KEY,
        "report_type": "low_efficiency_grading",
        "tracking_mode": "local_debug_only",
        "manual_tracking": manual_tracking,
        "actions": actions,
        "state_machine": {
            "state_machine_ref": state_machine_ref,
            "previous_state": current_state,
            "current_state": "MANUAL_TRACKING_RECORDED",
            "next_state": "DEBUG_CLOSED" if can_close else "MANUAL_TRACKING_RECORDED",
        },
        "source_refs": source_refs,
        "overall_status": overall_status,
        "operator_note": (
            "闭环三件套已完成，可形成本地调试关闭建议。"
            if can_close
            else "当前仅记录本地人工处理状态，缺失项完成前保持继续观察。"
        ),
        "next_action": (
            "归档本地调试结论；线上关闭仍需外部审批。"
            if can_close
            else "补齐 closure_check.missing_before_close 后重新执行闭环检查。"
        ),
        "continue_observation": not can_close,
        "evidence_refs": collected_evidence,
        "tracking_records": records,
        "closure_check": closure_check,
        "closure": closure,
        "follow_up": follow_up,
        "plus1_status": notification_draft.get("plus1_status", "evidence_only"),
        "filtered_report_refs": {
            key: value
            for key, value in notification_draft.get("data_link", {})
            .get("csv_files", {})
            .items()
            if "exclude_pre_period_plus1" in key
        },
        "safety": safety,
    }


def validate_inputs(
    notification_draft: dict[str, Any],
    send_plan: dict[str, Any],
    current_state: str,
) -> None:
    if notification_draft.get("scenario_key") != SCENARIO_KEY:
        raise ValueError("notification_draft scenario_key mismatch.")
    if send_plan.get("scenario_key") != SCENARIO_KEY:
        raise ValueError("send_plan scenario_key mismatch.")
    if current_state not in {
        "ANALYSIS_READY",
        "OWNER_SUGGESTED",
        "NOTIFICATION_DRAFTED",
        "MANUAL_TRACKING_RECORDED",
        "HUMAN_REVIEW_REQUIRED",
    }:
        raise ValueError(f"Unsupported current_state: {current_state}")
    for field in (
        "requires_confirmation",
        "group_send_blocked",
        "sent",
        "real_group_send_executed",
        "online_write_executed",
    ):
        if not isinstance(send_plan.get(field), bool):
            raise ValueError(f"send_plan.{field} must be boolean.")
    if send_plan["group_send_blocked"] and send_plan["sent"]:
        raise ValueError("send_plan cannot be sent while group_send_blocked=true.")
    if send_plan["real_group_send_executed"] != send_plan["sent"]:
        raise ValueError("send_plan sent and real_group_send_executed must agree.")


def build_safety(send_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "requires_confirmation": send_plan["requires_confirmation"],
        "group_send_blocked": send_plan["group_send_blocked"],
        "group_send_sent": send_plan["sent"],
        "real_group_send_executed": send_plan["real_group_send_executed"],
        "online_write_executed": send_plan["online_write_executed"],
        "online_state_write_allowed": False,
    }


def build_closure_check(
    *,
    manual_action: str | None,
    manual_response: str | None,
    resolution_note: str | None,
    evidence_refs: list[dict[str, Any]],
    operator_confirmation: bool,
) -> dict[str, Any]:
    missing: list[str] = []
    if not manual_action:
        missing.append("manual_action")
    if not evidence_refs:
        missing.append("evidence_refs")
    if not (resolution_note or manual_response):
        missing.append("manual_response_or_resolution_note")
    if not operator_confirmation:
        missing.append("operator_confirmation")
    return {
        "can_close": not missing,
        "reason": (
            "action_evidence_conclusion_complete"
            if not missing
            else "closure_requirements_incomplete"
        ),
        "missing_before_close": missing,
    }


def build_follow_up(
    *,
    can_close: bool,
    due: str | None,
    operator: str | None,
    missing: list[str],
) -> dict[str, Any]:
    return {
        "needs_iteration": not can_close,
        "iteration_reasons": ["missing_evidence"] if missing else [],
        "abnormal_flags": ["needs_review"] if missing else [],
        "owner": operator or "人审运营",
        "next_review_owner": operator or "人审运营",
        "due": due,
        "next_review_deadline": due,
        "review_conditions": missing,
        "escalation_conditions": ["sla_timeout", "repeated_issue"],
    }


def build_tracking_record(level: str, rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "severity_level": level,
        "status": "pending_manual_follow_up",
        "reason_count": int(rule.get("reason_count", 0) or 0),
        "target_roles": rule.get("target_roles", []),
        "action_required": rule.get("action_required"),
        "recipient_resolution": rule.get("recipient_resolution", {}),
        "operator_note": "真实触达和线上状态仍由外部审批流程负责。",
        "next_action": "记录人工动作、证据和结论。",
        "continue_observation": True,
        "evidence_refs": list(rule.get("evidence_refs", [])),
    }


def build_source_refs(
    notification_draft: dict[str, Any],
    send_plan: dict[str, Any],
    source_paths: dict[str, str],
) -> dict[str, Any]:
    return {
        "notification_draft": source_paths.get("notification_draft")
        or send_plan.get("content_source", {}).get("notification_draft"),
        "send_plan": source_paths.get("send_plan"),
        "poc_routing_plan": notification_draft.get("poc_routing", {}).get(
            "poc_routing_plan"
        ),
        "card_json": send_plan.get("content_source", {}).get("card_json"),
        "card_hash_check": notification_draft.get("card_draft", {}).get(
            "card_hash_check"
        ),
        "sheet_url": notification_draft.get("data_link", {}).get("sheet_url"),
        "source_footer": notification_draft.get("methodology", {}).get(
            "source_footer"
        ),
    }


def build_evidence_refs(
    notification_draft: dict[str, Any],
    records: list[dict[str, Any]],
    explicit_refs: list[Any],
) -> list[dict[str, Any]]:
    evidence = [
        {
            "source": "notification_draft",
            "field": "level_counts",
            "value": notification_draft.get("level_counts"),
        },
        {
            "source": "notification_draft",
            "field": "methodology.source_footer",
            "value": notification_draft.get("methodology", {}).get("source_footer"),
        },
        {
            "source": "notification_draft",
            "field": "data_link",
            "value": notification_draft.get("data_link"),
        },
        {
            "source": "manual_tracking_records",
            "field": "covered_levels",
            "value": [record["severity_level"] for record in records],
        },
    ]
    for record in records:
        evidence.extend(record.get("evidence_refs", []))
    for value in explicit_refs:
        evidence.append({"source": "operator", "field": "evidence_ref", "value": value})
    return [item for item in evidence if item.get("value") not in (None, "", [], {})]


def evidence_ref_label(value: dict[str, Any]) -> str:
    return f"{value.get('source')}:{value.get('field')}"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
