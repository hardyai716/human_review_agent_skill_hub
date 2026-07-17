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
)
OUTPUT_DATE = "20260708"
DEFAULT_DAYS = 7
DEFAULT_DIMENSIONS = "reason"
DEFAULT_QUERY_MODE = "ranking"
QUERY_MODE_CHOICES = ("ranking", "group_count")
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
REQUIRED_SQL_SNIPPETS_STATIC = [
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


def analysis_mode_for(query_mode: str) -> str:
    if query_mode == "group_count":
        return "low_label_rate_group_count"
    return "label_rate_ranking"


def default_results_path(
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
    return DEFAULT_RESULTS / filename


def required_sql_snippets(
    days: int,
    dimensions: list[dict[str, str]],
    query_mode: str,
    time_range: dict[str, Any],
) -> list[str]:
    dimension_snippets = [
        f"{dimension['source_field']} AS {dimension['name']}"
        for dimension in dimensions
    ]
    group_by_snippet = "GROUP BY " + ", ".join(
        dimension["name"] for dimension in dimensions
    )
    mode_snippets = [group_by_snippet]
    if query_mode == "group_count":
        mode_snippets += [
            "SELECT count() AS low_label_rate_group_cnt",
            ") AS low_label_rate_groups",
        ]
    else:
        mode_snippets += [
            "ORDER BY review_done_cnt DESC",
            "LIMIT 1000",
        ]
    if time_range.get("start_date") and time_range.get("end_date_exclusive"):
        date_snippets = [
            f"`[p_date]` >= '{time_range['start_date']}'",
            f"`[p_date]` < '{time_range['end_date_exclusive']}'",
        ]
    else:
        date_snippets = [
            f"`[p_date]` >= today() - {days}",
            "`[p_date]` < today()",
        ]
    return date_snippets + dimension_snippets + REQUIRED_SQL_SNIPPETS_STATIC + mode_snippets


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate(
    results_path: Path,
    days: int,
    dimensions: list[dict[str, str]],
    query_mode: str,
) -> None:
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
    assert_query_plan(sample, days, dimensions, query_mode)
    assert_tool_call(sample)
    assert_readonly_execution(sample, dimensions, query_mode)
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


def assert_query_plan(
    sample: dict[str, Any],
    days: int,
    dimensions: list[dict[str, str]],
    query_mode: str,
) -> None:
    query_plan = sample.get("QueryPlan")
    expected_dimensions = [dimension["name"] for dimension in dimensions]
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
    if query_plan.get("analysis_mode") != analysis_mode_for(query_mode):
        raise AssertionError("QueryPlan analysis_mode mismatch.")
    if query_plan.get("query_mode") != query_mode:
        raise AssertionError("QueryPlan query_mode mismatch.")
    if query_plan.get("dimensions") != expected_dimensions:
        raise AssertionError("QueryPlan dimensions mismatch.")
    expected_mappings = [
        {
            "dimension_id": dimension["name"],
            "source_field": dimension["source_field"],
            "source_tier": "governed_dataset",
        }
        for dimension in dimensions
    ]
    if query_plan.get("dimension_mappings") != expected_mappings:
        raise AssertionError("QueryPlan dimension_mappings mismatch.")
    if query_plan.get("time_range", {}).get("days") != days:
        raise AssertionError("QueryPlan days mismatch.")
    time_range = query_plan.get("time_range", {})
    if time_range.get("start_date") and time_range.get("end_date_exclusive"):
        expected_where = (
            f"`[p_date]` >= '{time_range['start_date']}' "
            f"AND `[p_date]` < '{time_range['end_date_exclusive']}'"
        )
    else:
        expected_where = f"`[p_date]` >= today() - {days} AND `[p_date]` < today()"
    if time_range.get("where") != expected_where:
        raise AssertionError("QueryPlan where mismatch.")

    sql = query_plan.get("sql", "")
    for snippet in required_sql_snippets(days, dimensions, query_mode, time_range):
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


def assert_readonly_execution(
    sample: dict[str, Any],
    dimensions: list[dict[str, str]],
    query_mode: str,
) -> None:
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

    expected_dimension_fields = [dimension["name"] for dimension in dimensions]
    if query_mode == "group_count":
        required_fields = ["low_label_rate_group_cnt"]
    else:
        required_fields = expected_dimension_fields + [
            "review_done_cnt",
            "label_cnt",
            "label_rate",
        ]
    for field in required_fields:
        if field not in execution.get("evidence_fields", []):
            raise AssertionError(f"Missing evidence field: {field}")

    if query_mode == "group_count":
        if len(execution["rows"]) != 1:
            raise AssertionError("group_count query must return exactly one row.")
        if execution["rows"][0]["low_label_rate_group_cnt"] < 0:
            raise AssertionError("low_label_rate_group_cnt must be non-negative.")
    else:
        for row in execution["rows"]:
            for dimension_field in expected_dimension_fields:
                if dimension_field not in row:
                    raise AssertionError(f"Missing dimension field: {dimension_field}")
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
    if provenance.get("dimensions") != sample["QueryPlan"]["dimensions"]:
        raise AssertionError("provenance dimensions mismatch.")
    if provenance.get("tool_call_ids") != sample["QueryPlan"]["tool_calls"]:
        raise AssertionError("provenance tool_call_ids mismatch.")


def assert_no_side_effect_outputs(sample: dict[str, Any]) -> None:
    for forbidden in ("notification_draft", "owner_recommendation", "manual_tracking"):
        if sample.get(forbidden) is not None:
            raise AssertionError(f"Unexpected side-effect output: {forbidden}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_path", nargs="?")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--dimensions", default=DEFAULT_DIMENSIONS)
    parser.add_argument("--query-mode", default=DEFAULT_QUERY_MODE, choices=QUERY_MODE_CHOICES)
    args = parser.parse_args()
    if args.days <= 0:
        raise SystemExit("--days must be a positive integer.")
    dimensions = parse_dimensions(args.dimensions)
    results_path = (
        Path(args.results_path)
        if args.results_path
        else default_results_path(args.days, dimensions, args.query_mode)
    )
    validate(results_path, args.days, dimensions, args.query_mode)
    print(f"Stage 1 real readonly label-rate OK: {results_path}")


if __name__ == "__main__":
    main()
