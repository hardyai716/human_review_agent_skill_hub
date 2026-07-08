#!/usr/bin/env python3
"""Validate real readonly label-rate query results."""

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
    / "20260708_real_readonly_label_rate_results.jsonl"
)
REQUIRED_SQL_SNIPPETS = [
    "`[p_date]` >= today() - 7",
    "`[p_date]` < today()",
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
    "`[机审一级标签]` IS NULL OR `[机审一级标签]` IN",
    "HAVING review_done_cnt > 0 AND label_rate < 0.1",
]


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

    if environment.get("execution_mode") != "real_readonly_query":
        raise AssertionError("Environment execution_mode mismatch.")
    if environment.get("real_query_executed") is not True:
        raise AssertionError("Environment must mark real_query_executed=true.")

    assert_permission(sample)
    assert_query_plan(sample)
    assert_tool_call(sample)
    assert_readonly_execution(sample)
    assert_analysis_result(sample)
    assert_no_side_effect_outputs(sample)


def assert_permission(sample: dict[str, Any]) -> None:
    permission_checks = sample.get("permission_checks", {})
    if permission_checks.get("read_only") is not True:
        raise AssertionError("Real query must remain readonly.")
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
    if query_plan.get("metric_id") != "label_rate":
        raise AssertionError("QueryPlan metric_id mismatch.")
    if query_plan.get("review_required") is not False:
        raise AssertionError("Readonly query should not require manual confirmation.")
    if query_plan.get("execution_mode") != "real_readonly_query":
        raise AssertionError("QueryPlan execution_mode mismatch.")

    sql = query_plan.get("sql", "")
    for snippet in REQUIRED_SQL_SNIPPETS:
        if snippet not in sql:
            raise AssertionError(f"SQL missing required snippet: {snippet}")

    metric_entity = query_plan["metric_entities"][0]
    if metric_entity.get("aeolus_dataset_id") != "3888816":
        raise AssertionError("QueryPlan must bind dataset 3888816.")
    if metric_entity.get("aeolus_metric_id") != "10000036292379":
        raise AssertionError("QueryPlan must bind Aeolus label_rate metric.")


def assert_tool_call(sample: dict[str, Any]) -> None:
    query_plan = sample["QueryPlan"]
    tool_call_records = sample.get("tool_call_records", [])
    if len(tool_call_records) != 1:
        raise AssertionError("Expected exactly one real readonly tool_call_record.")
    tool_call = tool_call_records[0]
    if query_plan.get("tool_calls") != [tool_call["tool_call_id"]]:
        raise AssertionError("QueryPlan tool_calls mismatch.")
    if tool_call.get("tool_name") != "bytedcli_aeolus_query":
        raise AssertionError("Unexpected tool_name.")
    if tool_call.get("permission_level") != "readonly":
        raise AssertionError("Tool call must be readonly.")
    if tool_call.get("execution_mode") != "real_readonly_query":
        raise AssertionError("Tool call execution_mode mismatch.")
    if tool_call.get("real_query_executed") is not True:
        raise AssertionError("Tool call must mark real_query_executed=true.")


def assert_readonly_execution(sample: dict[str, Any]) -> None:
    execution = sample.get("readonly_execution")
    if not isinstance(execution, dict):
        raise AssertionError("Missing readonly_execution.")
    if execution.get("execution_mode") != "real_readonly_query":
        raise AssertionError("readonly_execution mode mismatch.")
    if execution.get("status") != "success":
        raise AssertionError("readonly_execution must succeed.")
    if execution.get("source_tier") != "governed_dataset":
        raise AssertionError("readonly_execution source_tier mismatch.")
    if execution.get("truncated") is not False:
        raise AssertionError("Result must not be truncated.")
    if execution.get("row_count", 0) <= 0:
        raise AssertionError("Result must include rows.")

    for field in ("reason", "review_done_cnt", "label_cnt", "label_rate"):
        if field not in execution.get("evidence_fields", []):
            raise AssertionError(f"Missing evidence field: {field}")

    for row in execution["rows"]:
        if row["review_done_cnt"] <= 0:
            raise AssertionError("review_done_cnt must be positive.")
        if not (0 <= row["label_rate"] < 0.1):
            raise AssertionError(f"label_rate out of range: {row}")


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
    validate(Path(args.results_path))
    print(f"Stage 1 real readonly label-rate OK: {args.results_path}")


if __name__ == "__main__":
    main()
