#!/usr/bin/env python3
"""Validate stage 2 label-rate notification draft artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
NOTIFICATION_SCRIPTS = ROOT / "skills" / "notification" / "scripts"
sys.path.insert(0, str(NOTIFICATION_SCRIPTS))

from card_hash import strip_internal_keys, verify_card_hash  # noqa: E402
from label_rate_notification_artifacts import build_label_rate_notification_artifacts  # noqa: E402
from render_label_rate_grading_card import card_design_check  # noqa: E402


DEFAULT_OUTPUT_DIR = (
    ROOT
    / "evals"
    / "efficiency-label-rate"
    / "stage_2_runs"
    / "20260709_low_label_rate_grading_min_review_in_draft"
)
REQUIRED_FILES = [
    "summary.json",
    "notification_draft.json",
    "send_plan.json",
    "汇总统计.csv",
    "汇总统计_剔除+1同意.csv",
    "notice.csv",
    "P2.csv",
    "P1.csv",
    "P0.csv",
    "综合.csv",
    "综合_剔除+1同意.csv",
    "publish/low_efficiency_grading.card.json",
    "publish/low_efficiency_grading.card.with_meta.json",
    "publish/low_efficiency_grading.publish_summary.json",
    "publish/card_hash_check.json",
]
FORBIDDEN_CARD_CONTRACT_TERMS = (
    "各等级命中 " + "reason 数柱状图",
    "Top " + "reason",
    "四维策略" + "分组",
    "送审" + "原因",
)
_TEMP_DIRS: list[tempfile.TemporaryDirectory[str]] = []


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
    notification_draft = load_json(output_dir / "notification_draft.json")
    send_plan = load_json(output_dir / "send_plan.json")
    card = load_json(output_dir / "publish" / "low_efficiency_grading.card.json")
    card_with_meta = load_json(
        output_dir / "publish" / "low_efficiency_grading.card.with_meta.json"
    )
    publish_summary = load_json(
        output_dir / "publish" / "low_efficiency_grading.publish_summary.json"
    )
    hash_check = load_json(output_dir / "publish" / "card_hash_check.json")

    assert_summary(summary, expect_sent=expect_sent)
    assert_notification_draft(notification_draft, summary)
    assert_send_plan(send_plan, notification_draft)
    assert_csvs(output_dir, summary)
    assert_card(card, card_with_meta, hash_check)
    assert_publish_summary(publish_summary, summary, expect_sent=expect_sent)


def missing_required_files(output_dir: Path) -> list[str]:
    return [relative for relative in REQUIRED_FILES if not (output_dir / relative).exists()]


def build_default_smoke_output() -> Path:
    from validate_label_rate_notification_scripts import write_source

    temp_dir = tempfile.TemporaryDirectory(prefix="label-rate-stage2-draft-smoke-")
    _TEMP_DIRS.append(temp_dir)
    temp_path = Path(temp_dir.name)
    source_path = temp_path / "source.jsonl"
    output_dir = temp_path / "output"
    write_source(source_path)
    build_label_rate_notification_artifacts(
        source_path=source_path,
        output_dir=output_dir,
        top_n=2,
        sheet_url="https://example.com/sheets/stage2-smoke",
        identity="bot",
        title="近7天低效打标策略全等级结果",
        self_send_requested=False,
        sent_payload=None,
        target_user_id=None,
        target_chat_id=None,
        auto_import_sheet=False,
    )
    return output_dir


def assert_summary(summary: dict[str, Any], *, expect_sent: bool) -> None:
    if summary.get("schema_version") != "stage_2_notification_draft.v1":
        raise AssertionError("summary schema_version mismatch.")
    if summary.get("report_type") != "low_efficiency_grading":
        raise AssertionError("summary report_type mismatch.")
    if summary.get("scenario_key") != "efficiency-label-rate":
        raise AssertionError("summary scenario_key mismatch.")
    assert_level_counts(summary)
    if expect_sent and not summary.get("sheet_url"):
        raise AssertionError("summary sheet_url is required for the sent card.")

    outputs = summary.get("outputs", {})
    workbook = outputs.get("workbook")
    if not workbook:
        raise AssertionError("summary outputs.workbook missing.")
    for field in ("poc_routing_plan", "notification_draft", "send_plan"):
        if not outputs.get(field):
            raise AssertionError(f"summary outputs.{field} missing.")
    if outputs.get("summary_by_label_poc_csv") != "汇总统计.csv":
        raise AssertionError("summary outputs.summary_by_label_poc_csv missing.")
    if (
        outputs.get("summary_by_label_poc_exclude_pre_period_plus1_csv")
        != "汇总统计_剔除+1同意.csv"
    ):
        raise AssertionError(
            "summary outputs.summary_by_label_poc_exclude_pre_period_plus1_csv missing."
        )


def assert_level_counts(summary: dict[str, Any]) -> None:
    level_counts = summary.get("level_counts")
    expected_levels = {"notice", "P2", "P1", "P0"}
    if set(level_counts or {}) != expected_levels:
        raise AssertionError("summary level_counts must cover notice/P2/P1/P0.")
    for level, count in level_counts.items():
        if not isinstance(count, int) or count < 0:
            raise AssertionError(f"summary {level} count must be a non-negative integer.")
    comprehensive_reason_count = summary.get("comprehensive_reason_count")
    if not isinstance(comprehensive_reason_count, int) or comprehensive_reason_count < 0:
        raise AssertionError("summary comprehensive_reason_count must be a non-negative integer.")
    comprehensive_alert_count = summary.get(
        "comprehensive_alert_count", comprehensive_reason_count
    )
    if comprehensive_alert_count != comprehensive_reason_count:
        raise AssertionError("summary comprehensive_alert_count mismatch.")
    if comprehensive_reason_count > level_counts.get("notice", 0):
        raise AssertionError("summary comprehensive_reason_count cannot exceed notice count.")
    comprehensive_group_count = summary.get("comprehensive_strategy_group_count")
    if comprehensive_group_count != comprehensive_reason_count:
        raise AssertionError("summary comprehensive_strategy_group_count mismatch.")
    filtered_count = summary.get("comprehensive_exclude_pre_period_plus1_count")
    if not isinstance(filtered_count, int) or filtered_count < 0:
        raise AssertionError(
            "summary comprehensive_exclude_pre_period_plus1_count must be a non-negative integer."
        )
    if filtered_count > comprehensive_reason_count:
        raise AssertionError("filtered comprehensive count cannot exceed comprehensive count.")
    if not summary.get("plus1_exclusion_cutoff_date"):
        raise AssertionError("summary plus1_exclusion_cutoff_date missing.")
    filtered_summary_count = summary.get(
        "label_poc_summary_exclude_pre_period_plus1_count"
    )
    if not isinstance(filtered_summary_count, int) or filtered_summary_count < 0:
        raise AssertionError(
            "summary label_poc_summary_exclude_pre_period_plus1_count "
            "must be a non-negative integer."
        )
    if filtered_summary_count > summary.get("label_poc_summary_count", 0):
        raise AssertionError("filtered label/POC summary count cannot exceed full count.")


def assert_notification_draft(
    notification_draft: dict[str, Any],
    summary: dict[str, Any],
) -> None:
    if notification_draft.get("schema_version") != "stage_2_notification_draft_detail.v1":
        raise AssertionError("notification_draft schema_version mismatch.")
    if notification_draft.get("scenario_key") != "efficiency-label-rate":
        raise AssertionError("notification_draft scenario_key mismatch.")
    if notification_draft.get("report_type") != "low_efficiency_grading":
        raise AssertionError("notification_draft report_type mismatch.")
    if notification_draft.get("default_self_validation") is not True:
        raise AssertionError("notification_draft must declare default self validation.")
    if notification_draft.get("real_poc_mapping_used") is not True:
        raise AssertionError("notification_draft must use name-level POC mapping.")
    if notification_draft.get("level_counts") != summary.get("level_counts"):
        raise AssertionError("notification_draft level_counts mismatch.")
    if notification_draft.get("comprehensive_reason_count") != summary.get(
        "comprehensive_reason_count"
    ):
        raise AssertionError("notification_draft comprehensive count mismatch.")
    if notification_draft.get(
        "comprehensive_alert_count", notification_draft.get("comprehensive_reason_count")
    ) != summary.get("comprehensive_alert_count", summary.get("comprehensive_reason_count")):
        raise AssertionError("notification_draft comprehensive alert count mismatch.")
    if notification_draft.get("comprehensive_strategy_group_count") != summary.get(
        "comprehensive_strategy_group_count"
    ):
        raise AssertionError("notification_draft comprehensive group count mismatch.")

    data_link = notification_draft.get("data_link", {})
    if data_link.get("sheet_url") != summary.get("sheet_url"):
        raise AssertionError("notification_draft data link sheet_url mismatch.")
    if not data_link.get("workbook"):
        raise AssertionError("notification_draft data link workbook missing.")
    csv_files = data_link.get("csv_files", {})
    if csv_files.get("summary_by_label_poc_exclude_pre_period_plus1") != (
        "汇总统计_剔除+1同意.csv"
    ):
        raise AssertionError(
            "notification_draft filtered label/POC summary link missing."
        )

    card_draft = notification_draft.get("card_draft", {})
    if card_draft.get("send_card_meta_removed") is not True:
        raise AssertionError("notification_draft must declare _meta removal.")

    poc_routing = notification_draft.get("poc_routing", {})
    if poc_routing.get("routing_mode") != "mach_root_label_mapping":
        raise AssertionError("notification_draft routing_mode must be mach_root_label_mapping.")
    if poc_routing.get("routing_key") != "mach_root_label_name":
        raise AssertionError("notification_draft routing_key mismatch.")
    if poc_routing.get("contact_resolution_status") != "name_only":
        raise AssertionError("notification_draft contact_resolution_status mismatch.")
    if poc_routing.get("mapped_row_count", 0) <= 0:
        raise AssertionError("notification_draft mapped_row_count must be positive.")
    if poc_routing.get("default_recipient") != "self":
        raise AssertionError("notification_draft default_recipient must be self.")
    routing_rules = poc_routing.get("routing_rules", {})
    if set(routing_rules) != {"notice", "P2", "P1", "P0"}:
        raise AssertionError("notification_draft routing rules must cover all levels.")
    for level, rule in routing_rules.items():
        if not rule.get("target_roles"):
            raise AssertionError(f"{level} target_roles missing.")
        if not rule.get("action_required"):
            raise AssertionError(f"{level} action_required missing.")
        resolution = rule.get("recipient_resolution", {})
        if resolution.get("mode") != "mach_root_label_mapping":
            raise AssertionError(f"{level} recipient_resolution mode mismatch.")
        if resolution.get("routing_key") != "mach_root_label_name":
            raise AssertionError(f"{level} recipient_resolution routing_key mismatch.")
        if rule.get("alert_count", rule.get("reason_count", 0)) > 0 and not rule.get("poc_names"):
            raise AssertionError(f"{level} poc_names missing.")
        if rule.get("group_send_blocked") is not True:
            raise AssertionError(f"{level} group_send_blocked must be true.")

    send_safety = notification_draft.get("send_safety", {})
    if send_safety.get("requires_confirmation_before_group_send") is not True:
        raise AssertionError("notification_draft must require confirmation.")
    if send_safety.get("group_send_blocked") is not True:
        raise AssertionError("notification_draft must block group send.")
    if send_safety.get("sent") is not False:
        raise AssertionError("notification_draft group send sent must be false.")
    if send_safety.get("real_group_send_executed") is not False:
        raise AssertionError("notification_draft must not execute real group send.")
    if send_safety.get("online_write_executed") is not False:
        raise AssertionError("notification_draft must not write online state.")


def assert_send_plan(
    send_plan: dict[str, Any],
    notification_draft: dict[str, Any],
) -> None:
    if send_plan.get("schema_version") != "stage_2_send_plan.v1":
        raise AssertionError("send_plan schema_version mismatch.")
    if send_plan.get("scenario_key") != "efficiency-label-rate":
        raise AssertionError("send_plan scenario_key mismatch.")
    if send_plan.get("report_type") != "low_efficiency_grading":
        raise AssertionError("send_plan report_type mismatch.")
    if send_plan.get("requires_confirmation") is not True:
        raise AssertionError("send_plan requires_confirmation must be true.")
    if send_plan.get("confirmation_status") != "not_requested":
        raise AssertionError("send_plan confirmation_status mismatch.")
    if send_plan.get("group_send_blocked") is not True:
        raise AssertionError("send_plan group_send_blocked must be true.")
    if send_plan.get("group_send_allowed") is not False:
        raise AssertionError("send_plan group_send_allowed must be false.")
    if send_plan.get("group_recipients") != []:
        raise AssertionError("send_plan group_recipients must be empty.")
    if send_plan.get("sent") is not False:
        raise AssertionError("send_plan sent must be false.")
    if send_plan.get("real_group_send_executed") is not False:
        raise AssertionError("send_plan must not execute real group send.")
    if send_plan.get("online_write_executed") is not False:
        raise AssertionError("send_plan must not write online state.")
    if not send_plan.get("blocked_reason"):
        raise AssertionError("send_plan blocked_reason missing.")

    content_source = send_plan.get("content_source", {})
    if "notification_draft.json" not in content_source.get("notification_draft", ""):
        raise AssertionError("send_plan notification draft source mismatch.")
    if notification_draft.get("send_safety", {}).get("group_send_blocked") is not True:
        raise AssertionError("send_plan depends on an unsafe notification draft.")


def assert_csvs(output_dir: Path, summary: dict[str, Any]) -> None:
    level_counts = summary["level_counts"]
    expected_counts = {
        "汇总统计.csv": summary.get("label_poc_summary_count"),
        "汇总统计_剔除+1同意.csv": summary.get(
            "label_poc_summary_exclude_pre_period_plus1_count"
        ),
        "notice.csv": level_counts["notice"],
        "P2.csv": level_counts["P2"],
        "P1.csv": level_counts["P1"],
        "P0.csv": level_counts["P0"],
        "综合.csv": summary.get("comprehensive_alert_count", summary["comprehensive_reason_count"]),
        "综合_剔除+1同意.csv": summary["comprehensive_exclude_pre_period_plus1_count"],
    }
    for filename, expected_count in expected_counts.items():
        rows = read_csv_rows(output_dir / filename)
        if len(rows) != expected_count:
            raise AssertionError(f"{filename} row count mismatch.")
        if filename in {"汇总统计.csv", "汇总统计_剔除+1同意.csv"}:
            for field in (
                "机审一级标签",
                "POC",
                "低效策略数",
                "低效策略日均进审量",
                "低效策略日均完审量",
                "低效策略日均打标量",
                "低效策略打标率",
            ):
                if rows and field not in rows[0]:
                    raise AssertionError(f"{filename} missing field: {field}")
            assert_summary_label_rate_matches_displayed_counts(rows, filename)
            continue
        for field in (
            "机审一级标签",
            "策略ID",
            "策略名称",
            "预警维度",
            "最大有数日期",
            "POC",
            "日均进审量",
            "日均完审量",
            "日均打标量",
            "打标率",
            "命中原因",
            "是否+1同意",
            "更新日期",
            "+1同意日期是否在本次统计周期前",
        ):
            if rows and field not in rows[0]:
                raise AssertionError(f"{filename} missing field: {field}")
        assert_plus1_period_flag(rows, summary["plus1_exclusion_cutoff_date"], filename)


def assert_summary_label_rate_matches_displayed_counts(
    rows: list[dict[str, str]],
    filename: str,
) -> None:
    for row in rows:
        done = float(row.get("低效策略日均完审量") or 0)
        label = float(row.get("低效策略日均打标量") or 0)
        actual = float(row.get("低效策略打标率") or 0)
        expected = label / done if done else 0.0
        if abs(actual - expected) > 1e-12:
            raise AssertionError(f"{filename} 低效策略打标率 must equal 打标量 / 完审量.")


def assert_plus1_period_flag(
    rows: list[dict[str, str]],
    cutoff_date: str,
    filename: str,
) -> None:
    field = "+1同意日期是否在本次统计周期前"
    for row in rows:
        actual = row.get(field)
        if actual not in {"是", "否"}:
            raise AssertionError(f"{filename} {field} must be 是/否.")
        update_date = (row.get("更新日期") or "").strip().replace("/", "-")
        expected = (
            "是"
            if row.get("是否+1同意") == "是" and bool(update_date) and update_date < cutoff_date
            else "否"
        )
        if actual != expected:
            raise AssertionError(f"{filename} {field} mismatch.")


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

    summary_table_rows = extract_summary_table_rows(card_with_meta)
    if not summary_table_rows:
        raise AssertionError("Card summary table rows not found.")
    for row in summary_table_rows:
        for field in (
            "mach_root_label_name",
            "POC",
            "low_efficiency_strategy_count",
            "avg_review_in_cnt",
            "avg_review_done_cnt",
            "avg_label_cnt",
            "label_rate",
        ):
            if field not in row:
                raise AssertionError(f"Card summary row missing field: {field}")
        if not str(row.get("label_rate", "")).endswith("%"):
            raise AssertionError("Card summary label_rate must be rendered as percent.")

    table_rows_by_level = extract_table_rows_by_level(card_with_meta)
    if set(table_rows_by_level) != {"P0", "P1", "P2", "notice"}:
        raise AssertionError("Card must contain P0/P1/P2/notice table sections.")
    top_rows = [
        row
        for level in ("P0", "P1", "P2", "notice")
        for row in table_rows_by_level[level]
    ]
    for row in top_rows:
        for field in (
            "poc_name",
            "mach_root_label_name",
            "strategy_id",
            "strategy_name",
            "warning_dimension",
            "max_data_date",
            "hit_reason",
        ):
            if field not in row:
                raise AssertionError(f"Card table row missing field: {field}")
        if not str(row.get("label_rate", "")).endswith("%"):
            raise AssertionError("Card table label_rate must be rendered as percent.")
    verify_card_hash(card_with_meta, summary_table_rows + top_rows)
    design_check = card_design_check(card_with_meta)
    assert_no_old_card_contract(card_with_meta, design_check)
    expected_design_check = hash_check.get("design_check", {})
    for key, value in design_check.items():
        if expected_design_check.get(key) != value:
            raise AssertionError(f"design_check mismatch for {key}.")
    if design_check.get("passes_p0_p3_basic_gate") is not True:
        raise AssertionError("card design gate failed.")


def iter_card_tags(value: Any) -> list[str]:
    tags: list[str] = []
    if isinstance(value, dict):
        tag = value.get("tag")
        if isinstance(tag, str):
            tags.append(tag)
        for child in value.values():
            tags.extend(iter_card_tags(child))
    elif isinstance(value, list):
        for item in value:
            tags.extend(iter_card_tags(item))
    return tags


def assert_no_old_card_contract(
    card: dict[str, Any],
    design_check: dict[str, Any],
) -> None:
    rendered = json.dumps(card, ensure_ascii=False)
    for term in FORBIDDEN_CARD_CONTRACT_TERMS:
        if term in rendered:
            raise AssertionError(f"Card still contains old contract term: {term}")
    if "chart" in iter_card_tags(card):
        raise AssertionError("Card must not contain chart elements.")
    if "has_chart" in design_check:
        raise AssertionError("card_design_check must not expose has_chart.")


def extract_summary_table_rows(card: dict[str, Any]) -> list[dict[str, Any]]:
    found_summary_title = False
    for element in card.get("body", {}).get("elements", []):
        if not isinstance(element, dict):
            continue
        if element.get("tag") == "markdown" and "### 汇总统计" in str(
            element.get("content", "")
        ):
            found_summary_title = True
            continue
        if found_summary_title and element.get("tag") == "table":
            rows = element.get("rows")
            if isinstance(rows, list):
                return rows
    return []


def extract_table_rows_by_level(card: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    current_level: str | None = None
    for element in card.get("body", {}).get("elements", []):
        if not isinstance(element, dict):
            continue
        if element.get("tag") == "markdown":
            content = str(element.get("content", ""))
            for level, display in {
                "P0": "P0",
                "P1": "P1",
                "P2": "P2",
                "notice": "Notice",
            }.items():
                if f">{display} 等级 Top" in content:
                    current_level = level
                    break
        elif element.get("tag") == "table":
            rows = element.get("rows")
            if current_level and isinstance(rows, list):
                result[current_level] = rows
                current_level = None
    return result


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
    if not str(publish_summary.get("summary_by_label_poc_csv", "")).endswith(
        "汇总统计.csv"
    ):
        raise AssertionError("publish_summary summary_by_label_poc_csv missing.")
    if not str(
        publish_summary.get("summary_by_label_poc_exclude_pre_period_plus1_csv", "")
    ).endswith("汇总统计_剔除+1同意.csv"):
        raise AssertionError(
            "publish_summary summary_by_label_poc_exclude_pre_period_plus1_csv missing."
        )
    if publish_summary.get("sent") is not expect_sent:
        raise AssertionError("publish_summary sent mismatch.")
    if expect_sent:
        if publish_summary.get("send_identity") not in {"bot", "user"}:
            raise AssertionError("send_identity missing.")
        if publish_summary.get("target_type") == "user":
            if not publish_summary.get("target_user"):
                raise AssertionError("target_user missing.")
        elif publish_summary.get("target_type") == "chat":
            if not publish_summary.get("target_chat_id"):
                raise AssertionError("target_chat_id missing.")
        else:
            raise AssertionError("target_type missing.")
        if not publish_summary.get("message_id"):
            raise AssertionError("message_id missing.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", nargs="?", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--expect-sent", action="store_true")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if output_dir == DEFAULT_OUTPUT_DIR and missing_required_files(output_dir):
        output_dir = build_default_smoke_output()
    validate(output_dir, expect_sent=args.expect_sent)
    print(f"Stage 2 label-rate notification draft OK: {output_dir}")


if __name__ == "__main__":
    main()
