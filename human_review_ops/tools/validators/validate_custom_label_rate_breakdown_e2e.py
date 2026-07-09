#!/usr/bin/env python3
"""Validate custom multi-dimension low label-rate E2E artifacts."""

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


DEFAULT_OUTPUT_DIR = (
    ROOT
    / "evals"
    / "efficiency-label-rate"
    / "stage_2_runs"
    / "20260709_custom_label_rate_breakdown_summary_default_20260629_20260705"
)
EXPECTED_DIMENSIONS = [
    "mach_root_label_name",
    "strategy_id",
    "strategy_name",
    "reason",
]
EXPECTED_COLUMNS = EXPECTED_DIMENSIONS + [
    "data_days",
    "calendar_days",
    "total_review_in_cnt",
    "total_review_done_cnt",
    "total_label_cnt",
    "avg_review_in_cnt",
    "avg_review_done_cnt",
    "avg_label_cnt",
    "label_rate",
]
REQUIRED_SQL_SNIPPETS = [
    "`[p_date]` >= '2026-06-29'",
    "`[p_date]` < '2026-07-06'",
    "`[机审一级标签]`",
    "`[strategy_id]`",
    "`[strategy_name]`",
    "`[reason]`",
    "`[进审量_reviewid]`",
    "`[完审量_reviewid]`",
    "`[打标量__reviewid]`",
    "`[project_title]` NOT LIKE '%虚假%'",
    "`[project_title]` NOT LIKE '%标注%'",
    "`[project_title]` NOT LIKE '%自动处置%'",
    "`[scene]` IN ('community_audit_safe', 'community_audit_style', 'community_audit_moderate')",
    "`[reason]` NOT IN ('recall_skip_L6', 'fatal_output')",
    "`[机审一级标签]` IS NULL OR `[机审一级标签]` IN",
    "SUM(review_in_cnt) / COUNT(DISTINCT dt) AS avg_review_in_cnt",
    "SUM(review_done_cnt) / COUNT(DISTINCT dt) AS avg_review_done_cnt",
    "SUM(label_cnt) / COUNT(DISTINCT dt) AS avg_label_cnt",
    "SUM(label_cnt) / SUM(review_done_cnt)",
    "SUM(review_done_cnt) > 0",
    "< 0.1",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", nargs="?", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--expect-group-sent", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    validate(output_dir, expect_group_sent=args.expect_group_sent)
    print(f"Custom label-rate breakdown E2E OK: {output_dir}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def validate(output_dir: Path, *, expect_group_sent: bool) -> None:
    required_files = [
        "summary.json",
        "custom_label_rate_breakdown_results.jsonl",
        "custom_label_rate_breakdown.csv",
        "custom_label_rate_breakdown_2026-06-29_2026-07-05.xlsx",
        "publish/custom_label_rate_breakdown.publish_summary.json",
    ]
    if not expect_group_sent:
        required_files.append("analysis_summary.md")
    if expect_group_sent:
        required_files.append("group_send_validation.json")
    for relative in required_files:
        if not (output_dir / relative).exists():
            raise AssertionError(f"Missing artifact: {relative}")

    summary = load_json(output_dir / "summary.json")
    records = load_jsonl(output_dir / "custom_label_rate_breakdown_results.jsonl")
    csv_rows = read_csv_rows(output_dir / "custom_label_rate_breakdown.csv")
    publish_summary = load_json(
        output_dir / "publish" / "custom_label_rate_breakdown.publish_summary.json"
    )
    card_path = output_dir / "publish" / "custom_label_rate_breakdown.card.json"
    card_with_meta_path = output_dir / "publish" / "custom_label_rate_breakdown.card.with_meta.json"
    hash_check_path = output_dir / "publish" / "card_hash_check.json"

    require_analysis_summary = not expect_group_sent or (output_dir / "analysis_summary.md").exists()
    assert_summary(summary, require_analysis_summary=require_analysis_summary)
    if (output_dir / "analysis_summary.md").exists():
        assert_analysis_summary(output_dir / "analysis_summary.md", summary)
    assert_records(records, summary)
    assert_csv(csv_rows, summary)
    if card_path.exists() or card_with_meta_path.exists() or hash_check_path.exists():
        if not (card_path.exists() and card_with_meta_path.exists() and hash_check_path.exists()):
            raise AssertionError("Card artifacts must be complete when present.")
        assert_card(
            load_json(card_path),
            load_json(card_with_meta_path),
            load_json(hash_check_path),
        )
    assert_publish_summary(publish_summary, summary, expect_group_sent=expect_group_sent)
    if expect_group_sent:
        assert_group_send_validation(
            load_json(output_dir / "group_send_validation.json"),
            publish_summary,
            summary,
        )
    poc_routing_path = output_dir / "poc_routing_plan.json"
    if poc_routing_path.exists():
        assert_poc_routing_plan(load_json(poc_routing_path), summary)


def assert_summary(
    summary: dict[str, Any],
    *,
    require_analysis_summary: bool,
) -> None:
    if summary.get("schema_version") != "custom_label_rate_breakdown.v1":
        raise AssertionError("summary schema_version mismatch.")
    if summary.get("scenario_key") != "efficiency-label-rate":
        raise AssertionError("summary scenario_key mismatch.")
    if summary.get("report_type") != "custom_label_rate_breakdown":
        raise AssertionError("summary report_type mismatch.")
    if summary.get("dimensions") != EXPECTED_DIMENSIONS:
        raise AssertionError("summary dimensions mismatch.")
    period = summary.get("period", {})
    if period.get("start_date") != "2026-06-29":
        raise AssertionError("summary start_date mismatch.")
    if period.get("end_date") != "2026-07-05":
        raise AssertionError("summary end_date mismatch.")
    if period.get("calendar_days") != 7:
        raise AssertionError("summary calendar_days mismatch.")
    if summary.get("dataset_id") != "3888816":
        raise AssertionError("summary dataset_id mismatch.")
    if summary.get("source_tier") != "governed_dataset":
        raise AssertionError("summary source_tier mismatch.")
    if summary.get("row_count", 0) <= 0:
        raise AssertionError("summary row_count must be positive.")
    if summary.get("query_row_count") != summary.get("row_count"):
        raise AssertionError("summary query_row_count mismatch.")
    if summary.get("truncated") is not False:
        raise AssertionError("summary truncated must be false.")
    if not (0 <= summary.get("weighted_label_rate", -1) < 0.1):
        raise AssertionError("summary weighted_label_rate out of range.")
    if not summary.get("outputs", {}).get("sheet_url"):
        raise AssertionError("summary sheet_url missing.")
    if require_analysis_summary and not summary.get("outputs", {}).get("analysis_summary_md"):
        raise AssertionError("summary analysis_summary_md missing.")
    sql = summary.get("sql", "")
    for snippet in REQUIRED_SQL_SNIPPETS:
        if snippet not in sql:
            raise AssertionError(f"SQL missing required snippet: {snippet}")


def assert_analysis_summary(path: Path, summary: dict[str, Any]) -> None:
    text = path.read_text(encoding="utf-8")
    for snippet in (
        "自定义低打标率多维查询汇总",
        "机审一级标签 × strategy_id × strategy_name × reason",
        str(summary["row_count"]),
        "完整飞书电子表格",
        "Provenance",
    ):
        if snippet not in text:
            raise AssertionError(f"analysis_summary missing snippet: {snippet}")


def assert_poc_routing_plan(plan: dict[str, Any], summary: dict[str, Any]) -> None:
    if plan.get("schema_version") != "label_rate_mach_label_poc_routing_plan.v1":
        raise AssertionError("poc_routing_plan schema_version mismatch.")
    if plan.get("routing_mode") != "mach_root_label_mapping":
        raise AssertionError("poc_routing_plan routing_mode mismatch.")
    if plan.get("routing_key") != "mach_root_label_name":
        raise AssertionError("poc_routing_plan routing_key mismatch.")
    if plan.get("row_count") != summary["row_count"]:
        raise AssertionError("poc_routing_plan row_count mismatch.")
    if plan.get("mapped_row_count", 0) <= 0:
        raise AssertionError("poc_routing_plan mapped_row_count must be positive.")
    if plan.get("missing_route_dimension_count") != 0:
        raise AssertionError("poc_routing_plan should not miss mach_root_label_name.")
    constraints = plan.get("routing_constraints", {})
    if constraints.get("requires_contact_resolution_before_real_send") is not True:
        raise AssertionError("poc_routing_plan must require contact resolution.")
    if constraints.get("requires_human_confirmation_before_real_send") is not True:
        raise AssertionError("poc_routing_plan must require human confirmation.")
    if constraints.get("group_send_blocked") is not True:
        raise AssertionError("poc_routing_plan must keep group_send_blocked=true.")


def assert_records(records: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    environment = next(
        (record for record in records if record.get("record_type") == "environment"),
        None,
    )
    sample = next(
        (record for record in records if record.get("record_type") == "sample"),
        None,
    )
    if not environment or not sample:
        raise AssertionError("Missing environment or sample record.")
    if environment.get("real_query_executed") is not True:
        raise AssertionError("environment must mark real query executed.")
    if environment.get("online_write_blocked") is not True:
        raise AssertionError("environment must block online writes.")

    query_plan = sample.get("QueryPlan", {})
    if query_plan.get("analysis_mode") != "custom_dimension_breakdown":
        raise AssertionError("QueryPlan analysis_mode mismatch.")
    if query_plan.get("dimensions") != EXPECTED_DIMENSIONS:
        raise AssertionError("QueryPlan dimensions mismatch.")
    if query_plan.get("time_range", {}).get("start_date") != "2026-06-29":
        raise AssertionError("QueryPlan start_date mismatch.")
    if query_plan.get("time_range", {}).get("end_date") != "2026-07-05":
        raise AssertionError("QueryPlan end_date mismatch.")
    if query_plan.get("review_required") is not False:
        raise AssertionError("QueryPlan review_required must be false.")

    execution = sample.get("readonly_execution", {})
    if execution.get("row_count") != summary["row_count"]:
        raise AssertionError("readonly_execution row_count mismatch.")
    if execution.get("truncated") is not False:
        raise AssertionError("readonly_execution truncated must be false.")
    if execution.get("columns") != EXPECTED_COLUMNS:
        raise AssertionError("readonly_execution columns mismatch.")
    if len(execution.get("rows", [])) != summary["row_count"]:
        raise AssertionError("readonly_execution rows mismatch.")
    for row in execution.get("rows", []):
        assert_result_row(row)

    permission_checks = sample.get("permission_checks", {})
    if permission_checks.get("read_only") is not True:
        raise AssertionError("sample must remain readonly.")
    if permission_checks.get("online_write_blocked") is not True:
        raise AssertionError("sample must block online writes.")


def assert_result_row(row: dict[str, Any]) -> None:
    for field in EXPECTED_COLUMNS:
        if field not in row:
            raise AssertionError(f"row missing field: {field}")
    if row["calendar_days"] != 7:
        raise AssertionError("row calendar_days mismatch.")
    if not (1 <= row["data_days"] <= 7):
        raise AssertionError("row data_days out of range.")
    if row["total_review_done_cnt"] <= 0:
        raise AssertionError("row total_review_done_cnt must be positive.")
    if not (0 <= row["label_rate"] < 0.1):
        raise AssertionError(f"row label_rate out of range: {row['label_rate']}")
    for field in ("avg_review_in_cnt", "avg_review_done_cnt", "avg_label_cnt"):
        if row[field] < 0:
            raise AssertionError(f"{field} must be non-negative.")


def assert_csv(rows: list[dict[str, str]], summary: dict[str, Any]) -> None:
    if len(rows) != summary["row_count"]:
        raise AssertionError("CSV row count mismatch.")
    if set(rows[0]) != set(EXPECTED_COLUMNS):
        raise AssertionError("CSV columns mismatch.")
    for row in rows:
        if not (0 <= float(row["label_rate"]) < 0.1):
            raise AssertionError("CSV label_rate out of range.")


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
    top_rows = hash_check.get("top_rows", [])
    if not top_rows:
        top_rows = extract_table_rows(card_with_meta)
    verify_card_hash(card_with_meta, top_rows)
    design_check = hash_check.get("design_check", {})
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
    expect_group_sent: bool,
) -> None:
    if publish_summary.get("report_type") != "custom_label_rate_breakdown":
        raise AssertionError("publish_summary report_type mismatch.")
    if publish_summary.get("sheet_url") != summary.get("outputs", {}).get("sheet_url"):
        raise AssertionError("publish_summary sheet_url mismatch.")
    if publish_summary.get("sent") is not expect_group_sent:
        raise AssertionError("publish_summary sent mismatch.")
    if publish_summary.get("analysis_summary_md") != summary.get("outputs", {}).get("analysis_summary_md"):
        raise AssertionError("publish_summary analysis_summary_md mismatch.")
    if expect_group_sent:
        if publish_summary.get("send_identity") not in {"bot", "user"}:
            raise AssertionError("publish_summary send_identity missing.")
        if not publish_summary.get("target_chat_id"):
            raise AssertionError("publish_summary target_chat_id missing.")
        if not publish_summary.get("message_id"):
            raise AssertionError("publish_summary message_id missing.")
        if publish_summary.get("send_channel") not in {"interactive_card", "markdown_fallback"}:
            raise AssertionError("publish_summary send_channel mismatch.")


def assert_group_send_validation(
    group_send_validation: dict[str, Any],
    publish_summary: dict[str, Any],
    summary: dict[str, Any],
) -> None:
    if group_send_validation.get("schema_version") != "custom_label_rate_group_send_validation.v1":
        raise AssertionError("group_send_validation schema_version mismatch.")
    send_result = group_send_validation.get("send_result", {})
    if send_result.get("sent") is not True:
        raise AssertionError("group_send_validation sent must be true.")
    if send_result.get("message_id") != publish_summary.get("message_id"):
        raise AssertionError("group_send_validation message_id mismatch.")
    safety = group_send_validation.get("safety", {})
    if safety.get("user_explicitly_requested_group_validation") is not True:
        raise AssertionError("group validation must be user requested.")
    if safety.get("online_state_store_write_executed") is not False:
        raise AssertionError("group validation must not write online state.")
    if safety.get("dimensions") != EXPECTED_DIMENSIONS:
        raise AssertionError("group validation dimensions mismatch.")
    if safety.get("row_count") != summary.get("row_count"):
        raise AssertionError("group validation row_count mismatch.")


if __name__ == "__main__":
    main()
