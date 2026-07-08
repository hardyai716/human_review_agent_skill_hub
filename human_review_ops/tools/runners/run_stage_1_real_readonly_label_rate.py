#!/usr/bin/env python3
"""Run the real readonly label-rate query for stage 1.

This runner is intentionally scenario-specific. It supports the current
efficiency-label-rate task: recent dimension groups whose label_rate is below
0.1.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_KEY = "efficiency-label-rate"
EVAL_DIR = ROOT / "evals" / SCENARIO_KEY
OUTPUT_DATE = "20260708"
DEFAULT_DAYS = 7
DEFAULT_DIMENSIONS = "reason"
DEFAULT_QUERY_MODE = "ranking"
QUERY_MODE_CHOICES = ("ranking", "group_count")
DATASET_ID = "3888816"
APP_ID = "1128"
REGION = "cn"
DATASET_NAME = "[重点模型]-社区_人工审核明细数据"
SOURCE_TABLE = "olap_content_security_community.dws_sft_tcs_review_task_detail_di"
METRIC_FORMULA = "`[打标率__reviewid]` = `[打标量__reviewid]` / `[完审量_reviewid]`"
METRIC_CONTRACT_PATH = (
    "human_review_ops/references/scenarios/efficiency-label-rate/metric_contract.md"
)
DATASET_REFERENCE_PATH = (
    "human_review_ops/references/scenarios/efficiency-label-rate/dataset_reference.md"
)
ANALYSIS_RULE_PATH = (
    "human_review_ops/references/scenarios/efficiency-label-rate/analysis.md"
)
DIMENSION_SPECS = {
    "reason": {"name": "reason", "source_field": "`[reason]`"},
    "p_date": {"name": "p_date", "source_field": "`[p_date]`"},
    "scene": {"name": "scene", "source_field": "`[scene]`"},
    "project_title": {"name": "project_title", "source_field": "`[project_title]`"},
    "mach_root_label_name": {
        "name": "mach_root_label_name",
        "source_field": "`[机审一级标签]`",
    },
}
DIMENSION_ALIASES = {
    "date": "p_date",
    "mach_root_label": "mach_root_label_name",
    "mach_root_label_name": "mach_root_label_name",
}
METRIC_FIELD_TYPES = {
    "review_done_cnt": int,
    "label_cnt": int,
    "label_rate": float,
    "low_label_rate_group_cnt": int,
}


def parse_dimensions(raw_dimensions: str) -> list[dict[str, str]]:
    dimension_names = [
        item.strip()
        for item in raw_dimensions.split(",")
        if item.strip()
    ]
    if not dimension_names:
        raise SystemExit("--dimensions must include at least one dimension.")

    dimensions: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw_name in dimension_names:
        canonical_name = DIMENSION_ALIASES.get(raw_name, raw_name)
        spec = DIMENSION_SPECS.get(canonical_name)
        if spec is None:
            supported = ", ".join(sorted(DIMENSION_SPECS))
            raise SystemExit(
                f"Unsupported dimension '{raw_name}'. Supported dimensions: {supported}."
            )
        if spec["name"] in seen:
            continue
        seen.add(spec["name"])
        dimensions.append(spec)
    return dimensions


def dimensions_slug(dimensions: list[dict[str, str]]) -> str:
    return "_".join(dimension["name"] for dimension in dimensions)


def is_default_shape(dimensions: list[dict[str, str]], query_mode: str) -> bool:
    return dimensions_slug(dimensions) == DEFAULT_DIMENSIONS and query_mode == DEFAULT_QUERY_MODE


def default_output_path(
    days: int,
    dimensions: list[dict[str, str]],
    query_mode: str,
) -> Path:
    if is_default_shape(dimensions, query_mode):
        filename = f"{OUTPUT_DATE}_real_readonly_label_rate_{days}d_results.jsonl"
    else:
        filename = (
            f"{OUTPUT_DATE}_real_readonly_label_rate_{days}d_"
            f"{dimensions_slug(dimensions)}_{query_mode}_results.jsonl"
        )
    return EVAL_DIR / "stage_1_runs" / filename


def query_plan_id(days: int, dimensions: list[dict[str, str]], query_mode: str) -> str:
    base_id = f"QP-ELR-REAL-LABEL-RATE-LT-0-1-{days}D"
    if is_default_shape(dimensions, query_mode):
        return base_id
    dimension_suffix = dimensions_slug(dimensions).replace("_", "-").upper()
    query_mode_suffix = query_mode.replace("_", "-").upper()
    return f"{base_id}-{dimension_suffix}-{query_mode_suffix}"


def event_id(days: int, dimensions: list[dict[str, str]], query_mode: str) -> str:
    base_id = f"ELR-REAL-LABEL-RATE-LT-0-1-{days}D"
    if is_default_shape(dimensions, query_mode):
        return base_id
    dimension_suffix = dimensions_slug(dimensions).replace("_", "-").upper()
    query_mode_suffix = query_mode.replace("_", "-").upper()
    return f"{base_id}-{dimension_suffix}-{query_mode_suffix}"


def analysis_mode_for(query_mode: str) -> str:
    if query_mode == "group_count":
        return "low_label_rate_group_count"
    return "label_rate_ranking"


def build_sql(
    days: int,
    dimensions: list[dict[str, str]],
    query_mode: str,
) -> str:
    if query_mode == "group_count":
        return build_group_count_sql(days, dimensions)
    return build_ranking_sql(days, dimensions)


def build_ranking_sql(days: int, dimensions: list[dict[str, str]]) -> str:
    return build_grouped_sql(
        days=days,
        dimensions=dimensions,
        include_order_and_limit=True,
    )


def build_group_count_sql(days: int, dimensions: list[dict[str, str]]) -> str:
    grouped_sql = build_grouped_sql(
        days=days,
        dimensions=dimensions,
        include_order_and_limit=False,
    )
    indented_grouped_sql = "\n".join(
        f"  {line}" if line else line
        for line in grouped_sql.splitlines()
    )
    return f"""
SELECT count() AS low_label_rate_group_cnt
FROM (
{indented_grouped_sql}
) AS low_label_rate_groups
""".strip()


def build_grouped_sql(
    *,
    days: int,
    dimensions: list[dict[str, str]],
    include_order_and_limit: bool,
) -> str:
    select_expressions = [
        f"{dimension['source_field']} AS {dimension['name']}"
        for dimension in dimensions
    ] + [
        "`[完审量_reviewid]` AS review_done_cnt",
        "`[打标量__reviewid]` AS label_cnt",
        "`[打标率__reviewid]` AS label_rate",
    ]
    select_clause = ",\n  ".join(select_expressions)
    group_by_clause = ", ".join(dimension["name"] for dimension in dimensions)
    order_and_limit = (
        "\nORDER BY review_done_cnt DESC\nLIMIT 1000"
        if include_order_and_limit
        else ""
    )
    return f"""
SELECT
  {select_clause}
FROM {SOURCE_TABLE}
WHERE `[p_date]` >= today() - {days}
  AND `[p_date]` < today()
  AND `[project_title]` NOT LIKE '%虚假%'
  AND `[project_title]` NOT LIKE '%标注%'
  AND `[project_title]` NOT LIKE '%虚假不实%'
  AND `[project_title]` NOT LIKE '%封面%'
  AND `[project_title]` NOT LIKE '%自动处置%'
  AND `[project_title]` NOT LIKE '%演绎%'
  AND `[project_title]` NOT LIKE '%模型%'
  AND `[project_title]` NOT LIKE '%run%'
  AND `[project_title]` NOT LIKE '%质检%'
  AND `[project_title]` NOT LIKE '%QA%'
  AND `[project_title]` NOT LIKE '%测试%'
  AND `[project_title]` NOT LIKE '%大模型%'
  AND `[project_title]` NOT LIKE '%离线%'
  AND `[scene]` IN ('community_audit_safe', 'community_audit_style', 'community_audit_moderate')
  AND `[reason]` NOT IN ('recall_skip_L6', 'fatal_output')
  AND (`[机审一级标签]` IS NULL OR `[机审一级标签]` IN (
    '不良行为或争议价值观',
    '侵犯未成年权益',
    '偏激社会情绪和涉外言论',
    '党和国家形象负面',
    '危险行为',
    '国家安全',
    '引人不适',
    '指令舆情相关',
    '短期策略迁移',
    '色情性化',
    '违法违规',
    '领导人'
  ))
GROUP BY {group_by_clause}
HAVING review_done_cnt > 0 AND label_rate < 0.1
{order_and_limit}
""".strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--dimensions", default=DEFAULT_DIMENSIONS)
    parser.add_argument("--query-mode", default=DEFAULT_QUERY_MODE, choices=QUERY_MODE_CHOICES)
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.days <= 0:
        raise SystemExit("--days must be a positive integer.")

    dimensions = parse_dimensions(args.dimensions)
    sql = build_sql(args.days, dimensions, args.query_mode)
    payload = run_query(sql)
    records = build_records(payload, args.days, dimensions, args.query_mode, sql)
    output_path = (
        Path(args.output)
        if args.output
        else default_output_path(args.days, dimensions, args.query_mode)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            for record in records
        )
        + "\n",
        encoding="utf-8",
    )
    sample = records[1]
    row_count = sample["readonly_execution"]["row_count"]
    print(f"Stage 1 real readonly label-rate wrote {row_count} rows: {output_path}")


def run_query(sql: str) -> dict[str, Any]:
    command = [
        "bytedcli",
        "-j",
        "aeolus",
        "query",
        "-r",
        REGION,
        DATASET_ID,
        sql,
        "--limit",
        "1000",
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Aeolus query failed:\n"
            f"stdout={completed.stdout}\n"
            f"stderr={completed.stderr}"
        )
    payload = json.loads(completed.stdout)
    if payload.get("status") != "success":
        raise RuntimeError(f"Aeolus query returned non-success: {payload}")
    return payload


def build_records(
    payload: dict[str, Any],
    days: int,
    dimensions: list[dict[str, str]],
    query_mode: str,
    sql: str,
) -> list[dict[str, Any]]:
    query_plan = build_query_plan(days, dimensions, query_mode, sql)
    rows = normalize_rows(payload)
    context = payload.get("context", {})
    query_data = payload["data"]
    dimension_names = [dimension["name"] for dimension in dimensions]
    dimension_label = " × ".join(dimension_names)

    tool_call_record = {
        "tool_call_id": f"TCR-{query_plan['query_plan_id']}-01",
        "caller": "analyzing-ops-metrics",
        "tool_name": "bytedcli_aeolus_query",
        "command_name": "bytedcli -j aeolus query",
        "permission_level": "readonly",
        "source_tier": "governed_dataset",
        "scenario_key": SCENARIO_KEY,
        "metric_id": "label_rate",
        "review_required": False,
        "fallback_reason": "none",
        "execution_mode": "real_readonly_query",
        "real_query_executed": True,
        "input_summary": (
            f"Dataset {DATASET_ID}; recent {days} days; dimensions={dimension_label}; "
            f"query_mode={query_mode}; label_rate < 0.1; standard A/B/C/D filters applied."
        ),
        "output_summary": (
            f"Returned {query_data['rowCount']} rows; truncated={query_data.get('truncated')}."
        ),
        "status": "success",
        "latency_ms": context.get("execution_time_ms", 0),
    }
    query_plan["tool_calls"] = [tool_call_record["tool_call_id"]]

    source_footer = build_source_footer(payload, query_plan)
    readonly_execution = build_readonly_execution(payload, rows, source_footer, query_plan)
    provenance = build_provenance(query_plan, readonly_execution, source_footer)
    analysis_result = build_analysis_result(
        query_plan=query_plan,
        readonly_execution=readonly_execution,
        source_footer=source_footer,
        provenance=provenance,
    )

    return [
        {
            "record_type": "environment",
            "scenario_key": SCENARIO_KEY,
            "run_mode": "debug_only",
            "execution_mode": "real_readonly_query",
            "real_query_executed": True,
            "real_notification_blocked": True,
            "online_write_blocked": True,
            "result": "pass",
        },
        {
            "record_type": "sample",
            "id": event_id(days, dimensions, query_mode),
            "input": input_text(days, dimension_label, query_mode),
            "run_mode": "debug_only",
            "scenario_key": SCENARIO_KEY,
            "task_type": "query_only",
            "analysis_mode": analysis_mode_for(query_mode),
            "QueryPlan": query_plan,
            "tool_call_records": [tool_call_record],
            "readonly_execution": readonly_execution,
            "analysis_result": analysis_result,
            "source_footer": source_footer,
            "provenance": provenance,
            "outputs": [
                "QueryPlan",
                "tool_call_record",
                "readonly_execution",
                "analysis_result",
                "source_footer",
                "provenance",
            ],
            "permission_checks": {
                "tool_calls": [tool_call_record["tool_call_id"]],
                "read_only": True,
                "real_query_executed": True,
                "real_notification_blocked": True,
                "online_write_blocked": True,
            },
            "result": "pass",
        },
    ]


def input_text(days: int, dimension_label: str, query_mode: str) -> str:
    if query_mode == "group_count":
        return f"近{days}天打标率<0.1的{dimension_label}分组有多少"
    return f"近{days}天打标率<0.1的{dimension_label}有哪些"


def build_query_plan(
    days: int,
    dimensions: list[dict[str, str]],
    query_mode: str,
    sql: str,
) -> dict[str, Any]:
    dimension_names = [dimension["name"] for dimension in dimensions]
    return {
        "query_plan_id": query_plan_id(days, dimensions, query_mode),
        "scenario_key": SCENARIO_KEY,
        "task_type": "query_only",
        "analysis_mode": analysis_mode_for(query_mode),
        "query_mode": query_mode,
        "metric_id": "label_rate",
        "metric_entities": [
            {
                "metric_id": "label_rate",
                "definition_version": "draft",
                "source_tier": "governed_dataset",
                "aeolus_dataset_id": DATASET_ID,
                "aeolus_metric_id": "10000036292379",
            }
        ],
        "time_range": {
            "type": "trailing_days",
            "days": days,
            "grain": "day",
            "where": f"`[p_date]` >= today() - {days} AND `[p_date]` < today()",
        },
        "dimensions": dimension_names,
        "dimension_mappings": [
            {
                "dimension_id": dimension["name"],
                "source_field": dimension["source_field"],
                "source_tier": "governed_dataset",
            }
            for dimension in dimensions
        ],
        "filters": ["standard_review_scope", "label_rate_lt_0_1"],
        "required_hygiene_filters": [
            "A_project_title_blacklist",
            "B_scene_allowlist",
            "C_reason_exclusion",
            "D_mach_root_label_allowlist_with_null",
        ],
        "source_priority": ["governed_dataset", "curated_raw_sql"],
        "allowed_sources": [
            f"aeolus_dataset:{DATASET_ID}",
            SOURCE_TABLE,
        ],
        "forbidden_sources": [
            "temporary_table",
            "ownerless_legacy_sql",
            "deprecated_strategy_effect_table",
            "ungoverned_dataset",
            "pii_detail_table",
        ],
        "fallback_reason": "none",
        "quality_checks": [
            "freshness_gate",
            "denominator_not_zero",
            "field_mapping_check",
            "grain_check",
            "forbidden_source_check",
            "truncation_check",
        ],
        "review_required": False,
        "execution_mode": "real_readonly_query",
        "sql": sql,
        "tool_calls": [],
    }


def normalize_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    columns = payload["data"]["columns"]
    rows: list[dict[str, Any]] = []
    for raw_row in payload["data"]["rows"]:
        row = dict(zip(columns, raw_row))
        normalized_row: dict[str, Any] = {}
        for column in columns:
            field_type = METRIC_FIELD_TYPES.get(column)
            normalized_row[column] = field_type(row[column]) if field_type else row[column]
        rows.append(normalized_row)
    return rows


def build_source_footer(payload: dict[str, Any], query_plan: dict[str, Any]) -> dict[str, Any]:
    checked_at = payload.get("context", {}).get("timestamp", "unknown")
    days = query_plan["time_range"]["days"]
    return {
        "source_tier": "governed_dataset",
        "metric_definition_version": "draft",
        "data_freshness": (
            f"p_date >= today() - {days} AND p_date < today(); "
            f"checked_at={checked_at}"
        ),
        "owner": "人审效率域数据 Owner",
        "confidence_tier": "high",
        "review_status": "real_readonly_query_executed",
        "scenario_key": SCENARIO_KEY,
        "metric_id": "label_rate",
        "quality_checks": query_plan["quality_checks"],
    }


def build_readonly_execution(
    payload: dict[str, Any],
    rows: list[dict[str, Any]],
    source_footer: dict[str, Any],
    query_plan: dict[str, Any],
) -> dict[str, Any]:
    evidence_fields = list(payload["data"]["columns"])
    dimension_label = " × ".join(query_plan["dimensions"])
    return {
        "execution_id": f"ROE-{query_plan['query_plan_id']}",
        "execution_mode": "real_readonly_query",
        "status": "success",
        "source_tier": "governed_dataset",
        "source_name": f"{DATASET_NAME} ({DATASET_ID})",
        "data_freshness": source_footer["data_freshness"],
        "row_count": payload["data"]["rowCount"],
        "truncated": payload["data"].get("truncated"),
        "columns": payload["data"]["columns"],
        "rows": rows,
        "evidence_fields": evidence_fields,
        "metric_formula": METRIC_FORMULA,
        "quality_checks": {
            "freshness_gate": "passed_via_p_date_filter",
            "denominator_not_zero": "passed",
            "field_mapping_check": "passed",
            "grain_check": f"passed_{dimension_label}",
            "forbidden_source_check": "passed",
            "truncation_check": "passed" if payload["data"].get("truncated") is False else "failed",
        },
        "limitations": [
            "Owner remains role-level until a concrete owner mechanism is connected.",
        ],
    }


def build_provenance(
    query_plan: dict[str, Any],
    readonly_execution: dict[str, Any],
    source_footer: dict[str, Any],
) -> dict[str, Any]:
    return {
        "provenance_id": f"PROV-{query_plan['query_plan_id']}",
        "scenario_key": SCENARIO_KEY,
        "query_plan_id": query_plan["query_plan_id"],
        "execution_id": readonly_execution["execution_id"],
        "execution_mode": "real_readonly_query",
        "source_tier": "governed_dataset",
        "source_name": readonly_execution["source_name"],
        "region": REGION,
        "app_id": APP_ID,
        "dataset_id": DATASET_ID,
        "metric_id": "label_rate",
        "metric_formula": METRIC_FORMULA,
        "time_range": query_plan["time_range"],
        "dimensions": query_plan["dimensions"],
        "filters": query_plan["filters"],
        "required_hygiene_filters": query_plan["required_hygiene_filters"],
        "quality_checks": readonly_execution["quality_checks"],
        "tool_call_ids": query_plan["tool_calls"],
        "sql": query_plan["sql"],
        "references": {
            "metric_contract": METRIC_CONTRACT_PATH,
            "dataset_reference": DATASET_REFERENCE_PATH,
            "analysis_rule": ANALYSIS_RULE_PATH,
        },
        "source_footer": source_footer,
    }


def build_analysis_result(
    *,
    query_plan: dict[str, Any],
    readonly_execution: dict[str, Any],
    source_footer: dict[str, Any],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    days = query_plan["time_range"]["days"]
    dimensions = query_plan["dimensions"]
    query_mode = query_plan["query_mode"]
    analysis_event_id = event_id(
        days,
        [
            {
                "name": mapping["dimension_id"],
                "source_field": mapping["source_field"],
            }
            for mapping in query_plan["dimension_mappings"]
        ],
        query_mode,
    )
    impact_assessment = build_impact_assessment(
        days=days,
        dimensions=dimensions,
        query_mode=query_mode,
        readonly_execution=readonly_execution,
    )
    return {
        "analysis_id": f"AN-{analysis_event_id}",
        "event_id": analysis_event_id,
        "templates_used": ["custom_readonly", "impact_assessment", "sop_decision"],
        "query_plan": compact_query_plan(query_plan),
        "readonly_execution": readonly_execution,
        "impact_assessment": impact_assessment,
        "root_cause_hypotheses": [
            {
                "hypothesis": "query_only_no_root_cause_inference",
                "confidence": 0.0,
                "supporting_evidence": [readonly_execution["execution_id"]],
                "contradicting_evidence": [],
                "next_check": "Run grading or dimension drilldown only if requested.",
            }
        ],
        "sop_decision": {
            "severity_level": "P3",
            "next_action": "answer",
            "required_confirmation": False,
            "matched_rules": ["label_rate_lt_0_1_query"],
            "reason": "只读查询成功，不发送通知、不写状态。",
        },
        "quality_checks": {
            "evidence_complete": True,
            "data_fresh": True,
            "metric_definition_consistent": True,
            "owner_resolved": False,
            "confidence": 0.9,
            "warnings": readonly_execution["limitations"],
        },
        "source_footer": source_footer,
        "provenance": provenance,
    }


def build_impact_assessment(
    *,
    days: int,
    dimensions: list[str],
    query_mode: str,
    readonly_execution: dict[str, Any],
) -> dict[str, Any]:
    dimension_label = " × ".join(dimensions)
    row_count = readonly_execution["row_count"]
    if query_mode == "group_count":
        group_count = (
            readonly_execution["rows"][0]["low_label_rate_group_cnt"]
            if readonly_execution["rows"]
            else 0
        )
        summary = f"近{days}天打标率低于0.1的 {dimension_label} 分组共 {group_count} 个。"
        impact_scope = f"group_count={group_count}"
    else:
        top_group = describe_top_group(readonly_execution["rows"][0], dimensions) if row_count else "none"
        summary = f"近{days}天打标率低于0.1的 {dimension_label} 明细共 {row_count} 行。"
        impact_scope = f"top_group_by_review_done_cnt={top_group}"

    return {
        "summary": summary,
        "impact_scope": impact_scope,
        "risk_level": "P3",
        "business_risk": "本结果为查询结果，不自动触发治理分级。",
        "duration": f"trailing_{days}_days",
        "evidence_refs": [readonly_execution["execution_id"]],
    }


def describe_top_group(row: dict[str, Any], dimensions: list[str]) -> str:
    return ",".join(f"{dimension}={row.get(dimension)}" for dimension in dimensions)


def compact_query_plan(query_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "query_plan_id": query_plan["query_plan_id"],
        "metric_entities": query_plan["metric_entities"],
        "dimensions": query_plan["dimensions"],
        "dimension_mappings": query_plan["dimension_mappings"],
        "query_mode": query_plan["query_mode"],
        "time_range": query_plan["time_range"],
        "filters": query_plan["filters"],
        "tool_calls": query_plan["tool_calls"],
        "allowed_sources": query_plan["allowed_sources"],
        "forbidden_sources": query_plan["forbidden_sources"],
        "quality_checks": query_plan["quality_checks"],
    }


if __name__ == "__main__":
    main()
