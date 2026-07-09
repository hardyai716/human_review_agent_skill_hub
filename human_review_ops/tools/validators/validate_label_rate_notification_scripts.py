#!/usr/bin/env python3
"""Smoke-test reusable label-rate notification Skill scripts."""

from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[2]
NOTIFICATION_SCRIPTS = ROOT / "skills" / "notification" / "scripts"
sys.path.insert(0, str(NOTIFICATION_SCRIPTS))

from card_hash import strip_internal_keys, verify_card_hash  # noqa: E402
from label_rate_notification_artifacts import (  # noqa: E402
    build_card_summary_rows,
    build_label_rate_notification_artifacts,
    build_level_top_rows,
    flatten_level_top_rows,
)
from render_label_rate_grading_card import card_design_check  # noqa: E402


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
        "status": "ok",
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


def write_source(path: Path) -> None:
    sample = build_sample()
    path.write_text(json.dumps(sample, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def validate_artifacts(artifacts: Any) -> None:
    output_dir = artifacts.output_dir
    required = [
        "summary.json",
        "notification_draft.json",
        "send_plan.json",
        "poc_routing_plan.json",
        "汇总统计.csv",
        "notice.csv",
        "P2.csv",
        "P1.csv",
        "P0.csv",
        "综合.csv",
        "publish/low_efficiency_grading.card.json",
        "publish/low_efficiency_grading.card.with_meta.json",
        "publish/card_hash_check.json",
        "publish/low_efficiency_grading.publish_summary.json",
    ]
    for relative in required:
        if not (output_dir / relative).exists():
            raise AssertionError(f"Missing smoke artifact: {relative}")

    summary = read_json(output_dir / "summary.json")
    notification_draft = read_json(output_dir / "notification_draft.json")
    send_plan = read_json(output_dir / "send_plan.json")
    poc_routing = read_json(output_dir / "poc_routing_plan.json")
    card = read_json(output_dir / "publish" / "low_efficiency_grading.card.json")
    card_with_meta = read_json(
        output_dir / "publish" / "low_efficiency_grading.card.with_meta.json"
    )
    hash_check = read_json(output_dir / "publish" / "card_hash_check.json")

    if summary.get("schema_version") != "stage_2_notification_draft.v1":
        raise AssertionError("summary schema mismatch.")
    if summary.get("outputs", {}).get("summary_by_label_poc_csv") != "汇总统计.csv":
        raise AssertionError("summary must expose summary_by_label_poc_csv.")
    if summary.get("label_poc_summary_count") != 4:
        raise AssertionError("summary label_poc_summary_count mismatch.")
    if notification_draft.get("real_poc_mapping_used") is not True:
        raise AssertionError("notification_draft must use name-level POC mapping.")
    if notification_draft.get("send_safety", {}).get("group_send_blocked") is not True:
        raise AssertionError("notification_draft must block group send.")
    if send_plan.get("requires_confirmation") is not True:
        raise AssertionError("send_plan must require confirmation.")
    if send_plan.get("sent") is not False:
        raise AssertionError("send_plan must not mark real send as sent.")
    if poc_routing.get("routing_mode") != "mach_root_label_mapping":
        raise AssertionError("poc_routing must use mach_root_label_mapping.")
    if poc_routing.get("mapped_row_count") != 4:
        raise AssertionError("poc_routing mapped_row_count mismatch.")

    summary_rows = read_csv_rows(output_dir / "汇总统计.csv")
    if len(summary_rows) != 4:
        raise AssertionError("summary CSV row count mismatch.")
    for field in ("机审一级标签", "POC", "低效策略打标率"):
        if field not in summary_rows[0]:
            raise AssertionError(f"summary CSV missing field: {field}")
    if len(read_csv_rows(output_dir / "综合.csv")) != 4:
        raise AssertionError("comprehensive CSV row count mismatch.")
    if len(read_csv_rows(output_dir / "P0.csv")) != 1:
        raise AssertionError("P0 CSV row count mismatch.")

    workbook_files = list(output_dir.glob("low_label_rate_grading_*.xlsx"))
    if len(workbook_files) != 1:
        raise AssertionError("expected exactly one smoke workbook.")
    workbook = load_workbook(workbook_files[0], read_only=True)
    try:
        expected_sheets = {"P0", "P1", "P2", "Notice", "综合", "汇总统计"}
        if set(workbook.sheetnames) != expected_sheets:
            raise AssertionError("workbook sheet structure mismatch.")
    finally:
        workbook.close()

    if "_meta" in card:
        raise AssertionError("send card must not contain _meta.")
    if strip_internal_keys(card_with_meta) != card:
        raise AssertionError("card must equal stripped card_with_meta.")
    level_top_rows = build_level_top_rows(
        build_sample()["readonly_execution"]["level_results"],
        2,
    )
    hash_rows = build_card_summary_rows(artifacts.report.summary_rows)
    hash_rows += flatten_level_top_rows(level_top_rows)
    verify_card_hash(card_with_meta, hash_rows)
    if hash_check.get("ok") is not True:
        raise AssertionError("hash_check must be ok.")
    if card_design_check(card_with_meta).get("passes_p0_p3_basic_gate") is not True:
        raise AssertionError("card design smoke gate failed.")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="label-rate-notification-smoke-") as tmp:
        tmp_path = Path(tmp)
        source_path = tmp_path / "source.jsonl"
        output_dir = tmp_path / "output"
        write_source(source_path)
        artifacts = build_label_rate_notification_artifacts(
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
        validate_artifacts(artifacts)
    print("Label-rate notification scripts smoke OK.")


if __name__ == "__main__":
    main()
