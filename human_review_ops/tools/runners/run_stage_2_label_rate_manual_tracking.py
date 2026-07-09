#!/usr/bin/env python3
"""Generate local manual tracking for stage 2 label-rate outputs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESOLUTION_SCRIPTS = ROOT / "skills" / "resolution" / "scripts"
sys.path.insert(0, str(RESOLUTION_SCRIPTS))

from build_label_rate_manual_tracking import (  # noqa: E402
    build_manual_tracking,
    load_json,
    write_json,
)


SCENARIO_KEY = "efficiency-label-rate"
DEFAULT_OUTPUT_DIR = (
    ROOT
    / "evals"
    / SCENARIO_KEY
    / "stage_2_runs"
    / "20260709_low_label_rate_grading_notification_draft"
)
STATE_MACHINE_REF = (
    "human_review_ops/references/scenarios/efficiency-label-rate/state_machine.md"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    notification_draft_path = output_dir / "notification_draft.json"
    send_plan_path = output_dir / "send_plan.json"
    manual_tracking_path = output_dir / "manual_tracking.json"

    notification_draft = load_json(notification_draft_path)
    send_plan = load_json(send_plan_path)
    manual_tracking = build_manual_tracking(
        notification_draft=notification_draft,
        send_plan=send_plan,
        state_machine_ref=STATE_MACHINE_REF,
    )
    write_json(manual_tracking_path, manual_tracking)
    print(f"Stage 2 label-rate manual tracking wrote {relative_to_root(manual_tracking_path)}")


def relative_to_root(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


if __name__ == "__main__":
    main()
