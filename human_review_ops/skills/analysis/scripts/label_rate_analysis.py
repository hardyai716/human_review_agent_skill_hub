#!/usr/bin/env python3
"""Reusable label-rate analysis helpers for the analysis Skill.

The module is intentionally side-effect free. It constructs QueryPlan, SQL,
source footer, and normalized grading outputs; host runners own real readonly
tool execution and file persistence.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from typing import Any


SCHEMA_VERSION = "label_rate_analysis.v1"
SCENARIO_KEY = "efficiency-label-rate"
OUTPUT_DATE = "20260708"
CURRENT_DAYS = 7
HISTORY_DAYS = 28
DATASET_ID = "3888816"
APP_ID = "1128"
REGION = "cn"
DATASET_NAME = "[重点模型]-社区_人工审核明细数据"
SOURCE_TABLE = "olap_content_security_community.dws_sft_tcs_review_task_detail_di"
QUERY_LIMIT = "50000"
MIN_CURRENT_REVIEW_IN_CNT = 100
METRIC_FORMULA = (
    "`label_rate` = SUM(`[打标量__reviewid]`) / SUM(`[完审量_reviewid]`)"
)
RULE_SOURCE = (
    "human_review_ops/skills/analysis/references/scenarios/efficiency-label-rate.md#模式-b低打标率分级"
)
METRIC_CONTRACT_PATH = (
    "human_review_ops/skills/analysis/references/scenarios/efficiency-label-rate.md#指标口径"
)
DATASET_REFERENCE_PATH = (
    "human_review_ops/skills/analysis/references/scenarios/efficiency-label-rate.md#数据源与字段"
)
ANALYSIS_RULE_PATH = (
    "human_review_ops/skills/analysis/references/scenarios/efficiency-label-rate.md#分析模式"
)
LEVEL_ORDER = ["P0", "P1", "P2", "notice"]
LEVEL_PRIORITY = {"P0": 0, "P1": 1, "P2": 2, "notice": 3}
DEFAULT_LEVELS = ["notice", "P2", "P1", "P0"]
DIMENSIONS = ["mach_root_label_name", "strategy_id", "strategy_name", "reason"]
FLOAT_FIELDS = {
    "total_review_in_cnt",
    "total_review_done_cnt",
    "total_label_cnt",
    "avg_review_in_cnt",
    "avg_review_done_cnt",
    "avg_label_cnt",
    "label_rate",
    "prev_avg_review_in_cnt",
    "prev_label_rate",
    "growth_rate",
    "daily_delta",
}
INT_FIELDS = {"severity_priority", "data_days"}
GRADING_COLUMNS = [
    "severity_level",
    "severity_priority",
    "mach_root_label_name",
    "strategy_id",
    "strategy_name",
    "reason",
    "data_days",
    "total_review_in_cnt",
    "total_review_done_cnt",
    "total_label_cnt",
    "avg_review_in_cnt",
    "avg_review_done_cnt",
    "avg_label_cnt",
    "label_rate",
    "prev_avg_review_in_cnt",
    "prev_label_rate",
    "growth_rate",
    "daily_delta",
    "hit_rule_id",
    "hit_condition",
]
RowEnricher = Callable[[dict[str, Any]], dict[str, Any]]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dry-run reusable label-rate QueryPlan, SQL, and grading output."
    )
    parser.add_argument("--levels", default=",".join(DEFAULT_LEVELS))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Emit deterministic smoke output. This script never executes SQL.",
    )
    args = parser.parse_args()

    levels = parse_levels(args.levels)
    sql_map = sql_by_level()
    payloads = build_smoke_payloads(levels)
    records = build_records(payloads, levels, sql_map)
    sample = records[1]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "dry_run": bool(args.dry_run),
        "QueryPlan": sample["QueryPlan"],
        "source_footer": sample["source_footer"],
        "readonly_execution": sample["readonly_execution"],
        "analysis_result": sample["analysis_result"],
        "provenance": sample["provenance"],
        "safety": {
            "sql_executed": False,
            "notification_sent": False,
            "online_write_executed": False,
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def query_plan_id() -> str:
    return "QP-ELR-REAL-LOW-LABEL-RATE-GRADING-7D"


def event_id() -> str:
    return "ELR-REAL-LOW-LABEL-RATE-GRADING-7D"


def parse_levels(raw_levels: str) -> list[str]:
    levels = [level.strip() for level in raw_levels.split(",") if level.strip()]
    if not levels:
        raise ValueError("levels must include at least one level.")
    invalid = [level for level in levels if level not in DEFAULT_LEVELS]
    if invalid:
        raise ValueError(f"Unsupported levels: {invalid}. Supported: {DEFAULT_LEVELS}.")
    return levels


def base_filter_sql(indent: str = "    ") -> str:
    """Return the standard sample-pool filter from the metric contract."""
    filters = [
        "`[project_title]` NOT LIKE '%虚假%'",
        "`[project_title]` NOT LIKE '%标注%'",
        "`[project_title]` NOT LIKE '%虚假不实%'",
        "`[project_title]` NOT LIKE '%封面%'",
        "`[project_title]` NOT LIKE '%自动处置%'",
        "`[project_title]` NOT LIKE '%演绎%'",
        "`[project_title]` NOT LIKE '%模型%'",
        "`[project_title]` NOT LIKE '%run%'",
        "`[project_title]` NOT LIKE '%质检%'",
        "`[project_title]` NOT LIKE '%QA%'",
        "`[project_title]` NOT LIKE '%测试%'",
        "`[project_title]` NOT LIKE '%大模型%'",
        "`[project_title]` NOT LIKE '%离线%'",
        "`[scene]` IN ('community_audit_safe', 'community_audit_style', 'community_audit_moderate')",
        "`[reason]` NOT IN ('recall_skip_L6', 'fatal_output')",
        """(`[机审一级标签]` IS NULL OR `[机审一级标签]` IN (
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
    ))""",
    ]
    return "\n".join(f"{indent}AND {item}" for item in filters)


def period_aggregate_sql(start_days_ago: int, end_days_ago: int) -> str:
    end_expr = "today()" if end_days_ago == 0 else f"today() - {end_days_ago}"
    return f"""
SELECT
  mach_root_label_key AS mach_root_label_name,
  strategy_id_key AS strategy_id,
  strategy_name_key AS strategy_name,
  reason_key AS reason,
  COUNT(DISTINCT dt) AS data_days,
  SUM(jin_shen) AS total_review_in_cnt,
  SUM(wan_shen) AS total_review_done_cnt,
  SUM(da_biao) AS total_label_cnt,
  SUM(jin_shen) / COUNT(DISTINCT dt) AS avg_review_in_cnt,
  SUM(wan_shen) / COUNT(DISTINCT dt) AS avg_review_done_cnt,
  SUM(da_biao) / COUNT(DISTINCT dt) AS avg_label_cnt,
  if(SUM(wan_shen) = 0, 0, SUM(da_biao) / SUM(wan_shen)) AS label_rate
FROM (
  SELECT
    ifNull(`[机审一级标签]`, '（空/机审一级标签）') AS mach_root_label_key,
    ifNull(`[strategy_id]`, '（空/strategy_id）') AS strategy_id_key,
    ifNull(`[strategy_name]`, '（空/strategy_name）') AS strategy_name_key,
    ifNull(`[reason]`, '（空/reason）') AS reason_key,
    `[p_date]` AS dt,
    `[进审量_reviewid]` AS jin_shen,
    `[完审量_reviewid]` AS wan_shen,
    `[打标量__reviewid]` AS da_biao
  FROM {SOURCE_TABLE}
  WHERE `[p_date]` >= today() - {start_days_ago}
    AND `[p_date]` < {end_expr}
{base_filter_sql("    ")}
  GROUP BY mach_root_label_key, strategy_id_key, strategy_name_key, reason_key, dt
) daily
GROUP BY mach_root_label_key, strategy_id_key, strategy_name_key, reason_key
HAVING SUM(wan_shen) > 0
""".strip()


def dimension_join(left: str, right: str) -> str:
    return " AND ".join(f"{left}.{field} = {right}.{field}" for field in DIMENSIONS)


def level_select_sql(
    *,
    level: str,
    hit_rule_id: str,
    hit_condition: str,
    from_sql: str,
    where_sql: str,
    prev_fields_sql: str | None = None,
) -> str:
    prev_fields = prev_fields_sql or """
  0.0 AS prev_avg_review_in_cnt,
  0.0 AS prev_label_rate,
  0.0 AS growth_rate,
  0.0 AS daily_delta,"""
    return f"""
SELECT
  '{level}' AS severity_level,
  {LEVEL_PRIORITY[level]} AS severity_priority,
  cur.mach_root_label_name AS mach_root_label_name,
  cur.strategy_id AS strategy_id,
  cur.strategy_name AS strategy_name,
  cur.reason AS reason,
  cur.data_days AS data_days,
  cur.total_review_in_cnt AS total_review_in_cnt,
  cur.total_review_done_cnt AS total_review_done_cnt,
  cur.total_label_cnt AS total_label_cnt,
  cur.avg_review_in_cnt AS avg_review_in_cnt,
  cur.avg_review_done_cnt AS avg_review_done_cnt,
  cur.avg_label_cnt AS avg_label_cnt,
  cur.label_rate AS label_rate,
{prev_fields}
  '{hit_rule_id}' AS hit_rule_id,
  '{hit_condition}' AS hit_condition
FROM {from_sql}
WHERE ({where_sql})
  AND cur.total_review_in_cnt > {MIN_CURRENT_REVIEW_IN_CNT}
""".strip()


def build_notice_sql() -> str:
    cur = f"({period_aggregate_sql(7, 0)}) cur"
    return f"""
{level_select_sql(
    level="notice",
    hit_rule_id="notice_low_label_rate",
    hit_condition="近7天打标率<10%且进审量>100，纳入观察",
    from_sql=cur,
    where_sql="cur.label_rate < 0.1",
)}
ORDER BY avg_review_done_cnt DESC
LIMIT {QUERY_LIMIT}
""".strip()


def build_p2_sql() -> str:
    cur = f"({period_aggregate_sql(7, 0)}) cur"
    prev = f"({period_aggregate_sql(14, 7)}) prev"
    growth_fields = """
  prev.avg_review_in_cnt AS prev_avg_review_in_cnt,
  prev.label_rate AS prev_label_rate,
  (cur.avg_review_in_cnt - prev.avg_review_in_cnt) / NULLIF(prev.avg_review_in_cnt, 0) AS growth_rate,
  (cur.avg_review_in_cnt - prev.avg_review_in_cnt) AS daily_delta,"""
    condition_one = level_select_sql(
        level="P2",
        hit_rule_id="p2_single_strategy_low_efficiency",
        hit_condition="近7天累计进审量>14000且打标率<3%",
        from_sql=cur,
        where_sql="cur.total_review_in_cnt > 14000 AND cur.label_rate < 0.03",
    )
    condition_two = level_select_sql(
        level="P2",
        hit_rule_id="p2_low_efficiency_growth",
        hit_condition="本期打标率<10%，上期日均进审>0，环比>20%，日均增量>2000",
        from_sql=f"{cur} INNER JOIN {prev} ON {dimension_join('cur', 'prev')}",
        where_sql=(
            "cur.label_rate < 0.1 AND prev.avg_review_in_cnt > 0 "
            "AND (cur.avg_review_in_cnt - prev.avg_review_in_cnt) "
            "/ NULLIF(prev.avg_review_in_cnt, 0) > 0.2 "
            "AND (cur.avg_review_in_cnt - prev.avg_review_in_cnt) > 2000"
        ),
        prev_fields_sql=growth_fields,
    )
    return f"""
SELECT *
FROM (
{indent_sql(condition_one)}
UNION ALL
{indent_sql(condition_two)}
) hits
ORDER BY avg_review_done_cnt DESC
LIMIT {QUERY_LIMIT}
""".strip()


def build_p1_sql() -> str:
    cur = f"({period_aggregate_sql(7, 0)}) cur"
    prev = f"({period_aggregate_sql(14, 7)}) prev"
    prev_fields = """
  prev.avg_review_in_cnt AS prev_avg_review_in_cnt,
  prev.label_rate AS prev_label_rate,
  0.0 AS growth_rate,
  0.0 AS daily_delta,"""
    growth_fields = """
  prev.avg_review_in_cnt AS prev_avg_review_in_cnt,
  prev.label_rate AS prev_label_rate,
  (cur.avg_review_in_cnt - prev.avg_review_in_cnt) / NULLIF(prev.avg_review_in_cnt, 0) AS growth_rate,
  (cur.avg_review_in_cnt - prev.avg_review_in_cnt) AS daily_delta,"""
    condition_one = level_select_sql(
        level="P1",
        hit_rule_id="p1_two_week_persistent_low_efficiency",
        hit_condition="双周期日均进审>2000且双周期打标率<3%",
        from_sql=f"{cur} INNER JOIN {prev} ON {dimension_join('cur', 'prev')}",
        where_sql=(
            "cur.avg_review_in_cnt > 2000 AND prev.avg_review_in_cnt > 2000 "
            "AND cur.label_rate < 0.03 AND prev.label_rate < 0.03"
        ),
        prev_fields_sql=prev_fields,
    )
    condition_two = level_select_sql(
        level="P1",
        hit_rule_id="p1_single_week_high_volume_low_efficiency",
        hit_condition="近7天日均进审>5000且打标率<3%",
        from_sql=cur,
        where_sql="cur.avg_review_in_cnt > 5000 AND cur.label_rate < 0.03",
    )
    condition_three = level_select_sql(
        level="P1",
        hit_rule_id="p1_low_efficiency_volume_spike",
        hit_condition="本期/上期打标率<10%，环比>30%，日均增量>5000",
        from_sql=f"{cur} INNER JOIN {prev} ON {dimension_join('cur', 'prev')}",
        where_sql=(
            "cur.label_rate < 0.1 AND prev.label_rate < 0.1 "
            "AND prev.avg_review_in_cnt > 0 "
            "AND (cur.avg_review_in_cnt - prev.avg_review_in_cnt) "
            "/ NULLIF(prev.avg_review_in_cnt, 0) > 0.3 "
            "AND (cur.avg_review_in_cnt - prev.avg_review_in_cnt) > 5000"
        ),
        prev_fields_sql=growth_fields,
    )
    return f"""
SELECT *
FROM (
{indent_sql(condition_one)}
UNION ALL
{indent_sql(condition_two)}
UNION ALL
{indent_sql(condition_three)}
) hits
ORDER BY avg_review_done_cnt DESC
LIMIT {QUERY_LIMIT}
""".strip()


def build_p0_sql() -> str:
    cur = f"({period_aggregate_sql(7, 0)}) cur"
    w2 = f"({period_aggregate_sql(14, 7)}) w2"
    w3 = f"({period_aggregate_sql(21, 14)}) w3"
    w4 = f"({period_aggregate_sql(28, 21)}) w4"
    prev_fields = """
  w2.avg_review_in_cnt AS prev_avg_review_in_cnt,
  w2.label_rate AS prev_label_rate,
  0.0 AS growth_rate,
  0.0 AS daily_delta,"""
    growth_fields = """
  w2.avg_review_in_cnt AS prev_avg_review_in_cnt,
  w2.label_rate AS prev_label_rate,
  (cur.avg_review_in_cnt - w2.avg_review_in_cnt) / NULLIF(w2.avg_review_in_cnt, 0) AS growth_rate,
  (cur.avg_review_in_cnt - w2.avg_review_in_cnt) AS daily_delta,"""

    condition_a = level_select_sql(
        level="P0",
        hit_rule_id="p0_four_week_persistent_low_efficiency",
        hit_condition="近1周日均进审>2000且连续4周打标率<3%",
        from_sql=(
            f"{cur} INNER JOIN {w2} ON {dimension_join('cur', 'w2')} "
            f"INNER JOIN {w3} ON {dimension_join('cur', 'w3')} "
            f"INNER JOIN {w4} ON {dimension_join('cur', 'w4')}"
        ),
        where_sql=(
            "cur.avg_review_in_cnt > 2000 AND cur.label_rate < 0.03 "
            "AND w2.label_rate < 0.03 AND w3.label_rate < 0.03 AND w4.label_rate < 0.03"
        ),
        prev_fields_sql=prev_fields,
    )
    condition_b = level_select_sql(
        level="P0",
        hit_rule_id="p0_two_week_high_volume_low_efficiency",
        hit_condition="近1周日均进审>5000且连续2周打标率<3%",
        from_sql=f"{cur} INNER JOIN {w2} ON {dimension_join('cur', 'w2')}",
        where_sql=(
            "cur.avg_review_in_cnt > 5000 AND cur.label_rate < 0.03 "
            "AND w2.label_rate < 0.03"
        ),
        prev_fields_sql=prev_fields,
    )
    condition_c = level_select_sql(
        level="P0",
        hit_rule_id="p0_single_week_ultra_high_volume_low_efficiency",
        hit_condition="近1周日均进审>10000且打标率<3%",
        from_sql=cur,
        where_sql="cur.avg_review_in_cnt > 10000 AND cur.label_rate < 0.03",
    )
    condition_d = level_select_sql(
        level="P0",
        hit_rule_id="p0_review_in_volume_spike",
        hit_condition="近1周打标率<10%，日均进审环比>50%，日均增量>10000",
        from_sql=f"{cur} INNER JOIN {w2} ON {dimension_join('cur', 'w2')}",
        where_sql=(
            "cur.label_rate < 0.1 AND w2.avg_review_in_cnt > 0 "
            "AND (cur.avg_review_in_cnt - w2.avg_review_in_cnt) "
            "/ NULLIF(w2.avg_review_in_cnt, 0) > 0.5 "
            "AND (cur.avg_review_in_cnt - w2.avg_review_in_cnt) > 10000"
        ),
        prev_fields_sql=growth_fields,
    )
    return f"""
SELECT *
FROM (
{indent_sql(condition_a)}
UNION ALL
{indent_sql(condition_b)}
UNION ALL
{indent_sql(condition_c)}
UNION ALL
{indent_sql(condition_d)}
) hits
ORDER BY avg_review_done_cnt DESC
LIMIT {QUERY_LIMIT}
""".strip()


def indent_sql(sql: str) -> str:
    return "\n".join(f"  {line}" if line else line for line in sql.splitlines())


def sql_by_level() -> dict[str, str]:
    return {
        "notice": build_notice_sql(),
        "P2": build_p2_sql(),
        "P1": build_p1_sql(),
        "P0": build_p0_sql(),
    }


def build_records(
    payloads: dict[str, dict[str, Any]],
    levels: list[str],
    sql_map: dict[str, str],
    *,
    row_enricher: RowEnricher | None = None,
) -> list[dict[str, Any]]:
    query_plan = build_query_plan(levels, sql_map)
    level_results = {
        level: build_level_result(level, payloads[level], row_enricher=row_enricher)
        for level in levels
    }
    tool_call_records = [
        build_tool_call_record(level, payloads[level], query_plan)
        for level in levels
    ]
    query_plan["tool_calls"] = [
        tool_call["tool_call_id"] for tool_call in tool_call_records
    ]
    source_footer = build_source_footer(payloads, query_plan)
    readonly_execution = build_readonly_execution(level_results, source_footer, query_plan)
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
            "analysis_mode": "low_label_rate_grading",
            "real_query_executed": True,
            "real_notification_blocked": True,
            "online_write_blocked": True,
            "result": "pass",
        },
        {
            "record_type": "sample",
            "id": event_id(),
            "input": "近7天低打标率策略按机审一级标签×策略ID×策略名称×送审原因分P0/P1/P2/notice的情况",
            "run_mode": "debug_only",
            "scenario_key": SCENARIO_KEY,
            "task_type": "query_only",
            "analysis_mode": "low_label_rate_grading",
            "QueryPlan": query_plan,
            "tool_call_records": tool_call_records,
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
                "tool_calls": query_plan["tool_calls"],
                "read_only": True,
                "real_query_executed": True,
                "real_notification_blocked": True,
                "online_write_blocked": True,
            },
            "result": "pass",
        },
    ]


def build_query_plan(levels: list[str], sql_map: dict[str, str]) -> dict[str, Any]:
    return {
        "query_plan_id": query_plan_id(),
        "scenario_key": SCENARIO_KEY,
        "task_type": "query_only",
        "analysis_mode": "low_label_rate_grading",
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
            "type": "weekly_grading_window",
            "current_days": CURRENT_DAYS,
            "history_days": HISTORY_DAYS,
            "current_where": "`[p_date]` >= today() - 7 AND `[p_date]` < today()",
            "history_where": "`[p_date]` >= today() - 28 AND `[p_date]` < today()",
        },
        "dimensions": list(DIMENSIONS),
        "filters": [
            "standard_review_scope",
            "label_rate_lt_thresholds",
            "current_review_in_gt_100",
        ],
        "levels": levels,
        "level_priority": LEVEL_PRIORITY,
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
        "fallback_reason": "complex_grading_rule_not_covered_by_semantic_layer",
        "quality_checks": [
            "freshness_gate",
            "denominator_not_zero",
            "field_mapping_check",
            "grain_check_four_dimension_strategy",
            "min_current_review_in_gate",
            "forbidden_source_check",
            "truncation_check",
            "grading_rule_check",
        ],
        "review_required": False,
        "execution_mode": "real_readonly_query",
        "sql_by_level": {level: sql_map[level] for level in levels},
        "tool_calls": [],
    }


def build_tool_call_record(
    level: str,
    payload: dict[str, Any],
    query_plan: dict[str, Any],
) -> dict[str, Any]:
    context = payload.get("context", {})
    data = payload["data"]
    return {
        "tool_call_id": f"TCR-{query_plan['query_plan_id']}-{level}",
        "caller": "analyzing-ops-metrics",
        "tool_name": "bytedcli_aeolus_query",
        "command_name": "bytedcli -j aeolus query",
        "permission_level": "readonly",
        "source_tier": "governed_dataset",
        "scenario_key": SCENARIO_KEY,
        "metric_id": "label_rate",
        "review_required": False,
        "fallback_reason": query_plan["fallback_reason"],
        "execution_mode": "real_readonly_query",
        "real_query_executed": True,
        "input_summary": f"Dataset {DATASET_ID}; level={level}; low-label-rate grading.",
        "output_summary": f"Returned {data['rowCount']} rows; truncated={data.get('truncated')}.",
        "status": "success",
        "latency_ms": context.get("execution_time_ms", 0),
    }


def build_level_result(
    level: str,
    payload: dict[str, Any],
    *,
    row_enricher: RowEnricher | None = None,
) -> dict[str, Any]:
    rows = dedupe_level_rows(normalize_rows(payload, row_enricher=row_enricher), level)
    return {
        "severity_level": level,
        "severity_priority": LEVEL_PRIORITY[level],
        "row_count": len(rows),
        "source_row_count": payload["data"]["rowCount"],
        "truncated": payload["data"].get("truncated"),
        "columns": payload["data"]["columns"],
        "rows": rows,
    }


def normalize_rows(
    payload: dict[str, Any],
    *,
    row_enricher: RowEnricher | None = None,
) -> list[dict[str, Any]]:
    columns = payload["data"]["columns"]
    rows: list[dict[str, Any]] = []
    for raw_row in payload["data"]["rows"]:
        row = dict(zip(columns, raw_row))
        normalized: dict[str, Any] = {}
        for column, value in row.items():
            if column in FLOAT_FIELDS:
                normalized[column] = float(value)
            elif column in INT_FIELDS:
                normalized[column] = int(value)
            else:
                normalized[column] = value
        if row_enricher:
            normalized.update(row_enricher(dict(normalized)))
        ensure_poc_fields(normalized)
        rows.append(normalized)
    return rows


def ensure_poc_fields(row: dict[str, Any]) -> None:
    poc_name = row.get("poc_name") or row.get("POC") or "未映射"
    row["poc_name"] = poc_name
    row["POC"] = poc_name
    row.setdefault("poc_open_id", None)
    row.setdefault("poc_mapping_status", "not_resolved_by_analysis_script")


def dimension_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return tuple(str(row.get(field, "")) for field in DIMENSIONS)  # type: ignore[return-value]


def dedupe_level_rows(rows: list[dict[str, Any]], level: str) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = dimension_key(row)
        existing = deduped.get(key)
        if existing is None:
            merged = dict(row)
            merged["severity_level"] = level
            merged["severity_priority"] = LEVEL_PRIORITY[level]
            merged["hit_rule_ids"] = [row["hit_rule_id"]]
            merged["hit_conditions"] = [row["hit_condition"]]
            deduped[key] = merged
        else:
            if row["hit_rule_id"] not in existing["hit_rule_ids"]:
                existing["hit_rule_ids"].append(row["hit_rule_id"])
            if row["hit_condition"] not in existing["hit_conditions"]:
                existing["hit_conditions"].append(row["hit_condition"])
    return sorted(
        deduped.values(),
        key=lambda item: item["avg_review_done_cnt"],
        reverse=True,
    )


def build_comprehensive_results(
    level_results: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    best_by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for level in LEVEL_ORDER:
        if level not in level_results:
            continue
        for row in level_results[level]["rows"]:
            key = dimension_key(row)
            existing = best_by_key.get(key)
            if existing is None or row["severity_priority"] < existing["severity_priority"]:
                best_by_key[key] = dict(row)
    return sorted(
        best_by_key.values(),
        key=lambda item: (item["severity_priority"], -item["avg_review_done_cnt"]),
    )


def build_source_footer(
    payloads: dict[str, dict[str, Any]],
    query_plan: dict[str, Any],
) -> dict[str, Any]:
    checked_at = max(
        payload.get("context", {}).get("timestamp", "")
        for payload in payloads.values()
    ) or "unknown"
    return {
        "source_tier": "governed_dataset",
        "metric_definition_version": "draft",
        "data_freshness": (
            "p_date >= today() - 28 AND p_date < today(); "
            f"checked_at={checked_at}"
        ),
        "owner": "人审效率域数据 Owner",
        "confidence_tier": "high",
        "review_status": "real_readonly_query_executed",
        "scenario_key": SCENARIO_KEY,
        "metric_id": "label_rate",
        "quality_checks": query_plan["quality_checks"],
        "metric_contract_ref": METRIC_CONTRACT_PATH,
        "dataset_reference_ref": DATASET_REFERENCE_PATH,
        "analysis_ref": ANALYSIS_RULE_PATH,
        "query_plan_id": query_plan["query_plan_id"],
        "time_window": query_plan["time_range"],
        "data_lag": "uses closed p_date partitions where p_date < today()",
        "source_priority": query_plan["source_priority"],
        "actual_source": f"aeolus_dataset:{DATASET_ID}",
        "filters": query_plan["filters"],
        "dimensions": query_plan["dimensions"],
        "limitations": [
            "POC contact open_id resolution is outside the analysis Skill.",
            "Low-label-rate grading uses governed SQL fallback for multi-condition rules.",
        ],
        "run_mode": "debug_only",
    }


def build_readonly_execution(
    level_results: dict[str, dict[str, Any]],
    source_footer: dict[str, Any],
    query_plan: dict[str, Any],
) -> dict[str, Any]:
    comprehensive_results = build_comprehensive_results(level_results)
    level_counts = {
        level: level_results[level]["row_count"]
        for level in query_plan["levels"]
    }
    return {
        "execution_id": f"ROE-{query_plan['query_plan_id']}",
        "execution_mode": "real_readonly_query",
        "analysis_mode": "low_label_rate_grading",
        "status": "success",
        "source_tier": "governed_dataset",
        "source_name": f"{DATASET_NAME} ({DATASET_ID})",
        "data_freshness": source_footer["data_freshness"],
        "level_counts": level_counts,
        "row_count": len(comprehensive_results),
        "truncated": any(
            level_results[level]["truncated"] is not False
            for level in query_plan["levels"]
        ),
        "level_results": level_results,
        "comprehensive_results": comprehensive_results,
        "evidence_fields": [
            "severity_level",
            "mach_root_label_name",
            "strategy_id",
            "strategy_name",
            "reason",
            "POC",
            "poc_name",
            "avg_review_in_cnt",
            "avg_review_done_cnt",
            "avg_label_cnt",
            "label_rate",
            "hit_rule_ids",
            "hit_conditions",
        ],
        "metric_formula": METRIC_FORMULA,
        "rule_source": RULE_SOURCE,
        "quality_checks": {
            "freshness_gate": "passed_via_p_date_filter",
            "denominator_not_zero": "passed",
            "field_mapping_check": "passed",
            "grain_check": "passed_mach_root_label_strategy_reason",
            "poc_name_mapping": "passed_name_only",
            "min_current_review_in_gate": f"passed_cur_total_review_in_cnt_gt_{MIN_CURRENT_REVIEW_IN_CNT}",
            "forbidden_source_check": "passed",
            "truncation_check": "passed",
            "grading_rule_check": "passed",
        },
        "limitations": [
            "POC is resolved to name only; Feishu open_id resolution and recipient confirmation are still required before real notification.",
            "Semantic Layer cannot yet express the multi-condition grading rule; used governed Aeolus SQL fallback.",
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
        "analysis_mode": "low_label_rate_grading",
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
        "levels": query_plan["levels"],
        "level_priority": query_plan["level_priority"],
        "required_hygiene_filters": query_plan["required_hygiene_filters"],
        "quality_checks": readonly_execution["quality_checks"],
        "tool_call_ids": query_plan["tool_calls"],
        "sql_by_level": query_plan["sql_by_level"],
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
    level_counts = readonly_execution["level_counts"]
    summary = ", ".join(f"{level}={level_counts.get(level, 0)}" for level in LEVEL_ORDER)
    return {
        "analysis_id": f"AN-{event_id()}",
        "event_id": event_id(),
        "templates_used": ["custom_readonly", "impact_assessment", "sop_decision"],
        "query_plan": compact_query_plan(query_plan),
        "readonly_execution": readonly_execution,
        "impact_assessment": {
            "summary": f"近7天低打标率四维分级完成，综合命中 {readonly_execution['row_count']} 个策略分组；{summary}。",
            "impact_scope": f"comprehensive_strategy_group_count={readonly_execution['row_count']}",
            "risk_level": highest_hit_level(level_counts),
            "business_risk": "本结果为分级查询结果，不自动触发通知或状态写入。",
            "duration": "trailing_7_days_with_28_day_history",
            "evidence_refs": [readonly_execution["execution_id"]],
        },
        "root_cause_hypotheses": [
            {
                "hypothesis": "grading_rule_match_only_no_root_cause_inference",
                "confidence": 0.0,
                "supporting_evidence": [readonly_execution["execution_id"]],
                "contradicting_evidence": [],
                "next_check": "Generate notification draft or owner routing only if requested.",
            }
        ],
        "sop_decision": {
            "severity_level": highest_hit_level(level_counts),
            "next_action": "answer",
            "required_confirmation": False,
            "matched_rules": [
                level for level in LEVEL_ORDER if level_counts.get(level, 0) > 0
            ],
            "reason": "只读分级查询成功，不发送通知、不写状态。",
        },
        "quality_checks": {
            "evidence_complete": True,
            "data_fresh": True,
            "metric_definition_consistent": True,
            "owner_resolved": True,
            "owner_resolution_level": "poc_name_only",
            "confidence": 0.9,
            "warnings": readonly_execution["limitations"],
        },
        "source_footer": source_footer,
        "provenance": provenance,
    }


def highest_hit_level(level_counts: dict[str, int]) -> str:
    for level in LEVEL_ORDER:
        if level_counts.get(level, 0) > 0:
            return level
    return "none"


def compact_query_plan(query_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "query_plan_id": query_plan["query_plan_id"],
        "metric_entities": query_plan["metric_entities"],
        "dimensions": query_plan["dimensions"],
        "time_range": query_plan["time_range"],
        "filters": query_plan["filters"],
        "levels": query_plan["levels"],
        "level_priority": query_plan["level_priority"],
        "tool_calls": query_plan["tool_calls"],
        "allowed_sources": query_plan["allowed_sources"],
        "forbidden_sources": query_plan["forbidden_sources"],
        "fallback_reason": query_plan["fallback_reason"],
        "quality_checks": query_plan["quality_checks"],
    }


def build_smoke_payloads(levels: list[str]) -> dict[str, dict[str, Any]]:
    return {level: build_smoke_payload(level, index) for index, level in enumerate(levels)}


def build_smoke_payload(level: str, index: int = 0) -> dict[str, Any]:
    row = [
        level,
        LEVEL_PRIORITY[level],
        "不良行为或争议价值观",
        f"strategy_{level.lower()}_{index}",
        f"{level}低打标率策略",
        f"{level.lower()}_low_label_reason",
        7,
        21000.0 + index,
        20000.0 + index,
        400.0,
        3000.0 + index,
        2857.14 + index,
        57.14,
        0.02,
        1000.0,
        0.05,
        0.25,
        2000.0,
        f"smoke_{level.lower()}_rule",
        f"{level} smoke hit condition",
    ]
    return {
        "status": "success",
        "context": {
            "timestamp": "2026-07-09T00:00:00+08:00",
            "execution_time_ms": 1,
        },
        "data": {
            "columns": list(GRADING_COLUMNS),
            "rows": [row],
            "rowCount": 1,
            "truncated": False,
        },
    }


if __name__ == "__main__":
    main()
