#!/usr/bin/env python3
"""Run stage 1 mock readonly execution with analysis_result and provenance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mock_readonly_execution import attach_readonly_execution
from run_stage_1_minimal_chain import EVAL_DIR, load_jsonl
from run_stage_1_mock_tool_chain import build_mock_tool_records


DEFAULT_OUTPUT = EVAL_DIR / "stage_1_runs" / "20260708_readonly_execution_results.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    samples = load_jsonl(EVAL_DIR / "eval_samples.jsonl")
    records = attach_readonly_execution(build_mock_tool_records(samples))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            for record in records
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Stage 1 readonly execution wrote {len(records)} records: {output_path}")


if __name__ == "__main__":
    main()
