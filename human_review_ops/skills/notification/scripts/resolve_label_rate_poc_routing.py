#!/usr/bin/env python3
"""Resolve placeholder POC routing for label-rate grading results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


LEVEL_ORDER = ["notice", "P2", "P1", "P0"]
LEVEL_RULES: dict[str, dict[str, Any]] = {
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
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source_path = Path(args.source)
    output_path = Path(args.output)
    sample = load_stage_1_sample(source_path)
    plan = build_poc_routing_plan(sample, source_stage_1_result=str(source_path))
    write_json(output_path, plan)
    print(f"POC routing placeholder wrote {output_path}")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_stage_1_sample(path: Path) -> dict[str, Any]:
    records = load_jsonl(path)
    sample = next(
        (record for record in records if record.get("record_type") == "sample"),
        None,
    )
    if not sample:
        raise ValueError("Missing sample record in stage 1 results.")
    if sample.get("analysis_mode") != "low_label_rate_grading":
        raise ValueError("Stage 1 source must be low_label_rate_grading.")
    if "readonly_execution" not in sample:
        raise ValueError("Stage 1 source missing readonly_execution.")
    return sample


def build_poc_routing_plan(
    sample: dict[str, Any],
    *,
    source_stage_1_result: str,
) -> dict[str, Any]:
    execution = sample["readonly_execution"]
    level_results = execution.get("level_results", {})
    level_counts = execution.get("level_counts", {})
    routing_rules = {
        level: build_level_rule(level, level_results.get(level, {}))
        for level in LEVEL_ORDER
    }
    return {
        "schema_version": "stage_2_poc_routing_plan.v1",
        "scenario_key": "efficiency-label-rate",
        "report_type": "low_efficiency_grading",
        "source_stage_1_result": source_stage_1_result,
        "routing_mode": "placeholder",
        "fallback_to_default_user": True,
        "default_recipient": "self",
        "real_poc_mapping_used": False,
        "real_poc_mapping_source": None,
        "level_counts": {level: int(level_counts.get(level, 0)) for level in LEVEL_ORDER},
        "comprehensive_reason_count": int(execution.get("row_count", 0)),
        "routing_rules": routing_rules,
        "routing_constraints": {
            "group_send_blocked": True,
            "group_send_allowed": False,
            "group_recipients": [],
            "real_notification_executed": False,
            "online_write_executed": False,
            "online_state_write_allowed": False,
        },
        "provenance": {
            "source_footer": sample.get("source_footer", {}),
            "query_plan_id": sample.get("QueryPlan", {}).get("query_plan_id"),
            "readonly_execution_mode": True,
        },
    }


def build_level_rule(level: str, level_result: dict[str, Any]) -> dict[str, Any]:
    rule = LEVEL_RULES[level]
    rows = level_result.get("rows", [])
    return {
        "severity_level": level,
        "target_roles": rule["target_roles"],
        "action_required": rule["action_required"],
        "default_recipient": "self",
        "recipient_resolution": {
            "mode": "placeholder",
            "recipients": ["self"],
            "real_poc_count": 0,
            "fallback_reason": "real reason/strategy -> POC mapping is not available",
        },
        "requires_human_confirmation_before_real_send": True,
        "group_send_blocked": True,
        "online_write_executed": False,
        "reason_count": len(rows),
        "evidence_refs": [
            {
                "reason": row.get("reason"),
                "hit_rule_ids": row.get("hit_rule_ids"),
                "hit_conditions": row.get("hit_conditions"),
            }
            for row in rows[:5]
        ],
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
