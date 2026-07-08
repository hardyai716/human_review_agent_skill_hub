#!/usr/bin/env python3
"""Run stage 1 with mock readonly tool_call_record generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mock_readonly_tools import (
    EXECUTION_MODE,
    build_permission_checks,
    build_tool_call_records,
)
from run_stage_1_minimal_chain import EVAL_DIR, build_records, load_jsonl


DEFAULT_OUTPUT = EVAL_DIR / "stage_1_runs" / "20260708_mock_tool_chain_results.jsonl"


def attach_mock_tool_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched_records: list[dict[str, Any]] = []
    for record in records:
        enriched_record = dict(record)

        if enriched_record.get("record_type") == "environment":
            enriched_record["tool_mode"] = EXECUTION_MODE
            enriched_record["tool_call_record_contract"] = "mock_readonly"
            enriched_record["real_query_blocked"] = True
            enriched_records.append(enriched_record)
            continue

        query_plan = enriched_record.get("QueryPlan")
        if not isinstance(query_plan, dict):
            enriched_record["tool_call_records"] = []
            enriched_record.setdefault("permission_checks", {})["tool_calls"] = []
            enriched_records.append(enriched_record)
            continue

        tool_call_records = build_tool_call_records(query_plan)
        tool_call_ids = [
            tool_call_record["tool_call_id"]
            for tool_call_record in tool_call_records
        ]

        query_plan = dict(query_plan)
        query_plan["tool_calls"] = tool_call_ids
        enriched_record["QueryPlan"] = query_plan
        enriched_record["tool_call_records"] = tool_call_records
        enriched_record["permission_checks"] = build_permission_checks(
            enriched_record.get("permission_checks", {}),
            tool_call_records,
        )
        enriched_record["outputs"] = sorted(
            set(enriched_record.get("outputs", [])) | {"tool_call_record"}
        )
        enriched_records.append(enriched_record)

    return enriched_records


def build_mock_tool_records(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return attach_mock_tool_records(build_records(samples))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    samples = load_jsonl(EVAL_DIR / "eval_samples.jsonl")
    records = build_mock_tool_records(samples)
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
    print(f"Stage 1 mock tool chain wrote {len(records)} records: {output_path}")


if __name__ == "__main__":
    main()
