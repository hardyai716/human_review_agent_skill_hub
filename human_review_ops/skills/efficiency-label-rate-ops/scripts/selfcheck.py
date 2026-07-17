#!/usr/bin/env python3
"""Self-check for the efficiency-label-rate scenario bundle."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import label_rate_analysis as analysis  # noqa: E402
from build_label_rate_manual_tracking import build_manual_tracking, load_json  # noqa: E402
from label_rate_notification_artifacts import build_label_rate_notification_artifacts  # noqa: E402
from label_rate_perception import detect_label_rate_perception  # noqa: E402


def run_perception_check() -> None:
    payload = detect_label_rate_perception(
        raw_user_request="帮我看近7天低打标率策略，按P0/P1/P2/notice分级。"
    )
    assert payload["scenario_key"] == "efficiency-label-rate"
    assert payload["task_type"] == "low_label_rate_grading"
    assert payload["readiness"]["status"] == "ready"


def build_analysis_records() -> list[dict]:
    levels = analysis.parse_levels(",".join(analysis.DEFAULT_LEVELS))
    sql_map = analysis.sql_by_level()
    payloads = analysis.build_smoke_payloads(levels)
    return analysis.build_records(payloads, levels, sql_map)


def run_notification_and_resolution_check(records: list[dict]) -> None:
    with tempfile.TemporaryDirectory(prefix="label-rate-bundle-selfcheck-") as tmp:
        tmp_path = Path(tmp)
        source_path = tmp_path / "analysis_result.jsonl"
        output_dir = tmp_path / "notification"
        source_path.write_text(
            "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
            encoding="utf-8",
        )
        build_label_rate_notification_artifacts(
            source_path=source_path,
            output_dir=output_dir,
            top_n=2,
            sheet_url="https://example.com/sheets/smoke",
            identity="bot",
            title="近7天低效打标策略全等级结果",
            self_send_requested=False,
            sent_payload=None,
            target_user_id=None,
            target_chat_id=None,
            auto_import_sheet=False,
        )
        notification_draft = load_json(output_dir / "notification_draft.json")
        send_plan = load_json(output_dir / "send_plan.json")
        tracking = build_manual_tracking(
            notification_draft=notification_draft,
            send_plan=send_plan,
            state_machine_ref="references/scenario_contract.md#state_machine.md",
        )
        assert send_plan["sent"] is False
        assert send_plan["group_send_blocked"] is True
        assert tracking["tracking_mode"] == "local_debug_only"
        assert tracking["safety"]["online_write_executed"] is False
        assert tracking["closure_check"]["can_close"] is False
        assert tracking["state_machine"]["next_state"] == "MANUAL_TRACKING_RECORDED"


def main() -> None:
    run_perception_check()
    records = build_analysis_records()
    sample = records[1]
    for key in ("QueryPlan", "source_footer", "readonly_execution", "analysis_result"):
        assert key in sample, f"analysis sample missing {key}"
    run_notification_and_resolution_check(records)
    print("efficiency-label-rate scenario bundle selfcheck OK")


if __name__ == "__main__":
    main()
