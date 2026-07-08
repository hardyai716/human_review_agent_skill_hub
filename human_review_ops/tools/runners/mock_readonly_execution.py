"""Mock readonly execution fixtures for stage 1 analysis results.

The fixtures model the shape of readonly query outputs without connecting to
Semantic Layer, Aeolus, Hive, ClickHouse, or any online system.
"""

from __future__ import annotations

from typing import Any


EXECUTION_MODE = "mock_readonly_execution"
TOOL_EXECUTION_MODE = "mock_readonly_no_real_query"
SCENARIO_KEY = "efficiency-label-rate"
GENERATED_AT = "2026-07-08T00:00:00+08:00"
METRIC_CONTRACT_PATH = (
    "human_review_ops/references/scenarios/efficiency-label-rate/metric_contract.md"
)
DATASET_REFERENCE_PATH = (
    "human_review_ops/references/scenarios/efficiency-label-rate/dataset_reference.md"
)
ANALYSIS_RULE_PATH = (
    "human_review_ops/references/scenarios/efficiency-label-rate/analysis.md"
)
METRIC_FORMULA = "SUM(label_cnt) / SUM(review_done_cnt)"


def attach_readonly_execution(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach mock readonly execution, analysis_result, and provenance."""

    enriched_records: list[dict[str, Any]] = []
    for record in records:
        enriched_record = dict(record)

        if enriched_record.get("record_type") == "environment":
            enriched_record["execution_mode"] = EXECUTION_MODE
            enriched_record["analysis_result_contract"] = "readonly_execution_with_provenance"
            enriched_record["real_query_executed"] = False
            enriched_records.append(enriched_record)
            continue

        query_plan = enriched_record.get("QueryPlan")
        if not isinstance(query_plan, dict):
            enriched_record["readonly_execution"] = None
            enriched_record["analysis_result"] = None
            enriched_record["provenance"] = None
            enriched_records.append(enriched_record)
            continue

        readonly_execution = _build_readonly_execution(query_plan)
        execution_tool_call = _build_execution_tool_call(query_plan, readonly_execution)
        tool_call_records = list(enriched_record.get("tool_call_records", []))
        tool_call_records.append(execution_tool_call)
        tool_call_ids = [tool_call_record["tool_call_id"] for tool_call_record in tool_call_records]

        query_plan = dict(query_plan)
        query_plan["tool_calls"] = tool_call_ids

        source_footer = _build_source_footer(query_plan, readonly_execution)
        provenance = _build_provenance(query_plan, readonly_execution, tool_call_ids)
        analysis_result = _build_analysis_result(
            record=enriched_record,
            query_plan=query_plan,
            readonly_execution=readonly_execution,
            source_footer=source_footer,
            provenance=provenance,
        )

        permission_checks = dict(enriched_record.get("permission_checks", {}))
        permission_checks.update(
            {
                "tool_calls": tool_call_ids,
                "tool_call_record_count": len(tool_call_ids),
                "execution_mode": EXECUTION_MODE,
                "mock_readonly_execution_only": True,
                "real_query_executed": False,
                "real_query_blocked": True,
                "real_notification_blocked": True,
                "online_write_blocked": True,
            }
        )

        enriched_record["QueryPlan"] = query_plan
        enriched_record["tool_call_records"] = tool_call_records
        enriched_record["readonly_execution"] = readonly_execution
        enriched_record["analysis_result"] = analysis_result
        enriched_record["provenance"] = provenance
        enriched_record["source_footer"] = source_footer
        enriched_record["permission_checks"] = permission_checks
        enriched_record["outputs"] = sorted(
            set(enriched_record.get("outputs", []))
            | {"analysis_result", "provenance", "readonly_execution"}
        )
        enriched_records.append(enriched_record)

    return enriched_records


def _build_readonly_execution(query_plan: dict[str, Any]) -> dict[str, Any]:
    analysis_mode = query_plan["analysis_mode"]
    if analysis_mode == "dimension_discovery":
        return _dimension_discovery_block(query_plan)

    rows = _fixture_rows(query_plan)
    return {
        "execution_id": f"ROE-{query_plan['query_plan_id']}",
        "execution_mode": EXECUTION_MODE,
        "status": "success",
        "source_tier": _execution_source_tier(query_plan),
        "source_name": _execution_source_name(query_plan),
        "data_freshness": "mock_fixture_not_real_data",
        "row_count": len(rows),
        "columns": _columns_for(query_plan),
        "rows": rows,
        "evidence_fields": [
            "review_done_cnt",
            "label_cnt",
            "label_rate",
            "time_window",
        ],
        "metric_formula": METRIC_FORMULA,
        "quality_checks": _quality_checks("success"),
        "limitations": [
            "mock fixture only, not real online data",
            "used for validating analysis_result and provenance shape",
        ],
    }


def _dimension_discovery_block(query_plan: dict[str, Any]) -> dict[str, Any]:
    requested = query_plan.get("dimension_discovery", {}).get("requested_dimensions", [])
    return {
        "execution_id": f"ROE-{query_plan['query_plan_id']}",
        "execution_mode": EXECUTION_MODE,
        "status": "blocked",
        "block_reason": "dimension_discovery_required",
        "source_tier": "governed_dataset",
        "source_name": "mock_governed_dataset_catalog",
        "data_freshness": "not_queried_dimension_discovery_required",
        "row_count": 0,
        "columns": [],
        "rows": [],
        "evidence_fields": [],
        "metric_formula": METRIC_FORMULA,
        "quality_checks": _quality_checks("blocked"),
        "required_followups": [
            f"confirm dimension metadata: {', '.join(requested) or 'unknown'}",
            "confirm grain impact",
            "confirm owner and permission",
        ],
        "limitations": [
            "unsupported dimension cannot be queried until metadata is confirmed",
        ],
    }


def _fixture_rows(query_plan: dict[str, Any]) -> list[dict[str, Any]]:
    analysis_mode = query_plan["analysis_mode"]
    sort_direction = query_plan.get("sort_direction")

    if analysis_mode == "label_rate_trend":
        return [
            _rate_row("2026-07-01", "all_reason", 12800, 930),
            _rate_row("2026-07-02", "all_reason", 13120, 1010),
            _rate_row("2026-07-03", "all_reason", 12760, 880),
            _rate_row("2026-07-04", "all_reason", 12490, 910),
            _rate_row("2026-07-05", "all_reason", 11980, 780),
            _rate_row("2026-07-06", "all_reason", 13040, 960),
            _rate_row("2026-07-07", "all_reason", 12950, 940),
        ]

    if analysis_mode == "label_rate_ranking" and sort_direction == "desc":
        return [
            _rate_row("2026-07-01..2026-07-07", "reason_high_01", 1860, 690),
            _rate_row("2026-07-01..2026-07-07", "reason_high_02", 2140, 690),
            _rate_row("2026-07-01..2026-07-07", "reason_high_03", 1790, 510),
        ]

    if analysis_mode == "label_rate_ranking":
        return [
            _rate_row("2026-07-01..2026-07-07", "reason_low_01", 8230, 96),
            _rate_row("2026-07-01..2026-07-07", "reason_low_02", 6420, 101),
            _rate_row("2026-07-01..2026-07-07", "reason_low_03", 5900, 121),
        ]

    if analysis_mode == "low_label_rate_grading":
        return [
            _graded_row("P1", "reason_low_01", 1176, 14, "single_week_high_volume_low_rate"),
            _graded_row("P2", "reason_low_02", 917, 14, "single_strategy_low_rate"),
            _graded_row("notice", "reason_low_03", 843, 17, "label_rate_below_10_percent"),
        ]

    if analysis_mode == "dimension_breakdown":
        return [
            _dimension_row("危险行为", "reason_low_01", 3520, 52),
            _dimension_row("违法违规", "reason_low_02", 2860, 49),
            _dimension_row("（空/机审一级标签）", "reason_low_03", 1980, 46),
        ]

    return []


def _rate_row(time_window: str, reason: str, review_done_cnt: int, label_cnt: int) -> dict[str, Any]:
    return {
        "time_window": time_window,
        "reason": reason,
        "review_done_cnt": review_done_cnt,
        "label_cnt": label_cnt,
        "label_rate": round(label_cnt / review_done_cnt, 4),
    }


def _graded_row(
    severity_level: str,
    reason: str,
    daily_review_done_cnt: int,
    daily_label_cnt: int,
    matched_rule: str,
) -> dict[str, Any]:
    return {
        "time_window": "2026-07-01..2026-07-07",
        "severity_level": severity_level,
        "reason": reason,
        "daily_review_done_cnt": daily_review_done_cnt,
        "daily_label_cnt": daily_label_cnt,
        "label_rate": round(daily_label_cnt / daily_review_done_cnt, 4),
        "matched_rule": matched_rule,
    }


def _dimension_row(
    mach_root_label_name: str,
    reason: str,
    review_done_cnt: int,
    label_cnt: int,
) -> dict[str, Any]:
    return {
        "time_window": "2026-07-01..2026-07-07",
        "mach_root_label_name": mach_root_label_name,
        "reason": reason,
        "review_done_cnt": review_done_cnt,
        "label_cnt": label_cnt,
        "label_rate": round(label_cnt / review_done_cnt, 4),
    }


def _columns_for(query_plan: dict[str, Any]) -> list[str]:
    analysis_mode = query_plan["analysis_mode"]
    if analysis_mode == "low_label_rate_grading":
        return [
            "time_window",
            "severity_level",
            "reason",
            "daily_review_done_cnt",
            "daily_label_cnt",
            "label_rate",
            "matched_rule",
        ]
    if analysis_mode == "dimension_breakdown":
        return [
            "time_window",
            "mach_root_label_name",
            "reason",
            "review_done_cnt",
            "label_cnt",
            "label_rate",
        ]
    return ["time_window", "reason", "review_done_cnt", "label_cnt", "label_rate"]


def _quality_checks(status: str) -> dict[str, str]:
    if status == "blocked":
        return {
            "freshness_gate": "not_run",
            "denominator_not_zero": "not_run",
            "field_mapping_check": "blocked",
            "grain_check": "blocked",
            "forbidden_source_check": "passed",
        }
    return {
        "freshness_gate": "mock_passed",
        "denominator_not_zero": "passed",
        "field_mapping_check": "mock_passed",
        "grain_check": "mock_passed",
        "forbidden_source_check": "passed",
    }


def _execution_source_tier(query_plan: dict[str, Any]) -> str:
    if query_plan["fallback_reason"] in {
        "complex_grading_rule_not_covered_by_semantic_layer",
        "dimension_reason_breakdown_requires_curated_sql",
    }:
        return "curated_raw_sql"
    return "semantic_layer"


def _execution_source_name(query_plan: dict[str, Any]) -> str:
    if _execution_source_tier(query_plan) == "curated_raw_sql":
        return "mock_fixture:olap_content_security_community.dws_sft_tcs_review_task_detail_di"
    return "mock_fixture:semantic_layer.label_rate"


def _build_execution_tool_call(
    query_plan: dict[str, Any],
    readonly_execution: dict[str, Any],
) -> dict[str, Any]:
    status = "success" if readonly_execution["status"] == "success" else "blocked"
    record = {
        "tool_call_id": f"TCR-{query_plan['query_plan_id']}-99",
        "caller": "analyzing-ops-metrics",
        "tool_name": "mock_readonly_result_fixture",
        "command_name": "execute_mock_readonly_analysis",
        "permission_level": "readonly",
        "source_tier": readonly_execution["source_tier"],
        "scenario_key": SCENARIO_KEY,
        "metric_id": query_plan["metric_id"],
        "review_required": query_plan["review_required"],
        "fallback_reason": query_plan["fallback_reason"],
        "execution_mode": TOOL_EXECUTION_MODE,
        "real_query_executed": False,
        "input_summary": (
            f"Build mock readonly result for {query_plan['query_plan_id']} "
            f"analysis_mode={query_plan['analysis_mode']}."
        ),
        "output_summary": (
            f"Mock readonly execution status={readonly_execution['status']}, "
            f"row_count={readonly_execution['row_count']}. No real query executed."
        ),
        "status": status,
        "latency_ms": 0,
    }
    if status == "blocked":
        record["error_reason"] = readonly_execution.get("block_reason", "blocked")
    return record


def _build_source_footer(
    query_plan: dict[str, Any],
    readonly_execution: dict[str, Any],
) -> dict[str, Any]:
    confidence_tier = "medium" if readonly_execution["status"] == "success" else "low"
    review_status = (
        "debug_only_mock_readonly_execution"
        if readonly_execution["status"] == "success"
        else "debug_only_execution_blocked"
    )
    return {
        "source_tier": readonly_execution["source_tier"],
        "metric_definition_version": "draft",
        "data_freshness": readonly_execution["data_freshness"],
        "owner": "人审效率域数据 Owner",
        "confidence_tier": confidence_tier,
        "review_status": review_status,
        "scenario_key": SCENARIO_KEY,
        "metric_id": query_plan["metric_id"],
        "quality_checks": query_plan["quality_checks"],
    }


def _build_provenance(
    query_plan: dict[str, Any],
    readonly_execution: dict[str, Any],
    tool_call_ids: list[str],
) -> dict[str, Any]:
    return {
        "provenance_id": f"PROV-{query_plan['query_plan_id']}",
        "scenario_key": SCENARIO_KEY,
        "query_plan_id": query_plan["query_plan_id"],
        "execution_id": readonly_execution["execution_id"],
        "execution_mode": EXECUTION_MODE,
        "generated_at": GENERATED_AT,
        "source_tier": readonly_execution["source_tier"],
        "source_name": readonly_execution["source_name"],
        "metric_id": query_plan["metric_id"],
        "metric_formula": METRIC_FORMULA,
        "time_range": query_plan["time_range"],
        "dimensions": query_plan["dimensions"],
        "filters": query_plan["filters"],
        "required_hygiene_filters": query_plan.get("required_hygiene_filters", []),
        "quality_checks": readonly_execution["quality_checks"],
        "tool_call_ids": tool_call_ids,
        "references": {
            "metric_contract": METRIC_CONTRACT_PATH,
            "dataset_reference": DATASET_REFERENCE_PATH,
            "analysis_rule": ANALYSIS_RULE_PATH,
        },
        "limitations": readonly_execution["limitations"],
    }


def _build_analysis_result(
    *,
    record: dict[str, Any],
    query_plan: dict[str, Any],
    readonly_execution: dict[str, Any],
    source_footer: dict[str, Any],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    status = readonly_execution["status"]
    return {
        "analysis_id": f"AN-{record['id']}",
        "event_id": record["id"],
        "templates_used": ["custom_readonly", "impact_assessment", "sop_decision"],
        "query_plan": _compact_query_plan(query_plan),
        "readonly_execution": readonly_execution,
        "impact_assessment": _impact_assessment(query_plan, readonly_execution),
        "root_cause_hypotheses": _root_cause_hypotheses(query_plan, readonly_execution),
        "sop_decision": _sop_decision(query_plan, readonly_execution),
        "quality_checks": {
            "evidence_complete": status == "success",
            "data_fresh": False,
            "metric_definition_consistent": True,
            "owner_resolved": True,
            "confidence": 0.66 if status == "success" else 0.35,
            "warnings": readonly_execution["limitations"],
        },
        "source_footer": source_footer,
        "provenance": provenance,
    }


def _compact_query_plan(query_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "query_plan_id": query_plan["query_plan_id"],
        "metric_entities": query_plan["metric_entities"],
        "dimensions": query_plan["dimensions"],
        "time_range": query_plan["time_range"],
        "filters": query_plan["filters"],
        "tool_calls": query_plan["tool_calls"],
        "allowed_sources": query_plan["allowed_sources"],
        "forbidden_sources": query_plan["forbidden_sources"],
        "quality_checks": query_plan["quality_checks"],
    }


def _impact_assessment(
    query_plan: dict[str, Any],
    readonly_execution: dict[str, Any],
) -> dict[str, Any]:
    if readonly_execution["status"] != "success":
        return {
            "summary": "无法执行打标率查询：存在未确认扩展维度。",
            "impact_scope": "dimension_discovery_required",
            "risk_level": "unknown",
            "business_risk": "字段含义、粒度和 Owner 未确认，不能输出业务结论。",
            "duration": "not_queried",
            "evidence_refs": [readonly_execution["execution_id"]],
        }

    return {
        "summary": f"已基于 mock 只读结果生成 {query_plan['analysis_mode']} 分析结构。",
        "impact_scope": "mock_fixture_scope",
        "risk_level": _risk_level(query_plan),
        "business_risk": "当前为 mock 结果，只验证分析结构和依据链路，不代表真实业务风险。",
        "duration": "2026-07-01..2026-07-07",
        "evidence_refs": [readonly_execution["execution_id"]],
    }


def _root_cause_hypotheses(
    query_plan: dict[str, Any],
    readonly_execution: dict[str, Any],
) -> list[dict[str, Any]]:
    if readonly_execution["status"] != "success":
        return [
            {
                "hypothesis": "requested_dimension_not_confirmed",
                "confidence": 0.75,
                "supporting_evidence": [readonly_execution["execution_id"]],
                "contradicting_evidence": [],
                "next_check": "run semantic layer dimension discovery before querying",
            }
        ]

    return [
        {
            "hypothesis": f"mock_{query_plan['analysis_mode']}_pattern",
            "confidence": 0.45,
            "supporting_evidence": [readonly_execution["execution_id"]],
            "contradicting_evidence": [
                "mock fixture is not real production data",
            ],
            "next_check": "replace mock fixture with approved readonly data tool",
        }
    ]


def _sop_decision(
    query_plan: dict[str, Any],
    readonly_execution: dict[str, Any],
) -> dict[str, Any]:
    if readonly_execution["status"] != "success":
        return {
            "severity_level": "P3",
            "next_action": "ask_more",
            "required_confirmation": True,
            "matched_rules": ["dimension_discovery_required"],
            "reason": "扩展维度未确认，需先完成字段发现。",
        }

    return {
        "severity_level": _risk_level(query_plan),
        "next_action": "answer",
        "required_confirmation": False,
        "matched_rules": [query_plan["analysis_mode"]],
        "reason": "QueryPlan 已通过，mock 只读执行结果可用于验证输出结构。",
    }


def _risk_level(query_plan: dict[str, Any]) -> str:
    if query_plan["analysis_mode"] == "low_label_rate_grading":
        return "P2"
    return "P3"
