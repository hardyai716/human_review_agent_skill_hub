#!/usr/bin/env python3
"""Reusable Feishu Sheet import helpers for notification artifacts."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]


def import_xlsx_as_feishu_sheet(
    *,
    workbook_path: Path,
    output_dir: Path,
    sheet_name: str,
    result_filename: str = "sheet_import_result.json",
) -> str | None:
    """Import an XLSX report as a Feishu Sheet; failures are non-blocking."""

    import_result_path = output_dir / result_filename
    command = [
        "lark-cli",
        "sheets",
        "+workbook-import",
        "--json",
        "--as",
        "user",
        "--file",
        workbook_path.name,
        "--name",
        sheet_name,
    ]
    try:
        payload = run_lark_cli(command, cwd=workbook_path.parent)
    except Exception as error:  # noqa: BLE001 - import failure must degrade.
        write_json(
            import_result_path,
            {
                "status": "failed",
                "error": str(error),
                "command": command_without_local_path(command),
            },
        )
        return None

    url = payload.get("data", {}).get("url")
    if not url:
        write_json(
            import_result_path,
            {
                "status": "failed",
                "error": "workbook import did not return url",
                "payload": payload,
                "command": command_without_local_path(command),
            },
        )
        return None

    write_json(
        import_result_path,
        {
            "status": "success",
            "sheet_url": str(url),
            "payload": payload,
            "command": command_without_local_path(command),
        },
    )
    return str(url)


def run_lark_cli(command: list[str], *, cwd: Path | None = None) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        cwd=cwd or ROOT.parent,
        env={
            **os.environ,
            "LARKSUITE_CLI_NO_UPDATE_NOTIFIER": "1",
            "LARKSUITE_CLI_NO_SKILLS_NOTIFIER": "1",
        },
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "lark-cli command failed:\n"
            f"args={command_without_local_path(command)}\n"
            f"stdout={completed.stdout}\n"
            f"stderr={completed.stderr}"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"lark-cli returned non-json output: {completed.stdout}"
        ) from exc


def command_without_local_path(command: list[str]) -> list[str]:
    redacted = list(command)
    if "--file" in redacted:
        index = redacted.index("--file")
        if index + 1 < len(redacted):
            redacted[index + 1] = "<workbook.xlsx>"
    return redacted


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
