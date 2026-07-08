#!/usr/bin/env python3
"""Validate minimal Skill package structure."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILLS = ["perception", "analysis", "notification", "resolution"]


def main() -> None:
    missing: list[str] = []
    for skill in SKILLS:
        base = ROOT / "skills" / skill
        required = [
            base / "SKILL.md",
            base / "references" / "common.md",
            base / "references" / "scenario-index.md",
            base / "references" / "scenarios",
        ]
        missing.extend(str(path.relative_to(ROOT)) for path in required if not path.exists())

    if missing:
        raise SystemExit("Missing Skill files:\n" + "\n".join(missing))
    print("Skill packages OK")


if __name__ == "__main__":
    main()
