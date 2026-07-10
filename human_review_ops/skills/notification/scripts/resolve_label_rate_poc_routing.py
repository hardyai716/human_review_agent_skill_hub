#!/usr/bin/env python3
"""Resolve POC routing for label-rate results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


LEVEL_ORDER = ["notice", "P2", "P1", "P0"]
SCENARIO_REFERENCE = "references/scenarios/efficiency-label-rate.md"
POC_MAPPING_ASSET = "assets/efficiency-label-rate/mach_root_label_poc_mapping.json"
DEFAULT_POC_MAPPING_PATH = (
    Path(__file__).resolve().parents[1]
    / "assets"
    / "efficiency-label-rate"
    / "mach_root_label_poc_mapping.json"
)
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
    print(f"POC routing wrote {output_path}")


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


def load_poc_mapping(path: Path | None = None) -> dict[str, Any]:
    mapping_path = path or DEFAULT_POC_MAPPING_PATH
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    if mapping.get("schema_version") != "label_rate_mach_root_label_poc_mapping.v1":
        raise ValueError("POC mapping schema_version mismatch.")
    if mapping.get("scenario_key") != "efficiency-label-rate":
        raise ValueError("POC mapping scenario_key mismatch.")
    return mapping


def poc_mapping_index(mapping: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for entry in mapping.get("entries", []):
        label = normalize_label(entry.get("mach_root_label_name"))
        if not label:
            continue
        index[label] = entry
    return index


def normalize_label(value: Any) -> str:
    return str(value or "").strip()


def row_mach_root_label(row: dict[str, Any]) -> str:
    return normalize_label(
        row.get("mach_root_label_name")
        or row.get("机审一级标签")
        or row.get("mach_root_label")
    )


def resolve_row_poc(
    row: dict[str, Any],
    mapping_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    label = row_mach_root_label(row)
    if not label:
        return {
            "mach_root_label_name": None,
            "poc_name": None,
            "poc_open_id": None,
            "mapping_status": "missing_route_dimension",
        }
    entry = mapping_index.get(label)
    if not entry:
        return {
            "mach_root_label_name": label,
            "poc_name": None,
            "poc_open_id": None,
            "mapping_status": "unmapped_label",
        }
    return {
        "mach_root_label_name": label,
        "poc_name": entry.get("poc_name"),
        "poc_open_id": entry.get("poc_open_id"),
        "mapping_status": "mapped_name_only"
        if not entry.get("poc_open_id")
        else "mapped_open_id",
    }


def build_custom_dimension_poc_routing_plan(
    rows: list[dict[str, Any]],
    *,
    source_result: str,
    sheet_url: str | None = None,
    mapping_path: Path | None = None,
) -> dict[str, Any]:
    mapping = load_poc_mapping(mapping_path)
    index = poc_mapping_index(mapping)
    assignments = [resolve_row_poc(row, index) | summarize_row(row) for row in rows]
    mapped = [item for item in assignments if item["mapping_status"].startswith("mapped_")]
    unmapped = [item for item in assignments if item["mapping_status"] == "unmapped_label"]
    missing = [
        item
        for item in assignments
        if item["mapping_status"] == "missing_route_dimension"
    ]
    return {
        "schema_version": "label_rate_mach_label_poc_routing_plan.v1",
        "scenario_key": "efficiency-label-rate",
        "report_type": "custom_label_rate_breakdown",
        "source_result": source_result,
        "source_sheet_url": sheet_url,
        "reference_docs": [SCENARIO_REFERENCE],
        "asset_refs": {
            "poc_mapping": POC_MAPPING_ASSET,
        },
        "routing_mode": "mach_root_label_mapping",
        "routing_key": "mach_root_label_name",
        "real_poc_mapping_used": bool(mapped),
        "real_poc_mapping_source": mapping.get("source"),
        "contact_resolution_status": mapping.get("contact_resolution_status", "name_only"),
        "row_count": len(rows),
        "mapped_row_count": len(mapped),
        "unmapped_row_count": len(unmapped),
        "missing_route_dimension_count": len(missing),
        "mapped_label_count": len({item["mach_root_label_name"] for item in mapped}),
        "unmapped_labels": sorted(
            {
                item["mach_root_label_name"]
                for item in unmapped
                if item.get("mach_root_label_name")
            }
        ),
        "poc_summary": build_poc_summary(mapped),
        "assignment_preview": assignments[:20],
        "routing_constraints": {
            "requires_contact_resolution_before_real_send": True,
            "requires_human_confirmation_before_real_send": True,
            "group_send_blocked": True,
            "group_send_allowed": False,
            "real_notification_executed": False,
            "online_write_executed": False,
            "online_state_write_allowed": False,
        },
        "limitations": [
            "当前映射仅到 POC 姓名，尚未解析飞书 open_id。",
            "真实触达前必须完成联系人解析、目标确认和发送门禁校验。",
        ],
    }


def summarize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "strategy_id": row.get("strategy_id"),
        "strategy_name": row.get("strategy_name"),
        "reason": row.get("reason"),
        "avg_review_done_cnt": row.get("avg_review_done_cnt"),
        "label_rate": row.get("label_rate"),
    }


def build_poc_summary(assignments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in assignments:
        poc_name = item.get("poc_name")
        if not poc_name:
            continue
        bucket = grouped.setdefault(
            poc_name,
            {
                "poc_name": poc_name,
                "poc_open_id": item.get("poc_open_id"),
                "mach_root_label_names": set(),
                "row_count": 0,
                "top_reasons": [],
            },
        )
        bucket["mach_root_label_names"].add(item.get("mach_root_label_name"))
        bucket["row_count"] += 1
        if len(bucket["top_reasons"]) < 5:
            bucket["top_reasons"].append(
                {
                    "reason": item.get("reason"),
                    "strategy_id": item.get("strategy_id"),
                    "avg_review_done_cnt": item.get("avg_review_done_cnt"),
                    "label_rate": item.get("label_rate"),
                }
            )
    result = []
    for bucket in grouped.values():
        result.append(
            {
                **bucket,
                "mach_root_label_names": sorted(
                    label for label in bucket["mach_root_label_names"] if label
                ),
            }
        )
    return sorted(result, key=lambda item: (-item["row_count"], item["poc_name"]))


def build_poc_routing_plan(
    sample: dict[str, Any],
    *,
    source_stage_1_result: str,
) -> dict[str, Any]:
    execution = sample["readonly_execution"]
    level_results = execution.get("level_results", {})
    level_counts = execution.get("level_counts", {})
    mapping = load_poc_mapping()
    index = poc_mapping_index(mapping)
    comprehensive_rows = execution.get("comprehensive_results", [])
    assignments = [
        resolve_row_poc(row, index)
        | summarize_row(row)
        | {
            "severity_level": row.get("severity_level"),
            "hit_rule_ids": row.get("hit_rule_ids"),
            "hit_conditions": row.get("hit_conditions"),
        }
        for row in comprehensive_rows
    ]
    mapped = [item for item in assignments if item["mapping_status"].startswith("mapped_")]
    unmapped = [item for item in assignments if item["mapping_status"] == "unmapped_label"]
    missing = [
        item
        for item in assignments
        if item["mapping_status"] == "missing_route_dimension"
    ]
    routing_rules = {
        level: build_level_rule(level, level_results.get(level, {}), index)
        for level in LEVEL_ORDER
    }
    return {
        "schema_version": "stage_2_poc_routing_plan.v1",
        "scenario_key": "efficiency-label-rate",
        "report_type": "low_efficiency_grading",
        "source_stage_1_result": source_stage_1_result,
        "reference_docs": [SCENARIO_REFERENCE],
        "asset_refs": {
            "poc_mapping": POC_MAPPING_ASSET,
        },
        "routing_mode": "mach_root_label_mapping",
        "routing_key": "mach_root_label_name",
        "fallback_to_default_user": bool(unmapped or missing),
        "default_recipient": "self",
        "real_poc_mapping_used": bool(mapped),
        "real_poc_mapping_source": mapping.get("source"),
        "contact_resolution_status": mapping.get("contact_resolution_status", "name_only"),
        "level_counts": {level: int(level_counts.get(level, 0)) for level in LEVEL_ORDER},
        "comprehensive_reason_count": int(execution.get("row_count", 0)),
        "comprehensive_strategy_group_count": int(execution.get("row_count", 0)),
        "mapped_row_count": len(mapped),
        "unmapped_row_count": len(unmapped),
        "missing_route_dimension_count": len(missing),
        "mapped_label_count": len({item["mach_root_label_name"] for item in mapped}),
        "unmapped_labels": sorted(
            {
                item["mach_root_label_name"]
                for item in unmapped
                if item.get("mach_root_label_name")
            }
        ),
        "poc_summary": build_poc_summary(mapped),
        "assignment_preview": assignments[:20],
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
            "reference_docs": [SCENARIO_REFERENCE],
            "asset_refs": {
                "poc_mapping": POC_MAPPING_ASSET,
            },
            "source_footer": sample.get("source_footer", {}),
            "query_plan_id": sample.get("QueryPlan", {}).get("query_plan_id"),
            "readonly_execution_mode": True,
        },
        "limitations": [
            "当前映射仅到 POC 姓名，尚未将 open_id 写入发布资产。",
            "真实触达前必须完成联系人歧义确认、目标群确认和发送门禁校验。",
        ],
    }


def build_level_rule(
    level: str,
    level_result: dict[str, Any],
    mapping_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rule = LEVEL_RULES[level]
    rows = level_result.get("rows", [])
    assignments = [
        resolve_row_poc(row, mapping_index)
        | summarize_row(row)
        | {
            "severity_level": level,
            "hit_rule_ids": row.get("hit_rule_ids"),
            "hit_conditions": row.get("hit_conditions"),
        }
        for row in rows
    ]
    mapped = [item for item in assignments if item["mapping_status"].startswith("mapped_")]
    unmapped = [item for item in assignments if item["mapping_status"] == "unmapped_label"]
    missing = [
        item
        for item in assignments
        if item["mapping_status"] == "missing_route_dimension"
    ]
    poc_names = sorted({item["poc_name"] for item in mapped if item.get("poc_name")})
    return {
        "severity_level": level,
        "target_roles": rule["target_roles"],
        "action_required": rule["action_required"],
        "default_recipient": "self",
        "recipient_resolution": {
            "mode": "mach_root_label_mapping",
            "routing_key": "mach_root_label_name",
            "recipients": poc_names,
            "contact_resolution_status": "name_only",
            "real_poc_count": len(poc_names),
            "mapped_row_count": len(mapped),
            "unmapped_row_count": len(unmapped),
            "missing_route_dimension_count": len(missing),
            "fallback_recipient": "self" if unmapped or missing else None,
        },
        "requires_human_confirmation_before_real_send": True,
        "group_send_blocked": True,
        "online_write_executed": False,
        "reason_count": len(rows),
        "strategy_group_count": len(rows),
        "poc_names": poc_names,
        "unmapped_labels": sorted(
            {
                item["mach_root_label_name"]
                for item in unmapped
                if item.get("mach_root_label_name")
            }
        ),
        "evidence_refs": [
            {
                "mach_root_label_name": row.get("mach_root_label_name"),
                "strategy_id": row.get("strategy_id"),
                "strategy_name": row.get("strategy_name"),
                "reason": row.get("reason"),
                "POC": row.get("POC") or row.get("poc_name"),
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
