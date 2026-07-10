#!/usr/bin/env python3
"""Generate and optionally send a stage 2 label-rate grading card draft."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
NOTIFICATION_SCRIPTS = ROOT / "skills" / "notification" / "scripts"
sys.path.insert(0, str(NOTIFICATION_SCRIPTS))

from label_rate_notification_artifacts import (  # noqa: E402
    REPORT_TYPE,
    build_label_rate_notification_artifacts,
    relative_to_root,
)


SCENARIO_KEY = "efficiency-label-rate"
OUTPUT_DATE = "20260709"
DEFAULT_SOURCE = (
    ROOT
    / "evals"
    / SCENARIO_KEY
    / "stage_1_runs"
    / "20260709_real_readonly_label_rate_grading_four_dim_results.jsonl"
)
DEFAULT_OUTPUT_DIR = (
    ROOT
    / "evals"
    / SCENARIO_KEY
    / "stage_2_runs"
    / f"{OUTPUT_DATE}_low_label_rate_grading_notification_draft"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--sheet-url")
    parser.add_argument("--import-workbook", action="store_true")
    parser.add_argument("--send-user-id")
    parser.add_argument("--send-chat-id")
    parser.add_argument("--identity", choices=["bot", "user"], default="bot")
    parser.add_argument("--title", default="近7天低效打标策略全等级结果")
    args = parser.parse_args()

    if args.top_n <= 0:
        raise SystemExit("--top-n must be a positive integer.")
    if args.send_user_id and args.send_chat_id:
        raise SystemExit("--send-user-id and --send-chat-id cannot be used together.")

    source_path = Path(args.source)
    output_dir = Path(args.output_dir)
    self_send_requested = args.send_user_id is not None or args.send_chat_id is not None
    sheet_url = args.sheet_url

    artifacts = build_artifacts(
        args=args,
        source_path=source_path,
        output_dir=output_dir,
        sheet_url=sheet_url,
        self_send_requested=self_send_requested,
        sent_payload=None,
    )
    sheet_url = artifacts.summary.get("sheet_url") or sheet_url

    sent_payload = send_preview_if_requested(args, artifacts.card.card_path)
    if sent_payload is not None:
        artifacts = build_artifacts(
            args=args,
            source_path=source_path,
            output_dir=output_dir,
            sheet_url=sheet_url,
            self_send_requested=self_send_requested,
            sent_payload=sent_payload,
        )

    print(
        "Stage 2 label-rate notification draft wrote "
        f"{relative_to_root(artifacts.output_dir)}; "
        f"sent={artifacts.publish_summary['sent']}; "
        f"message_id={artifacts.publish_summary['message_id']}"
    )


def build_artifacts(
    *,
    args: argparse.Namespace,
    source_path: Path,
    output_dir: Path,
    sheet_url: str | None,
    self_send_requested: bool,
    sent_payload: dict[str, Any] | None,
) -> Any:
    return build_label_rate_notification_artifacts(
        source_path=source_path,
        output_dir=output_dir,
        top_n=args.top_n,
        sheet_url=sheet_url,
        identity=args.identity,
        title=args.title,
        self_send_requested=self_send_requested,
        sent_payload=sent_payload,
        target_user_id=args.send_user_id,
        target_chat_id=args.send_chat_id,
        auto_import_sheet=args.import_workbook,
    )


def send_preview_if_requested(
    args: argparse.Namespace,
    card_path: Path,
) -> dict[str, Any] | None:
    if args.send_user_id:
        return send_card(
            card_path=card_path,
            user_id=args.send_user_id,
            chat_id=None,
            identity=args.identity,
            idempotency_key=safe_idempotency_key(
                f"{REPORT_TYPE}-{OUTPUT_DATE}-{Path(args.output_dir).name}-{args.send_user_id}"
            ),
        )
    if args.send_chat_id:
        return send_card(
            card_path=card_path,
            user_id=None,
            chat_id=args.send_chat_id,
            identity=args.identity,
            idempotency_key=safe_idempotency_key(
                f"{REPORT_TYPE}-{OUTPUT_DATE}-{Path(args.output_dir).name}-{args.send_chat_id}"
            ),
        )
    return None


def import_workbook(workbook_path: Path, name: str) -> str:
    payload = run_lark_cli(
        [
            "lark-cli",
            "sheets",
            "+workbook-import",
            "--json",
            "--as",
            "user",
            "--file",
            relative_to_cwd(workbook_path),
            "--name",
            name,
        ]
    )
    data = payload.get("data", {})
    url = data.get("url")
    if not url:
        raise RuntimeError(f"workbook import did not return url: {payload}")
    return str(url)


def send_card(
    *,
    card_path: Path,
    user_id: str | None,
    chat_id: str | None,
    identity: str,
    idempotency_key: str,
) -> dict[str, Any]:
    if bool(user_id) == bool(chat_id):
        raise ValueError("Exactly one of user_id or chat_id is required.")
    target_args = ["--user-id", user_id] if user_id else ["--chat-id", str(chat_id)]
    return run_lark_cli(
        [
            "lark-cli",
            "im",
            "+messages-send",
            "--json",
            "--as",
            identity,
            *target_args,
            "--msg-type",
            "interactive",
            "--content",
            card_path.read_text(encoding="utf-8"),
            "--idempotency-key",
            idempotency_key,
        ]
    )


def run_lark_cli(args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT.parent,
        env={
            **os.environ,
            "LARKSUITE_CLI_NO_UPDATE_NOTIFIER": "1",
            "LARKSUITE_CLI_NO_SKILLS_NOTIFIER": "1",
        },
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "lark-cli command failed:\n"
            f"args={args}\nstdout={completed.stdout}\nstderr={completed.stderr}"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"lark-cli returned non-json output: {completed.stdout}") from exc


def relative_to_cwd(path: Path) -> str:
    resolved = path.resolve()
    cwd = ROOT.parent.resolve()
    try:
        return str(resolved.relative_to(cwd))
    except ValueError:
        return str(path)


def safe_idempotency_key(raw: str) -> str:
    key = re.sub(r"[^A-Za-z0-9-]+", "-", raw).strip("-")
    key = re.sub(r"-{2,}", "-", key)
    return key[-50:] or "label-rate-card"


if __name__ == "__main__":
    main()
