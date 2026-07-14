#!/usr/bin/env python3
"""Single dry-run flow for the minimal scenario Skill template."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCENARIO_KEY = "scenario-key"
METRIC_ID = "METRIC_ID"


def dump(payload: Any, path: Path | None = None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def data_hash(payload: Any) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def perception(request: str) -> dict[str, Any]:
    blocked_terms = ["群发", "拉群", "直接发", "写状态", "关闭线上", "open_id", "手机号"]
    trigger_terms = ["SCENARIO_NAME", "METRIC_ID", "METRIC_NAME"]
    blocked = [term for term in blocked_terms if term in request]
    matched = [term for term in trigger_terms if term in request]
    if blocked:
        readiness = "blocked"
        next_stage = "stop"
        reasons = [f"external_side_effect_requested:{term}" for term in blocked]
    elif not matched:
        readiness = "needs_clarification"
        next_stage = "stop"
        reasons = ["scenario_not_unique"]
    else:
        readiness = "ready"
        next_stage = "analysis"
        reasons = []
    return {
        "scenario_key": SCENARIO_KEY if matched else None,
        "task_type": detect_task_type(request),
        "metric_ids": [METRIC_ID] if matched else [],
        "readiness": readiness,
        "blocking_reasons": reasons,
        "next_stage": next_stage,
    }


def detect_task_type(request: str) -> str:
    if any(term in request for term in ["通知", "Card", "card", "send_plan"]):
        return "notification_request"
    if any(term in request for term in ["闭环", "manual tracking", "复查", "处理状态"]):
        return "resolution_tracking"
    if any(term in request for term in ["P0", "P1", "P2", "notice", "撞线", "阈值", "分级"]):
        return "threshold_alert"
    if any(term in request for term in ["Top", "top", "排序", "排名", "清单"]):
        return "metric_ranking"
    if any(term in request for term in ["拆解", "维度", "按"]):
        return "dimension_breakdown"
    return "metric_trend"


def query_plan(task_type: str) -> dict[str, Any]:
    return {
        "query_plan_id": f"QP-{SCENARIO_KEY}-dry-run",
        "scenario_key": SCENARIO_KEY,
        "metric_id": METRIC_ID,
        "task_type": task_type,
        "time_range": {"current": "last_7_closed_partitions", "previous": "previous_7_closed_partitions"},
        "dimensions": ["dimension_a"],
        "filters": ["default_filters_from_scenario_contract"],
        "allowed_sources": ["semantic_layer", "governed_dataset", "controlled_readonly_sql"],
        "forbidden_sources": ["temporary_table", "deprecated_dataset", "sensitive_personal_detail", "write_api"],
        "quality_checks": ["partition_ready", "denominator_not_zero", "field_mapping_confirmed"],
        "review_required": False,
        "readonly_sql": "SELECT dimension_a, SUM(numerator) / NULLIF(SUM(denominator), 0) AS metric_value FROM DATASET_ID GROUP BY dimension_a",
    }


def analysis_records(task_type: str) -> list[dict[str, Any]]:
    plan = query_plan(task_type)
    source_footer = {
        "scenario_key": SCENARIO_KEY,
        "scenario_contract_ref": "references/scenario_contract.md#3-指标与数据",
        "analysis_ref": "references/scenario_contract.md#4-分析",
        "query_plan_id": plan["query_plan_id"],
        "run_mode": "debug_only",
        "limitations": ["dry_run_payload_not_business_fact"],
    }
    return [
        {
            "record_type": "environment",
            "scenario_key": SCENARIO_KEY,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "query_plan": plan,
        },
        {
            "record_type": "sample",
            "scenario_key": SCENARIO_KEY,
            "analysis_mode": task_type,
            "readonly_execution": {"mode": "dry_run", "executed": False, "row_count": 2},
            "analysis_result": {
                "metric_id": METRIC_ID,
                "level_counts": {"notice": 1, "P2": 1, "P1": 0, "P0": 0},
                "rows": [
                    {
                        "risk_level": "P2",
                        "object_key": "OBJECT_SAMPLE_001",
                        "object_name": "示例对象 001",
                        "owner_route_key": "DIMENSION_A_VALUE_SAMPLE",
                        "metric_value": 0.12,
                        "sample_size": 1200,
                        "hit_reason": "dry-run sample",
                    },
                    {
                        "risk_level": "notice",
                        "object_key": "OBJECT_SAMPLE_002",
                        "object_name": "示例对象 002",
                        "owner_route_key": "DIMENSION_A_VALUE_SAMPLE",
                        "metric_value": 0.18,
                        "sample_size": 800,
                        "hit_reason": "dry-run sample",
                    },
                ],
            },
            "source_footer": source_footer,
        },
    ]


def write_jsonl(records: list[dict[str, Any]], output: Path | None) -> None:
    text = "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def notify(source: Path, output_dir: Path) -> dict[str, str]:
    sample = next(record for record in load_jsonl(source) if record.get("record_type") == "sample")
    rows = sample["analysis_result"]["rows"]
    owner_map = load_json(ROOT / "assets" / "owner_mapping.template.json")
    route_by_key = {item["owner_route_key"]: item for item in owner_map.get("routes", [])}
    routing = {
        "scenario_key": SCENARIO_KEY,
        "mapped_owners": [
            {"object_key": row["object_key"], **route_by_key[row["owner_route_key"]]}
            for row in rows
            if row.get("owner_route_key") in route_by_key
        ],
        "unmapped_owners": [row for row in rows if row.get("owner_route_key") not in route_by_key],
        "requires_contact_resolution_before_real_send": True,
    }
    send_plan = {
        "send_mode": "preview_only",
        "requires_confirmation": True,
        "group_send_blocked": True,
        "sent": False,
        "real_group_send_executed": False,
        "online_write_executed": False,
    }
    draft = {
        "scenario_key": SCENARIO_KEY,
        "run_mode": "debug_only",
        "summary": sample["analysis_result"]["level_counts"],
        "evidence_rows": rows,
        "source_footer": sample["source_footer"],
    }
    card = load_json(ROOT / "assets" / "notification_card_template.json")
    card["card"]["data"] = {"summary": draft["summary"], "top_items": rows[:10], "source_footer": sample["source_footer"]}
    card["card"]["_meta"]["data_hash"] = data_hash(card["card"]["data"])
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "notification_draft": output_dir / "notification_draft.json",
        "poc_routing_plan": output_dir / "poc_routing_plan.json",
        "send_plan": output_dir / "send_plan.json",
        "card": output_dir / "card.json",
    }
    dump(draft, outputs["notification_draft"])
    dump(routing, outputs["poc_routing_plan"])
    dump(send_plan, outputs["send_plan"])
    dump(card, outputs["card"])
    return {key: str(value) for key, value in outputs.items()}


def track(notification_draft: Path, send_plan: Path, output: Path) -> dict[str, Any]:
    draft = load_json(notification_draft)
    plan = load_json(send_plan)
    missing = []
    if not plan.get("sent"):
        missing.append("real_send_or_user_confirmed_no_send")
    if plan.get("group_send_blocked", True):
        missing.append("group_send_confirmation")
    missing.extend(["manual_action", "resolution_note"])
    payload = {
        "scenario_key": draft.get("scenario_key", SCENARIO_KEY),
        "tracking_mode": "local_debug_only",
        "overall_status": "pending_manual_confirmation",
        "closure_check": {"can_close": False, "missing_before_close": missing},
        "safety": {
            "group_send_blocked": plan.get("group_send_blocked", True),
            "real_group_send_executed": plan.get("real_group_send_executed", False),
            "online_write_executed": plan.get("online_write_executed", False),
            "online_state_write_allowed": False,
        },
    }
    dump(payload, output)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("perception")
    p.add_argument("--request", required=True)
    a = sub.add_parser("analysis")
    a.add_argument("--task-type", default="metric_trend")
    a.add_argument("--output", type=Path)
    n = sub.add_parser("notify")
    n.add_argument("--source", type=Path, required=True)
    n.add_argument("--output-dir", type=Path, required=True)
    t = sub.add_parser("track")
    t.add_argument("--notification-draft", type=Path, required=True)
    t.add_argument("--send-plan", type=Path, required=True)
    t.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "perception":
        dump(perception(args.request))
    elif args.command == "analysis":
        write_jsonl(analysis_records(args.task_type), args.output)
    elif args.command == "notify":
        dump(notify(args.source, args.output_dir))
    elif args.command == "track":
        track(args.notification_draft, args.send_plan, args.output)


if __name__ == "__main__":
    main()
