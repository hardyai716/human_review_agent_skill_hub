#!/usr/bin/env python3
"""Validate required fields in a QueryPlan JSON file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_FIELDS = [
    "metric_id",
    "time_range",
    "dimensions",
    "filters",
    "allowed_sources",
    "forbidden_sources",
    "quality_checks",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query_plan_json")
    args = parser.parse_args()

    payload = json.loads(Path(args.query_plan_json).read_text(encoding="utf-8"))
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise SystemExit(f"Missing QueryPlan fields: {', '.join(missing)}")
    print("QueryPlan OK")


if __name__ == "__main__":
    main()
