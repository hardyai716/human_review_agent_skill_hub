#!/usr/bin/env python3
"""Validate stage 2 label-rate notification draft artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
NOTIFICATION_SCRIPTS = ROOT / "skills" / "notification" / "scripts"
sys.path.insert(0, str(NOTIFICATION_SCRIPTS))

from card_hash import strip_internal_keys, verify_card_hash  # noqa: E402
from render_label_rate_grading_card import card_design_check  # noqa: E402


DEFAULT_OUTPUT_DIR = (
    ROOT
    / "evals"
    / "efficiency-label-rate"
    / "stage_2_runs"
    / "20260709_low_label_rate_grading_notification_draft"
)
REQUIRED_FILES = [
    "summary.json",
    "notice.csv",
    "P2.csv",
    "P1.csv",
    "P0.csv",
    "综合.csv",
    "publish/low_efficiency_grading.card.json",
    "publish/low_efficiency_grading.card.with_meta.json",
    "publish/low_efficiency_grading.publish_summary.json",
    "publish/card_hash_check.json",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def validate(output_dir: Path, *, expect_sent: bool) -> None:
    for relative in REQUIRED_FILES:
        if not (output_dir / relative).exists():
            raise AssertionError(f"Missing artifact: {relative}")

    summary = load_json(output_dir / "summary.json")
    card = load_json(output_dir / "publish" / "low_efficiency_grading.card.json")
    card_with_meta = load_json(
        output_dir / "publish" / "low_efficiency_grading.card.with_meta.json"
    )
    publish_summary = load_json(
        output_dir / "publish" / "low_efficiency_grading.publish_summary.json"
    )
    hash_check = load_json(output_dir / "publish" / "card_hash_check.json")

    assert_summary(summary)
    assert_csvs(output_dir, summary)
    assert_card(card, card_with_meta, hash_check)
    assert_publish_summary(publish_summary, summary, expect_sent=expect_sent)


def assert_summary(summary: dict[str, Any]) -> None:
    if summary.get("schema_version") != "stage_2_notification_draft.v1":
        raise AssertionError("summary schema_version mismatch.")
    if summary.get("report_type") != "low_efficiency_grading":
        raise AssertionError("summary report_type mismatch.")
    if summary.get("scenario_key") != "efficiency-label-rate":
        raise AssertionError("summary scenario_key mismatch.")
    if summary.get("level_counts") != {"notice": 410, "P2": 7, "P1": 6, "P0": 4}:
        raise AssertionError("summary level_counts mismatch.")
    if summary.get("comprehensive_reason_count") != 410:
        raise AssertionError("summary comprehensive_reason_count mismatch.")
    if not summary.get("sheet_url"):
        raise AssertionError("summary sheet_url is required for the sent card.")

    outputs = summary.get("outputs", {})
    workbook = outputs.get("workbook")
    if not workbook:
        raise AssertionError("summary outputs.workbook missing.")


def assert_csvs(output_dir: Path, summary: dict[str, Any]) -> None:
    expected_counts = {
        "notice.csv": 410,
        "P2.csv": 7,
        "P1.csv": 6,
        "P0.csv": 4,
        "综合.csv": summary["comprehensive_reason_count"],
    }
    for filename, expected_count in expected_counts.items():
        rows = read_csv_rows(output_dir / filename)
        if len(rows) != expected_count:
            raise AssertionError(f"{filename} row count mismatch.")
        for field in (
            "severity_level",
            "reason",
            "avg_review_in_cnt",
            "avg_review_done_cnt",
            "avg_label_cnt",
            "label_rate",
            "hit_rule_ids",
            "hit_conditions",
        ):
            if field not in rows[0]:
                raise AssertionError(f"{filename} missing field: {field}")


def assert_card(
    card: dict[str, Any],
    card_with_meta: dict[str, Any],
    hash_check: dict[str, Any],
) -> None:
    if "_meta" in card:
        raise AssertionError("send card must not contain _meta.")
    if "_meta" not in card_with_meta:
        raise AssertionError("card_with_meta must contain _meta.")
    if strip_internal_keys(card_with_meta) != card:
        raise AssertionError("card JSON must equal stripped card_with_meta.")
    if hash_check.get("ok") is not True:
        raise AssertionError("hash_check must be ok.")
    if hash_check.get("internal_meta_removed") is not True:
        raise AssertionError("hash_check must confirm _meta removal.")

    top_rows = extract_table_rows(card_with_meta)
    verify_card_hash(card_with_meta, top_rows)
    design_check = card_design_check(card_with_meta)
    if design_check != hash_check.get("design_check"):
        raise AssertionError("design_check mismatch.")
    if design_check.get("passes_p0_p3_basic_gate") is not True:
        raise AssertionError("card design gate failed.")


def extract_table_rows(card: dict[str, Any]) -> list[dict[str, Any]]:
    for element in card.get("body", {}).get("elements", []):
        if isinstance(element, dict) and element.get("tag") == "table":
            rows = element.get("rows")
            if isinstance(rows, list):
                return rows
    raise AssertionError("Card table rows not found.")


def assert_publish_summary(
    publish_summary: dict[str, Any],
    summary: dict[str, Any],
    *,
    expect_sent: bool,
) -> None:
    if publish_summary.get("report_type") != "low_efficiency_grading":
        raise AssertionError("publish_summary report_type mismatch.")
    if publish_summary.get("sheet_url") != summary.get("sheet_url"):
        raise AssertionError("publish_summary sheet_url mismatch.")
    if publish_summary.get("sent") is not expect_sent:
        raise AssertionError("publish_summary sent mismatch.")
    if expect_sent:
        if publish_summary.get("send_identity") not in {"bot", "user"}:
            raise AssertionError("send_identity missing.")
        if not publish_summary.get("target_user"):
            raise AssertionError("target_user missing.")
        if not publish_summary.get("message_id"):
            raise AssertionError("message_id missing.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", nargs="?", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--expect-sent", action="store_true")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    validate(output_dir, expect_sent=args.expect_sent)
    print(f"Stage 2 label-rate notification draft OK: {output_dir}")


if __name__ == "__main__":
    main()
