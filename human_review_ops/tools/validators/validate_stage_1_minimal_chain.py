#!/usr/bin/env python3
"""Validate stage 1 perception + analysis minimal-chain results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_KEY = "efficiency-label-rate"
EVAL_DIR = ROOT / "evals" / SCENARIO_KEY
DEFAULT_RESULTS = EVAL_DIR / "stage_1_runs" / "20260708_minimal_chain_results.jsonl"

QUERY_PLAN_REQUIRED = [
    "scenario_key",
    "task_type",
    "analysis_mode",
    "metric_id",
    "time_range",
    "dimensions",
    "filters",
    "source_priority",
    "allowed_sources",
    "forbidden_sources",
    "fallback_reason",
    "quality_checks",
    "review_required",
    "execution_mode",
]

SOURCE_FOOTER_REQUIRED = [
    "source_tier",
    "metric_definition_version",
    "data_freshness",
    "owner",
    "confidence_tier",
    "review_status",
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def assert_no_side_effects(record: dict[str, Any]) -> None:
    permission_checks = record.get("permission_checks", {})
    if permission_checks.get("read_only") is not True:
        raise AssertionError(f"{record.get('id')} must stay read-only.")
    if permission_checks.get("real_query_blocked") is not True:
        raise AssertionError(f"{record.get('id')} must block real queries.")
    if permission_checks.get("real_notification_blocked") is not True:
        raise AssertionError(f"{record.get('id')} must block real notifications.")
    if permission_checks.get("online_write_blocked") is not True:
        raise AssertionError(f"{record.get('id')} must block online writes.")


def assert_query_plan(record: dict[str, Any], expected: dict[str, Any]) -> None:
    query_plan = record.get("QueryPlan")
    if not isinstance(query_plan, dict):
        raise AssertionError(f"{record['id']} missing QueryPlan.")

    missing = [field for field in QUERY_PLAN_REQUIRED if field not in query_plan]
    if missing:
        raise AssertionError(f"{record['id']} missing QueryPlan fields: {missing}")

    if query_plan["scenario_key"] != SCENARIO_KEY:
        raise AssertionError(f"{record['id']} scenario_key mismatch.")
    if query_plan["metric_id"] != "label_rate":
        raise AssertionError(f"{record['id']} metric_id must be label_rate.")
    if query_plan["source_priority"][0] != "semantic_layer":
        raise AssertionError(f"{record['id']} must use semantic_layer first.")
    if query_plan["execution_mode"] != "no_real_query":
        raise AssertionError(f"{record['id']} must not run real queries.")
    if query_plan["analysis_mode"] != expected["expected_analysis_mode"]:
        raise AssertionError(f"{record['id']} analysis_mode mismatch.")

    if expected["expected_analysis_mode"] == "dimension_discovery":
        discovery = query_plan.get("dimension_discovery", {})
        if discovery.get("status") != "required":
            raise AssertionError(f"{record['id']} must require dimension discovery.")
        if query_plan["fallback_reason"] != "dimension_discovery_required":
            raise AssertionError(f"{record['id']} must record dimension discovery fallback.")


def assert_source_footer(record: dict[str, Any]) -> None:
    footer = record.get("source_footer")
    if not isinstance(footer, dict):
        raise AssertionError(f"{record['id']} missing source_footer.")

    missing = [field for field in SOURCE_FOOTER_REQUIRED if field not in footer]
    if missing:
        raise AssertionError(f"{record['id']} missing source_footer fields: {missing}")

    if footer["data_freshness"] != "not_queried":
        raise AssertionError(f"{record['id']} must not claim real data freshness.")
    if footer["review_status"] != "debug_only_no_real_query":
        raise AssertionError(f"{record['id']} review_status mismatch.")


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
    if environment.get("root_package_read") is not True:
        raise AssertionError("Root package must be readable.")

    for sample_id, expected in expected_samples.items():
        record = samples[sample_id]
        if record.get("result") != "pass":
            raise AssertionError(f"{sample_id} did not pass.")
        assert_no_side_effects(record)

        if expected["type"] == "positive":
            if record.get("scenario_key") != SCENARIO_KEY:
                raise AssertionError(f"{sample_id} scenario_key mismatch.")
            if record.get("task_type") != expected["expected_task_type"]:
                raise AssertionError(f"{sample_id} task_type mismatch.")
            assert_query_plan(record, expected)
            assert_source_footer(record)

        if expected["type"] == "negative":
            if record.get("scenario_key") == expected["expected_reject_scenario_key"]:
                raise AssertionError(f"{sample_id} incorrectly matched scenario.")
            if record.get("QueryPlan") is not None:
                raise AssertionError(f"{sample_id} must not generate QueryPlan.")

        if expected["type"] == "low_context":
            if "ask_more_info" not in record.get("outputs", []):
                raise AssertionError(f"{sample_id} must ask for more information.")
            if record.get("QueryPlan") is not None:
                raise AssertionError(f"{sample_id} must not generate QueryPlan.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_path", nargs="?", default=str(DEFAULT_RESULTS))
    args = parser.parse_args()
    validate(Path(args.results_path))
    print(f"Stage 1 minimal chain OK: {args.results_path}")


if __name__ == "__main__":
    main()
