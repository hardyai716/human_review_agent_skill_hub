#!/usr/bin/env python3
"""Self-contained smoke check for the notification Skill (drafts only, never sends)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from label_rate_notification_artifacts import (  # noqa: E402
    build_label_rate_notification_artifacts,
)
from label_rate_weekly_summary_comparison import (  # noqa: E402
    build_weekly_summary_comparison,
)


def make_row(
    *,
    level: str,
    label: str,
    poc: str,
    strategy_id: str,
    reason: str,
    avg_done: int,
    label_rate: float,
) -> dict[str, Any]:
    return {
        "severity_level": level,
        "severity_priority": {"P0": 0, "P1": 1, "P2": 2, "notice": 3}[level],
        "mach_root_label_name": label,
        "strategy_id": strategy_id,
        "strategy_name": f"{strategy_id}_name",
        "reason": reason,
        "POC": poc,
        "poc_name": poc,
        "poc_open_id": None,
        "poc_mapping_status": "mapped_name_only",
        "data_days": 7,
        "total_review_in_cnt": avg_done * 7,
        "total_review_done_cnt": avg_done * 7,
        "total_label_cnt": round(avg_done * 7 * label_rate),
        "avg_review_in_cnt": avg_done,
        "avg_review_done_cnt": avg_done,
        "avg_label_cnt": round(avg_done * label_rate, 2),
        "label_rate": label_rate,
        "prev_avg_review_in_cnt": avg_done - 10,
        "prev_label_rate": label_rate,
        "growth_rate": 0.25,
        "daily_delta": 10,
        "hit_rule_id": f"{level}_smoke_rule",
        "hit_rule_ids": [f"{level}_smoke_rule"],
        "hit_condition": "smoke low label-rate condition",
        "hit_conditions": ["smoke low label-rate condition"],
    }


def build_sample() -> dict[str, Any]:
    p0 = make_row(
        level="P0",
        label="国家安全",
        poc="杜衡",
        strategy_id="strategy_p0",
        reason="reason_p0",
        avg_done=12000,
        label_rate=0.01,
    )
    p1 = make_row(
        level="P1",
        label="领导人",
        poc="宋诗慧",
        strategy_id="strategy_p1",
        reason="reason_p1",
        avg_done=6000,
        label_rate=0.02,
    )
    p2 = make_row(
        level="P2",
        label="违法违规",
        poc="叶健",
        strategy_id="strategy_p2",
        reason="reason_p2",
        avg_done=3000,
        label_rate=0.04,
    )
    notice = make_row(
        level="notice",
        label="危险行为",
        poc="陈雅静",
        strategy_id="strategy_notice",
        reason="reason_notice",
        avg_done=800,
        label_rate=0.08,
    )
    comprehensive = [p0, p1, p2, notice]
    execution = {
        "analysis_mode": "low_label_rate_grading",
        "execution_mode": "smoke",
        "status": "success",
        "level_counts": {"notice": 4, "P2": 1, "P1": 1, "P0": 1},
        "level_results": {
            "notice": {"rows": comprehensive},
            "P2": {"rows": [p2]},
            "P1": {"rows": [p1]},
            "P0": {"rows": [p0]},
        },
        "comprehensive_results": comprehensive,
        "row_count": len(comprehensive),
        "metric_formula": "`label_rate` = SUM(`[打标量__reviewid]`) / SUM(`[完审量_reviewid]`)",
    }
    return {
        "record_type": "sample",
        "id": "smoke-label-rate-notification",
        "scenario_key": "efficiency-label-rate",
        "task_type": "notification",
        "analysis_mode": "low_label_rate_grading",
        "run_mode": "debug_only",
        "QueryPlan": {
            "query_plan_id": "QP-SMOKE-LABEL-RATE-NOTIFICATION",
            "scenario_key": "efficiency-label-rate",
            "task_type": "low_label_rate_grading",
            "fallback_reason": "smoke_test_fixture",
        },
        "readonly_execution": execution,
        "provenance": {
            "dataset_id": "smoke_dataset",
            "region": "cn",
            "query_plan_id": "QP-SMOKE-LABEL-RATE-NOTIFICATION",
        },
        "source_footer": {
            "source_tier": "governed_dataset",
            "metric_definition_version": "smoke",
            "data_freshness": "p_date >= today() - 7 AND p_date < today(); checked_at=2026-07-09T12:00:00+08:00",
            "owner": "人审效率域数据 Owner",
            "confidence_tier": "high",
            "review_status": "smoke_fixture",
            "scenario_key": "efficiency-label-rate",
            "metric_id": "label_rate",
            "quality_checks": ["smoke_fixture"],
        },
    }


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_checks() -> None:
    with tempfile.TemporaryDirectory(prefix="notification-selfcheck-") as tmp:
        tmp_path = Path(tmp)
        source_path = tmp_path / "source.jsonl"
        output_dir = tmp_path / "output"
        source_path.write_text(
            json.dumps(build_sample(), ensure_ascii=False) + "\n",
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
        )

        send_plan_path = output_dir / "send_plan.json"
        notification_draft_path = output_dir / "notification_draft.json"
        poc_routing_path = output_dir / "poc_routing_plan.json"
        assert send_plan_path.exists(), "send_plan.json missing"
        assert notification_draft_path.exists(), "notification_draft.json missing"
        assert poc_routing_path.exists(), "poc_routing_plan.json missing"

        send_plan = read_json(send_plan_path)
        assert send_plan["requires_confirmation"] is True, (
            "send_plan must require confirmation"
        )
        assert send_plan["sent"] is False, "send_plan must not mark real send as sent"
        assert send_plan.get("group_send_blocked") is True, (
            "send_plan must block group send by default"
        )
        assert send_plan.get("online_write_executed") is False, (
            "send_plan must not mark online write executed"
        )

        # Default path must not import a Feishu online sheet: no sheet_url given
        # and auto_import_sheet off means the local draft has an empty link and
        # no online write happens.
        default_output_dir = tmp_path / "output_no_import"
        artifacts = build_label_rate_notification_artifacts(
            source_path=source_path,
            output_dir=default_output_dir,
            top_n=2,
            sheet_url=None,
            identity="bot",
            title="近7天低效打标策略全等级结果",
            self_send_requested=False,
            sent_payload=None,
            target_user_id=None,
            target_chat_id=None,
        )
        assert artifacts.publish_summary.get("sheet_url") in (None, ""), (
            "default run must not produce an online sheet_url without opt-in"
        )
        assert not (default_output_dir / "sheet_import_result.json").exists(), (
            "default run must not attempt a Feishu sheet import"
        )

        previous_summary = tmp_path / "previous" / "汇总统计_剔除+1同意.csv"
        current_summary = tmp_path / "current" / "汇总统计_剔除+1同意.csv"
        summary_header = (
            "机审一级标签,POC,低效策略数,低效策略日均进审量,"
            "低效策略日均完审量,低效策略日均打标量,低效策略打标率\n"
        )
        previous_summary.parent.mkdir(parents=True)
        current_summary.parent.mkdir(parents=True)
        previous_summary.write_text(
            "\ufeff" + summary_header + "国家安全,杜衡,2,100,100,5,0.05\n",
            encoding="utf-8",
        )
        current_summary.write_text(
            "\ufeff" + summary_header
            + "国家安全,杜衡,1,120,120,12,0.10\n"
            + "领导人,宋诗慧,1,80,80,4,0.05\n",
            encoding="utf-8",
        )
        comparison = build_weekly_summary_comparison(
            previous_summary_path=previous_summary,
            current_summary_path=current_summary,
            previous_start_date="2026-07-06",
            previous_end_date="2026-07-12",
            current_start_date="2026-07-13",
            current_end_date="2026-07-19",
            output_dir=tmp_path / "weekly_comparison",
        )
        assert comparison.workbook_path.exists(), "weekly comparison workbook missing"
        assert comparison.sheet_url is None, (
            "weekly comparison must not import an online sheet by default"
        )
        assert comparison.totals["current_label_rate"] == 0.08, (
            "weekly comparison must weight total label rate"
        )


def main() -> None:
    try:
        run_checks()
    except Exception as error:  # noqa: BLE001
        print(f"notification selfcheck FAILED: {error}")
        raise SystemExit(1)
    print("notification selfcheck OK")


if __name__ == "__main__":
    main()
