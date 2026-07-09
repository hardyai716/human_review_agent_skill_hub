#!/usr/bin/env python3
"""Generate stage 2 POC routing from label-rate grading results."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
NOTIFICATION_SCRIPTS = ROOT / "skills" / "notification" / "scripts"
sys.path.insert(0, str(NOTIFICATION_SCRIPTS))

from resolve_label_rate_poc_routing import (  # noqa: E402
    build_poc_routing_plan,
    load_stage_1_sample,
    write_json,
)


SCENARIO_KEY = "efficiency-label-rate"
DEFAULT_SOURCE = (
    ROOT
    / "evals"
    / SCENARIO_KEY
    / "stage_1_runs"
    / "20260708_real_readonly_label_rate_grading_results.jsonl"
)
DEFAULT_OUTPUT_DIR = (
    ROOT
    / "evals"
    / SCENARIO_KEY
    / "stage_2_runs"
    / "20260709_low_label_rate_grading_notification_draft"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    source_path = Path(args.source)
    output_dir = Path(args.output_dir)
    output_path = output_dir / "poc_routing_plan.json"

    sample = load_stage_1_sample(source_path)
    plan = build_poc_routing_plan(
        sample,
        source_stage_1_result=relative_to_root(source_path),
    )
    write_json(output_path, plan)
    print(f"Stage 2 label-rate POC routing wrote {relative_to_root(output_path)}")


def relative_to_root(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


if __name__ == "__main__":
    main()
