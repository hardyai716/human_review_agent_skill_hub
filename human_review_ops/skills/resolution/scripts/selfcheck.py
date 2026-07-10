#!/usr/bin/env python3
"""Self-contained smoke check for the resolution Skill (local tracking, no online writes)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import build_label_rate_manual_tracking as tracking  # noqa: E402


LEVEL_ORDER = ["notice", "P2", "P1", "P0"]


def build_notification_draft() -> dict[str, Any]:
    routing_rules = {
        level: {
            "severity_level": level,
            "target_roles": ["人审运营"],
            "action_required": f"{level} smoke action",
            "recipient_resolution": {"mode": "mach_root_label_mapping"},
            "reason_count": 1,
            "strategy_group_count": 1,
        }
        for level in LEVEL_ORDER
    }
    return {
        "level_counts": {"notice": 1, "P2": 1, "P1": 1, "P0": 1},
        "data_link": {"sheet_url": "https://example.com/sheets/smoke"},
        "poc_routing": {
            "poc_routing_plan": "poc_routing_plan.json",
            "routing_rules": routing_rules,
        },
    }


def build_send_plan() -> dict[str, Any]:
    return {
        "requires_confirmation": True,
        "group_send_blocked": True,
        "sent": False,
        "real_group_send_executed": False,
        "content_source": {
            "card_json": "publish/low_efficiency_grading.card.json",
            "notification_draft": "notification_draft.json",
        },
    }


def run_checks() -> None:
    result = tracking.build_manual_tracking(
        notification_draft=build_notification_draft(),
        send_plan=build_send_plan(),
        state_machine_ref="references/scenarios/efficiency-label-rate.md#状态机",
    )

    assert result["tracking_mode"] == "local_debug_only", "tracking_mode mismatch"
    assert result["schema_version"] == "stage_2_manual_tracking.v1", (
        "schema_version mismatch"
    )
    assert result["safety"]["online_write_executed"] is False, (
        "online_write_executed must be False"
    )
    assert result["safety"]["online_state_write_allowed"] is False, (
        "online_state_write_allowed must be False"
    )
    severities = [record["severity_level"] for record in result["tracking_records"]]
    assert severities == LEVEL_ORDER, f"tracking severities mismatch: {severities}"


def main() -> None:
    try:
        run_checks()
    except Exception as error:  # noqa: BLE001
        print(f"resolution selfcheck FAILED: {error}")
        raise SystemExit(1)
    print("resolution selfcheck OK")


if __name__ == "__main__":
    main()
