#!/usr/bin/env python3
"""Validate required fields in a source_footer JSON file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_FIELDS = [
    "source_tier",
    "metric_definition_version",
    "data_freshness",
    "owner",
    "confidence_tier",
    "review_status",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_footer_json")
    args = parser.parse_args()

    payload = json.loads(Path(args.source_footer_json).read_text(encoding="utf-8"))
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise SystemExit(f"Missing source_footer fields: {', '.join(missing)}")
    print("source_footer OK")


if __name__ == "__main__":
    main()
