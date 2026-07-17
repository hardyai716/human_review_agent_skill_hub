#!/usr/bin/env python3
"""Validate real readonly low-label-rate grading results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_KEY = "efficiency-label-rate"
DEFAULT_RESULTS = (
    ROOT
    / "evals"
    / SCENARIO_KEY
    / "stage_1_runs"
    / "20260713_real_readonly_label_rate_grading_results.jsonl"
)
LEVEL_ORDER = ["P0", "P1", "P2", "notice"]
LEVEL_PRIORITY = {"P0": 0, "P1": 1, "P2": 2, "notice": 3}
DIMENSIONS = ["mach_root_label_name", "strategy_id", "strategy_name"]
DEDUPE_DIMENSIONS = ["warning_dimension", *DIMENSIONS]
REQUIRED_SQL_SNIPPETS = [
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


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate(results_path: Path) -> None:
    records = load_jsonl(results_path)
    environment = next(
        (record for record in records if record.get("record_type") == "environment"),
        None,
    )
    sample = next(
        (record for record in records if record.get("record_type") == "sample"),
        None,
    )
    if not environment:
        raise AssertionError("Missing environment record.")
    if not sample:
        raise AssertionError("Missing sample record.")

    assert_environment(environment)
    assert_permission(sample)
    assert_query_plan(sample)
    assert_tool_calls(sample)
    assert_readonly_execution(sample)
    assert_analysis_result(sample)
    assert_no_side_effect_outputs(sample)


def assert_environment(environment: dict[str, Any]) -> None:
    if environment.get("scenario_key") != SCENARIO_KEY:
        raise AssertionError("Environment scenario_key mismatch.")
    if environment.get("execution_mode") != "real_readonly_query":
        raise AssertionError("Environment execution_mode mismatch.")
    if environment.get("analysis_mode") != "low_label_rate_grading":
        raise AssertionError("Environment analysis_mode mismatch.")
    if environment.get("real_query_executed") is not True:
        raise AssertionError("Environment must mark real_query_executed=true.")


def assert_permission(sample: dict[str, Any]) -> None:
    permission_checks = sample.get("permission_checks", {})
    if permission_checks.get("read_only") is not True:
        raise AssertionError("Grading query must remain readonly.")
    if permission_checks.get("real_query_executed") is not True:
        raise AssertionError("Permission check must record real query execution.")
    if permission_checks.get("real_notification_blocked") is not True:
        raise AssertionError("Real notification must stay blocked.")
    if permission_checks.get("online_write_blocked") is not True:
        raise AssertionError("Online writes must stay blocked.")


def assert_query_plan(sample: dict[str, Any]) -> None:
    query_plan = sample.get("QueryPlan")
    if not isinstance(query_plan, dict):
        raise AssertionError("Missing QueryPlan.")
    if query_plan.get("scenario_key") != SCENARIO_KEY:
        raise AssertionError("QueryPlan scenario_key mismatch.")
    if query_plan.get("analysis_mode") != "low_label_rate_grading":
        raise AssertionError("QueryPlan analysis_mode mismatch.")
    if query_plan.get("metric_id") != "label_rate":
        raise AssertionError("QueryPlan metric_id mismatch.")
    if query_plan.get("review_required") is not False:
        raise AssertionError("Readonly grading should not require manual confirmation.")
    if query_plan.get("execution_mode") != "real_readonly_query":
        raise AssertionError("QueryPlan execution_mode mismatch.")
    if query_plan.get("fallback_reason") != "complex_grading_rule_not_covered_by_semantic_layer":
        raise AssertionError("QueryPlan fallback_reason mismatch.")
    if query_plan.get("dimensions") != DIMENSIONS:
        raise AssertionError("Grading dimensions must be mach label, strategy id, strategy name.")
    if query_plan.get("levels") != ["notice", "P2", "P1", "P0"]:
        raise AssertionError("Grading must run notice/P2/P1/P0.")
    if query_plan.get("level_priority") != LEVEL_PRIORITY:
        raise AssertionError("Grading level priority mismatch.")
    if query_plan.get("time_range", {}).get("current_days") != 7:
        raise AssertionError("Grading current_days mismatch.")
    if query_plan.get("time_range", {}).get("history_days") != 28:
        raise AssertionError("Grading history_days mismatch.")

    metric_entity = query_plan["metric_entities"][0]
    if metric_entity.get("aeolus_dataset_id") != "3888816":
        raise AssertionError("QueryPlan must bind dataset 3888816.")
    if metric_entity.get("aeolus_metric_id") != "10000036292379":
        raise AssertionError("QueryPlan must bind Aeolus label_rate metric.")

    sql_by_level = query_plan.get("sql_by_level")
    if not isinstance(sql_by_level, dict):
        raise AssertionError("Missing sql_by_level.")
    for level in query_plan["levels"]:
        sql = sql_by_level.get(level, "")
        if not sql:
            raise AssertionError(f"Missing SQL for level: {level}")
        for snippet in REQUIRED_SQL_SNIPPETS + expected_level_window_snippets(
            query_plan,
            level,
        ):
            if snippet not in sql:
                raise AssertionError(f"{level} SQL missing snippet: {snippet}")
        if "AS mach_root_label_name,\n    ifNull(`[strategy_id]`" in sql:
            raise AssertionError(
                f"{level} SQL regressed to physical-field alias collision."
            )


def expected_level_window_snippets(
    query_plan: dict[str, Any],
    level: str,
) -> list[str]:
    time_range = query_plan.get("time_range", {})
    if not time_range.get("current_start"):
        return LEVEL_WINDOW_SNIPPETS[level]
    current_start = time_range["current_start"]
    current_end_exclusive = time_range["current_end_exclusive"]
    previous_windows = time_range.get("previous_windows", [])
    snippets = [
        f"`[p_date]` >= '{current_start}'",
        f"`[p_date]` < '{current_end_exclusive}'",
    ]
    if level in {"P2", "P1"} and previous_windows:
        snippets.append(f"`[p_date]` >= '{previous_windows[0]['start']}'")
        snippets.append("风险域维度")
    if level == "P0":
        snippets.append(f"`[p_date]` >= '{time_range['history_start']}'")
        snippets.append("风险域维度")
    return snippets


def assert_tool_calls(sample: dict[str, Any]) -> None:
    query_plan = sample["QueryPlan"]
    tool_call_records = sample.get("tool_call_records", [])
    if len(tool_call_records) != 4:
        raise AssertionError("Expected four level tool_call_records.")
    if query_plan.get("tool_calls") != [
        tool_call["tool_call_id"] for tool_call in tool_call_records
    ]:
        raise AssertionError("QueryPlan tool_calls mismatch.")
    for tool_call in tool_call_records:
        if tool_call.get("tool_name") != "bytedcli_aeolus_query":
            raise AssertionError("Unexpected tool_name.")
        if tool_call.get("permission_level") != "readonly":
            raise AssertionError("Tool call must be readonly.")
        if tool_call.get("execution_mode") != "real_readonly_query":
            raise AssertionError("Tool call execution_mode mismatch.")
        if tool_call.get("real_query_executed") is not True:
            raise AssertionError("Tool call must mark real_query_executed=true.")
        if tool_call.get("fallback_reason") != query_plan["fallback_reason"]:
            raise AssertionError("Tool call fallback_reason mismatch.")


def assert_readonly_execution(sample: dict[str, Any]) -> None:
    execution = sample.get("readonly_execution")
    if not isinstance(execution, dict):
        raise AssertionError("Missing readonly_execution.")
    if execution.get("execution_mode") != "real_readonly_query":
        raise AssertionError("readonly_execution mode mismatch.")
    if execution.get("analysis_mode") != "low_label_rate_grading":
        raise AssertionError("readonly_execution analysis_mode mismatch.")
    if execution.get("status") != "success":
        raise AssertionError("readonly_execution must succeed.")
    if execution.get("source_tier") != "governed_dataset":
        raise AssertionError("readonly_execution source_tier mismatch.")
    if execution.get("truncated") is not False:
        raise AssertionError("Result must not be truncated.")
    if execution.get("row_count", 0) <= 0:
        raise AssertionError("Comprehensive result must include rows.")

    level_results = execution.get("level_results")
    if not isinstance(level_results, dict):
        raise AssertionError("Missing level_results.")
    for level, priority in LEVEL_PRIORITY.items():
        result = level_results.get(level)
        if not isinstance(result, dict):
            raise AssertionError(f"Missing level result: {level}")
        if result.get("severity_level") != level:
            raise AssertionError(f"Level result severity mismatch: {level}")
        if result.get("severity_priority") != priority:
            raise AssertionError(f"Level result priority mismatch: {level}")
        if result.get("truncated") is not False:
            raise AssertionError(f"Level result truncated: {level}")
        seen_keys: set[tuple[str, ...]] = set()
        for row in result.get("rows", []):
            assert_grading_row(row, level, priority)
            key = dimension_key(row)
            if key in seen_keys:
                raise AssertionError(f"Duplicate dimension key inside level {level}: {key}")
            seen_keys.add(key)

    comprehensive = execution.get("comprehensive_results")
    if not isinstance(comprehensive, list):
        raise AssertionError("Missing comprehensive_results.")
    seen_comprehensive: set[tuple[str, ...]] = set()
    for row in comprehensive:
        assert_grading_row(row, row["severity_level"], row["severity_priority"])
        key = dimension_key(row)
        if key in seen_comprehensive:
            raise AssertionError(f"Duplicate dimension key in comprehensive: {key}")
        seen_comprehensive.add(key)
        highest = highest_level_for_key(key, level_results)
        if row["severity_level"] != highest:
            raise AssertionError("Comprehensive result must keep highest severity.")
    if execution.get("row_count") != len(comprehensive):
        raise AssertionError("readonly_execution row_count mismatch.")

    for field in (
        "warning_dimension",
        "severity_level",
        "mach_root_label_name",
        "strategy_id",
        "strategy_name",
        "max_data_date",
        "POC",
        "avg_review_in_cnt",
        "avg_review_done_cnt",
        "avg_label_cnt",
        "label_rate",
        "is_plus1_agreed",
        "plus1_update_date",
        "hit_rule_ids",
        "hit_conditions",
    ):
        if field not in execution.get("evidence_fields", []):
            raise AssertionError(f"Missing evidence field: {field}")


def assert_grading_row(row: dict[str, Any], level: str, priority: int) -> None:
    if row.get("severity_level") != level:
        raise AssertionError("Row severity_level mismatch.")
    if row.get("severity_priority") != priority:
        raise AssertionError("Row severity_priority mismatch.")
    if row.get("warning_dimension") not in {"单策略维度", "风险域维度"}:
        raise AssertionError("Row warning_dimension mismatch.")
    if not row.get("mach_root_label_name"):
        raise AssertionError("Row mach_root_label_name is required.")
    if row.get("warning_dimension") == "单策略维度":
        for field in ("strategy_id", "strategy_name"):
            if not row.get(field):
                raise AssertionError(f"Single-strategy row {field} is required.")
    if row.get("warning_dimension") == "风险域维度":
        if row.get("strategy_id") or row.get("strategy_name"):
            raise AssertionError("Risk-domain row strategy fields must be empty.")
    if not row.get("max_data_date"):
        raise AssertionError("Row max_data_date is required.")
    if not row.get("POC") and not row.get("poc_name"):
        raise AssertionError("Row POC is required.")
    if row.get("is_plus1_agreed") not in {"是", "否"}:
        raise AssertionError("Row is_plus1_agreed must be 是 or 否.")
    if row.get("is_plus1_agreed") == "否" and row.get("plus1_update_date"):
        raise AssertionError("Non-plus1 row must not have plus1_update_date.")
    if row.get("avg_review_in_cnt", 0) < 0:
        raise AssertionError("avg_review_in_cnt must be non-negative.")
    if row.get("avg_review_done_cnt", 0) <= 0:
        raise AssertionError("avg_review_done_cnt must be positive.")
    if row.get("avg_label_cnt", 0) < 0:
        raise AssertionError("avg_label_cnt must be non-negative.")
    if not (0 <= row.get("label_rate", -1) < 0.1):
        raise AssertionError(f"label_rate out of low-label range: {row}")
    if not row.get("hit_rule_ids"):
        raise AssertionError("hit_rule_ids required.")
    if not row.get("hit_conditions"):
        raise AssertionError("hit_conditions required.")


def dimension_key(row: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "")) for field in DEDUPE_DIMENSIONS)


def highest_level_for_key(
    key: tuple[str, ...],
    level_results: dict[str, dict[str, Any]],
) -> str:
    for level in LEVEL_ORDER:
        for row in level_results[level]["rows"]:
            if dimension_key(row) == key:
                return level
    raise AssertionError(f"Dimension key missing from level results: {key}")


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
    if analysis_result["sop_decision"].get("required_confirmation") is not False:
        raise AssertionError("Readonly answer must not require manual confirmation.")

    source_footer = sample["source_footer"]
    if source_footer.get("review_status") != "real_readonly_query_executed":
        raise AssertionError("source_footer review_status mismatch.")
    if source_footer.get("confidence_tier") != "high":
        raise AssertionError("source_footer confidence_tier mismatch.")

    provenance = sample["provenance"]
    if provenance.get("dataset_id") != "3888816":
        raise AssertionError("provenance dataset_id mismatch.")
    if provenance.get("app_id") != "1128":
        raise AssertionError("provenance app_id mismatch.")
    if provenance.get("levels") != sample["QueryPlan"]["levels"]:
        raise AssertionError("provenance levels mismatch.")
    if provenance.get("tool_call_ids") != sample["QueryPlan"]["tool_calls"]:
        raise AssertionError("provenance tool_call_ids mismatch.")


def assert_no_side_effect_outputs(sample: dict[str, Any]) -> None:
    for forbidden in ("notification_draft", "owner_recommendation", "manual_tracking"):
        if sample.get(forbidden) is not None:
            raise AssertionError(f"Unexpected side-effect output: {forbidden}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_path", nargs="?", default=str(DEFAULT_RESULTS))
    args = parser.parse_args()
    results_path = Path(args.results_path)
    validate(results_path)
    print(f"Stage 1 real readonly label-rate grading OK: {results_path}")


if __name__ == "__main__":
    main()
