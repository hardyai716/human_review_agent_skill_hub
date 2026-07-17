#!/usr/bin/env python3
"""Reusable label-rate analysis helpers for the analysis Skill.

The module is intentionally side-effect free. It constructs QueryPlan, SQL,
source footer, and normalized grading outputs; external execution environments
own real readonly tool execution and file persistence.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
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
REPORT_FLOW_DATASET_ID = "3952594"
REPORT_FLOW_APP_ID = "555137"
REPORT_FLOW_DATASET_NAME = "举报流转任务明细数据集"
REPORT_FLOW_PHYSICAL_TABLE = (
    "`aeolus_data_db_aeolus_sagittarius_mini_202511`."
    "`aeolus_data_table_22_3373535_migrate_v1_prod`"
)
QUERY_LIMIT = "50000"
METRIC_FORMULA = (
    "`label_rate` = SUM(`[打标量__reviewid]`) / SUM(`[完审量_reviewid]`)"
)
RULE_SOURCE = (
    "references/scenario_contract.md#模式-b低打标率分级"
)
METRIC_CONTRACT_PATH = (
    "references/scenario_contract.md#指标口径"
)
DATASET_REFERENCE_PATH = (
    "references/scenario_contract.md#数据源与字段"
)
ANALYSIS_RULE_PATH = (
    "references/scenario_contract.md#分析模式"
)
PLUS1_AGREED_ASSET = "plus1_agreed_strategy_updates.json"
LEVEL_ORDER = ["P0", "P1", "P2", "notice"]
LEVEL_PRIORITY = {"P0": 0, "P1": 1, "P2": 2, "notice": 3}
DEFAULT_LEVELS = ["notice", "P2", "P1", "P0"]
WARNING_DIMENSION_SINGLE_STRATEGY = "单策略维度"
WARNING_DIMENSION_RISK_DOMAIN = "风险域维度"
DIMENSIONS = ["mach_root_label_name", "strategy_id", "strategy_name"]
DEDUPE_DIMENSIONS = ["warning_dimension", *DIMENSIONS]
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
    "warning_dimension",
    "severity_level",
    "severity_priority",
    "mach_root_label_name",
    "strategy_id",
    "strategy_name",
    "data_days",
    "max_data_date",
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
    "is_plus1_agreed",
    "plus1_update_date",
    "plus1_agreed_before_current_period",
]
RowEnricher = Callable[[dict[str, Any]], dict[str, Any]]

REPORT_FLOW_LAST_QUEUE_NAMES = [
    "【视频专项_举报】D-J-不良行为和争议价值观-B",
    "【视频专项_举报】D-J-人工分流-B",
    "【视频专项_举报】D-J-危险行为-B",
    "【视频专项_举报】D-J-引人不适-B",
    "【视频专项_举报】D-J-未成年-B",
    "【视频专项_举报】D-J-色情低俗-B",
    "【视频专项_举报】D-J-违法犯罪-B",
    "【视频专项_举报】【众包-PC端】短视频-安全-举报-时政",
    "【视频专项_举报】短视频-安全-举报-兜底",
    "【视频专项_举报】短视频-安全-举报-时政",
    "短视频-安全-疑难研判专审队列-涉政-举报",
]
REPORT_FLOW_FIRST_QUEUE_NAMES = [
    "【众包-PC端】【视频专项_举报】短视频-安全-举报-兜底",
    "【视频专项_举报】D-J-不良行为和争议价值观-B",
    "【视频专项_举报】D-J-人工分流-B",
    "【视频专项_举报】D-J-危险行为-B",
    "【视频专项_举报】D-J-引人不适-B",
    "【视频专项_举报】D-J-未成年-B",
    "【视频专项_举报】D-J-短视频-兜底-2.0",
    "【视频专项_举报】D-J-短视频特殊2.0",
    "【视频专项_举报】D-J-色情低俗-B",
    "【视频专项_举报】D-J-违法犯罪-B",
    "【视频专项_举报】D-J-长视频特殊2.0",
    "【视频专项_举报】D-J-音频-B",
    "【视频专项_举报】D-J-高审",
    "【视频专项_举报】D-J-高频",
    "【视频专项_举报】【众包-PC端】短视频-安全-举报-时政",
    "【视频专项_举报】短视频-安全-举报-兜底",
    "【视频专项_举报】短视频-安全-举报-时政",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dry-run reusable label-rate QueryPlan, SQL, and grading output."
    )
    parser.add_argument("--levels", default=",".join(DEFAULT_LEVELS))
    parser.add_argument(
        "--data-direction",
        choices=["manual_review_detail", "report_flow"],
        default="manual_review_detail",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Emit deterministic smoke output. This script never executes SQL.",
    )
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    args = parser.parse_args()

    time_range = build_cli_time_range(args)
    if args.data_direction == "report_flow":
        payload = build_report_flow_dry_run_payload(
            dry_run=True,
            time_range=time_range,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    levels = parse_levels(args.levels)
    sql_map = sql_by_level(time_range)
    payloads = build_smoke_payloads(levels)
    records = build_records(payloads, levels, sql_map, time_range=time_range)
    sample = records[1]
    mark_sample_as_dry_run(sample)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "sample",
        "dry_run": True,
        "scenario_key": sample["scenario_key"],
        "task_type": sample["task_type"],
        "analysis_mode": sample["analysis_mode"],
        "run_mode": sample["run_mode"],
        "QueryPlan": sample["QueryPlan"],
        "source_footer": sample["source_footer"],
        "readonly_execution": sample["readonly_execution"],
        "analysis_result": sample["analysis_result"],
        "provenance": sample["provenance"],
        "safety": {
            "sql_executed": False,
            "notification_sent": False,
            "online_write_executed": False,
            "real_query_executed": False,
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def mark_sample_as_dry_run(sample: dict[str, Any]) -> None:
    """Relabel every nested execution object as a non-authoritative fixture."""

    execution = sample["readonly_execution"]
    execution["execution_mode"] = "mock_readonly_no_real_query"
    execution["status"] = "not_executed"
    execution["level_counts"] = {
        level: 0 for level in execution.get("level_counts", {})
    }
    for result in execution.get("level_results", {}).values():
        result["row_count"] = 0
        result["source_row_count"] = 0
        result["rows"] = []
        result["truncated"] = None
    execution["row_count"] = 0
    execution["comprehensive_results"] = []
    execution["truncated"] = None
    execution["quality_checks"]["freshness_gate"] = "not_executed"
    execution["quality_checks"]["truncation_check"] = "not_executed"

    source_footer = sample["source_footer"]
    source_footer["source_tier"] = "mock_fixture"
    source_footer["review_status"] = "debug_only_mock_readonly_execution"
    source_footer["confidence_tier"] = "low"

    provenance = sample["provenance"]
    provenance["execution_mode"] = "mock_readonly_no_real_query"
    provenance["source_tier"] = "mock_fixture"
    provenance["limitations"] = list(execution["limitations"]) + [
        "CLI output contains deterministic smoke rows and is not business evidence."
    ]

    analysis_result = sample["analysis_result"]
    analysis_result["impact_assessment"]["summary"] = (
        "Dry-run 仅验证 QueryPlan、SQL 和输出结构，未产生业务命中结果。"
    )
    analysis_result["impact_assessment"]["impact_scope"] = (
        "unknown_until_external_readonly_execution"
    )
    analysis_result["impact_assessment"]["risk_level"] = "unknown"
    analysis_result["impact_assessment"]["business_risk"] = (
        "Dry-run fixture only; no business conclusion is available."
    )
    analysis_result["sop_decision"].update(
        {
            "severity_level": "unknown",
            "next_action": "ask_more",
            "required_confirmation": True,
            "matched_rules": [],
            "reason": "必须由外部只读执行器回填真实查询结果后再下业务结论。",
        }
    )
    analysis_result["quality_checks"].update(
        {
            "evidence_complete": False,
            "data_fresh": False,
            "owner_resolved": False,
            "confidence": 0.0,
        }
    )

    sample["permission_checks"]["real_query_executed"] = False
    for tool_call in sample["tool_call_records"]:
        tool_call.update(
            {
                "execution_mode": "mock_readonly_no_real_query",
                "real_query_executed": False,
                "status": "blocked",
                "output_summary": "Deterministic smoke fixture; no query executed.",
            }
        )


def build_cli_time_range(args: argparse.Namespace) -> dict[str, Any] | None:
    if bool(args.start_date) != bool(args.end_date):
        raise SystemExit("--start-date and --end-date must be provided together.")
    if not args.start_date:
        return None
    try:
        return build_grading_time_range(
            start_date=args.start_date,
            end_date=args.end_date,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


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
        """(`[机审一级标签]` IS NULL OR `[机审一级标签]` = '' OR `[机审一级标签]` IN (
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


def mach_root_label_key_sql(indent: str = "    ") -> str:
    """Return normalized mach-root-label SQL with null-label strategy mapping."""
    strategy_name = "ifNull(`[strategy_name]`, '')"
    pad = indent
    inner = indent + "  "
    return "\n".join(
        [
            f"{pad}multiIf(",
            f"{inner}not isNull(`[机审一级标签]`) AND `[机审一级标签]` != '', `[机审一级标签]`,",
            f"{inner}{strategy_name} = '高价值-兜底vv进审', '高热',",
            f"{inner}{strategy_name} = '短视频-特殊账号-达到VV阈值', '高热',",
            f"{inner}{strategy_name} = '非白名单政媒账号投稿vv大于5万vv送审', '政媒',",
            f"{inner}{strategy_name} = '商业化付费视频全人审ugc', '商业化',",
            f"{inner}{strategy_name} = '白名单账号投稿vv大于5万vv送审', '政媒',",
            f"{inner}{strategy_name} = '中视频-特殊账号-达到VV阈值', '高热',",
            f"{inner}{strategy_name} = '星图预审35wvv强制召回', '高热',",
            f"{inner}{strategy_name} = '【ZL推人】麒麟芯片9030', '指令舆情相关',",
            f"{inner}{strategy_name} = '【ZL推人】涉日股市负面-词', '指令舆情相关',",
            f"{inner}{strategy_name} = '高热虐猫虐狗上升召回-内容现象', '高热',",
            f"{inner}{strategy_name} = '【兜底送审】普通视频豁免25W进审', '高热',",
            f"{inner}position({strategy_name}, 'ZL') > 0, '指令舆情相关',",
            f"{inner}position({strategy_name}, '商业化') > 0, '商业化',",
            f"{inner}position({strategy_name}, '政媒') > 0, '政媒',",
            f"{inner}'（空/机审一级标签）'",
            f"{pad}) AS mach_root_label_key",
        ]
    )


def quote_sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def parse_date_value(raw_value: str) -> date:
    return date.fromisoformat(raw_value.strip().replace("/", "-"))


def parse_user_period(raw_text: str | None) -> dict[str, Any] | None:
    """Extract an explicit inclusive date range from user text."""

    if not raw_text:
        return None
    match = re.search(
        r"(?P<start>\d{4}[-/]\d{1,2}[-/]\d{1,2})\s*"
        r"(?:至|到|~|～|—|–|-)\s*"
        r"(?P<end>\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        raw_text,
    )
    if not match:
        return None
    return build_grading_time_range(
        start_date=parse_date_value(match.group("start")),
        end_date=parse_date_value(match.group("end")),
    )


def build_grading_time_range(
    *,
    start_date: date | str,
    end_date: date | str,
    checked_at: str | None = None,
) -> dict[str, Any]:
    """Build the explicit weekly grading window used by low-label-rate rules."""

    current_start = (
        parse_date_value(start_date) if isinstance(start_date, str) else start_date
    )
    current_end = parse_date_value(end_date) if isinstance(end_date, str) else end_date
    if current_end < current_start:
        raise ValueError("end_date must be >= start_date.")
    current_days = (current_end - current_start).days + 1
    if current_days != CURRENT_DAYS:
        raise ValueError(
            "low_label_rate_grading requires a 7-day current window; "
            f"got {current_days} days."
        )

    current_end_exclusive = current_end + timedelta(days=1)
    history_start = current_start - timedelta(days=HISTORY_DAYS - CURRENT_DAYS)
    previous_windows = []
    for index in range(1, 4):
        window_start = current_start - timedelta(days=CURRENT_DAYS * index)
        window_end_exclusive = current_start - timedelta(
            days=CURRENT_DAYS * (index - 1)
        )
        previous_windows.append(
            {
                "start": window_start.isoformat(),
                "end": (window_end_exclusive - timedelta(days=1)).isoformat(),
                "end_exclusive": window_end_exclusive.isoformat(),
            }
        )

    checked_at_value = checked_at or (
        datetime.combine(current_end_exclusive, datetime.min.time()).isoformat()
        + "+08:00"
    )
    return {
        "type": "explicit_weekly_grading_window",
        "current_start": current_start.isoformat(),
        "current_end": current_end.isoformat(),
        "current_end_exclusive": current_end_exclusive.isoformat(),
        "current_days": current_days,
        "history_start": history_start.isoformat(),
        "history_end": current_end.isoformat(),
        "history_days": HISTORY_DAYS,
        "previous_windows": previous_windows,
        "current_where": (
            f"`[p_date]` >= '{current_start.isoformat()}' "
            f"AND `[p_date]` < '{current_end_exclusive.isoformat()}'"
        ),
        "history_where": (
            f"`[p_date]` >= '{history_start.isoformat()}' "
            f"AND `[p_date]` < '{current_end_exclusive.isoformat()}'"
        ),
        "checked_at": checked_at_value,
    }


def explicit_p_date_filter(
    start_days_ago: int,
    end_days_ago: int,
    time_range: dict[str, Any],
) -> str:
    current_end_exclusive = parse_date_value(time_range["current_end_exclusive"])
    start = current_end_exclusive - timedelta(days=start_days_ago)
    end_exclusive = current_end_exclusive - timedelta(days=end_days_ago)
    return (
        f"`[p_date]` >= '{start.isoformat()}' "
        f"AND `[p_date]` < '{end_exclusive.isoformat()}'"
    )


def p_date_filter_sql(
    start_days_ago: int,
    end_days_ago: int,
    time_range: dict[str, Any] | None,
) -> str:
    if time_range and time_range.get("type") == "explicit_weekly_grading_window":
        return explicit_p_date_filter(start_days_ago, end_days_ago, time_range)
    end_expr = "today()" if end_days_ago == 0 else f"today() - {end_days_ago}"
    return f"`[p_date]` >= today() - {start_days_ago} AND `[p_date]` < {end_expr}"


def query_plan_id_for_time_range(time_range: dict[str, Any] | None) -> str:
    if time_range and time_range.get("current_start") and time_range.get("current_end"):
        start = str(time_range["current_start"]).replace("-", "")
        end = str(time_range["current_end"]).replace("-", "")
        return f"QP-ELR-REAL-LOW-LABEL-RATE-GRADING-{start}-{end}"
    return query_plan_id()


def event_id_for_time_range(time_range: dict[str, Any] | None) -> str:
    if time_range and time_range.get("current_start") and time_range.get("current_end"):
        start = str(time_range["current_start"]).replace("-", "")
        end = str(time_range["current_end"]).replace("-", "")
        return f"ELR-REAL-LOW-LABEL-RATE-GRADING-{start}-{end}"
    return event_id()


def sql_in_list(values: list[str], indent: str = "    ") -> str:
    return (",\n" + indent).join(quote_sql_string(value) for value in values)


def report_flow_filter_sql(indent: str = "  ") -> str:
    return "\n".join(
        [
            f"{indent}AND `[终轮队列名称]` IN (",
            f"{indent}  {sql_in_list(REPORT_FLOW_LAST_QUEUE_NAMES, indent + '  ')}",
            f"{indent})",
            f"{indent}AND `[一轮队列名称]` IN (",
            f"{indent}  {sql_in_list(REPORT_FLOW_FIRST_QUEUE_NAMES, indent + '  ')}",
            f"{indent})",
            f"{indent}AND `[任务类型]` IN ('关注-【举报专项】任务链路流转')",
            f"{indent}AND `[一轮队列名称]` NOT LIKE '%兜底%'",
            f"{indent}AND `[一轮队列名称]` NOT LIKE '%海外%'",
            f"{indent}AND `[一轮队列名称]` NOT LIKE '%特殊%'",
        ]
    )


def build_report_flow_time_range(
    time_range: dict[str, Any] | None,
) -> dict[str, Any]:
    if time_range and time_range.get("current_start") and time_range.get("current_end"):
        start = str(time_range["current_start"])
        end_exclusive = str(
            time_range.get("current_end_exclusive")
            or (
                parse_date_value(str(time_range["current_end"])) + timedelta(days=1)
            ).isoformat()
        )
        return {
            "type": "explicit_date_range",
            "current_start": start,
            "current_end": str(time_range["current_end"]),
            "current_end_exclusive": end_exclusive,
            "days": CURRENT_DAYS,
            "date_field": "进审日期",
            "where": (
                f"`[进审日期]` >= '{start}' "
                f"AND `[进审日期]` < '{end_exclusive}'"
            ),
        }
    return {
        "type": "trailing_days",
        "days": CURRENT_DAYS,
        "date_field": "进审日期",
        "where": "`[进审日期]` >= today() - 7 AND `[进审日期]` < today()",
    }


def build_report_flow_low_label_rate_sql(
    time_range: dict[str, Any] | None = None,
) -> str:
    resolved_time_range = build_report_flow_time_range(time_range)
    date_filter = resolved_time_range["where"]
    return f"""
WITH daily AS (
  SELECT
    ifNull(`[enpool_reason]`, '（空/enpool_reason）') AS enpool_reason_key,
    `[进审日期]` AS review_date_key,
    `[人审完结量_report_id]` AS report_review_done_cnt,
    `[打标量_report_id]` AS report_label_cnt
  FROM {REPORT_FLOW_PHYSICAL_TABLE}
  WHERE {date_filter}
{report_flow_filter_sql("    ")}
  GROUP BY enpool_reason_key, review_date_key
)
SELECT
  enpool_reason_key AS enpool_reason,
  SUM(report_review_done_cnt) / count(distinct review_date_key) AS avg_report_review_done_cnt,
  SUM(report_label_cnt) / count(distinct review_date_key) AS avg_report_label_cnt,
  SUM(report_label_cnt) / nullIf(SUM(report_review_done_cnt), 0) AS report_label_rate
FROM daily
GROUP BY enpool_reason_key
HAVING SUM(report_review_done_cnt) > 0
   AND SUM(report_label_cnt) / nullIf(SUM(report_review_done_cnt), 0) < 0.1
ORDER BY avg_report_review_done_cnt DESC
LIMIT {QUERY_LIMIT}
""".strip()


def build_report_flow_query_plan(
    sql: str,
    time_range: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_time_range = build_report_flow_time_range(time_range)
    period_suffix = ""
    if resolved_time_range.get("current_start"):
        period_suffix = (
            "-"
            + str(resolved_time_range["current_start"]).replace("-", "")
            + "-"
            + str(resolved_time_range["current_end"]).replace("-", "")
        )
    return {
        "query_plan_id": f"QP-ELR-REPORT-FLOW-LOW-LABEL-RATE{period_suffix or '-7D'}",
        "scenario_key": SCENARIO_KEY,
        "task_type": "report_flow_low_label_rate",
        "analysis_mode": "report_flow_low_label_rate",
        "metric_id": "report_label_rate",
        "data_direction": "report_flow",
        "source_profile": "report_flow_review",
        "metric_entities": [
            {
                "metric_id": "report_label_rate",
                "definition_version": "draft",
                "source_tier": "governed_dataset",
                "aeolus_dataset_id": REPORT_FLOW_DATASET_ID,
                "aeolus_metric_id": "10000001274387",
            }
        ],
        "time_range": resolved_time_range,
        "dimensions": ["enpool_reason"],
        "filters": [
            "report_flow_queue_scope",
            "task_type_report_flow",
            "first_queue_exclusion",
            "report_label_rate_lt_0_1",
            "report_review_done_cnt_gt_0",
        ],
        "required_hygiene_filters": [
            "A_report_flow_last_queue_allowlist",
            "B_report_flow_first_queue_allowlist",
            "C_report_flow_task_type",
            "D_report_flow_first_queue_exclusion",
        ],
        "source_priority": ["governed_dataset", "curated_raw_sql"],
        "allowed_sources": [f"aeolus_dataset:{REPORT_FLOW_DATASET_ID}"],
        "forbidden_sources": [
            f"aeolus_dataset:{DATASET_ID}",
            "temporary_table",
            "ownerless_legacy_sql",
            "deprecated_strategy_effect_table",
            "pii_detail_table",
        ],
        "fallback_reason": "report_flow_source_profile",
        "quality_checks": [
            "field_mapping_check",
            "freshness_gate",
            "denominator_not_zero",
            "grain_check_enpool_reason",
            "forbidden_source_check",
            "truncation_check",
        ],
        "review_required": False,
        "execution_mode": "dry_run_sql_template",
        "sql": sql,
        "tool_calls": [],
    }


def build_report_flow_source_footer(query_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_tier": "governed_dataset",
        "metric_definition_version": "draft",
        "data_freshness": "uses `[进审日期]` trailing 7 complete days; checked_at=dry_run",
        "owner": "人审效率域数据 Owner",
        "confidence_tier": "high",
        "review_status": "debug_only_no_real_query",
        "scenario_key": SCENARIO_KEY,
        "metric_id": "report_label_rate",
        "data_direction": "report_flow",
        "source_profile": "report_flow_review",
        "quality_checks": query_plan["quality_checks"],
        "metric_contract_ref": METRIC_CONTRACT_PATH,
        "dataset_reference_ref": DATASET_REFERENCE_PATH,
        "analysis_ref": ANALYSIS_RULE_PATH,
        "query_plan_id": query_plan["query_plan_id"],
        "time_window": query_plan["time_range"],
        "data_lag": "uses closed `进审日期` values where `进审日期` < today()",
        "source_priority": query_plan["source_priority"],
        "actual_source": f"aeolus_dataset:{REPORT_FLOW_DATASET_ID}",
        "filters": query_plan["filters"],
        "dimensions": query_plan["dimensions"],
        "limitations": [
            "This payload only builds the report-flow QueryPlan and SQL template; external execution owns real readonly query execution.",
            "The physical table fallback is recorded in dataset_reference and should be kept in provenance when used.",
        ],
        "run_mode": "debug_only",
    }


def build_report_flow_dry_run_payload(
    *,
    dry_run: bool,
    time_range: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sql = build_report_flow_low_label_rate_sql(time_range=time_range)
    query_plan = build_report_flow_query_plan(sql, time_range)
    source_footer = build_report_flow_source_footer(query_plan)
    readonly_execution = {
        "execution_id": f"ROE-{query_plan['query_plan_id']}",
        "execution_mode": "dry_run_sql_template",
        "analysis_mode": "report_flow_low_label_rate",
        "status": "not_executed",
        "source_tier": "governed_dataset",
        "source_name": f"{REPORT_FLOW_DATASET_NAME} ({REPORT_FLOW_DATASET_ID})",
        "data_freshness": source_footer["data_freshness"],
        "row_count": 0,
        "truncated": None,
        "columns": [
            "enpool_reason",
            "avg_report_review_done_cnt",
            "avg_report_label_cnt",
            "report_label_rate",
        ],
        "rows": [],
        "metric_formula": "`report_label_rate` = `[打标量_report_id]` / `[人审完结量_report_id]`",
        "quality_checks": {
            "field_mapping_check": "passed_static_contract",
            "freshness_gate": "requires_external_execution",
            "denominator_not_zero": "encoded_in_having",
            "grain_check": "passed_enpool_reason",
            "forbidden_source_check": "passed",
        },
    }
    provenance = {
        "provenance_id": f"PROV-{query_plan['query_plan_id']}",
        "scenario_key": SCENARIO_KEY,
        "query_plan_id": query_plan["query_plan_id"],
        "execution_id": readonly_execution["execution_id"],
        "execution_mode": "dry_run_sql_template",
        "analysis_mode": "report_flow_low_label_rate",
        "source_tier": "governed_dataset",
        "source_name": readonly_execution["source_name"],
        "region": REGION,
        "app_id": REPORT_FLOW_APP_ID,
        "dataset_id": REPORT_FLOW_DATASET_ID,
        "metric_id": "report_label_rate",
        "metric_formula": readonly_execution["metric_formula"],
        "time_range": query_plan["time_range"],
        "dimensions": query_plan["dimensions"],
        "filters": query_plan["filters"],
        "sql": sql,
        "references": {
            "metric_contract": METRIC_CONTRACT_PATH,
            "dataset_reference": DATASET_REFERENCE_PATH,
            "analysis_rule": ANALYSIS_RULE_PATH,
        },
        "tool_call_ids": [],
        "limitations": source_footer["limitations"],
        "source_footer": source_footer,
    }
    analysis_result = {
        "analysis_id": "AN-ELR-REPORT-FLOW-LOW-LABEL-RATE-7D",
        "event_id": "ELR-REPORT-FLOW-LOW-LABEL-RATE-7D",
        "templates_used": ["report_flow_low_label_rate", "source_footer"],
        "query_plan": query_plan,
        "readonly_execution": readonly_execution,
        "impact_assessment": {
            "summary": "仅生成举报方向 QueryPlan 和 SQL，尚未执行真实查询。",
            "impact_scope": "unknown_until_external_readonly_execution",
            "risk_level": "unknown",
            "business_risk": "无真实查询结果，不下业务结论。",
            "duration": "not_executed",
            "evidence_refs": [readonly_execution["execution_id"]],
        },
        "root_cause_hypotheses": [
            {
                "hypothesis": "not_analyzed_without_query_result",
                "confidence": 0.0,
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "next_check": "由外部只读执行器执行 QueryPlan。",
            }
        ],
        "sop_decision": {
            "severity_level": "none",
            "next_action": "external_readonly_execute",
            "required_confirmation": False,
            "reason": "Dry-run generated QueryPlan and SQL only.",
        },
        "quality_checks": {
            "evidence_complete": False,
            "data_fresh": False,
            "metric_definition_consistent": True,
            "owner_resolved": False,
            "confidence": 0.0,
            "warnings": source_footer["limitations"],
        },
        "source_footer": source_footer,
        "provenance": provenance,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "sample",
        "dry_run": dry_run,
        "scenario_key": SCENARIO_KEY,
        "task_type": "report_flow_low_label_rate",
        "analysis_mode": "report_flow_low_label_rate",
        "run_mode": "debug_only",
        "data_direction": "report_flow",
        "source_profile": "report_flow_review",
        "QueryPlan": query_plan,
        "source_footer": source_footer,
        "readonly_execution": readonly_execution,
        "analysis_result": analysis_result,
        "provenance": provenance,
        "safety": {
            "sql_executed": False,
            "notification_sent": False,
            "online_write_executed": False,
            "real_query_executed": False,
        },
    }


def period_aggregate_sql(
    start_days_ago: int,
    end_days_ago: int,
    time_range: dict[str, Any] | None = None,
) -> str:
    p_date_filter = p_date_filter_sql(start_days_ago, end_days_ago, time_range)
    return f"""
SELECT
  mach_root_label_key AS mach_root_label_name,
  strategy_id_key AS strategy_id,
  strategy_name_key AS strategy_name,
  COUNT(DISTINCT dt) AS data_days,
  MAX(dt) AS max_data_date,
  SUM(jin_shen) AS total_review_in_cnt,
  SUM(wan_shen) AS total_review_done_cnt,
  SUM(da_biao) AS total_label_cnt,
  SUM(jin_shen) / COUNT(DISTINCT dt) AS avg_review_in_cnt,
  SUM(wan_shen) / COUNT(DISTINCT dt) AS avg_review_done_cnt,
  SUM(da_biao) / COUNT(DISTINCT dt) AS avg_label_cnt,
  if(SUM(wan_shen) = 0, 0, SUM(da_biao) / SUM(wan_shen)) AS label_rate
FROM (
  SELECT
{mach_root_label_key_sql("    ")},
    ifNull(`[strategy_id]`, '（空/strategy_id）') AS strategy_id_key,
    ifNull(`[strategy_name]`, '（空/strategy_name）') AS strategy_name_key,
    `[p_date]` AS dt,
    `[进审量_reviewid]` AS jin_shen,
    `[完审量_reviewid]` AS wan_shen,
    `[打标量__reviewid]` AS da_biao
  FROM {SOURCE_TABLE}
  WHERE {p_date_filter}
{base_filter_sql("    ")}
  GROUP BY mach_root_label_key, strategy_id_key, strategy_name_key, dt
) daily
GROUP BY mach_root_label_key, strategy_id_key, strategy_name_key
HAVING SUM(wan_shen) > 0
""".strip()


def dimension_join(left: str, right: str) -> str:
    return " AND ".join(f"{left}.{field} = {right}.{field}" for field in DIMENSIONS)


def daily_strategy_sql(
    start_days_ago: int,
    end_days_ago: int,
    time_range: dict[str, Any] | None = None,
) -> str:
    p_date_filter = p_date_filter_sql(start_days_ago, end_days_ago, time_range)
    return f"""
SELECT
{mach_root_label_key_sql("  ")},
  ifNull(`[strategy_id]`, '（空/strategy_id）') AS strategy_id_key,
  ifNull(`[strategy_name]`, '（空/strategy_name）') AS strategy_name_key,
  `[p_date]` AS dt,
  `[进审量_reviewid]` AS jin_shen,
  `[完审量_reviewid]` AS wan_shen,
  `[打标量__reviewid]` AS da_biao
FROM {SOURCE_TABLE}
WHERE {p_date_filter}
{base_filter_sql("  ")}
GROUP BY mach_root_label_key, strategy_id_key, strategy_name_key, dt
""".strip()


def risk_domain_spike_source_sql(time_range: dict[str, Any] | None = None) -> str:
    cur = f"({period_aggregate_sql(7, 0, time_range)}) cur_strategy"
    prev = f"({period_aggregate_sql(14, 7, time_range)}) prev_strategy"
    cur_daily = f"({daily_strategy_sql(7, 0, time_range)}) cur_daily"
    prev_daily = f"({daily_strategy_sql(14, 7, time_range)}) prev_daily"
    return f"""
(
  WITH
  cur_low_keys AS (
    SELECT mach_root_label_name, strategy_id, strategy_name
    FROM {cur}
    WHERE label_rate < 0.1
  ),
  prev_low_keys AS (
    SELECT mach_root_label_name, strategy_id, strategy_name
    FROM {prev}
    WHERE label_rate < 0.1
  ),
  cur_domain AS (
    SELECT
      cur_daily.mach_root_label_key AS mach_root_label_name,
      '' AS strategy_id,
      '' AS strategy_name,
      COUNT(DISTINCT cur_daily.dt) AS data_days,
      MAX(cur_daily.dt) AS max_data_date,
      SUM(cur_daily.jin_shen) AS total_review_in_cnt,
      SUM(cur_daily.wan_shen) AS total_review_done_cnt,
      SUM(cur_daily.da_biao) AS total_label_cnt,
      SUM(cur_daily.jin_shen) / COUNT(DISTINCT cur_daily.dt) AS avg_review_in_cnt,
      SUM(cur_daily.wan_shen) / COUNT(DISTINCT cur_daily.dt) AS avg_review_done_cnt,
      SUM(cur_daily.da_biao) / COUNT(DISTINCT cur_daily.dt) AS avg_label_cnt,
      if(SUM(cur_daily.wan_shen) = 0, 0, SUM(cur_daily.da_biao) / SUM(cur_daily.wan_shen)) AS label_rate
    FROM {cur_daily}
    INNER JOIN cur_low_keys
      ON cur_daily.mach_root_label_key = cur_low_keys.mach_root_label_name
     AND cur_daily.strategy_id_key = cur_low_keys.strategy_id
     AND cur_daily.strategy_name_key = cur_low_keys.strategy_name
    GROUP BY cur_daily.mach_root_label_key
  ),
  prev_domain AS (
    SELECT
      prev_daily.mach_root_label_key AS mach_root_label_name,
      SUM(prev_daily.jin_shen) / COUNT(DISTINCT prev_daily.dt) AS prev_avg_review_in_cnt,
      if(SUM(prev_daily.wan_shen) = 0, 0, SUM(prev_daily.da_biao) / SUM(prev_daily.wan_shen)) AS prev_label_rate
    FROM {prev_daily}
    INNER JOIN prev_low_keys
      ON prev_daily.mach_root_label_key = prev_low_keys.mach_root_label_name
     AND prev_daily.strategy_id_key = prev_low_keys.strategy_id
     AND prev_daily.strategy_name_key = prev_low_keys.strategy_name
    GROUP BY prev_daily.mach_root_label_key
  )
  SELECT
    cur_domain.*,
    ifNull(prev_domain.prev_avg_review_in_cnt, 0) AS prev_avg_review_in_cnt,
    ifNull(prev_domain.prev_label_rate, 0) AS prev_label_rate,
    if(prev_domain.prev_avg_review_in_cnt = 0 OR isNull(prev_domain.prev_avg_review_in_cnt), 0,
      (cur_domain.avg_review_in_cnt - prev_domain.prev_avg_review_in_cnt)
      / prev_domain.prev_avg_review_in_cnt
    ) AS growth_rate,
    cur_domain.avg_review_in_cnt - ifNull(prev_domain.prev_avg_review_in_cnt, 0) AS daily_delta
  FROM cur_domain
  LEFT JOIN prev_domain ON cur_domain.mach_root_label_name = prev_domain.mach_root_label_name
) cur
""".strip()


def level_select_sql(
    *,
    level: str,
    hit_rule_id: str,
    hit_condition: str,
    from_sql: str,
    where_sql: str,
    warning_dimension: str = WARNING_DIMENSION_SINGLE_STRATEGY,
    prev_fields_sql: str | None = None,
) -> str:
    prev_fields = prev_fields_sql or """
  0.0 AS prev_avg_review_in_cnt,
  0.0 AS prev_label_rate,
  0.0 AS growth_rate,
  0.0 AS daily_delta,"""
    return f"""
SELECT
  '{warning_dimension}' AS warning_dimension,
  '{level}' AS severity_level,
  {LEVEL_PRIORITY[level]} AS severity_priority,
  cur.mach_root_label_name AS mach_root_label_name,
  cur.strategy_id AS strategy_id,
  cur.strategy_name AS strategy_name,
  cur.data_days AS data_days,
  cur.max_data_date AS max_data_date,
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
""".strip()


def build_notice_sql(time_range: dict[str, Any] | None = None) -> str:
    cur = f"({period_aggregate_sql(7, 0, time_range)}) cur"
    return f"""
{level_select_sql(
    level="notice",
    hit_rule_id="notice_low_label_rate",
    hit_condition="近7天三维粒度打标率<10%，不限制累计进审量",
    from_sql=cur,
    where_sql="cur.label_rate < 0.1",
)}
ORDER BY avg_review_done_cnt DESC
LIMIT {QUERY_LIMIT}
""".strip()


def build_p2_sql(time_range: dict[str, Any] | None = None) -> str:
    cur = f"({period_aggregate_sql(7, 0, time_range)}) cur"
    growth_fields = """
  cur.prev_avg_review_in_cnt AS prev_avg_review_in_cnt,
  cur.prev_label_rate AS prev_label_rate,
  cur.growth_rate AS growth_rate,
  cur.daily_delta AS daily_delta,"""
    condition_one = level_select_sql(
        level="P2",
        hit_rule_id="p2_single_strategy_low_efficiency",
        hit_condition="近7天日均进审量>2000且打标率<3%",
        from_sql=cur,
        where_sql="cur.avg_review_in_cnt > 2000 AND cur.label_rate < 0.03",
    )
    condition_two = level_select_sql(
        level="P2",
        hit_rule_id="p2_risk_domain_low_efficiency_growth",
        hit_condition="风险域下低效策略汇总日均进审量环比上涨>20%，日均增量>2000，上期进审量>0",
        from_sql=risk_domain_spike_source_sql(time_range),
        where_sql=(
            "cur.prev_avg_review_in_cnt > 0 "
            "AND cur.growth_rate > 0.2 "
            "AND cur.daily_delta > 2000"
        ),
        warning_dimension=WARNING_DIMENSION_RISK_DOMAIN,
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


def build_p1_sql(time_range: dict[str, Any] | None = None) -> str:
    cur = f"({period_aggregate_sql(7, 0, time_range)}) cur"
    prev = f"({period_aggregate_sql(14, 7, time_range)}) prev"
    prev_fields = """
  prev.avg_review_in_cnt AS prev_avg_review_in_cnt,
  prev.label_rate AS prev_label_rate,
  0.0 AS growth_rate,
  0.0 AS daily_delta,"""
    growth_fields = """
  cur.prev_avg_review_in_cnt AS prev_avg_review_in_cnt,
  cur.prev_label_rate AS prev_label_rate,
  cur.growth_rate AS growth_rate,
  cur.daily_delta AS daily_delta,"""
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
        hit_rule_id="p1_risk_domain_low_efficiency_volume_spike",
        hit_condition="风险域下低效策略汇总日均进审量环比上涨>30%，日均增量>5000，上期进审量>0",
        from_sql=risk_domain_spike_source_sql(time_range),
        where_sql=(
            "cur.prev_avg_review_in_cnt > 0 "
            "AND cur.growth_rate > 0.3 "
            "AND cur.daily_delta > 5000"
        ),
        warning_dimension=WARNING_DIMENSION_RISK_DOMAIN,
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


def build_p0_sql(time_range: dict[str, Any] | None = None) -> str:
    cur = f"({period_aggregate_sql(7, 0, time_range)}) cur"
    w2 = f"({period_aggregate_sql(14, 7, time_range)}) w2"
    w3 = f"({period_aggregate_sql(21, 14, time_range)}) w3"
    w4 = f"({period_aggregate_sql(28, 21, time_range)}) w4"
    prev_fields = """
  w2.avg_review_in_cnt AS prev_avg_review_in_cnt,
  w2.label_rate AS prev_label_rate,
  0.0 AS growth_rate,
  0.0 AS daily_delta,"""
    growth_fields = """
  cur.prev_avg_review_in_cnt AS prev_avg_review_in_cnt,
  cur.prev_label_rate AS prev_label_rate,
  cur.growth_rate AS growth_rate,
  cur.daily_delta AS daily_delta,"""

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
        hit_rule_id="p0_risk_domain_review_in_volume_spike",
        hit_condition="风险域下低效策略汇总日均进审量环比上涨>50%，日均增量>10000，上期进审量>0",
        from_sql=risk_domain_spike_source_sql(time_range),
        where_sql=(
            "cur.prev_avg_review_in_cnt > 0 "
            "AND cur.growth_rate > 0.5 "
            "AND cur.daily_delta > 10000"
        ),
        warning_dimension=WARNING_DIMENSION_RISK_DOMAIN,
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


def sql_by_level(time_range: dict[str, Any] | None = None) -> dict[str, str]:
    return {
        "notice": build_notice_sql(time_range),
        "P2": build_p2_sql(time_range),
        "P1": build_p1_sql(time_range),
        "P0": build_p0_sql(time_range),
    }


def build_records(
    payloads: dict[str, dict[str, Any]],
    levels: list[str],
    sql_map: dict[str, str],
    *,
    row_enricher: RowEnricher | None = None,
    time_range: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    query_plan = build_query_plan(levels, sql_map, time_range=time_range)
    stop = detect_execution_stop(payloads, levels)
    if stop:
        return build_stopped_records(
            payloads=payloads,
            query_plan=query_plan,
            time_range=time_range,
            status=stop["status"],
            stop_reason=stop["stop_reason"],
        )
    plus1_cutoff_date = query_plan["time_range"].get("current_start")
    level_results = {
        level: build_level_result(
            level,
            payloads[level],
            row_enricher=row_enricher,
            plus1_cutoff_date=plus1_cutoff_date,
        )
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
            "id": event_id_for_time_range(time_range),
            "period": query_plan["time_range"],
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
            "id": event_id_for_time_range(time_range),
            "input": build_input_summary(query_plan["time_range"]),
            "run_mode": "debug_only",
            "scenario_key": SCENARIO_KEY,
            "task_type": "low_label_rate_grading",
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


def detect_execution_stop(
    payloads: dict[str, dict[str, Any]],
    levels: list[str],
) -> dict[str, str] | None:
    for level in levels:
        payload = payloads.get(level)
        if not isinstance(payload, dict):
            return {
                "status": "failed",
                "stop_reason": f"missing_query_payload:{level}",
            }
        if payload.get("status") != "success":
            return {
                "status": "failed",
                "stop_reason": f"query_failed:{level}:{payload.get('status', 'unknown')}",
            }
        data = payload.get("data")
        if not isinstance(data, dict):
            return {
                "status": "failed",
                "stop_reason": f"missing_query_data:{level}",
            }
        if data.get("truncated") is not False:
            return {
                "status": "degraded",
                "stop_reason": f"query_result_truncated:{level}",
            }
    return None


def build_stopped_records(
    *,
    payloads: dict[str, dict[str, Any]],
    query_plan: dict[str, Any],
    time_range: dict[str, Any] | None,
    status: str,
    stop_reason: str,
) -> list[dict[str, Any]]:
    query_plan["tool_calls"] = []
    source_footer = build_source_footer(payloads, query_plan)
    source_footer.update(
        {
            "confidence_tier": "low",
            "review_status": "debug_only_execution_blocked",
            "limitations": list(source_footer["limitations"]) + [stop_reason],
        }
    )
    readonly_execution = {
        "execution_id": f"ROE-{query_plan['query_plan_id']}",
        "execution_mode": "real_readonly_query",
        "analysis_mode": "low_label_rate_grading",
        "status": status,
        "source_tier": "governed_dataset",
        "source_name": f"{DATASET_NAME} ({DATASET_ID})",
        "data_freshness": source_footer["data_freshness"],
        "level_counts": {},
        "row_count": 0,
        "truncated": status == "degraded",
        "level_results": {},
        "comprehensive_results": [],
        "evidence_fields": [],
        "metric_formula": METRIC_FORMULA,
        "quality_checks": {
            "freshness_gate": "not_verified",
            "denominator_not_zero": "not_verified",
            "field_mapping_check": "not_verified",
            "forbidden_source_check": "not_verified",
            "truncation_check": "failed" if status == "degraded" else "not_verified",
            "grading_rule_check": "not_executed",
        },
        "limitations": [stop_reason],
    }
    sample = {
        "record_type": "sample",
        "id": event_id_for_time_range(time_range),
        "input": build_input_summary(query_plan["time_range"]),
        "run_mode": "debug_only",
        "scenario_key": SCENARIO_KEY,
        "task_type": "low_label_rate_grading",
        "analysis_mode": "low_label_rate_grading",
        "QueryPlan": query_plan,
        "tool_call_records": [],
        "readonly_execution": readonly_execution,
        "source_footer": source_footer,
        "stop_reason": stop_reason,
        "outputs": ["QueryPlan", "readonly_execution", "source_footer", "stop_reason"],
        "permission_checks": {
            "tool_calls": [],
            "read_only": True,
            "real_query_executed": False,
            "real_notification_blocked": True,
            "online_write_blocked": True,
        },
        "result": status,
    }
    return [
        {
            "record_type": "environment",
            "scenario_key": SCENARIO_KEY,
            "id": event_id_for_time_range(time_range),
            "period": query_plan["time_range"],
            "run_mode": "debug_only",
            "execution_mode": "real_readonly_query",
            "analysis_mode": "low_label_rate_grading",
            "real_query_executed": False,
            "real_notification_blocked": True,
            "online_write_blocked": True,
            "result": status,
            "stop_reason": stop_reason,
        },
        sample,
    ]


def build_input_summary(time_range: dict[str, Any]) -> str:
    if time_range.get("current_start") and time_range.get("current_end"):
        return (
            f"{time_range['current_start']}~{time_range['current_end']} "
            "低打标率策略按单策略维度和风险域维度分P0/P1/P2/notice的情况"
        )
    return "近7天低打标率策略按单策略维度和风险域维度分P0/P1/P2/notice的情况"


def period_label(time_range: dict[str, Any]) -> str:
    if time_range.get("current_start") and time_range.get("current_end"):
        return f"{time_range['current_start']}~{time_range['current_end']}"
    return "近7天"


def duration_label(time_range: dict[str, Any]) -> str:
    if time_range.get("current_start") and time_range.get("current_end"):
        return (
            f"{time_range['current_start']}_to_{time_range['current_end']}"
            f"_with_{time_range.get('history_days', HISTORY_DAYS)}_day_history"
        )
    return "trailing_7_days_with_28_day_history"


def default_grading_time_range() -> dict[str, Any]:
    return {
        "type": "weekly_grading_window",
        "current_days": CURRENT_DAYS,
        "history_days": HISTORY_DAYS,
        "current_where": "`[p_date]` >= today() - 7 AND `[p_date]` < today()",
        "history_where": "`[p_date]` >= today() - 28 AND `[p_date]` < today()",
    }


def build_query_plan(
    levels: list[str],
    sql_map: dict[str, str],
    *,
    time_range: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_time_range = time_range or default_grading_time_range()
    return {
        "query_plan_id": query_plan_id_for_time_range(time_range),
        "scenario_key": SCENARIO_KEY,
        "task_type": "low_label_rate_grading",
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
        "time_range": resolved_time_range,
        "dimensions": list(DIMENSIONS),
        "filters": [
            "standard_review_scope",
            "label_rate_lt_thresholds",
            "default_three_dimension_strategy_grain",
            "risk_domain_low_strategy_rollup",
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
            "grain_check_three_dimension_strategy",
            "risk_domain_rollup_check",
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
        "input_summary": (
            f"Dataset {DATASET_ID}; level={level}; "
            f"period={period_label(query_plan['time_range'])}; "
            "low-label-rate grading."
        ),
        "output_summary": f"Returned {data['rowCount']} rows; truncated={data.get('truncated')}.",
        "status": "success",
        "latency_ms": context.get("execution_time_ms", 0),
    }


def build_level_result(
    level: str,
    payload: dict[str, Any],
    *,
    row_enricher: RowEnricher | None = None,
    plus1_cutoff_date: str | None = None,
) -> dict[str, Any]:
    rows = dedupe_level_rows(
        normalize_rows(
            payload,
            row_enricher=row_enricher,
            plus1_cutoff_date=plus1_cutoff_date,
        ),
        level,
    )
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
    plus1_cutoff_date: str | None = None,
) -> list[dict[str, Any]]:
    columns = payload["data"]["columns"]
    plus1_index = load_plus1_agreed_index()
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
        ensure_plus1_fields(normalized, plus1_index, plus1_cutoff_date)
        rows.append(normalized)
    return rows


def ensure_poc_fields(row: dict[str, Any]) -> None:
    poc_name = row.get("poc_name") or row.get("POC") or "未映射"
    row["poc_name"] = poc_name
    row["POC"] = poc_name
    row.setdefault("poc_open_id", None)
    row.setdefault("poc_mapping_status", "not_resolved_by_analysis_script")


def plus1_asset_candidate_paths() -> list[Path]:
    script_path = Path(__file__).resolve()
    return [
        script_path.parents[1]
        / "assets"
        / "efficiency-label-rate"
        / PLUS1_AGREED_ASSET,
    ]


def load_plus1_agreed_index() -> dict[str, dict[str, Any]]:
    for path in plus1_asset_candidate_paths():
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {
            str(entry.get("strategy_id", "")).strip(): entry
            for entry in payload.get("entries", [])
            if str(entry.get("strategy_id", "")).strip()
        }
    expected = plus1_asset_candidate_paths()[0]
    raise FileNotFoundError(f"Missing required +1 governance asset: {expected}")


def ensure_plus1_fields(
    row: dict[str, Any],
    plus1_index: dict[str, dict[str, Any]],
    cutoff_date: str | None,
) -> None:
    strategy_id = str(row.get("strategy_id") or "").strip()
    entry = plus1_index.get(strategy_id)
    if entry:
        row["is_plus1_agreed"] = "是"
        row["plus1_update_date"] = entry.get("update_date") or ""
    else:
        row["is_plus1_agreed"] = "否"
        row["plus1_update_date"] = ""
    update_date = parse_optional_date(row["plus1_update_date"])
    cutoff = parse_optional_date(cutoff_date)
    row["plus1_agreed_before_current_period"] = (
        "是"
        if row["is_plus1_agreed"] == "是"
        and update_date is not None
        and cutoff is not None
        and update_date < cutoff
        else "否"
    )


def parse_optional_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10].replace("/", "-"))
    except ValueError as exc:
        raise ValueError(f"Invalid ISO date value: {value!r}") from exc


def dimension_key(row: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "")) for field in DEDUPE_DIMENSIONS)


def dedupe_level_rows(rows: list[dict[str, Any]], level: str) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, ...], dict[str, Any]] = {}
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
    best_by_key: dict[tuple[str, ...], dict[str, Any]] = {}
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
    checked_at = (
        max(
            (
                payload.get("context", {}).get("timestamp", "")
                for payload in payloads.values()
            ),
            default="",
        )
        or "unknown"
    )
    time_range = query_plan["time_range"]
    explicit_period = time_range.get("type") == "explicit_weekly_grading_window"
    if explicit_period:
        checked_at = str(time_range.get("checked_at") or checked_at)
        data_freshness = (
            f"p_date >= {time_range['history_start']} "
            f"AND p_date <= {time_range['current_end']}; "
            f"current_period={time_range['current_start']}~{time_range['current_end']}; "
            f"checked_at={checked_at}"
        )
        data_lag = f"uses closed p_date partitions through {time_range['current_end']}"
    else:
        data_freshness = (
            "p_date >= today() - 28 AND p_date < today(); "
            f"checked_at={checked_at}"
        )
        data_lag = "uses closed p_date partitions where p_date < today()"
    return {
        "source_tier": "governed_dataset",
        "metric_definition_version": "draft",
        "data_freshness": data_freshness,
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
        "time_window": time_range,
        "data_lag": data_lag,
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
            "warning_dimension",
            "severity_level",
            "mach_root_label_name",
            "strategy_id",
            "strategy_name",
            "max_data_date",
            "POC",
            "poc_name",
            "avg_review_in_cnt",
            "avg_review_done_cnt",
            "avg_label_cnt",
            "label_rate",
            "is_plus1_agreed",
            "plus1_update_date",
            "plus1_agreed_before_current_period",
            "hit_rule_ids",
            "hit_conditions",
        ],
        "metric_formula": METRIC_FORMULA,
        "rule_source": RULE_SOURCE,
        "quality_checks": {
            "freshness_gate": "passed_via_p_date_filter",
            "denominator_not_zero": "passed",
            "field_mapping_check": "passed",
            "grain_check": "passed_warning_dimension_mach_root_label_strategy",
            "risk_domain_rollup": "passed_low_strategy_rollup_by_mach_root_label",
            "poc_name_mapping": "passed_name_only",
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
        "limitations": readonly_execution["limitations"],
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
    time_range = query_plan["time_range"]
    period = period_label(time_range)
    return {
        "analysis_id": f"AN-{event_id_for_time_range(time_range)}",
        "event_id": event_id_for_time_range(time_range),
        "templates_used": ["custom_readonly", "impact_assessment", "sop_decision"],
        "query_plan": compact_query_plan(query_plan),
        "readonly_execution": readonly_execution,
        "impact_assessment": {
            "summary": f"{period} 低打标率分级完成，综合命中 {readonly_execution['row_count']} 个预警分组；{summary}。",
            "impact_scope": f"comprehensive_strategy_group_count={readonly_execution['row_count']}",
            "risk_level": highest_hit_level(level_counts),
            "business_risk": "本结果为分级查询结果，不自动触发通知或状态写入。",
            "duration": duration_label(time_range),
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
        "scenario_key": query_plan["scenario_key"],
        "task_type": query_plan["task_type"],
        "analysis_mode": query_plan["analysis_mode"],
        "metric_id": query_plan["metric_id"],
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
        "review_required": query_plan["review_required"],
    }


def build_smoke_payloads(levels: list[str]) -> dict[str, dict[str, Any]]:
    return {level: build_smoke_payload(level, index) for index, level in enumerate(levels)}


def build_smoke_payload(level: str, index: int = 0) -> dict[str, Any]:
    row = [
        WARNING_DIMENSION_SINGLE_STRATEGY,
        level,
        LEVEL_PRIORITY[level],
        "不良行为或争议价值观",
        f"strategy_{level.lower()}_{index}",
        f"{level}低打标率策略",
        7,
        "2026-07-12",
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
        "否",
        "",
        "否",
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
