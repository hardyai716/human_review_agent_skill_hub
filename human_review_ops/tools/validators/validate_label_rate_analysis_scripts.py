#!/usr/bin/env python3
"""Smoke-validate reusable label-rate analysis scripts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


HUMAN_REVIEW_OPS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = HUMAN_REVIEW_OPS_ROOT.parent
SCRIPT_DIR = HUMAN_REVIEW_OPS_ROOT / "skills" / "analysis" / "scripts"
SCRIPT_PATH = SCRIPT_DIR / "label_rate_analysis.py"
sys.path.insert(0, str(SCRIPT_DIR))

import label_rate_analysis  # noqa: E402


REQUIRED_QUERY_PLAN_FIELDS = {
    "query_plan_id",
    "scenario_key",
    "task_type",
    "analysis_mode",
    "metric_id",
    "metric_entities",
    "time_range",
    "dimensions",
    "filters",
    "levels",
    "level_priority",
    "source_priority",
    "allowed_sources",
    "forbidden_sources",
    "fallback_reason",
    "quality_checks",
    "review_required",
    "execution_mode",
    "sql_by_level",
}
REQUIRED_SOURCE_FOOTER_FIELDS = {
    "source_tier",
    "metric_definition_version",
    "data_freshness",
    "owner",
    "confidence_tier",
    "review_status",
    "scenario_key",
    "metric_id",
    "quality_checks",
    "metric_contract_ref",
    "dataset_reference_ref",
    "analysis_ref",
    "query_plan_id",
    "time_window",
    "data_lag",
    "source_priority",
    "actual_source",
    "filters",
    "dimensions",
    "limitations",
    "run_mode",
}
REQUIRED_SQL_SNIPPETS = [
    "`[p_date]` >= today() - 7",
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
    "`[机审一级标签]` IS NULL OR `[机审一级标签]` = '' OR `[机审一级标签]` IN",
    "multiIf(",
    "高价值-兜底vv进审', '高热'",
    "商业化付费视频全人审ugc', '商业化'",
    "【ZL推人】麒麟芯片9030', '指令舆情相关'",
    "position(ifNull(`[strategy_name]`, ''), 'ZL') > 0, '指令舆情相关'",
    "position(ifNull(`[strategy_name]`, ''), '商业化') > 0, '商业化'",
    "position(ifNull(`[strategy_name]`, ''), '政媒') > 0, '政媒'",
    ") AS mach_root_label_key",
    "ifNull(`[strategy_id]`, '（空/strategy_id）') AS strategy_id_key",
    "ifNull(`[strategy_name]`, '（空/strategy_name）') AS strategy_name_key",
    "GROUP BY mach_root_label_key, strategy_id_key, strategy_name_key",
    "SUM(jin_shen) / COUNT(DISTINCT dt) AS avg_review_in_cnt",
    "if(SUM(wan_shen) = 0, 0, SUM(da_biao) / SUM(wan_shen)) AS label_rate",
    "MAX(dt) AS max_data_date",
]
LEVEL_WINDOW_SNIPPETS = {
    "notice": ["`[p_date]` >= today() - 7"],
    "P2": ["`[p_date]` >= today() - 14", "风险域维度"],
    "P1": ["`[p_date]` >= today() - 14", "风险域维度"],
    "P0": ["`[p_date]` >= today() - 28", "风险域维度"],
}


def main() -> None:
    validate_imported_module_contract()
    validate_explicit_period_contract()
    validate_report_flow_contract()
    validate_cli_dry_run()
    print("Label-rate analysis scripts OK")


def validate_imported_module_contract() -> None:
    levels = list(label_rate_analysis.DEFAULT_LEVELS)
    sql_map = label_rate_analysis.sql_by_level()
    query_plan = label_rate_analysis.build_query_plan(levels, sql_map)
    payloads = label_rate_analysis.build_smoke_payloads(levels)
    records = label_rate_analysis.build_records(payloads, levels, sql_map)
    sample = records[1]

    assert_query_plan(query_plan, levels)
    assert_sql_by_level(sql_map, levels)
    assert_records(sample, levels)
    assert_source_footer(sample["source_footer"], query_plan)
    assert_readonly_execution(sample["readonly_execution"], levels)
    assert_analysis_result(sample)


def validate_explicit_period_contract() -> None:
    time_range = label_rate_analysis.build_grading_time_range(
        start_date="2026-07-06",
        end_date="2026-07-12",
    )
    sql_map = label_rate_analysis.sql_by_level(time_range)
    if any("today()" in sql for sql in sql_map.values()):
        raise AssertionError("Explicit period SQL must not contain today().")
    if "`[p_date]` >= '2026-07-06'" not in sql_map["notice"]:
        raise AssertionError("Explicit notice SQL missing current period start.")
    if "`[p_date]` < '2026-07-13'" not in sql_map["notice"]:
        raise AssertionError("Explicit notice SQL missing current period exclusive end.")
    if "`[p_date]` >= '2026-06-15'" not in sql_map["P0"]:
        raise AssertionError("Explicit P0 SQL missing four-week history start.")
    query_plan = label_rate_analysis.build_query_plan(
        list(label_rate_analysis.DEFAULT_LEVELS),
        sql_map,
        time_range=time_range,
    )
    if query_plan["time_range"].get("current_start") != "2026-07-06":
        raise AssertionError("Explicit QueryPlan current_start mismatch.")
    if query_plan["query_plan_id"] != (
        "QP-ELR-REAL-LOW-LABEL-RATE-GRADING-20260706-20260712"
    ):
        raise AssertionError("Explicit QueryPlan id must include period.")


def validate_cli_dry_run() -> None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--dry-run",
            "--levels",
            ",".join(label_rate_analysis.DEFAULT_LEVELS),
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"CLI dry-run stdout is not JSON: {completed.stdout}") from exc
    if payload.get("schema_version") != label_rate_analysis.SCHEMA_VERSION:
        raise AssertionError("CLI dry-run schema_version mismatch.")
    if payload.get("dry_run") is not True:
        raise AssertionError("CLI dry-run must mark dry_run=true.")
    for field in (
        "QueryPlan",
        "source_footer",
        "readonly_execution",
        "analysis_result",
        "provenance",
    ):
        if field not in payload:
            raise AssertionError(f"CLI dry-run missing {field}.")
    expected_safety = {
        "sql_executed": False,
        "notification_sent": False,
        "online_write_executed": False,
        "real_query_executed": False,
    }
    if payload.get("safety") != expected_safety:
        raise AssertionError(f"Unexpected CLI dry-run safety: {payload.get('safety')}")
    if payload.get("source_footer", {}).get("review_status") == "real_readonly_query_executed":
        raise AssertionError("CLI dry-run must not claim a real readonly query was executed.")
    if payload.get("readonly_execution", {}).get("execution_mode") == "real_readonly_query":
        raise AssertionError("CLI dry-run must not label execution_mode as real_readonly_query.")


def validate_report_flow_contract() -> None:
    sql = label_rate_analysis.build_report_flow_low_label_rate_sql()
    required_snippets = [
        "`[进审日期]` >= today() - 7",
        "`[进审日期]` < today()",
        "ifNull(`[enpool_reason]`, '（空/enpool_reason）') AS enpool_reason_key",
        "enpool_reason_key AS enpool_reason",
        "SUM(report_review_done_cnt) / count(distinct review_date_key) AS avg_report_review_done_cnt",
        "SUM(report_label_cnt) / count(distinct review_date_key) AS avg_report_label_cnt",
        "SUM(report_label_cnt) / nullIf(SUM(report_review_done_cnt), 0) AS report_label_rate",
        "`[终轮队列名称]` IN",
        "`[一轮队列名称]` IN",
        "`[任务类型]` IN ('关注-【举报专项】任务链路流转')",
        "`[一轮队列名称]` NOT LIKE '%兜底%'",
        "GROUP BY enpool_reason_key",
        "HAVING SUM(report_review_done_cnt) > 0",
        "AND SUM(report_label_cnt) / nullIf(SUM(report_review_done_cnt), 0) < 0.1",
    ]
    for snippet in required_snippets:
        if snippet not in sql:
            raise AssertionError(f"Report-flow SQL missing snippet: {snippet}")
    forbidden_snippets = [
        "partition",
        "`[p_date]`",
        "`[reason]`",
        "`[完审量_reviewid]`",
        "`[打标量__reviewid]`",
        "3888816",
    ]
    for snippet in forbidden_snippets:
        if snippet in sql:
            raise AssertionError(f"Report-flow SQL contains forbidden snippet: {snippet}")

    payload = label_rate_analysis.build_report_flow_dry_run_payload(dry_run=True)
    query_plan = payload["QueryPlan"]
    if query_plan.get("data_direction") != "report_flow":
        raise AssertionError("Report-flow QueryPlan data_direction mismatch.")
    if query_plan.get("source_profile") != "report_flow_review":
        raise AssertionError("Report-flow QueryPlan source_profile mismatch.")
    if query_plan.get("metric_id") != "report_label_rate":
        raise AssertionError("Report-flow QueryPlan metric_id mismatch.")
    if query_plan.get("metric_entities", [{}])[0].get("aeolus_dataset_id") != "3952594":
        raise AssertionError("Report-flow QueryPlan dataset mismatch.")
    if query_plan.get("time_range", {}).get("date_field") != "进审日期":
        raise AssertionError("Report-flow QueryPlan must use 进审日期.")
    if query_plan.get("dimensions") != ["enpool_reason"]:
        raise AssertionError("Report-flow QueryPlan dimensions mismatch.")
    if payload.get("safety", {}).get("sql_executed") is not False:
        raise AssertionError("Report-flow dry-run must not execute SQL.")
    explicit = label_rate_analysis.build_report_flow_dry_run_payload(
        dry_run=True,
        time_range=label_rate_analysis.build_grading_time_range(
            start_date="2026-07-06",
            end_date="2026-07-12",
        ),
    )
    explicit_sql = explicit["QueryPlan"]["sql"]
    if "today()" in explicit_sql:
        raise AssertionError("Explicit report-flow SQL must not contain today().")
    if "`[进审日期]` >= '2026-07-06'" not in explicit_sql:
        raise AssertionError("Explicit report-flow SQL missing start date.")


def assert_query_plan(query_plan: dict[str, Any], levels: list[str]) -> None:
    missing = REQUIRED_QUERY_PLAN_FIELDS - set(query_plan)
    if missing:
        raise AssertionError(f"QueryPlan missing fields: {sorted(missing)}")
    if query_plan["scenario_key"] != label_rate_analysis.SCENARIO_KEY:
        raise AssertionError("QueryPlan scenario_key mismatch.")
    if query_plan["analysis_mode"] != "low_label_rate_grading":
        raise AssertionError("QueryPlan analysis_mode mismatch.")
    if query_plan["metric_id"] != "label_rate":
        raise AssertionError("QueryPlan metric_id mismatch.")
    if query_plan["dimensions"] != label_rate_analysis.DIMENSIONS:
        raise AssertionError("QueryPlan dimensions mismatch.")
    if query_plan["levels"] != levels:
        raise AssertionError("QueryPlan levels mismatch.")
    if query_plan["level_priority"] != label_rate_analysis.LEVEL_PRIORITY:
        raise AssertionError("QueryPlan level_priority mismatch.")
    if query_plan["review_required"] is not False:
        raise AssertionError("QueryPlan review_required should be false for readonly runner.")
    metric_entity = query_plan["metric_entities"][0]
    if metric_entity["aeolus_dataset_id"] != label_rate_analysis.DATASET_ID:
        raise AssertionError("QueryPlan dataset id mismatch.")
    if metric_entity["aeolus_metric_id"] != "10000036292379":
        raise AssertionError("QueryPlan Aeolus metric id mismatch.")


def assert_sql_by_level(sql_map: dict[str, str], levels: list[str]) -> None:
    if set(sql_map) != set(label_rate_analysis.DEFAULT_LEVELS):
        raise AssertionError("sql_by_level must generate all default levels.")
    for level in levels:
        sql = sql_map.get(level, "")
        if not sql:
            raise AssertionError(f"Missing SQL for level: {level}")
        for snippet in REQUIRED_SQL_SNIPPETS + LEVEL_WINDOW_SNIPPETS[level]:
            if snippet not in sql:
                raise AssertionError(f"{level} SQL missing snippet: {snippet}")
        if "AS mach_root_label_name,\n    ifNull(`[strategy_id]`" in sql:
            raise AssertionError(
                f"{level} SQL regressed to physical-field alias collision."
            )
        if "INSERT " in sql.upper() or "DELETE " in sql.upper():
            raise AssertionError(f"{level} SQL must stay readonly.")


def assert_records(sample: dict[str, Any], levels: list[str]) -> None:
    if sample.get("record_type") != "sample":
        raise AssertionError("Sample record missing.")
    if sample.get("QueryPlan", {}).get("levels") != levels:
        raise AssertionError("Sample QueryPlan levels mismatch.")
    if sample.get("permission_checks", {}).get("read_only") is not True:
        raise AssertionError("Sample permission check read_only mismatch.")
    if sample.get("permission_checks", {}).get("real_notification_blocked") is not True:
        raise AssertionError("Sample must block real notification.")
    if sample.get("permission_checks", {}).get("online_write_blocked") is not True:
        raise AssertionError("Sample must block online writes.")


def assert_source_footer(
    source_footer: dict[str, Any],
    query_plan: dict[str, Any],
) -> None:
    missing = REQUIRED_SOURCE_FOOTER_FIELDS - set(source_footer)
    if missing:
        raise AssertionError(f"source_footer missing fields: {sorted(missing)}")
    if source_footer["review_status"] != "real_readonly_query_executed":
        raise AssertionError("source_footer review_status mismatch.")
    if source_footer["confidence_tier"] != "high":
        raise AssertionError("source_footer confidence_tier mismatch.")
    if source_footer["query_plan_id"] != query_plan["query_plan_id"]:
        raise AssertionError("source_footer query_plan_id mismatch.")
    if source_footer["dimensions"] != query_plan["dimensions"]:
        raise AssertionError("source_footer dimensions mismatch.")
    if source_footer["actual_source"] != f"aeolus_dataset:{label_rate_analysis.DATASET_ID}":
        raise AssertionError("source_footer actual_source mismatch.")


def assert_readonly_execution(
    readonly_execution: dict[str, Any],
    levels: list[str],
) -> None:
    if readonly_execution["execution_mode"] != "real_readonly_query":
        raise AssertionError("readonly_execution mode mismatch.")
    if readonly_execution["analysis_mode"] != "low_label_rate_grading":
        raise AssertionError("readonly_execution analysis_mode mismatch.")
    if readonly_execution["status"] != "success":
        raise AssertionError("readonly_execution status mismatch.")
    if readonly_execution["row_count"] != len(levels):
        raise AssertionError("readonly_execution row_count mismatch for smoke payloads.")
    level_results = readonly_execution["level_results"]
    comprehensive = readonly_execution["comprehensive_results"]
    if len(comprehensive) != len(levels):
        raise AssertionError("comprehensive smoke rows mismatch.")
    for level in levels:
        result = level_results[level]
        if result["severity_priority"] != label_rate_analysis.LEVEL_PRIORITY[level]:
            raise AssertionError(f"{level} severity priority mismatch.")
        if result["truncated"] is not False:
            raise AssertionError(f"{level} smoke result must not be truncated.")
        row = result["rows"][0]
        for field in (
            "warning_dimension",
            "severity_level",
            "severity_priority",
            "mach_root_label_name",
            "strategy_id",
            "strategy_name",
            "max_data_date",
            "POC",
            "avg_review_in_cnt",
            "avg_review_done_cnt",
            "avg_label_cnt",
            "label_rate",
            "hit_rule_ids",
            "hit_conditions",
        ):
            if field not in row:
                raise AssertionError(f"{level} normalized row missing {field}.")
        if not isinstance(row["label_rate"], float):
            raise AssertionError(f"{level} label_rate must be normalized to float.")
        if not isinstance(row["data_days"], int):
            raise AssertionError(f"{level} data_days must be normalized to int.")


def assert_analysis_result(sample: dict[str, Any]) -> None:
    analysis_result = sample.get("analysis_result")
    if not isinstance(analysis_result, dict):
        raise AssertionError("Missing analysis_result.")
    if analysis_result["readonly_execution"] != sample["readonly_execution"]:
        raise AssertionError("analysis_result readonly_execution mismatch.")
    if analysis_result["source_footer"] != sample["source_footer"]:
        raise AssertionError("analysis_result source_footer mismatch.")
    if analysis_result["provenance"] != sample["provenance"]:
        raise AssertionError("analysis_result provenance mismatch.")
    if analysis_result["sop_decision"]["required_confirmation"] is not False:
        raise AssertionError("analysis_result should not require confirmation.")


if __name__ == "__main__":
    main()
