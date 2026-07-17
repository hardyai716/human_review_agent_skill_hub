#!/usr/bin/env python3
"""Run real readonly low-label-rate grading for stage 1.

This runner is intentionally scenario-specific. It executes the current
efficiency-label-rate grading rules for notice/P2/P1/P0 and keeps all actions
readonly.
"""

from __future__ import annotations

import argparse
import json
import os
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
PLUS1_SHEET_TOKEN_ENV = "HUMAN_REVIEW_OPS_PLUS1_SHEET_TOKEN"
PLUS1_SHEET_ID = "0301e2"
PLUS1_SHEET_NAME = "Sheet1"
PLUS1_READ_RANGE = "A1:N1000"
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

    payload = read_plus1_sheet_values()
    refreshed = build_plus1_asset_from_sheet(payload, read_at=today)
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


def read_plus1_sheet_values() -> dict[str, Any]:
    sheet_token = os.environ.get(PLUS1_SHEET_TOKEN_ENV, "").strip()
    if not sheet_token:
        raise RuntimeError(
            f"Missing required environment variable: {PLUS1_SHEET_TOKEN_ENV}"
        )
    command = [
        "lark-cli",
        "sheets",
        "+cells-get",
        "--spreadsheet-token",
        sheet_token,
        "--sheet-id",
        PLUS1_SHEET_ID,
        "--range",
        PLUS1_READ_RANGE,
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


def build_plus1_asset_from_sheet(payload: dict[str, Any], *, read_at: str) -> dict[str, Any]:
    ranges = payload.get("data", {}).get("ranges") or []
    if not ranges:
        raise RuntimeError("+1 agreed strategy sheet returned no ranges.")
    raw_rows = ranges[0].get("cells") or []
    rows = [[str(cell.get("value", "")).strip() for cell in row] for row in raw_rows]
    if not rows:
        raise RuntimeError("+1 agreed strategy sheet returned no rows.")
    headers = rows[0]
    header_index = {header: index for index, header in enumerate(headers) if header}
    for required in ("strategy_id", "+1评估", "更新日期"):
        if required not in header_index:
            raise RuntimeError(f"+1 agreed strategy sheet missing column: {required}")

    entries_by_id: dict[str, dict[str, Any]] = {}
    raw_agreed_count = 0
    for row in rows[1:]:
        row = row + [""] * (len(headers) - len(row))
        strategy_id = row[header_index["strategy_id"]].strip()
        plus1_eval = row[header_index["+1评估"]].strip()
        update_date = normalize_update_date(row[header_index["更新日期"]].strip())
        if not strategy_id or plus1_eval != "同意":
            continue
        raw_agreed_count += 1
        existing = entries_by_id.get(strategy_id)
        if existing is None or update_date > existing.get("update_date", ""):
            entries_by_id[strategy_id] = {
                "strategy_id": strategy_id,
                "plus1_agreed": True,
                "update_date": update_date,
                "source_status": "current_sheet_agreed",
            }

    return {
        "schema_version": "label_rate_plus1_agreed_strategy_updates.v1",
        "scenario_key": SCENARIO_KEY,
        "source": {
            "type": "lark_sheet",
            "spreadsheet_token_env": PLUS1_SHEET_TOKEN_ENV,
            "sheet_id": PLUS1_SHEET_ID,
            "sheet_name": PLUS1_SHEET_NAME,
            "range": PLUS1_READ_RANGE,
            "read_at": read_at,
            "refresh_policy": PLUS1_REFRESH_POLICY,
            "filter": "+1评估 == 同意",
        },
        "raw_agreed_count": raw_agreed_count,
        "unique_strategy_count": len(entries_by_id),
        "entries": sorted(entries_by_id.values(), key=lambda item: item["strategy_id"]),
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
