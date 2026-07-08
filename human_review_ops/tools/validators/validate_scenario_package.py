#!/usr/bin/env python3
"""Validate required files in a scenario package."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIRED_FILES = [
    "scenario_manifest.md",
    "state_machine.md",
    "sla.md",
    "metric_contract.md",
    "dataset_reference.md",
    "owner_routing.md",
    "notification_templates.md",
    "analysis.md",
    "examples.md",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_key")
    args = parser.parse_args()

    scenario_dir = ROOT / "references" / "scenarios" / args.scenario_key
    missing = [name for name in REQUIRED_FILES if not (scenario_dir / name).exists()]
    if missing:
        raise SystemExit(f"Missing scenario files: {', '.join(missing)}")
    print(f"Scenario package OK: {scenario_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
