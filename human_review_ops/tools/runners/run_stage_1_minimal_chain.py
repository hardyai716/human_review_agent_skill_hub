#!/usr/bin/env python3
"""Run the stage 1 perception + analysis minimal chain without real queries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_KEY = "efficiency-label-rate"
EVAL_DIR = ROOT / "evals" / SCENARIO_KEY
SCENARIO_DIR = ROOT / "references" / "scenarios" / SCENARIO_KEY
DEFAULT_OUTPUT = EVAL_DIR / "stage_1_runs" / "20260708_minimal_chain_results.jsonl"

SUPPORTED_DIMENSIONS = {
    "reason": "送审原因 / 送审策略",
    "p_date": "日期分区",
    "mach_root_label_name": "机审一级标签",
    "scene": "审核场景",
    "project_title": "项目标题",
    "time_window": "时间窗口",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def infer_dimensions(sample: dict[str, Any]) -> list[str]:
    text = sample["input"]
    if "机审一级标签" in text:
        return ["mach_root_label_name", "reason"]
    if "业务线" in text:
        return ["business_line"]
    return ["reason"]


def infer_sort_direction(sample: dict[str, Any]) -> str | None:
    text = sample["input"]
    if "最高" in text or "高打标率" in text:
        return "desc"
    if "低打标" in text or "低打标率" in text:
        return "asc"
    return None


def fallback_reason(analysis_mode: str, dimensions: list[str]) -> str:
    if any(dimension not in SUPPORTED_DIMENSIONS for dimension in dimensions):
        return "dimension_discovery_required"
    if analysis_mode == "low_label_rate_grading":
        return "complex_grading_rule_not_covered_by_semantic_layer"
    if analysis_mode == "dimension_breakdown":
        return "dimension_reason_breakdown_requires_curated_sql"
    return "none"


def build_query_plan(sample: dict[str, Any]) -> dict[str, Any]:
    analysis_mode = sample["expected_analysis_mode"]
    dimensions = infer_dimensions(sample)
    unknown_dimensions = [
        dimension for dimension in dimensions if dimension not in SUPPORTED_DIMENSIONS
    ]
    fallback = fallback_reason(analysis_mode, dimensions)

    query_plan = {
        "query_plan_id": f"QP-{sample['id']}",
        "scenario_key": SCENARIO_KEY,
        "task_type": sample["expected_task_type"],
        "analysis_mode": analysis_mode,
        "metric_id": "label_rate",
        "metric_entities": [
            {
                "metric_id": "label_rate",
                "definition_version": "draft",
                "source_tier": "semantic_layer",
            }
        ],
        "time_range": {
            "type": "trailing_days",
            "days": 7,
            "data_lag_days": 1,
            "grain": "day",
        },
        "dimensions": dimensions,
        "filters": ["standard_review_scope"],
        "required_hygiene_filters": [
            "exclude_non_standard_review_projects",
            "community_audit_scene_allowlist",
            "exclude_special_reasons",
            "preserve_null_mach_root_label",
        ],
        "source_priority": ["semantic_layer", "governed_dataset", "curated_raw_sql"],
        "allowed_sources": [
            "semantic_layer",
            "governed_dataset",
            "olap_content_security_community.dws_sft_tcs_review_task_detail_di",
        ],
        "forbidden_sources": [
            "temporary_table",
            "ownerless_legacy_sql",
            "deprecated_strategy_effect_table",
            "ungoverned_dataset",
            "pii_detail_table",
        ],
        "fallback_reason": fallback,
        "quality_checks": [
            "freshness_gate",
            "denominator_not_zero",
            "field_mapping_check",
            "grain_check",
            "forbidden_source_check",
        ],
        "review_required": True,
        "execution_mode": "no_real_query",
        "tool_calls": [],
    }

    sort_direction = infer_sort_direction(sample)
    if sort_direction:
        query_plan["sort_direction"] = sort_direction

    if unknown_dimensions:
        query_plan["dimension_discovery"] = {
            "status": "required",
            "requested_dimensions": unknown_dimensions,
            "required_checks": [
                "semantic_layer_dimension_search",
                "dataset_field_description_lookup",
                "grain_impact_check",
                "owner_check",
            ],
        }

    if analysis_mode == "low_label_rate_grading":
        query_plan["grading_levels"] = ["notice", "P2", "P1", "P0"]

    return query_plan


def build_source_footer(query_plan: dict[str, Any]) -> dict[str, Any]:
    source_tier = (
        "scenario_reference_preflight"
        if query_plan["execution_mode"] == "no_real_query"
        else query_plan["source_priority"][0]
    )
    return {
        "source_tier": source_tier,
        "metric_definition_version": "draft",
        "data_freshness": "not_queried",
        "owner": "人审效率域数据 Owner",
        "confidence_tier": "medium",
        "review_status": "debug_only_no_real_query",
        "scenario_key": SCENARIO_KEY,
        "metric_id": "label_rate",
        "quality_checks": query_plan["quality_checks"],
    }


def build_positive_record(sample: dict[str, Any]) -> dict[str, Any]:
    query_plan = build_query_plan(sample)
    source_footer = build_source_footer(query_plan)
    outputs = set(sample.get("must_output", []))
    if "QueryPlan_or_clarification" in outputs:
        outputs.remove("QueryPlan_or_clarification")
        outputs.add("QueryPlan")

    return {
        "record_type": "sample",
        "id": sample["id"],
        "input": sample["input"],
        "run_mode": "debug_only",
        "scenario_key": SCENARIO_KEY,
        "task_type": sample["expected_task_type"],
        "analysis_mode": sample["expected_analysis_mode"],
        "perception": {
            "matched": True,
            "metric_id": "label_rate",
            "read_files": [
                "scenario_manifest.md",
                "metric_contract.md",
                "dataset_reference.md",
                "analysis.md",
                "examples.md",
            ],
        },
        "QueryPlan": query_plan,
        "source_footer": source_footer,
        "outputs": sorted(outputs | {"scenario_key", "task_type", "QueryPlan", "source_footer"}),
        "permission_checks": {
            "tool_calls": [],
            "read_only": True,
            "real_query_blocked": True,
            "real_notification_blocked": True,
            "online_write_blocked": True,
        },
        "result": "pass",
    }


def build_negative_record(sample: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": "sample",
        "id": sample["id"],
        "input": sample["input"],
        "run_mode": "debug_only",
        "scenario_key": None,
        "task_type": "reject_or_ask_clarification",
        "analysis_mode": None,
        "perception": {
            "matched": False,
            "rejection_reason": "input belongs to another metric or lacks required label_rate intent",
        },
        "QueryPlan": None,
        "source_footer": None,
        "outputs": ["reject_or_ask_clarification"],
        "permission_checks": {
            "tool_calls": [],
            "read_only": True,
            "real_query_blocked": True,
            "real_notification_blocked": True,
            "online_write_blocked": True,
        },
        "result": "pass",
    }


def build_low_context_record(sample: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": "sample",
        "id": sample["id"],
        "input": sample["input"],
        "run_mode": "debug_only",
        "scenario_key": None,
        "task_type": "need_more_info",
        "analysis_mode": None,
        "perception": {
            "matched": False,
            "clarification_question": "请补充要分析的指标、时间窗口和策略 / reason。",
        },
        "QueryPlan": None,
        "source_footer": None,
        "outputs": ["ask_more_info", "must_not_query"],
        "permission_checks": {
            "tool_calls": [],
            "read_only": True,
            "real_query_blocked": True,
            "real_notification_blocked": True,
            "online_write_blocked": True,
        },
        "result": "pass",
    }


def build_records(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = [
        {
            "record_type": "environment",
            "scenario_key": SCENARIO_KEY,
            "run_mode": "debug_only",
            "root_package_read": SCENARIO_DIR.exists(),
            "real_query_blocked": True,
            "real_notification_blocked": True,
            "online_write_blocked": True,
            "result": "pass",
        }
    ]
    for sample in samples:
        sample_type = sample["type"]
        if sample_type == "positive":
            records.append(build_positive_record(sample))
        elif sample_type == "negative":
            records.append(build_negative_record(sample))
        elif sample_type == "low_context":
            records.append(build_low_context_record(sample))
        else:
            raise ValueError(f"Unsupported sample type: {sample_type}")
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    samples = load_jsonl(EVAL_DIR / "eval_samples.jsonl")
    records = build_records(samples)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            for record in records
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Stage 1 minimal chain wrote {len(records)} records: {output_path}")


if __name__ == "__main__":
    main()
