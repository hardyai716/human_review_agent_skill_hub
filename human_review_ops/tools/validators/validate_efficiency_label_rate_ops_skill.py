#!/usr/bin/env python3
"""Validate the efficiency-label-rate scenario Skill bundle."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


HUMAN_REVIEW_OPS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = HUMAN_REVIEW_OPS_ROOT.parent


COMMANDS = [
    [
        sys.executable,
        "human_review_ops/tools/validators/validate_skill_path_registry.py",
    ],
    [
        sys.executable,
        "human_review_ops/tools/validators/validate_skill_productization.py",
        "--strict",
        "--profile",
        "scenario_label_rate",
    ],
    [
        sys.executable,
        "human_review_ops/tools/validators/validate_skill_standalone_smoke.py",
        "--profile",
        "scenario_label_rate",
    ],
    [
        sys.executable,
        "human_review_ops/tools/packagers/build_skill_package.py",
        "efficiency-label-rate",
        "--target",
        "scenario-bundle",
        "--check-sync",
    ],
]


def main() -> None:
    for command in COMMANDS:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            output = "\n".join(
                part.strip()
                for part in (completed.stdout, completed.stderr)
                if part.strip()
            )
            raise SystemExit(
                "Efficiency-label-rate scenario Skill validation failed:\n"
                f"command={' '.join(command)}\n{output}"
            )
    print("Efficiency-label-rate scenario Skill OK")


if __name__ == "__main__":
    main()
