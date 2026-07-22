#!/usr/bin/env python3
"""Validate combined manual-review + report-flow label-rate flow helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT.parent
RUNNER_DIR = ROOT / "tools" / "runners"
ANALYSIS_DIR = ROOT / "skills" / "analysis" / "scripts"
sys.path.insert(0, str(RUNNER_DIR))
sys.path.insert(0, str(ANALYSIS_DIR))

import label_rate_analysis  # noqa: E402
import run_label_rate_formal_flow as formal_flow  # noqa: E402


def main() -> None:
    validate_combined_records()
    validate_report_flow_reason_plus1()
    validate_report_flow_risk_domain_reason_exclusion()
    print("Label-rate combined flow OK")


def validate_combined_records() -> None:
    levels = list(label_rate_analysis.DEFAULT_LEVELS)
    time_range = label_rate_analysis.build_grading_time_range(
        start_date="2026-07-14",
        end_date="2026-07-20",
    )
    manual_records = label_rate_analysis.build_records(
        label_rate_analysis.build_smoke_payloads(levels),
        levels,
        label_rate_analysis.sql_by_level(time_range),
        time_range=time_range,
        data_direction="manual_review_detail",
    )
    report_records = label_rate_analysis.build_records(
        label_rate_analysis.build_smoke_payloads(levels),
        levels,
        label_rate_analysis.report_flow_sql_by_level(time_range),
        time_range=time_range,
        data_direction="report_flow",
    )
    sample = formal_flow.build_combined_records([manual_records, report_records])[1]
    if sample.get("data_direction") != "combined":
        raise AssertionError("Combined sample must set data_direction=combined.")
    query_plan = sample["QueryPlan"]
    if query_plan.get("metric_id") != "combined_label_rate":
        raise AssertionError("Combined QueryPlan metric_id mismatch.")
    if query_plan.get("data_direction") != "combined":
        raise AssertionError("Combined QueryPlan data_direction mismatch.")
    if set(query_plan.get("sql_by_level", {})) != {
        "manual_review_detail",
        "report_flow",
    }:
        raise AssertionError("Combined QueryPlan must preserve per-source SQL maps.")
    execution = sample["readonly_execution"]
    if execution["level_counts"] != {
        "notice": 2,
        "P2": 2,
        "P1": 2,
        "P0": 2,
    }:
        raise AssertionError(f"Unexpected combined counts: {execution['level_counts']}")
    sources = {
        row.get("data_source")
        for row in execution["comprehensive_results"]
    }
    if sources != {
        label_rate_analysis.DATA_SOURCE_MANUAL_REVIEW,
        label_rate_analysis.DATA_SOURCE_REPORT_FLOW,
    }:
        raise AssertionError(f"Combined data sources mismatch: {sources}")
    if "data_source" not in execution.get("evidence_fields", []):
        raise AssertionError("Combined evidence fields must include data_source.")


def validate_report_flow_reason_plus1() -> None:
    original_loader = label_rate_analysis.load_plus1_agreed_indexes
    try:
        label_rate_analysis.load_plus1_agreed_indexes = lambda: {
            "strategy_id": {},
            "report_flow_reason": {
                "report_reason_a": {
                    "reason": "report_reason_a",
                    "plus1_agreed": True,
                    "update_date": "2026-07-13",
                }
            },
        }
        row: dict[str, Any] = {
            "data_direction": "report_flow",
            "data_source": label_rate_analysis.DATA_SOURCE_REPORT_FLOW,
            "mach_root_label_name": "举报",
            "strategy_id": "report_reason_a",
            "strategy_name": "report_reason_a",
            "enpool_reason": "report_reason_a",
        }
        indexes = label_rate_analysis.load_plus1_agreed_indexes()
        label_rate_analysis.ensure_plus1_fields(
            row,
            indexes["strategy_id"],
            "2026-07-14",
            report_flow_reason_index=indexes["report_flow_reason"],
            data_direction="report_flow",
        )
    finally:
        label_rate_analysis.load_plus1_agreed_indexes = original_loader
    if row.get("is_plus1_agreed") != "是":
        raise AssertionError("Report-flow reason must be marked as +1 agreed.")
    if row.get("plus1_agreed_before_current_period") != "是":
        raise AssertionError("Report-flow reason cutoff flag mismatch.")


def validate_report_flow_risk_domain_reason_exclusion() -> None:
    original_loader = label_rate_analysis.load_plus1_agreed_reason_index
    try:
        label_rate_analysis.load_plus1_agreed_reason_index = lambda: {
            "before_cutoff_reason": {"update_date": "2026-07-13"},
            "on_cutoff_reason": {"update_date": "2026-07-14"},
            "after_cutoff_reason": {"update_date": "2026-07-15"},
        }
        time_range = label_rate_analysis.build_grading_time_range(
            start_date="2026-07-14",
            end_date="2026-07-20",
        )
        excluded = label_rate_analysis.report_flow_pre_period_plus1_reasons(time_range)
        if excluded != ["before_cutoff_reason"]:
            raise AssertionError(f"Unexpected report-flow exclusions: {excluded}")
        sql = label_rate_analysis.report_flow_risk_domain_spike_source_sql(time_range)
    finally:
        label_rate_analysis.load_plus1_agreed_reason_index = original_loader
    if "ifNull(`[enpool_reason]`, '（空/enpool_reason）') NOT IN (" not in sql:
        raise AssertionError("Report-flow risk rollup must exclude reason pre-aggregation.")
    if "'before_cutoff_reason'" not in sql:
        raise AssertionError("Report-flow risk rollup missing excluded reason.")
    if "'on_cutoff_reason'" in sql or "'after_cutoff_reason'" in sql:
        raise AssertionError("Report-flow risk rollup included non-pre-period reason.")


if __name__ == "__main__":
    main()
