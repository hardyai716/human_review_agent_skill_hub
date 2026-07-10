#!/usr/bin/env python3
"""Self-contained smoke check for the perception Skill (dry-run, no side effects)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

PERCEPTION_SCRIPT = SCRIPTS_DIR / "label_rate_perception.py"
SAMPLE_REQUEST = "帮我看近 7 天低打标率 reason，按 P0/P1/P2/notice 分级。"
REQUIRED_KEYS = ("scenario_key", "task_type", "readiness")


def run_checks() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(PERCEPTION_SCRIPT),
            "--dry-run",
            "--request",
            SAMPLE_REQUEST,
        ],
        cwd=str(SKILL_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"perception dry-run exited {result.returncode}: {result.stderr.strip()}"
    )
    payload = json.loads(result.stdout)
    for key in REQUIRED_KEYS:
        assert key in payload, f"perception payload missing key: {key}"


def main() -> None:
    try:
        run_checks()
    except Exception as error:  # noqa: BLE001
        print(f"perception selfcheck FAILED: {error}")
        raise SystemExit(1)
    print("perception selfcheck OK")


if __name__ == "__main__":
    main()
