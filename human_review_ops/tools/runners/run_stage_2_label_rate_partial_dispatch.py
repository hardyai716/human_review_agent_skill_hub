#!/usr/bin/env python3
"""Generate stage 2 partial-dispatch regression records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_KEY = "efficiency-label-rate"
DEFAULT_OUTPUT_DIR = (
    ROOT
    / "evals"
    / SCENARIO_KEY
    / "stage_2_runs"
    / "20260709_low_label_rate_grading_notification_draft"
)
TASK_TYPES = ("owner_lookup_only", "notification_only", "resolution_only")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    artifacts = load_artifacts(output_dir)
    records = [
        build_owner_lookup_record(output_dir, artifacts),
        build_notification_record(output_dir, artifacts),
        build_resolution_record(output_dir, artifacts),
    ]
    for record in records:
        write_jsonl(output_dir / f"{record['task_type']}_results.jsonl", [record])
    write_jsonl(output_dir / "partial_dispatch_results.jsonl", records)
    print(f"Stage 2 label-rate partial dispatch wrote {relative_to_root(output_dir)}")


def load_artifacts(output_dir: Path) -> dict[str, dict[str, Any]]:
    paths = {
        "poc_routing_plan": output_dir / "poc_routing_plan.json",
        "notification_draft": output_dir / "notification_draft.json",
        "send_plan": output_dir / "send_plan.json",
        "manual_tracking": output_dir / "manual_tracking.json",
    }
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing artifacts for partial dispatch: {missing}")
    return {name: load_json(path) for name, path in paths.items()}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_owner_lookup_record(
    output_dir: Path,
    artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    poc_routing = artifacts["poc_routing_plan"]
    return base_record(
        output_dir,
        task_type="owner_lookup_only",
        semantic_task_type="poc_routing_only",
        result_artifacts=["poc_routing_plan.json"],
        summary={
            "routing_mode": poc_routing.get("routing_mode"),
            "default_recipient": poc_routing.get("default_recipient"),
            "real_poc_mapping_used": poc_routing.get("real_poc_mapping_used"),
            "level_counts": poc_routing.get("level_counts"),
        },
    )


def build_notification_record(
    output_dir: Path,
    artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    notification_draft = artifacts["notification_draft"]
    send_plan = artifacts["send_plan"]
    return base_record(
        output_dir,
        task_type="notification_only",
        semantic_task_type="notification_draft_only",
        result_artifacts=[
            "notification_draft.json",
            "send_plan.json",
            "publish/low_efficiency_grading.card.json",
        ],
        summary={
            "draft_mode": notification_draft.get("draft_mode"),
            "group_send_blocked": send_plan.get("group_send_blocked"),
            "requires_confirmation": send_plan.get("requires_confirmation"),
            "sent": send_plan.get("sent"),
        },
    )


def build_resolution_record(
    output_dir: Path,
    artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    manual_tracking = artifacts["manual_tracking"]
    return base_record(
        output_dir,
        task_type="resolution_only",
        semantic_task_type="manual_tracking_only",
        result_artifacts=["manual_tracking.json"],
        summary={
            "tracking_mode": manual_tracking.get("tracking_mode"),
            "current_state": manual_tracking.get("state_machine", {}).get(
                "current_state"
            ),
            "continue_observation": manual_tracking.get("continue_observation"),
            "overall_status": manual_tracking.get("overall_status"),
        },
    )


def base_record(
    output_dir: Path,
    *,
    task_type: str,
    semantic_task_type: str,
    result_artifacts: list[str],
    summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "record_type": "partial_dispatch_result",
        "schema_version": "stage_2_partial_dispatch_result.v1",
        "scenario_key": SCENARIO_KEY,
        "task_type": task_type,
        "semantic_task_type": semantic_task_type,
        "result_status": "ok",
        "source_output_dir": relative_to_root(output_dir),
        "result_artifacts": result_artifacts,
        "real_query_executed": False,
        "stage_1_query_reused": True,
        "external_cli_calls": [],
        "group_send_blocked": True,
        "group_send_sent": False,
        "real_group_send_executed": False,
        "online_write_executed": False,
        "online_state_write_allowed": False,
        "summary": summary,
    }


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def relative_to_root(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


if __name__ == "__main__":
    main()
