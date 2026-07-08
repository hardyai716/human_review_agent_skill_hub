#!/usr/bin/env python3
"""Validate stage 1 mock readonly tool-call records."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from validate_stage_1_minimal_chain import (
    EVAL_DIR,
    SCENARIO_KEY,
    load_jsonl,
    validate as validate_minimal_chain,
)


DEFAULT_RESULTS = EVAL_DIR / "stage_1_runs" / "20260708_mock_tool_chain_results.jsonl"
TOOL_EXECUTION_MODE = "mock_readonly_no_real_query"
VALID_SOURCE_TIERS = {
    "semantic_layer",
    "governed_dataset",
    "curated_raw_sql",
    "raw_exploration",
    "scenario_reference_preflight",
}
VALID_STATUSES = {"success", "failed", "timeout", "degraded", "blocked"}
TOOL_CALL_RECORD_REQUIRED = [
    "tool_call_id",
    "caller",
    "tool_name",
    "command_name",
    "permission_level",
    "source_tier",
    "scenario_key",
    "metric_id",
    "review_required",
    "fallback_reason",
    "execution_mode",
    "real_query_executed",
    "input_summary",
    "output_summary",
    "status",
    "latency_ms",
]
CURATED_SQL_FALLBACK_REASONS = {
    "complex_grading_rule_not_covered_by_semantic_layer",
    "dimension_reason_breakdown_requires_curated_sql",
}


def assert_tool_call_records(
    record: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    query_plan = record["QueryPlan"]
    tool_call_records = record.get("tool_call_records")
    if not isinstance(tool_call_records, list) or not tool_call_records:
        raise AssertionError(f"{record['id']} missing tool_call_records.")

    tool_call_ids = [
        tool_call_record.get("tool_call_id")
        for tool_call_record in tool_call_records
    ]
    if query_plan.get("tool_calls") != tool_call_ids:
        raise AssertionError(f"{record['id']} QueryPlan tool_calls mismatch.")

    permission_checks = record.get("permission_checks", {})
    if permission_checks.get("tool_calls") != tool_call_ids:
        raise AssertionError(f"{record['id']} permission tool_calls mismatch.")
    if permission_checks.get("tool_mode") != TOOL_EXECUTION_MODE:
        raise AssertionError(f"{record['id']} tool mode mismatch.")
    if permission_checks.get("mock_or_readonly_tool_only") is not True:
        raise AssertionError(f"{record['id']} must stay mock/readonly only.")

    source_tiers = set()
    statuses = set()
    for tool_call_record in tool_call_records:
        assert_one_tool_call_record(record, query_plan, tool_call_record)
        source_tiers.add(tool_call_record["source_tier"])
        statuses.add(tool_call_record["status"])

    if "semantic_layer" not in source_tiers:
        raise AssertionError(f"{record['id']} must preflight semantic_layer.")

    if expected["expected_analysis_mode"] == "dimension_discovery":
        if "governed_dataset" not in source_tiers:
            raise AssertionError(f"{record['id']} must run dataset field discovery.")
        if "degraded" not in statuses:
            raise AssertionError(f"{record['id']} dimension discovery must be degraded.")

    if query_plan["fallback_reason"] in CURATED_SQL_FALLBACK_REASONS:
        if "curated_raw_sql" not in source_tiers:
            raise AssertionError(f"{record['id']} must record curated SQL guard.")
        if "blocked" not in statuses:
            raise AssertionError(f"{record['id']} real curated SQL query must be blocked.")


def assert_one_tool_call_record(
    record: dict[str, Any],
    query_plan: dict[str, Any],
    tool_call_record: dict[str, Any],
) -> None:
    missing = [
        field
        for field in TOOL_CALL_RECORD_REQUIRED
        if field not in tool_call_record
    ]
    if missing:
        raise AssertionError(
            f"{record['id']} missing tool_call_record fields: {missing}"
        )

    if tool_call_record["caller"] != "analyzing-ops-metrics":
        raise AssertionError(f"{record['id']} caller mismatch.")
    if tool_call_record["permission_level"] != "readonly":
        raise AssertionError(f"{record['id']} tool must be readonly.")
    if tool_call_record["source_tier"] not in VALID_SOURCE_TIERS:
        raise AssertionError(f"{record['id']} invalid source_tier.")
    if tool_call_record["scenario_key"] != SCENARIO_KEY:
        raise AssertionError(f"{record['id']} tool scenario_key mismatch.")
    if tool_call_record["metric_id"] != query_plan["metric_id"]:
        raise AssertionError(f"{record['id']} tool metric_id mismatch.")
    if tool_call_record["review_required"] != query_plan["review_required"]:
        raise AssertionError(f"{record['id']} tool review_required mismatch.")
    if tool_call_record["fallback_reason"] != query_plan["fallback_reason"]:
        raise AssertionError(f"{record['id']} tool fallback_reason mismatch.")
    if tool_call_record["execution_mode"] != TOOL_EXECUTION_MODE:
        raise AssertionError(f"{record['id']} tool execution_mode mismatch.")
    if tool_call_record["real_query_executed"] is not False:
        raise AssertionError(f"{record['id']} must not execute real queries.")
    if tool_call_record["status"] not in VALID_STATUSES:
        raise AssertionError(f"{record['id']} invalid tool status.")
    if tool_call_record["latency_ms"] < 0:
        raise AssertionError(f"{record['id']} latency_ms must be non-negative.")


def validate(results_path: Path) -> None:
    validate_minimal_chain(results_path)

    expected_samples = {
        sample["id"]: sample for sample in load_jsonl(EVAL_DIR / "eval_samples.jsonl")
    }
    records = load_jsonl(results_path)
    samples = {
        record["id"]: record
        for record in records
        if record.get("record_type") == "sample"
    }

    environment = next(
        (record for record in records if record.get("record_type") == "environment"),
        None,
    )
    if not environment:
        raise AssertionError("Missing environment record.")
    if environment.get("tool_mode") != TOOL_EXECUTION_MODE:
        raise AssertionError("Environment tool_mode mismatch.")
    if environment.get("tool_call_record_contract") != "mock_readonly":
        raise AssertionError("Environment must declare mock_readonly contract.")

    for sample_id, expected in expected_samples.items():
        record = samples[sample_id]
        if expected["type"] == "positive":
            assert_tool_call_records(record, expected)
        else:
            if record.get("tool_call_records") not in (None, []):
                raise AssertionError(f"{sample_id} must not call tools.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_path", nargs="?", default=str(DEFAULT_RESULTS))
    args = parser.parse_args()
    validate(Path(args.results_path))
    print(f"Stage 1 mock tool chain OK: {args.results_path}")


if __name__ == "__main__":
    main()
