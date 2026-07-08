#!/usr/bin/env python3
"""Validate the real readonly integration readiness gate."""

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
    / "20260708_real_readonly_readiness.json"
)
REQUIRED_CHECKS = {
    "local_metric_contract",
    "real_semantic_metric_id",
    "governed_dataset_id",
    "curated_raw_source",
    "readonly_tool_binding",
    "freshness_gate",
    "field_mapping",
    "sensitive_scope_guard",
    "specific_owner",
}
EXPECTED_CURRENT_BLOCKERS = {
    "real_semantic_metric_id",
    "governed_dataset_id",
    "readonly_tool_binding",
}


def validate(results_path: Path) -> None:
    payload = json.loads(results_path.read_text(encoding="utf-8"))

    if payload.get("record_type") != "real_readonly_readiness":
        raise AssertionError("Invalid readiness record_type.")
    if payload.get("scenario_key") != SCENARIO_KEY:
        raise AssertionError("Readiness scenario_key mismatch.")
    if payload.get("principle") != "YAGNI":
        raise AssertionError("Readiness gate must record YAGNI principle.")

    checks = payload.get("checks")
    if not isinstance(checks, list):
        raise AssertionError("Readiness checks must be a list.")

    checks_by_id: dict[str, dict[str, Any]] = {
        check["check_id"]: check for check in checks if "check_id" in check
    }
    missing_checks = REQUIRED_CHECKS - set(checks_by_id)
    if missing_checks:
        raise AssertionError(f"Missing readiness checks: {sorted(missing_checks)}")

    for check in checks:
        if check.get("status") not in {"pass", "warn", "block"}:
            raise AssertionError(f"Invalid check status: {check}")
        if not isinstance(check.get("evidence"), list) or not check["evidence"]:
            raise AssertionError(f"Check must include evidence: {check['check_id']}")

    blockers = {
        check["check_id"]
        for check in payload.get("blockers", [])
        if check.get("status") == "block"
    }
    if payload.get("status") == "ready" and blockers:
        raise AssertionError("Ready status cannot include blockers.")
    if payload.get("status") == "blocked" and not blockers:
        raise AssertionError("Blocked status must include blockers.")

    missing_expected = EXPECTED_CURRENT_BLOCKERS - blockers
    if missing_expected:
        raise AssertionError(
            f"Current readiness must block on missing assets: {sorted(missing_expected)}"
        )

    if checks_by_id["curated_raw_source"]["status"] != "pass":
        raise AssertionError("Curated raw source should remain documented.")
    if checks_by_id["field_mapping"]["status"] != "pass":
        raise AssertionError("Field mapping should remain documented.")
    if checks_by_id["specific_owner"]["status"] != "warn":
        raise AssertionError("Specific owner should currently be a warning.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_path", nargs="?", default=str(DEFAULT_RESULTS))
    args = parser.parse_args()
    validate(Path(args.results_path))
    print(f"Stage 1 real readonly readiness OK: {args.results_path}")


if __name__ == "__main__":
    main()
