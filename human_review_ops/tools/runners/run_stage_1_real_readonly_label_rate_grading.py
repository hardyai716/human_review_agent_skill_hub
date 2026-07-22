#!/usr/bin/env python3
"""Run real readonly low-label-rate grading for stage 1.

This runner is intentionally scenario-specific. It executes the current
efficiency-label-rate grading rules for notice/P2/P1/P0 and keeps all actions
readonly.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_SCRIPTS = ROOT / "skills" / "analysis" / "scripts"
NOTIFICATION_SCRIPTS = ROOT / "skills" / "notification" / "scripts"
sys.path.insert(0, str(ANALYSIS_SCRIPTS))
sys.path.insert(0, str(NOTIFICATION_SCRIPTS))

import label_rate_analysis  # noqa: E402
from resolve_label_rate_poc_routing import (  # noqa: E402
    load_poc_mapping,
    poc_mapping_index,
    resolve_row_poc,
)


def build_poc_row_enrichment(
    row: dict[str, Any],
    mapping_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    poc = resolve_row_poc(row, mapping_index)
    poc_name = poc.get("poc_name") or "未映射"
    return {
        "poc_name": poc_name,
        "POC": poc_name,
        "poc_open_id": poc.get("poc_open_id"),
        "poc_mapping_status": poc.get("mapping_status"),
    }

SCENARIO_KEY = label_rate_analysis.SCENARIO_KEY
EVAL_DIR = ROOT / "evals" / SCENARIO_KEY
DATASET_ID = label_rate_analysis.DATASET_ID
REGION = label_rate_analysis.REGION
QUERY_LIMIT = label_rate_analysis.QUERY_LIMIT
PLUS1_SHEET_URL = (
    "https://bytedance.larkoffice.com/wiki/XjcwwUp4KiMdsNk0k7uc7aCEnrd"
)
PLUS1_SHEET_ID = "zXKBBM"
PLUS1_SHEET_NAME = "保持不变明细表"
# Column upper bound only; the row bound is intentionally omitted so the read
# range grows with the sheet (new rows are covered without editing this file).
PLUS1_READ_START_COLUMN = "A"
PLUS1_REFRESH_POLICY = "current_sheet_authoritative"


def default_output_path(time_range: dict[str, Any] | None = None) -> Path:
    output_date = date.today().strftime("%Y%m%d")
    if time_range and time_range.get("current_start") and time_range.get("current_end"):
        start = str(time_range["current_start"]).replace("-", "")
        end = str(time_range["current_end"]).replace("-", "")
        filename = f"{output_date}_real_readonly_label_rate_grading_{start}_{end}_results.jsonl"
    else:
        filename = f"{output_date}_real_readonly_label_rate_grading_results.jsonl"
    return (
        EVAL_DIR
        / "stage_1_runs"
        / filename
    )


def query_plan_id() -> str:
    return "QP-ELR-REAL-LOW-LABEL-RATE-GRADING-7D"


def event_id() -> str:
    return "ELR-REAL-LOW-LABEL-RATE-GRADING-7D"


def parse_levels(raw_levels: str) -> list[str]:
    levels = [level.strip() for level in raw_levels.split(",") if level.strip()]
    if not levels:
        raise SystemExit("--levels must include at least one level.")
    invalid = [level for level in levels if level not in label_rate_analysis.DEFAULT_LEVELS]
    if invalid:
        raise SystemExit(
            f"Unsupported levels: {invalid}. Supported: {label_rate_analysis.DEFAULT_LEVELS}."
        )
    return levels


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--levels", default=",".join(label_rate_analysis.DEFAULT_LEVELS))
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--output")
    args = parser.parse_args()

    try:
        levels = label_rate_analysis.parse_levels(args.levels)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    time_range = resolve_time_range(args)
    refresh_plus1_agreed_asset_if_needed()
    sql_map = label_rate_analysis.sql_by_level(time_range)
    mapping_index = poc_mapping_index(load_poc_mapping())
    payloads = {level: run_query(sql_map[level]) for level in levels}
    records = label_rate_analysis.build_records(
        payloads,
        levels,
        sql_map,
        row_enricher=lambda row: build_poc_row_enrichment(row, mapping_index),
        time_range=time_range,
    )
    output_path = Path(args.output) if args.output else default_output_path(time_range)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            for record in records
        )
        + "\n",
        encoding="utf-8",
    )
    sample = records[1]
    counts = sample["readonly_execution"]["level_counts"]
    print(f"Stage 1 real readonly label-rate grading wrote {counts}: {output_path}")


def resolve_time_range(args: argparse.Namespace) -> dict[str, Any] | None:
    if bool(args.start_date) != bool(args.end_date):
        raise SystemExit("--start-date and --end-date must be provided together.")
    if not args.start_date:
        return None
    try:
        return label_rate_analysis.build_grading_time_range(
            start_date=args.start_date,
            end_date=args.end_date,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def plus1_asset_paths() -> list[Path]:
    return [
        ROOT
        / "skills"
        / "analysis"
        / "assets"
        / SCENARIO_KEY
        / label_rate_analysis.PLUS1_AGREED_ASSET,
        ROOT
        / "references"
        / "scenarios"
        / SCENARIO_KEY
        / label_rate_analysis.PLUS1_AGREED_ASSET,
        ROOT
        / "skills"
        / "efficiency-label-rate-ops"
        / "assets"
        / SCENARIO_KEY
        / label_rate_analysis.PLUS1_AGREED_ASSET,
    ]


def refresh_plus1_agreed_asset_if_needed() -> None:
    asset_path = plus1_asset_paths()[0]
    today = date.today().isoformat()
    if asset_path.exists():
        current = json.loads(asset_path.read_text(encoding="utf-8"))
        source = current.get("source", {})
        if (
            source.get("read_at") == today
            and source.get("refresh_policy") == PLUS1_REFRESH_POLICY
        ):
            return

    read_range = resolve_plus1_read_range()
    payload = read_plus1_sheet_values(read_range)
    refreshed = build_plus1_asset_from_sheet(
        payload,
        read_at=today,
        read_range=read_range,
    )
    for path in plus1_asset_paths():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(refreshed, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        "Refreshed +1 agreed strategy asset "
        f"({refreshed['unique_strategy_count']} strategies) from Feishu sheet."
    )


def column_index_to_letter(column_count: int) -> str:
    """Convert a 1-based column count to its spreadsheet letter (1->A, 27->AA)."""
    if column_count < 1:
        raise ValueError(f"column_count must be >= 1, got {column_count}")
    letters = ""
    while column_count > 0:
        column_count, remainder = divmod(column_count - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def resolve_plus1_read_range() -> str:
    """Build a read range that spans every populated column and all rows.

    The end row is intentionally omitted (e.g. ``A1:M``) so newly appended
    rows are always covered without editing this file. The end column is
    derived from the sheet's live ``column_count`` so added columns are
    covered too.
    """
    command = [
        "lark-cli",
        "sheets",
        "+workbook-info",
        "--url",
        PLUS1_SHEET_URL,
        "--as",
        "user",
        "--format",
        "json",
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            "Failed to inspect +1 agreed strategy workbook:\n"
            f"stdout={completed.stdout}\n"
            f"stderr={completed.stderr}"
        )
    payload = json.loads(completed.stdout)
    if payload.get("ok") is not True:
        raise RuntimeError(f"Failed to inspect +1 agreed strategy workbook: {payload}")
    sheets = payload.get("data", {}).get("sheets") or []
    target = next(
        (sheet for sheet in sheets if sheet.get("sheet_id") == PLUS1_SHEET_ID),
        None,
    )
    if target is None:
        raise RuntimeError(
            f"+1 agreed strategy sheet not found: sheet_id={PLUS1_SHEET_ID}"
        )
    column_count = target.get("column_count")
    if not isinstance(column_count, int) or column_count < 1:
        raise RuntimeError(
            f"+1 agreed strategy sheet has invalid column_count: {column_count!r}"
        )
    end_column = column_index_to_letter(column_count)
    return f"{PLUS1_READ_START_COLUMN}1:{end_column}"


def read_plus1_sheet_values(read_range: str) -> dict[str, Any]:
    command = [
        "lark-cli",
        "sheets",
        "+cells-get",
        "--url",
        PLUS1_SHEET_URL,
        "--sheet-id",
        PLUS1_SHEET_ID,
        "--range",
        read_range,
        "--as",
        "user",
        "--include",
        "value",
        "--format",
        "json",
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Failed to refresh +1 agreed strategy sheet:\n"
            f"stdout={completed.stdout}\n"
            f"stderr={completed.stderr}"
        )
    payload = json.loads(completed.stdout)
    if payload.get("ok") is not True:
        raise RuntimeError(f"Failed to refresh +1 agreed strategy sheet: {payload}")
    return payload


def build_plus1_asset_from_sheet(
    payload: dict[str, Any],
    *,
    read_at: str,
    read_range: str,
) -> dict[str, Any]:
    ranges = payload.get("data", {}).get("ranges") or []
    if not ranges:
        raise RuntimeError("+1 agreed strategy sheet returned no ranges.")
    raw_rows = ranges[0].get("cells") or []
    rows = [[str(cell.get("value", "")).strip() for cell in row] for row in raw_rows]
    if not rows:
        raise RuntimeError("+1 agreed strategy sheet returned no rows.")
    headers = rows[0]
    header_index = {header: index for index, header in enumerate(headers) if header}
    for required in ("strategy_id", "reason", "+1评估", "更新日期"):
        if required not in header_index:
            raise RuntimeError(f"+1 agreed strategy sheet missing column: {required}")

    entries_by_id: dict[str, dict[str, Any]] = {}
    report_flow_entries_by_reason: dict[str, dict[str, Any]] = {}
    raw_agreed_count = 0
    raw_report_flow_agreed_count = 0
    skipped_agreed_without_strategy_id = 0
    skipped_agreed_without_reason = 0
    for row in rows[1:]:
        row = row + [""] * (len(headers) - len(row))
        strategy_id = row[header_index["strategy_id"]].strip()
        reason = row[header_index["reason"]].strip()
        plus1_eval = row[header_index["+1评估"]].strip()
        update_date = normalize_update_date(row[header_index["更新日期"]].strip())
        if plus1_eval != "同意":
            continue
        if not strategy_id:
            skipped_agreed_without_strategy_id += 1
        else:
            raw_agreed_count += 1
            existing = entries_by_id.get(strategy_id)
            if existing is None or update_date > existing.get("update_date", ""):
                entries_by_id[strategy_id] = {
                    "strategy_id": strategy_id,
                    "plus1_agreed": True,
                    "update_date": update_date,
                    "source_status": "current_sheet_agreed",
                }
        if not reason:
            skipped_agreed_without_reason += 1
        else:
            raw_report_flow_agreed_count += 1
            existing_reason = report_flow_entries_by_reason.get(reason)
            if (
                existing_reason is None
                or update_date > existing_reason.get("update_date", "")
            ):
                report_flow_entries_by_reason[reason] = {
                    "reason": reason,
                    "plus1_agreed": True,
                    "update_date": update_date,
                    "source_status": "current_sheet_agreed",
                }

    return {
        "schema_version": "label_rate_plus1_agreed_strategy_updates.v1",
        "scenario_key": SCENARIO_KEY,
        "source": {
            "type": "lark_sheet",
            "url": PLUS1_SHEET_URL,
            "sheet_id": PLUS1_SHEET_ID,
            "sheet_name": PLUS1_SHEET_NAME,
            "range": read_range,
            "read_at": read_at,
            "refresh_policy": PLUS1_REFRESH_POLICY,
            "filter": "+1评估 == 同意",
            "excluded_agreed_without_strategy_id": skipped_agreed_without_strategy_id,
            "excluded_agreed_without_reason": skipped_agreed_without_reason,
        },
        "raw_agreed_count": raw_agreed_count,
        "raw_report_flow_agreed_count": raw_report_flow_agreed_count,
        "unique_strategy_count": len(entries_by_id),
        "unique_report_flow_reason_count": len(report_flow_entries_by_reason),
        "entries": sorted(entries_by_id.values(), key=lambda item: item["strategy_id"]),
        "report_flow_entries": sorted(
            report_flow_entries_by_reason.values(),
            key=lambda item: item["reason"],
        ),
    }


def normalize_update_date(value: str) -> str:
    return value.replace("/", "-") if value else ""


def run_query(sql: str) -> dict[str, Any]:
    command = [
        "bytedcli",
        "-j",
        "aeolus",
        "query",
        "-r",
        REGION,
        DATASET_ID,
        sql,
        "--limit",
        QUERY_LIMIT,
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Aeolus grading query failed:\n"
            f"stdout={completed.stdout}\n"
            f"stderr={completed.stderr}"
        )
    payload = json.loads(completed.stdout)
    if payload.get("status") != "success":
        raise RuntimeError(f"Aeolus grading query returned non-success: {payload}")
    return payload



if __name__ == "__main__":
    main()
