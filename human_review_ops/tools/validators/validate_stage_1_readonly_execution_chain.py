#!/usr/bin/env python3
"""Validate stage 1 readonly execution outputs and provenance."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from validate_stage_1_minimal_chain import EVAL_DIR, SCENARIO_KEY, load_jsonl


DEFAULT_RESULTS = EVAL_DIR / "stage_1_runs" / "20260708_readonly_execution_results.jsonl"
EXECUTION_MODE = "mock_readonly_execution"
TOOL_EXECUTION_MODE = "mock_readonly_no_real_query"
SOURCE_FOOTER_REQUIRED = [
    "source_tier",
    "metric_definition_version",
    "data_freshness",
    "owner",
    "confidence_tier",
    "review_status",
]
ANALYSIS_RESULT_REQUIRED = [
    "analysis_id",
    "event_id",
    "templates_used",
    "query_plan",
    "readonly_execution",
    "impact_assessment",
    "root_cause_hypotheses",
    "sop_decision",
    "quality_checks",
    "source_footer",
    "provenance",
]
PROVENANCE_REQUIRED = [
    "provenance_id",
    "scenario_key",
    "query_plan_id",
    "execution_id",
    "execution_mode",
    "source_tier",
    "source_name",
    "metric_id",
    "metric_formula",
    "tool_call_ids",
    "references",
    "limitations",
]


def validate(results_path: Path) -> None:
    expected_samples = {
        sample["id"]: sample for sample in load_jsonl(EVAL_DIR / "eval_samples.jsonl")
    }
    records = load_jsonl(results_path)
    samples = {
        record["id"]: record
        for record in records
        if record.get("record_type") == "sample"
    }

    missing = set(expected_samples) - set(samples)
    if missing:
        raise AssertionError(f"Missing sample records: {sorted(missing)}")

    environment = next(
        (record for record in records if record.get("record_type") == "environment"),
        None,
    )
    if not environment:
        raise AssertionError("Missing environment record.")
    if environment.get("execution_mode") != EXECUTION_MODE:
        raise AssertionError("Environment execution_mode mismatch.")
    if environment.get("analysis_result_contract") != "readonly_execution_with_provenance":
        raise AssertionError("Environment must declare readonly execution contract.")

    for sample_id, expected in expected_samples.items():
        record = samples[sample_id]
        assert_no_side_effects(record)
        if expected["type"] == "positive":
            assert_positive_execution(record, expected)
        else:
            assert_no_execution(record)


def assert_no_side_effects(record: dict[str, Any]) -> None:
    permission_checks = record.get("permission_checks", {})
    if permission_checks.get("read_only") is not True:
        raise AssertionError(f"{record.get('id')} must stay read-only.")
    if permission_checks.get("real_notification_blocked") is not True:
        raise AssertionError(f"{record.get('id')} must block real notifications.")
    if permission_checks.get("online_write_blocked") is not True:
        raise AssertionError(f"{record.get('id')} must block online writes.")
    if record.get("notification_draft") is not None:
        raise AssertionError(f"{record.get('id')} must not generate notification draft.")
    if record.get("owner_recommendation") is not None:
        raise AssertionError(f"{record.get('id')} must not generate owner recommendation.")
    if record.get("manual_tracking") is not None:
        raise AssertionError(f"{record.get('id')} must not generate manual tracking.")


def assert_positive_execution(
    record: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    query_plan = record.get("QueryPlan")
    if not isinstance(query_plan, dict):
        raise AssertionError(f"{record['id']} missing QueryPlan.")

    tool_call_records = record.get("tool_call_records")
    if not isinstance(tool_call_records, list) or not tool_call_records:
        raise AssertionError(f"{record['id']} missing tool_call_records.")
    tool_call_ids = [tool_call_record["tool_call_id"] for tool_call_record in tool_call_records]
    if query_plan.get("tool_calls") != tool_call_ids:
        raise AssertionError(f"{record['id']} QueryPlan tool_calls mismatch.")

    for tool_call_record in tool_call_records:
        if tool_call_record.get("permission_level") != "readonly":
            raise AssertionError(f"{record['id']} tool call must be readonly.")
        if tool_call_record.get("execution_mode") != TOOL_EXECUTION_MODE:
            raise AssertionError(f"{record['id']} tool execution mode mismatch.")
        if tool_call_record.get("real_query_executed") is not False:
            raise AssertionError(f"{record['id']} must not execute real online queries.")

    readonly_execution = record.get("readonly_execution")
    if not isinstance(readonly_execution, dict):
        raise AssertionError(f"{record['id']} missing readonly_execution.")

    analysis_result = record.get("analysis_result")
    if not isinstance(analysis_result, dict):
        raise AssertionError(f"{record['id']} missing analysis_result.")
    missing = [field for field in ANALYSIS_RESULT_REQUIRED if field not in analysis_result]
    if missing:
        raise AssertionError(f"{record['id']} missing analysis_result fields: {missing}")

    if analysis_result["readonly_execution"] != readonly_execution:
        raise AssertionError(f"{record['id']} analysis_result readonly_execution mismatch.")
    if analysis_result["event_id"] != record["id"]:
        raise AssertionError(f"{record['id']} analysis event_id mismatch.")

    source_footer = record.get("source_footer")
    assert_source_footer(record, source_footer)
    if analysis_result["source_footer"] != source_footer:
        raise AssertionError(f"{record['id']} analysis source_footer mismatch.")

    provenance = record.get("provenance")
    assert_provenance(record, query_plan, readonly_execution, provenance, tool_call_ids)
    if analysis_result["provenance"] != provenance:
        raise AssertionError(f"{record['id']} analysis provenance mismatch.")

    if expected["expected_analysis_mode"] == "dimension_discovery":
        assert_dimension_discovery_block(record, readonly_execution, analysis_result)
    else:
        assert_successful_mock_execution(record, readonly_execution, analysis_result)


def assert_source_footer(record: dict[str, Any], source_footer: Any) -> None:
    if not isinstance(source_footer, dict):
        raise AssertionError(f"{record['id']} missing source_footer.")
    missing = [field for field in SOURCE_FOOTER_REQUIRED if field not in source_footer]
    if missing:
        raise AssertionError(f"{record['id']} missing source_footer fields: {missing}")
    if source_footer.get("metric_id") != "label_rate":
        raise AssertionError(f"{record['id']} source_footer metric_id mismatch.")


def assert_provenance(
    record: dict[str, Any],
    query_plan: dict[str, Any],
    readonly_execution: dict[str, Any],
    provenance: Any,
    tool_call_ids: list[str],
) -> None:
    if not isinstance(provenance, dict):
        raise AssertionError(f"{record['id']} missing provenance.")
    missing = [field for field in PROVENANCE_REQUIRED if field not in provenance]
    if missing:
        raise AssertionError(f"{record['id']} missing provenance fields: {missing}")
    if provenance["scenario_key"] != SCENARIO_KEY:
        raise AssertionError(f"{record['id']} provenance scenario_key mismatch.")
    if provenance["query_plan_id"] != query_plan["query_plan_id"]:
        raise AssertionError(f"{record['id']} provenance query_plan_id mismatch.")
    if provenance["execution_id"] != readonly_execution["execution_id"]:
        raise AssertionError(f"{record['id']} provenance execution_id mismatch.")
    if provenance["execution_mode"] != EXECUTION_MODE:
        raise AssertionError(f"{record['id']} provenance execution_mode mismatch.")
    if provenance["tool_call_ids"] != tool_call_ids:
        raise AssertionError(f"{record['id']} provenance tool_call_ids mismatch.")

    references = provenance.get("references", {})
    for reference_name in ("metric_contract", "dataset_reference", "analysis_rule"):
        if reference_name not in references:
            raise AssertionError(f"{record['id']} missing provenance {reference_name}.")


def assert_successful_mock_execution(
    record: dict[str, Any],
    readonly_execution: dict[str, Any],
    analysis_result: dict[str, Any],
) -> None:
    if readonly_execution.get("status") != "success":
        raise AssertionError(f"{record['id']} readonly execution must succeed.")
    if readonly_execution.get("row_count", 0) <= 0:
        raise AssertionError(f"{record['id']} readonly execution must include rows.")
    for field in ("review_done_cnt", "label_cnt", "label_rate", "time_window"):
        if field not in readonly_execution.get("evidence_fields", []):
            raise AssertionError(f"{record['id']} missing evidence field: {field}")
    if analysis_result["sop_decision"].get("required_confirmation") is not False:
        raise AssertionError(f"{record['id']} must not require confirmation after safe mock execution.")


def assert_dimension_discovery_block(
    record: dict[str, Any],
    readonly_execution: dict[str, Any],
    analysis_result: dict[str, Any],
) -> None:
    if readonly_execution.get("status") != "blocked":
        raise AssertionError(f"{record['id']} dimension discovery must block execution.")
    if readonly_execution.get("row_count") != 0:
        raise AssertionError(f"{record['id']} dimension discovery must not return rows.")
    if readonly_execution.get("block_reason") != "dimension_discovery_required":
        raise AssertionError(f"{record['id']} dimension discovery block reason mismatch.")
    if analysis_result["sop_decision"].get("next_action") != "ask_more":
        raise AssertionError(f"{record['id']} dimension discovery must ask for more info.")


def assert_no_execution(record: dict[str, Any]) -> None:
    if record.get("readonly_execution") is not None:
        raise AssertionError(f"{record['id']} must not have readonly_execution.")
    if record.get("analysis_result") is not None:
        raise AssertionError(f"{record['id']} must not have analysis_result.")
    if record.get("provenance") is not None:
        raise AssertionError(f"{record['id']} must not have provenance.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_path", nargs="?", default=str(DEFAULT_RESULTS))
    args = parser.parse_args()
    validate(Path(args.results_path))
    print(f"Stage 1 readonly execution OK: {args.results_path}")


if __name__ == "__main__":
    main()
