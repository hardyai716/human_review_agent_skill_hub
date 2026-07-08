#!/usr/bin/env python3
"""Build debug snapshots for Skill references from scenario packages."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

SKILL_FILE_MAP = {
    "perception": {
        "scenario_manifest.md": "manifest.md",
        "metric_contract.md": "metric_contract.md",
        "dataset_reference.md": "dataset_reference.md",
        "examples.md": "examples.md",
    },
    "analysis": {
        "metric_contract.md": "metric_contract.md",
        "dataset_reference.md": "dataset_reference.md",
        "analysis.md": "analysis.md",
        "examples.md": "examples.md",
    },
    "notification": {
        "owner_routing.md": "owner_routing.md",
        "notification_templates.md": "notification_templates.md",
        "sla.md": "sla.md",
    },
    "resolution": {
        "state_machine.md": "state_machine.md",
        "sla.md": "sla.md",
        "owner_routing.md": "owner_routing.md",
        "examples.md": "examples.md",
    },
}


def build_snapshots(scenario_key: str, dry_run: bool) -> None:
    scenario_dir = ROOT / "references" / "scenarios" / scenario_key
    if not scenario_dir.exists():
        raise FileNotFoundError(f"Scenario package not found: {scenario_dir}")

    for skill, file_map in SKILL_FILE_MAP.items():
        target_dir = ROOT / "skills" / skill / "references" / "scenarios"
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)

        for source_name, target_suffix in file_map.items():
            source = scenario_dir / source_name
            target = target_dir / f"{scenario_key}.{target_suffix}"
            if not source.exists():
                raise FileNotFoundError(f"Missing source file: {source}")
            print(f"{source.relative_to(ROOT)} -> {target.relative_to(ROOT)}")
            if not dry_run:
                shutil.copyfile(source, target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_key")
    parser.add_argument("--write", action="store_true", help="Write files instead of dry-run.")
    args = parser.parse_args()
    build_snapshots(args.scenario_key, dry_run=not args.write)


if __name__ == "__main__":
    main()
