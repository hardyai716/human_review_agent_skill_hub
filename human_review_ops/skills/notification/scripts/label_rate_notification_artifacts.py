#!/usr/bin/env python3
"""Build reusable label-rate notification artifacts without sending messages."""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from card_hash import strip_internal_keys, verify_card_hash
from render_label_rate_grading_card import (
    LEVEL_COLORS,
    card_design_check,
    render_grading_card,
)
from resolve_label_rate_poc_routing import build_poc_routing_plan, load_stage_1_sample


ROOT = Path(__file__).resolve().parents[3]
SCENARIO_KEY = "efficiency-label-rate"
SCENARIO_REFERENCE = "references/scenarios/efficiency-label-rate.md"
CARD_TEMPLATE_ASSET = (
    "assets/efficiency-label-rate/low_efficiency_grading_card_template.json"
)
CARD_SCHEMA_NOTES_ASSET = "assets/efficiency-label-rate/card_schema_notes.md"
POC_MAPPING_ASSET = "assets/efficiency-label-rate/mach_root_label_poc_mapping.json"
REPORT_TYPE = "low_efficiency_grading"
CSV_LEVELS = ["notice", "P2", "P1", "P0"]
CARD_LEVELS = ["P0", "P1", "P2", "notice"]
LEVEL_COLUMN_SPECS = [
    ("mach_root_label_name", "机审一级标签"),
    ("strategy_id", "策略ID"),
    ("strategy_name", "策略名称"),
    ("reason", "送审原因"),
    ("POC", "POC"),
    ("avg_review_in_cnt", "日均进审量"),
    ("avg_review_done_cnt", "日均完审量"),
    ("avg_label_cnt", "日均打标量"),
    ("label_rate", "打标率"),
    ("hit_conditions", "命中原因"),
]
SUMMARY_COLUMN_SPECS = [
    ("mach_root_label_name", "机审一级标签"),
    ("POC", "POC"),
    ("low_efficiency_strategy_count", "低效策略数"),
    ("avg_review_in_cnt", "低效策略日均进审量"),
    ("avg_review_done_cnt", "低效策略日均完审量"),
    ("avg_label_cnt", "低效策略日均打标量"),
    ("label_rate", "低效策略打标率"),
]


@dataclass(frozen=True)
class ReportArtifacts:
    """CSV/XLSX report files and the rows used by card summary tables."""

    summary_rows: list[dict[str, Any]]
    workbook_path: Path
    summary_csv_path: Path


@dataclass(frozen=True)
class CardArtifacts:
    """Card payload paths and hash-check metadata."""

    card_path: Path
    card_with_meta_path: Path
    hash_check_path: Path
    card_json: dict[str, Any]
    card_with_meta: dict[str, Any]
    hash_check: dict[str, Any]


@dataclass(frozen=True)
class NotificationArtifacts:
    """Top-level stage 2 notification artifact paths."""

    output_dir: Path
    summary_path: Path
    notification_draft_path: Path
    send_plan_path: Path
    poc_routing_path: Path
    publish_summary_path: Path
    report: ReportArtifacts
    card: CardArtifacts
    summary: dict[str, Any]
    notification_draft: dict[str, Any]
    send_plan: dict[str, Any]
    publish_summary: dict[str, Any]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build notification_draft, send_plan, CSV/XLSX reports, POC routing, "
            "and Card JSON for a label-rate grading stage 1 JSONL result. "
            "This script never sends Feishu messages."
        )
    )
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--sheet-url")
    parser.add_argument("--identity", choices=["bot", "user"], default="bot")
    parser.add_argument("--title", default="近7天低效打标策略全等级结果")
    args = parser.parse_args()

    if args.top_n <= 0:
        raise SystemExit("--top-n must be a positive integer.")

    artifacts = build_label_rate_notification_artifacts(
        source_path=Path(args.source),
        output_dir=Path(args.output_dir),
        top_n=args.top_n,
        sheet_url=args.sheet_url,
        identity=args.identity,
        title=args.title,
        self_send_requested=False,
        sent_payload=None,
        target_user_id=None,
        target_chat_id=None,
    )
    print(
        "Label-rate notification artifacts wrote "
        f"{relative_to_root(artifacts.output_dir)}; sent="
        f"{artifacts.publish_summary['sent']}; message_id="
        f"{artifacts.publish_summary['message_id']}"
    )


def build_label_rate_notification_artifacts(
    *,
    source_path: Path,
    output_dir: Path,
    top_n: int,
    sheet_url: str | None,
    identity: str,
    title: str,
    self_send_requested: bool,
    sent_payload: dict[str, Any] | None,
    target_user_id: str | None,
    target_chat_id: str | None,
) -> NotificationArtifacts:
    """Build all safe notification artifacts; caller owns any real send action."""

    if top_n <= 0:
        raise ValueError("top_n must be a positive integer.")
    output_dir.mkdir(parents=True, exist_ok=True)
    publish_dir = output_dir / "publish"
    publish_dir.mkdir(parents=True, exist_ok=True)

    sample = load_stage_1_sample(source_path)
    execution = sample["readonly_execution"]
    period = derive_period(sample)
    report = write_report_artifacts(output_dir, execution, period)
    summary = build_summary(
        source_path=source_path,
        output_dir=output_dir,
        workbook_path=report.workbook_path,
        sample=sample,
        period=period,
        sheet_url=sheet_url,
        top_n=top_n,
        self_send_requested=self_send_requested,
        label_poc_summary_count=len(report.summary_rows),
    )
    poc_routing_path = write_poc_routing_artifact(
        output_dir=output_dir,
        sample=sample,
        source_path=source_path,
    )
    card = write_card_artifacts(
        publish_dir=publish_dir,
        summary=summary,
        summary_rows=report.summary_rows,
        level_results=execution["level_results"],
        top_n=top_n,
        sheet_url=sheet_url,
        title=title,
    )

    summary_path = output_dir / "summary.json"
    notification_draft_path = output_dir / "notification_draft.json"
    send_plan_path = output_dir / "send_plan.json"
    publish_summary_path = publish_dir / f"{REPORT_TYPE}.publish_summary.json"
    publish_summary = build_publish_summary(
        source_path=source_path,
        output_dir=output_dir,
        summary_path=summary_path,
        workbook_path=report.workbook_path,
        summary_csv_path=report.summary_csv_path,
        sheet_url=sheet_url,
        card=card,
        notification_draft_path=notification_draft_path,
        send_plan_path=send_plan_path,
        identity=identity,
        sent_payload=sent_payload,
        target_user_id=target_user_id,
        target_chat_id=target_chat_id,
    )
    summary["publish"] = publish_summary
    notification_draft = build_notification_draft(
        summary=summary,
        poc_routing_path=poc_routing_path,
        card_path=card.card_path,
        card_with_meta_path=card.card_with_meta_path,
        hash_check_path=card.hash_check_path,
        publish_summary=publish_summary,
    )
    send_plan = build_send_plan(
        identity=identity,
        publish_summary=publish_summary,
        poc_routing_path=poc_routing_path,
        card_path=card.card_path,
        notification_draft_path=notification_draft_path,
    )

    write_json(notification_draft_path, notification_draft)
    write_json(send_plan_path, send_plan)
    write_json(summary_path, summary)
    write_json(publish_summary_path, publish_summary)
    return NotificationArtifacts(
        output_dir=output_dir,
        summary_path=summary_path,
        notification_draft_path=notification_draft_path,
        send_plan_path=send_plan_path,
        poc_routing_path=poc_routing_path,
        publish_summary_path=publish_summary_path,
        report=report,
        card=card,
        summary=summary,
        notification_draft=notification_draft,
        send_plan=send_plan,
        publish_summary=publish_summary,
    )


def derive_period(sample: dict[str, Any]) -> dict[str, str]:
    freshness = sample.get("source_footer", {}).get("data_freshness", "")
    match = re.search(r"checked_at=([^;\\s]+)", freshness)
    if match:
        checked_at = datetime.fromisoformat(match.group(1))
    else:
        checked_at = datetime.now()
    current_end = checked_at.date() - timedelta(days=1)
    current_start = current_end - timedelta(days=6)
    history_start = current_end - timedelta(days=27)
    return {
        "current_start": current_start.isoformat(),
        "current_end": current_end.isoformat(),
        "history_start": history_start.isoformat(),
        "checked_at": checked_at.isoformat(),
    }


def write_report_artifacts(
    output_dir: Path,
    execution: dict[str, Any],
    period: dict[str, str],
) -> ReportArtifacts:
    write_level_csvs(output_dir, execution)
    summary_rows = build_label_poc_summary_rows(execution["comprehensive_results"])
    summary_csv_path = output_dir / "汇总统计.csv"
    write_summary_csv(summary_csv_path, summary_rows)
    workbook_path = write_workbook(output_dir, execution, period, summary_rows)
    return ReportArtifacts(
        summary_rows=summary_rows,
        workbook_path=workbook_path,
        summary_csv_path=summary_csv_path,
    )


def write_level_csvs(output_dir: Path, execution: dict[str, Any]) -> None:
    for level in CSV_LEVELS:
        rows = execution["level_results"][level]["rows"]
        write_level_csv(output_dir / f"{level}.csv", rows)
    write_level_csv(output_dir / "综合.csv", execution["comprehensive_results"])


def write_level_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=[header for _, header in LEVEL_COLUMN_SPECS]
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    header: csv_value(csv_column_value(row, field))
                    for field, header in LEVEL_COLUMN_SPECS
                }
            )


def write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=[header for _, header in SUMMARY_COLUMN_SPECS]
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    header: csv_value(row.get(field))
                    for field, header in SUMMARY_COLUMN_SPECS
                }
            )


def write_workbook(
    output_dir: Path,
    execution: dict[str, Any],
    period: dict[str, str],
    summary_rows: list[dict[str, Any]],
) -> Path:
    workbook_path = (
        output_dir
        / f"low_label_rate_grading_{period['current_start']}_{period['current_end']}.xlsx"
    )
    workbook = Workbook()
    default_sheet = workbook.active
    workbook.remove(default_sheet)

    for sheet_name, rows in [
        ("P0", execution["level_results"]["P0"]["rows"]),
        ("P1", execution["level_results"]["P1"]["rows"]),
        ("P2", execution["level_results"]["P2"]["rows"]),
        ("Notice", execution["level_results"]["notice"]["rows"]),
        ("综合", execution["comprehensive_results"]),
    ]:
        sheet = workbook.create_sheet(sheet_name)
        sheet.append([header for _, header in LEVEL_COLUMN_SPECS])
        for row in rows:
            sheet.append(
                [
                    csv_value(csv_column_value(row, field))
                    for field, _ in LEVEL_COLUMN_SPECS
                ]
            )
        style_sheet_header(sheet)

    summary_sheet = workbook.create_sheet("汇总统计")
    summary_sheet.append([header for _, header in SUMMARY_COLUMN_SPECS])
    for row in summary_rows:
        summary_sheet.append(
            [csv_value(row.get(field)) for field, _ in SUMMARY_COLUMN_SPECS]
        )
    style_sheet_header(summary_sheet)
    workbook.save(workbook_path)
    return workbook_path


def write_poc_routing_artifact(
    *,
    output_dir: Path,
    sample: dict[str, Any],
    source_path: Path,
) -> Path:
    poc_routing_path = output_dir / "poc_routing_plan.json"
    plan = build_poc_routing_plan(
        sample,
        source_stage_1_result=relative_to_root(source_path),
    )
    write_json(poc_routing_path, plan)
    return poc_routing_path


def build_summary(
    *,
    source_path: Path,
    output_dir: Path,
    workbook_path: Path,
    sample: dict[str, Any],
    period: dict[str, str],
    sheet_url: str | None,
    top_n: int,
    self_send_requested: bool,
    label_poc_summary_count: int,
) -> dict[str, Any]:
    execution = sample["readonly_execution"]
    provenance = sample["provenance"]
    return {
        "schema_version": "stage_2_notification_draft.v1",
        "report_type": REPORT_TYPE,
        "scenario_key": SCENARIO_KEY,
        "run_mode": "debug_only_with_explicit_self_send"
        if self_send_requested
        else "draft_only_with_name_level_poc_routing",
        "source_stage_1_result": relative_to_root(source_path),
        "reference_docs": [SCENARIO_REFERENCE],
        "asset_refs": {
            "poc_mapping": POC_MAPPING_ASSET,
            "card_template": CARD_TEMPLATE_ASSET,
            "card_schema_notes": CARD_SCHEMA_NOTES_ASSET,
        },
        "output_dir": relative_to_root(output_dir),
        "dataset_id": provenance["dataset_id"],
        "region": provenance["region"],
        "period": period,
        "level_counts": execution["level_counts"],
        "comprehensive_reason_count": execution["row_count"],
        "comprehensive_strategy_group_count": execution["row_count"],
        "fallback_reason": sample["QueryPlan"]["fallback_reason"],
        "metric_formula": execution["metric_formula"],
        "top_n": top_n,
        "sheet_url": sheet_url,
        "label_poc_summary_count": label_poc_summary_count,
        "outputs": {
            "summary_json": "summary.json",
            "notice_csv": "notice.csv",
            "P2_csv": "P2.csv",
            "P1_csv": "P1.csv",
            "P0_csv": "P0.csv",
            "comprehensive_csv": "综合.csv",
            "workbook": workbook_path.name,
            "poc_routing_plan": "poc_routing_plan.json",
            "notification_draft": "notification_draft.json",
            "send_plan": "send_plan.json",
            "summary_by_label_poc_csv": "汇总统计.csv",
        },
        "source_footer": sample["source_footer"],
    }


def write_card_artifacts(
    *,
    publish_dir: Path,
    summary: dict[str, Any],
    summary_rows: list[dict[str, Any]],
    level_results: dict[str, dict[str, Any]],
    top_n: int,
    sheet_url: str | None,
    title: str,
) -> CardArtifacts:
    level_top_rows = build_level_top_rows(level_results, top_n)
    summary_card_rows = build_card_summary_rows(summary_rows)
    hash_rows = summary_card_rows + flatten_level_top_rows(level_top_rows)
    card_with_meta = render_grading_card(
        summary=summary,
        summary_rows=summary_card_rows,
        level_top_rows=level_top_rows,
        sheet_url=sheet_url,
        title=title,
    )
    verify_card_hash(card_with_meta, hash_rows)
    card_json = strip_internal_keys(card_with_meta)
    hash_check = {
        "ok": True,
        "data_hash": card_with_meta["_meta"]["_data_hash"],
        "top_rows_count": len(hash_rows),
        "level_top_rows_count": {
            level: len(rows) for level, rows in level_top_rows.items()
        },
        "internal_meta_removed": "_meta" not in card_json,
        "design_check": card_design_check(card_with_meta),
    }

    card_path = publish_dir / f"{REPORT_TYPE}.card.json"
    card_with_meta_path = publish_dir / f"{REPORT_TYPE}.card.with_meta.json"
    hash_check_path = publish_dir / "card_hash_check.json"
    write_json(card_path, card_json, compact=True)
    write_json(card_with_meta_path, card_with_meta)
    write_json(hash_check_path, hash_check)
    return CardArtifacts(
        card_path=card_path,
        card_with_meta_path=card_with_meta_path,
        hash_check_path=hash_check_path,
        card_json=card_json,
        card_with_meta=card_with_meta,
        hash_check=hash_check,
    )


def build_publish_summary(
    *,
    source_path: Path,
    output_dir: Path,
    summary_path: Path,
    workbook_path: Path,
    summary_csv_path: Path,
    sheet_url: str | None,
    card: CardArtifacts,
    notification_draft_path: Path,
    send_plan_path: Path,
    identity: str,
    sent_payload: dict[str, Any] | None,
    target_user_id: str | None,
    target_chat_id: str | None,
) -> dict[str, Any]:
    return {
        "report_type": REPORT_TYPE,
        "scenario_key": SCENARIO_KEY,
        "source_stage_1_result": relative_to_root(source_path),
        "output_dir": relative_to_root(output_dir),
        "summary_json": relative_to_root(summary_path),
        "workbook": relative_to_root(workbook_path),
        "summary_by_label_poc_csv": relative_to_root(summary_csv_path),
        "sheet_url": sheet_url,
        "card_json": relative_to_root(card.card_path),
        "card_json_with_meta": relative_to_root(card.card_with_meta_path),
        "card_hash_check": relative_to_root(card.hash_check_path),
        "sent": sent_payload is not None,
        "send_identity": identity if sent_payload is not None else None,
        "target_type": "user" if target_user_id else ("chat" if target_chat_id else None),
        "target_user": "self" if target_user_id and sent_payload is not None else None,
        "target_user_open_id_prefix": mask_identifier(target_user_id)
        if target_user_id and sent_payload is not None
        else None,
        "target_chat_id": target_chat_id if sent_payload is not None else None,
        "message_id": extract_message_id(sent_payload),
        "send_result": sanitize_send_payload(sent_payload),
        "notification_draft": relative_to_root(notification_draft_path),
        "send_plan": relative_to_root(send_plan_path),
    }


def build_notification_draft(
    *,
    summary: dict[str, Any],
    poc_routing_path: Path,
    card_path: Path,
    card_with_meta_path: Path,
    hash_check_path: Path,
    publish_summary: dict[str, Any],
) -> dict[str, Any]:
    if not poc_routing_path.exists():
        raise FileNotFoundError(f"Missing POC routing plan: {poc_routing_path}")
    poc_routing = load_json(poc_routing_path)
    constraints = poc_routing.get("routing_constraints", {})
    return {
        "schema_version": "stage_2_notification_draft_detail.v1",
        "scenario_key": SCENARIO_KEY,
        "report_type": REPORT_TYPE,
        "draft_mode": "self_preview_with_name_level_poc_routing",
        "default_self_validation": True,
        "real_poc_mapping_used": poc_routing.get("real_poc_mapping_used", False),
        "source_stage_1_result": summary["source_stage_1_result"],
        "level_counts": summary["level_counts"],
        "comprehensive_reason_count": summary["comprehensive_reason_count"],
        "comprehensive_strategy_group_count": summary[
            "comprehensive_strategy_group_count"
        ],
        "data_link": {
            "sheet_url": summary.get("sheet_url"),
            "workbook": summary["outputs"].get("workbook"),
            "csv_files": {
                "summary_by_label_poc": summary["outputs"].get(
                    "summary_by_label_poc_csv"
                ),
                "notice": summary["outputs"].get("notice_csv"),
                "P2": summary["outputs"].get("P2_csv"),
                "P1": summary["outputs"].get("P1_csv"),
                "P0": summary["outputs"].get("P0_csv"),
                "comprehensive": summary["outputs"].get("comprehensive_csv"),
            },
        },
        "card_draft": {
            "card_json": relative_to_root(card_path),
            "card_json_with_meta": relative_to_root(card_with_meta_path),
            "card_hash_check": relative_to_root(hash_check_path),
            "send_card_meta_removed": True,
        },
        "poc_routing": {
            "poc_routing_plan": relative_to_root(poc_routing_path),
            "routing_mode": poc_routing.get("routing_mode"),
            "fallback_to_default_user": poc_routing.get("fallback_to_default_user"),
            "default_recipient": poc_routing.get("default_recipient"),
            "routing_key": poc_routing.get("routing_key"),
            "contact_resolution_status": poc_routing.get("contact_resolution_status"),
            "mapped_row_count": poc_routing.get("mapped_row_count"),
            "unmapped_row_count": poc_routing.get("unmapped_row_count"),
            "missing_route_dimension_count": poc_routing.get(
                "missing_route_dimension_count"
            ),
            "poc_summary": poc_routing.get("poc_summary", []),
            "routing_rules": summarize_routing_rules(poc_routing),
            "routing_constraints": constraints,
        },
        "methodology": {
            "metric_formula": summary.get("metric_formula"),
            "period": summary.get("period"),
            "source_footer": summary.get("source_footer"),
            "reference_docs": [SCENARIO_REFERENCE],
            "asset_refs": {
                "poc_mapping": POC_MAPPING_ASSET,
                "card_template": CARD_TEMPLATE_ASSET,
                "card_schema_notes": CARD_SCHEMA_NOTES_ASSET,
            },
        },
        "send_safety": {
            "current_stage": "draft_only_for_group_send",
            "current_preview_recipient": "self",
            "requires_confirmation_before_group_send": True,
            "group_send_blocked": constraints.get("group_send_blocked", True),
            "group_send_allowed": constraints.get("group_send_allowed", False),
            "sent": False,
            "real_group_send_executed": False,
            "online_write_executed": constraints.get("online_write_executed", False),
            "self_preview_sent": publish_summary.get("sent", False),
            "self_preview_message_id": publish_summary.get("message_id"),
        },
        "provenance": {
            "reference_docs": [SCENARIO_REFERENCE],
            "asset_refs": {
                "poc_mapping": POC_MAPPING_ASSET,
                "card_template": CARD_TEMPLATE_ASSET,
                "card_schema_notes": CARD_SCHEMA_NOTES_ASSET,
            },
            "dataset_id": summary.get("dataset_id"),
            "region": summary.get("region"),
            "query_plan_id": summary.get("source_footer", {})
            .get("query_context", {})
            .get("query_plan_id"),
        },
    }


def build_send_plan(
    *,
    identity: str,
    publish_summary: dict[str, Any],
    poc_routing_path: Path,
    card_path: Path,
    notification_draft_path: Path,
) -> dict[str, Any]:
    return {
        "schema_version": "stage_2_send_plan.v1",
        "scenario_key": SCENARIO_KEY,
        "report_type": REPORT_TYPE,
        "plan_mode": "manual_confirmation_required",
        "target_type": "future_group_or_name_level_poc_after_confirmation",
        "target_source": relative_to_root(poc_routing_path),
        "content_source": {
            "card_json": relative_to_root(card_path),
            "notification_draft": relative_to_root(notification_draft_path),
        },
        "reference_docs": [SCENARIO_REFERENCE],
        "asset_refs": {
            "poc_mapping": POC_MAPPING_ASSET,
            "card_template": CARD_TEMPLATE_ASSET,
            "card_schema_notes": CARD_SCHEMA_NOTES_ASSET,
        },
        "send_identity": identity,
        "requires_confirmation": True,
        "confirmation_status": "not_requested",
        "group_send_blocked": True,
        "group_send_allowed": False,
        "group_recipients": [],
        "sent": False,
        "real_group_send_executed": False,
        "online_write_executed": False,
        "blocked_reason": (
            "Stage 2 has name-level POC routing only. Feishu open_id resolution, "
            "target chat confirmation, and explicit confirmation are required before "
            "real POC/group sending."
        ),
        "self_preview": {
            "default_recipient": "self",
            "sent": publish_summary.get("sent", False),
            "message_id": publish_summary.get("message_id"),
        },
        "required_before_real_send": [
            "resolve POC names to confirmed Feishu open_id",
            "confirm target chat or POC recipients",
            "confirm send identity and content",
            "run validator with group-send gate enabled",
        ],
    }


def build_label_poc_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (
            str(row.get("mach_root_label_name", "")),
            str(row.get("POC") or row.get("poc_name") or "未映射"),
        )
        bucket = grouped.setdefault(
            key,
            {
                "mach_root_label_name": key[0],
                "POC": key[1],
                "_strategy_names": set(),
                "_total_review_in_cnt": 0.0,
                "_total_review_done_cnt": 0.0,
                "_total_label_cnt": 0.0,
                "_avg_review_in_cnt": 0.0,
                "_avg_review_done_cnt": 0.0,
                "_avg_label_cnt": 0.0,
            },
        )
        strategy_name = str(row.get("strategy_name") or "")
        strategy_id = str(row.get("strategy_id") or "")
        strategy_key = strategy_id or strategy_name
        if strategy_key:
            bucket["_strategy_names"].add(strategy_key)
        bucket["_total_review_in_cnt"] += float(row.get("total_review_in_cnt", 0) or 0)
        bucket["_total_review_done_cnt"] += float(
            row.get("total_review_done_cnt", 0) or 0
        )
        bucket["_total_label_cnt"] += float(row.get("total_label_cnt", 0) or 0)
        bucket["_avg_review_in_cnt"] += float(row.get("avg_review_in_cnt", 0) or 0)
        bucket["_avg_review_done_cnt"] += float(row.get("avg_review_done_cnt", 0) or 0)
        bucket["_avg_label_cnt"] += float(row.get("avg_label_cnt", 0) or 0)

    result: list[dict[str, Any]] = []
    for bucket in grouped.values():
        total_done = bucket["_total_review_done_cnt"]
        result.append(
            {
                "mach_root_label_name": bucket["mach_root_label_name"],
                "POC": bucket["POC"],
                "low_efficiency_strategy_count": len(bucket["_strategy_names"]),
                "avg_review_in_cnt": round(bucket["_avg_review_in_cnt"]),
                "avg_review_done_cnt": round(bucket["_avg_review_done_cnt"]),
                "avg_label_cnt": round(bucket["_avg_label_cnt"]),
                "label_rate": bucket["_total_label_cnt"] / total_done
                if total_done
                else 0.0,
            }
        )
    return sorted(
        result,
        key=lambda item: (
            -float(item["avg_review_done_cnt"]),
            str(item["mach_root_label_name"]),
            str(item["POC"]),
        ),
    )


def build_level_top_rows(
    level_results: dict[str, dict[str, Any]],
    top_n: int,
) -> dict[str, list[dict[str, Any]]]:
    return {
        level: build_top_rows(level_results.get(level, {}).get("rows", []), top_n)
        for level in CARD_LEVELS
    }


def flatten_level_top_rows(
    level_top_rows: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for level in CARD_LEVELS:
        flattened.extend(level_top_rows.get(level, []))
    return flattened


def build_card_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "mach_root_label_name": row.get("mach_root_label_name", ""),
            "POC": row.get("POC", ""),
            "low_efficiency_strategy_count": int(
                row.get("low_efficiency_strategy_count", 0) or 0
            ),
            "avg_review_in_cnt": int(round(float(row.get("avg_review_in_cnt", 0) or 0))),
            "avg_review_done_cnt": int(
                round(float(row.get("avg_review_done_cnt", 0) or 0))
            ),
            "avg_label_cnt": int(round(float(row.get("avg_label_cnt", 0) or 0))),
            "label_rate": pct_value(row.get("label_rate")),
        }
        for row in rows
    ]


def build_top_rows(rows: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
    top_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows[:top_n], 1):
        level = row["severity_level"]
        top_rows.append(
            {
                "rank": index,
                "level": [{"text": level, "color": LEVEL_COLORS.get(level, "blue")}],
                "poc_name": row.get("POC") or row.get("poc_name", "未映射"),
                "mach_root_label_name": row.get("mach_root_label_name", ""),
                "strategy_id": row.get("strategy_id", ""),
                "strategy_name": row.get("strategy_name", ""),
                "reason": row["reason"],
                "avg_in": round(float(row["avg_review_in_cnt"])),
                "avg_done": round(float(row["avg_review_done_cnt"])),
                "avg_labeled": round(float(row["avg_label_cnt"])),
                "label_rate": pct_value(row.get("label_rate")),
                "hit_reason": csv_value(row.get("hit_conditions")),
            }
        )
    return top_rows


def summarize_routing_rules(poc_routing: dict[str, Any]) -> dict[str, Any]:
    rules = poc_routing.get("routing_rules", {})
    return {
        level: {
            "target_roles": rule.get("target_roles", []),
            "action_required": rule.get("action_required"),
            "default_recipient": rule.get("default_recipient"),
            "recipient_resolution": rule.get("recipient_resolution", {}),
            "requires_human_confirmation_before_real_send": rule.get(
                "requires_human_confirmation_before_real_send"
            ),
            "group_send_blocked": rule.get("group_send_blocked"),
            "reason_count": rule.get("reason_count"),
            "strategy_group_count": rule.get("strategy_group_count"),
            "poc_names": rule.get("poc_names", []),
            "unmapped_labels": rule.get("unmapped_labels", []),
        }
        for level, rule in rules.items()
    }


def style_sheet_header(sheet: Any) -> None:
    fill = PatternFill("solid", fgColor="D9E8FF")
    font = Font(bold=True)
    for cell in sheet[1]:
        cell.fill = fill
        cell.font = font
    sheet.freeze_panes = "A2"


def csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return "；".join(str(item) for item in value)
    return value


def csv_column_value(row: dict[str, Any], column: str) -> Any:
    if column == "POC":
        return row.get("POC") or row.get("poc_name")
    return row.get(column)


def pct_value(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return str(value)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        if compact
        else json.dumps(value, ensure_ascii=False, indent=2)
    )
    path.write_text(text + "\n", encoding="utf-8")


def relative_to_root(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def mask_identifier(value: str | None) -> str | None:
    if not value:
        return None
    return value[:10] + "..."


def extract_message_id(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    data = payload.get("data", {})
    if isinstance(data, dict):
        return data.get("message_id")
    return None


def sanitize_send_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    data = payload.get("data", {})
    return {
        "ok": payload.get("ok"),
        "identity": payload.get("identity"),
        "message_id": data.get("message_id") if isinstance(data, dict) else None,
        "create_time": data.get("create_time") if isinstance(data, dict) else None,
    }


if __name__ == "__main__":
    main()
