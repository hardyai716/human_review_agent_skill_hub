#!/usr/bin/env python3
"""Validate the reusable weekly filtered-summary comparison runner."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT.parent
RUNNER = (
    ROOT
    / "tools"
    / "runners"
    / "run_label_rate_weekly_summary_comparison.py"
)
SUMMARY_FILENAME = "汇总统计_剔除+1同意.csv"


def main() -> None:
    with tempfile.TemporaryDirectory(
        prefix="label-rate-weekly-comparison-runner-"
    ) as tmp:
        tmp_path = Path(tmp)
        previous_path = tmp_path / "previous" / SUMMARY_FILENAME
        current_path = tmp_path / "current" / SUMMARY_FILENAME
        output_dir = tmp_path / "output"
        write_summary(
            previous_path,
            [
                "国家安全,杜衡,2,100,100,5,0.05",
                "偏激社会情绪和涉外言论,张发奇,1,30,30,3,0.10",
            ],
        )
        write_summary(
            current_path,
            [
                "国家安全,杜衡,1,120,120,12,0.10",
                "领导人,宋诗慧,1,80,80,4,0.05",
            ],
        )
        completed = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--previous-start-date",
                "2026-07-06",
                "--previous-end-date",
                "2026-07-12",
                "--current-start-date",
                "2026-07-13",
                "--current-end-date",
                "2026-07-19",
                "--previous-summary",
                str(previous_path),
                "--current-summary",
                str(current_path),
                "--output-dir",
                str(output_dir),
                "--run-id",
                "smoke",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                "weekly comparison runner failed:\n"
                f"stdout={completed.stdout}\nstderr={completed.stderr}"
            )
        payload = json.loads(completed.stdout)
        if payload.get("source_mode") != "existing_summary_csv":
            raise AssertionError("runner must skip queries for supplied summaries.")
        if payload.get("sheet_url") is not None:
            raise AssertionError("runner must not import a Sheet without opt-in.")
        if payload.get("dispatch") is not None:
            raise AssertionError("runner must not send without explicit target.")
        run_summary = json.loads(
            (output_dir / "weekly_summary_comparison_run.json").read_text(
                encoding="utf-8"
            )
        )
        if run_summary.get("totals", {}).get("current_avg_review_done_cnt") != 200:
            raise AssertionError("runner current total done volume mismatch.")

        workbook_path = Path(payload["comparison_workbook"])
        workbook = load_workbook(workbook_path, data_only=False)
        try:
            sheet = workbook["汇总统计_剔除+1同意对比"]
            if sheet["A1"].value != "机审一级标签":
                raise AssertionError("runner did not create grouped comparison header.")
            if sheet["G3"].value != 20:
                raise AssertionError("runner comparison delta mismatch.")
        finally:
            workbook.close()
    print("Label-rate weekly summary comparison runner OK.")


def write_summary(path: Path, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "机审一级标签,POC,低效策略数,低效策略日均进审量,"
        "低效策略日均完审量,低效策略日均打标量,低效策略打标率\n"
    )
    path.write_text(
        "\ufeff" + header + "\n".join(rows) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
