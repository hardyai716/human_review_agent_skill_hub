#!/usr/bin/env python3
"""Self-contained smoke check for the analysis Skill (no SQL, no side effects)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
CLI_SCRIPT = SCRIPTS_DIR / "analyzing_ops_metrics.py"
sys.path.insert(0, str(SCRIPTS_DIR))

import label_rate_analysis as analysis  # noqa: E402


REQUIRED_SAMPLE_KEYS = (
    "QueryPlan",
    "source_footer",
    "readonly_execution",
    "analysis_result",
    "provenance",
)


def run_checks() -> None:
    run_library_checks()
    run_cli_checks()


def run_library_checks() -> None:
    levels = analysis.parse_levels(",".join(analysis.DEFAULT_LEVELS))
    sql_map = analysis.sql_by_level()
    payloads = analysis.build_smoke_payloads(levels)
    records = analysis.build_records(payloads, levels, sql_map)

    assert len(records) >= 2, "expected environment + sample records"
    sample = records[1]
    assert sample.get("record_type") == "sample", "records[1] must be the sample record"
    for key in REQUIRED_SAMPLE_KEYS:
        assert key in sample, f"sample record missing key: {key}"


def run_cli_checks() -> None:
    with tempfile.TemporaryDirectory(prefix="analysis-skill-selfcheck-") as tmp:
        tmp_path = Path(tmp)
        dry_run_dir = tmp_path / "lowest_reason"

        dry_run = run_cli(
            [
                "lowest-reason",
                "--days",
                "7",
                "--execute",
                "never",
                "--format",
                "json",
                "--output-dir",
                str(dry_run_dir),
            ]
        )
        assert_cli_safety(dry_run, expected_status="dry_run")
        assert_artifacts(dry_run_dir)
        dry_result = read_json(dry_run_dir / "analysis_result.json")
        assert dry_result["status"] == "dry_run", "lowest-reason must stay dry_run"
        assert dry_result["stop_reason"] == "execute_never", "dry-run stop_reason mismatch"
        assert "readonly_execution" not in dry_result, "dry-run must not include real rows"

        summary = (dry_run_dir / "analysis_summary.md").read_text(encoding="utf-8")
        assert "SQL text is stored in `query_plan.json`" in summary, (
            "summary must reference query_plan.json instead of inlining SQL"
        )
        assert "SELECT\n" not in summary, "summary must not inline SQL"

        handoff_expectations = {
            "notification": "notification",
            "resolution": "resolution",
            "perception": "perception",
        }
        for intent, next_skill in handoff_expectations.items():
            handoff_dir = tmp_path / f"handoff_{intent}"
            handoff = run_cli(
                [
                    "handoff",
                    "--intent",
                    intent,
                    "--execute",
                    "never",
                    "--format",
                    "json",
                    "--output-dir",
                    str(handoff_dir),
                ]
            )
            assert_cli_safety(handoff, expected_status="handoff")
            assert_artifacts(handoff_dir)
            handoff_result = read_json(handoff_dir / "analysis_result.json")
            assert handoff_result["status"] == "handoff", "handoff status mismatch"
            assert handoff_result["handoff"]["next_skill"] == next_skill, (
                f"{intent} handoff must route to {next_skill} Skill"
            )
            assert handoff_result["handoff"]["blocked_actions"], (
                "handoff must declare blocked downstream actions"
            )

        composite_dir = tmp_path / "composite_handoff"
        handoff = run_cli(
            [
                "lowest-reason",
                "--days",
                "7",
                "--execute",
                "never",
                "--format",
                "json",
                "--output-dir",
                str(composite_dir),
                "--prompt",
                "请分析近 7 天低打标率最低 reason，并基于结果生成飞书卡片通知 POC。",
            ]
        )
        assert_cli_safety(handoff, expected_status="dry_run")
        assert_artifacts(composite_dir)
        composite_result = read_json(composite_dir / "analysis_result.json")
        assert "handoff" in composite_result, "composite request must attach handoff"
        assert composite_result["handoff"]["next_skill"] == "notification_or_resolution", (
            "composite handoff must stop at downstream notification/resolution"
        )


def run_cli(args: list[str]) -> dict[str, object]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, str(CLI_SCRIPT), *args],
        cwd=SKILL_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "CLI command failed with exit "
            f"{completed.returncode}: stdout={completed.stdout} stderr={completed.stderr}"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError(f"CLI stdout must be JSON: {completed.stdout}") from error


def assert_cli_safety(payload: dict[str, object], *, expected_status: str) -> None:
    assert payload.get("status") == expected_status, (
        f"expected CLI status {expected_status}, got {payload.get('status')}"
    )
    safety = payload.get("safety")
    assert isinstance(safety, dict), "CLI output missing safety object"
    expected = {
        "sql_executed": False,
        "notification_sent": False,
        "online_write_executed": False,
    }
    for key, value in expected.items():
        assert safety.get(key) is value, f"CLI safety {key} must be {value}"


def assert_artifacts(output_dir: Path) -> None:
    for filename in (
        "query_plan.json",
        "source_footer.json",
        "analysis_result.json",
        "analysis_summary.md",
    ):
        path = output_dir / filename
        assert path.exists(), f"missing CLI artifact: {filename}"
    result = read_json(output_dir / "analysis_result.json")
    safety = result.get("safety")
    assert isinstance(safety, dict), "analysis_result missing safety"
    assert safety.get("sql_executed") is False, "selfcheck must not execute SQL"
    assert safety.get("notification_sent") is False, "selfcheck must not send notifications"
    assert safety.get("online_write_executed") is False, "selfcheck must not write online state"


def read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"{path.name} must contain a JSON object"
    return payload


def main() -> None:
    try:
        run_checks()
    except Exception as error:  # noqa: BLE001
        print(f"analysis selfcheck FAILED: {error}")
        raise SystemExit(1)
    print("analysis selfcheck OK")


if __name__ == "__main__":
    main()
