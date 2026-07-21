#!/usr/bin/env python3
"""Run two label-rate periods and publish their filtered-summary comparison."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT.parent
SCENARIO_KEY = "efficiency-label-rate"
FORMAL_FLOW_RUNNER = (
    ROOT / "tools" / "runners" / "run_label_rate_formal_flow.py"
)
NOTIFICATION_SCRIPTS = (
    ROOT / "skills" / "notification" / "scripts"
)
sys.path.insert(0, str(NOTIFICATION_SCRIPTS))

from label_rate_weekly_summary_comparison import (  # noqa: E402
    WeeklyComparisonArtifacts,
    build_weekly_summary_comparison,
)


FILTERED_SUMMARY_FILENAME = "汇总统计_剔除+1同意.csv"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Execute two explicit low-label-rate grading windows, compare their "
            "汇总统计_剔除+1同意 reports, and optionally import/send the comparison."
        )
    )
    parser.add_argument("--previous-start-date", required=True)
    parser.add_argument("--previous-end-date", required=True)
    parser.add_argument("--current-start-date", required=True)
    parser.add_argument("--current-end-date", required=True)
    parser.add_argument(
        "--previous-summary",
        help=(
            "Existing previous 汇总统计_剔除+1同意.csv. When both summary paths "
            "are supplied, skip real queries and only build the comparison."
        ),
    )
    parser.add_argument(
        "--current-summary",
        help=(
            "Existing current 汇总统计_剔除+1同意.csv. Must be supplied together "
            "with --previous-summary."
        ),
    )
    parser.add_argument("--run-id", default=datetime.now().strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--output-dir")
    parser.add_argument("--previous-label")
    parser.add_argument("--current-label")
    parser.add_argument(
        "--import-sheet",
        action="store_true",
        help="Explicitly import the comparison XLSX as a Feishu Sheet.",
    )
    parser.add_argument("--sheet-name")
    parser.add_argument("--send-chat-id")
    parser.add_argument("--send-user-id")
    parser.add_argument("--send-identity", choices=["bot", "user"], default="bot")
    parser.add_argument(
        "--confirm-send",
        action="store_true",
        help="Required with --send-chat-id or --send-user-id.",
    )
    parser.add_argument("--idempotency-key")
    args = parser.parse_args()

    validate_args(args)
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else ROOT
        / "evals"
        / SCENARIO_KEY
        / "stage_2_runs"
        / f"{args.run_id}_weekly_summary_comparison"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    source_mode = "existing_summary_csv"
    formal_runs: dict[str, dict[str, Any]] = {}
    if args.previous_summary and args.current_summary:
        previous_summary_path = Path(args.previous_summary)
        current_summary_path = Path(args.current_summary)
    else:
        source_mode = "real_readonly_full_level_grading"
        previous_run = run_formal_flow(
            run_id=f"{args.run_id}_previous",
            output_dir=output_dir / "previous_week",
            start_date=args.previous_start_date,
            end_date=args.previous_end_date,
            comparison_period=(
                f"{args.current_start_date}~{args.current_end_date}"
            ),
        )
        current_run = run_formal_flow(
            run_id=f"{args.run_id}_current",
            output_dir=output_dir / "current_week",
            start_date=args.current_start_date,
            end_date=args.current_end_date,
            comparison_period=(
                f"{args.previous_start_date}~{args.previous_end_date}"
            ),
        )
        formal_runs = {"previous": previous_run, "current": current_run}
        previous_summary_path = stage_filtered_summary_path(previous_run)
        current_summary_path = stage_filtered_summary_path(current_run)

    artifacts = build_weekly_summary_comparison(
        previous_summary_path=previous_summary_path,
        current_summary_path=current_summary_path,
        previous_start_date=args.previous_start_date,
        previous_end_date=args.previous_end_date,
        current_start_date=args.current_start_date,
        current_end_date=args.current_end_date,
        output_dir=output_dir,
        previous_label=args.previous_label,
        current_label=args.current_label,
        auto_import_sheet=args.import_sheet,
        sheet_name=args.sheet_name,
    )

    dispatch_record: dict[str, Any] | None = None
    if args.send_chat_id or args.send_user_id:
        dispatch_record = dispatch_comparison(
            args=args,
            output_dir=output_dir,
            artifacts=artifacts,
        )

    result = {
        "schema_version": "label_rate_weekly_summary_comparison_run.v1",
        "run_id": args.run_id,
        "source_mode": source_mode,
        "periods": {
            "previous": {
                "start": args.previous_start_date,
                "end": args.previous_end_date,
                "summary_csv": str(previous_summary_path),
            },
            "current": {
                "start": args.current_start_date,
                "end": args.current_end_date,
                "summary_csv": str(current_summary_path),
            },
        },
        "formal_runs": formal_runs,
        "comparison_summary": str(artifacts.summary_path),
        "comparison_workbook": str(artifacts.workbook_path),
        "sheet_url": artifacts.sheet_url,
        "totals": artifacts.totals,
        "online_write_attempted": artifacts.online_write_attempted,
        "online_write_executed": artifacts.online_write_executed,
        "dispatch": dispatch_record,
    }
    write_json(output_dir / "weekly_summary_comparison_run.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def validate_args(args: argparse.Namespace) -> None:
    if bool(args.previous_summary) != bool(args.current_summary):
        raise SystemExit(
            "--previous-summary and --current-summary must be supplied together."
        )
    if args.send_chat_id and args.send_user_id:
        raise SystemExit("--send-chat-id and --send-user-id are mutually exclusive.")
    if (args.send_chat_id or args.send_user_id) and not args.confirm_send:
        raise SystemExit(
            "--confirm-send is required before sending a real Feishu message."
        )
    if (args.send_chat_id or args.send_user_id) and not args.import_sheet:
        raise SystemExit(
            "sending requires --import-sheet so the message can carry a verified "
            "Feishu Sheet link."
        )


def run_formal_flow(
    *,
    run_id: str,
    output_dir: Path,
    start_date: str,
    end_date: str,
    comparison_period: str,
) -> dict[str, Any]:
    request = (
        f"执行 {start_date} 至 {end_date} 周期内低效打标全等级结果，"
        "按 notice/P2/P1/P0 分级，生成用于与 "
        f"{comparison_period} 对比的飞书表格汇总统计_剔除+1同意。"
    )
    command = [
        sys.executable,
        str(FORMAL_FLOW_RUNNER),
        "--request",
        request,
        "--start-date",
        start_date,
        "--end-date",
        end_date,
        "--levels",
        "notice,P2,P1,P0",
        "--run-id",
        run_id,
        "--output-dir",
        str(output_dir),
        "--no-import-workbook",
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "formal flow failed:\n"
            f"command={command}\nstdout={completed.stdout}\nstderr={completed.stderr}"
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"formal flow returned non-JSON output: {completed.stdout}"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"formal flow returned invalid payload: {payload!r}")
    return payload


def stage_filtered_summary_path(formal_run: dict[str, Any]) -> Path:
    output_dir = formal_run.get("stage2_output_dir")
    if not isinstance(output_dir, str) or not output_dir:
        raise RuntimeError("formal flow summary is missing stage2_output_dir.")
    path = Path(output_dir) / FILTERED_SUMMARY_FILENAME
    if not path.exists():
        raise RuntimeError(f"formal flow did not create {path}.")
    return path


def dispatch_comparison(
    *,
    args: argparse.Namespace,
    output_dir: Path,
    artifacts: WeeklyComparisonArtifacts,
) -> dict[str, Any]:
    if not artifacts.sheet_url:
        raise RuntimeError(
            "comparison sheet import did not return a sheet_url; refusing to send."
        )
    target_args = (
        ["--chat-id", args.send_chat_id]
        if args.send_chat_id
        else ["--user-id", args.send_user_id]
    )
    target_type = "chat" if args.send_chat_id else "user"
    target_id = args.send_chat_id or args.send_user_id
    markdown = comparison_markdown(artifacts)
    idempotency_key = args.idempotency_key or safe_idempotency_key(
        f"label-rate-comparison-{args.run_id}-{target_id}"
    )
    common_command = [
        "lark-cli",
        "im",
        "+messages-send",
        "--as",
        args.send_identity,
        *target_args,
        "--markdown",
        markdown,
        "--idempotency-key",
        idempotency_key,
    ]
    dry_run = run_lark_cli(
        [*common_command, "--dry-run"],
        expect_json=False,
    )
    (output_dir / "comparison_send_dry_run.txt").write_text(
        dry_run,
        encoding="utf-8",
    )
    sent_payload = run_lark_cli(["lark-cli", "im", "+messages-send", "--json", *common_command[3:]])
    if not sent_payload.get("ok"):
        raise RuntimeError(f"comparison message send failed: {sent_payload}")
    data = sent_payload.get("data", {})
    record = {
        "schema_version": "label_rate_weekly_comparison_dispatch.v1",
        "confirmed_by_user": True,
        "target_type": target_type,
        "target_id": target_id,
        "identity": args.send_identity,
        "idempotency_key": idempotency_key,
        "sheet_url": artifacts.sheet_url,
        "pre_send_checks": [
            {
                "check_id": "confirm_send",
                "status": "pass",
                "message": "--confirm-send supplied",
            },
            {
                "check_id": "sheet_url_present",
                "status": "pass",
                "message": "comparison message includes a Feishu Sheet URL",
            },
        ],
        "dry_run_request_captured": True,
        "send_result": sent_payload,
        "message_id": data.get("message_id"),
        "chat_id": data.get("chat_id"),
        "create_time": data.get("create_time"),
    }
    write_json(output_dir / "comparison_dispatch_record.json", record)
    return record


def comparison_markdown(artifacts: WeeklyComparisonArtifacts) -> str:
    totals = artifacts.totals
    previous_count = totals["previous_strategy_count"]
    current_count = totals["current_strategy_count"]
    previous_done = totals["previous_avg_review_done_cnt"]
    current_done = totals["current_avg_review_done_cnt"]
    done_delta = totals["avg_review_done_delta"]
    growth = totals["avg_review_done_growth_rate"]
    previous_rate = totals["previous_label_rate"]
    current_rate = totals["current_label_rate"]
    return "\n".join(
        [
            "## 低效打标「汇总统计_剔除+1同意」周环比",
            "",
            f"- 低效策略数：{previous_count:,} → {current_count:,}"
            f"（{current_count - previous_count:+,}）",
            f"- 日均完审量：{previous_done:,} → {current_done:,}"
            f"（{done_delta:+,}，{percent_or_slash(growth)}）",
            f"- 加权打标率：{percent_or_slash(previous_rate)} → "
            f"{percent_or_slash(current_rate)}",
            "",
            f"[打开飞书对比表]({artifacts.sheet_url})",
        ]
    )


def percent_or_slash(value: float | None) -> str:
    return "/" if value is None else f"{value * 100:.1f}%"


def run_lark_cli(
    command: list[str],
    *,
    expect_json: bool = True,
) -> dict[str, Any] | str:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "LARKSUITE_CLI_NO_UPDATE_NOTIFIER": "1",
            "LARKSUITE_CLI_NO_SKILLS_NOTIFIER": "1",
        },
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "lark-cli command failed:\n"
            f"command={command}\nstdout={completed.stdout}\nstderr={completed.stderr}"
        )
    if not expect_json:
        return completed.stdout
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"lark-cli returned non-JSON output: {completed.stdout}"
        ) from exc


def safe_idempotency_key(raw: str) -> str:
    key = re.sub(r"[^A-Za-z0-9]+", "", raw)
    return key[-48:] or "labelratecomparison"


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
