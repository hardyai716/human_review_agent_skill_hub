#!/usr/bin/env python3
"""Self-contained smoke check for the analysis Skill (no SQL, no side effects)."""

from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import label_rate_analysis as analysis  # noqa: E402


REQUIRED_SAMPLE_KEYS = (
    "QueryPlan",
    "source_footer",
    "readonly_execution",
    "analysis_result",
    "provenance",
)


def run_checks() -> None:
    levels = analysis.parse_levels(",".join(analysis.DEFAULT_LEVELS))
    sql_map = analysis.sql_by_level()
    payloads = analysis.build_smoke_payloads(levels)
    records = analysis.build_records(payloads, levels, sql_map)

    assert len(records) >= 2, "expected environment + sample records"
    sample = records[1]
    assert sample.get("record_type") == "sample", "records[1] must be the sample record"
    for key in REQUIRED_SAMPLE_KEYS:
        assert key in sample, f"sample record missing key: {key}"


def main() -> None:
    try:
        run_checks()
    except Exception as error:  # noqa: BLE001
        print(f"analysis selfcheck FAILED: {error}")
        raise SystemExit(1)
    print("analysis selfcheck OK")


if __name__ == "__main__":
    main()
