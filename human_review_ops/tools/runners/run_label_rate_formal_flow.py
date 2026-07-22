#!/usr/bin/env python3
"""Run the formal perception -> analysis -> notification label-rate flow."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from human_review_ops.tools.compat.skill_path_resolver import (  # noqa: E402
    active_path_mode,
    resolve_script_dir,
)


SCENARIO_KEY = "efficiency-label-rate"
PERCEPTION_SCRIPTS = resolve_script_dir(SCENARIO_KEY, "perception")
ANALYSIS_SCRIPTS = resolve_script_dir(SCENARIO_KEY, "analysis")
NOTIFICATION_SCRIPTS = resolve_script_dir(SCENARIO_KEY, "notification_artifacts")
POC_ROUTING_SCRIPTS = resolve_script_dir(SCENARIO_KEY, "poc_routing")
for script_dir in reversed(
    tuple(dict.fromkeys((
        PERCEPTION_SCRIPTS,
        ANALYSIS_SCRIPTS,
        NOTIFICATION_SCRIPTS,
        POC_ROUTING_SCRIPTS,
    )))
):
    sys.path.insert(0, str(script_dir))

import label_rate_analysis  # noqa: E402
from label_rate_perception import detect_label_rate_perception  # noqa: E402
from label_rate_notification_artifacts import (  # noqa: E402
    build_label_rate_notification_artifacts,
)
from resolve_label_rate_poc_routing import (  # noqa: E402
    load_poc_mapping,
    poc_mapping_index,
    resolve_row_poc,
)


REGION = "cn"
DATASET_ID = "3888816"
QUERY_LIMIT = "50000"
TEST_GROUP_CHAT_ID = "oc_9c691aa76c22a16207c6f443eac25816"
TEST_GROUP_NAME = "人审阶段2群发验证-20260709"
DEFAULT_REQUEST = (
    "请按正规流程测试现有打标率：先查询近7天低效打标策略，"
    "按P0/P1/P2/notice分级，再把结果推送到飞书测试群。"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", default=DEFAULT_REQUEST)
    parser.add_argument("--levels", default="notice,P2,P1,P0")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--run-id", default=datetime.now().strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--output-dir")
    parser.add_argument("--send-chat-id")
    parser.add_argument("--send-identity", choices=["bot", "user"], default="bot")
    parser.add_argument(
        "--data-direction",
        choices=["manual_review_detail", "report_flow", "combined", "auto"],
        default="auto",
        help=(
            "Data direction. auto follows perception; report_flow uses the "
            "举报数据集 and maps enpool_reason to strategy_id/strategy_name; "
            "combined runs manual_review_detail and report_flow, then merges "
            "the normalized grading results."
        ),
    )
    parser.add_argument("--confirm-send", action="store_true")
    parser.add_argument("--sheet-url")
    parser.add_argument("--no-import-workbook", action="store_true")
    parser.add_argument("--idempotency-key")
    args = parser.parse_args()

    base = (
        Path(args.output_dir)
        if args.output_dir
        else ROOT
        / "evals"
        / SCENARIO_KEY
        / "stage_2_runs"
        / f"{args.run_id}_formal_skill_flow"
    )
    base.mkdir(parents=True, exist_ok=True)
    stage1_path = (
        ROOT
        / "evals"
        / SCENARIO_KEY
        / "stage_1_runs"
        / f"{args.run_id}_formal_skill_flow_results.jsonl"
    )

    original_perception = run_perception(args.request)
    write_json(base / "perception_notification_request.json", original_perception)
    assert_notification_intent_or_raise(original_perception)
    time_range = resolve_grading_time_range(args, original_perception)
    data_direction = resolve_data_direction(args, original_perception)
    if time_range:
        write_json(base / "resolved_time_range.json", time_range)
    write_json(base / "resolved_data_direction.json", {"data_direction": data_direction})

    analysis_request = build_analysis_request(original_perception, data_direction)
    analysis_perception = run_perception(analysis_request)
    write_json(base / "perception_analysis_request.json", analysis_perception)
    assert_analysis_ready_or_raise(analysis_perception)

    stage1_record = run_analysis(
        args,
        base,
        stage1_path,
        time_range=time_range,
        data_direction=data_direction,
    )

    sheet_url = args.sheet_url
    artifacts = build_notification(
        args=args,
        base=base,
        stage1_path=stage1_path,
        sheet_url=sheet_url,
        sent_payload=None,
    )
    sheet_url = artifacts.summary.get("sheet_url") or sheet_url

    dispatch_record: dict[str, Any] | None = None
    if args.send_chat_id:
        dispatch_record = dispatch_to_lark(
            args=args,
            base=base,
            artifacts=artifacts,
            sheet_url=sheet_url,
        )
        artifacts = build_notification(
            args=args,
            base=base,
            stage1_path=stage1_path,
            sheet_url=sheet_url,
            sent_payload=dispatch_record["send_result"],
        )
        dispatch_record["publish_summary"] = artifacts.publish_summary
        write_json(base / "host_dispatch_record.json", dispatch_record)

    summary = {
        "run_id": args.run_id,
        "request": args.request,
        "stage1_result": str(stage1_path),
        "stage2_output_dir": str(base),
        "level_counts": stage1_record["readonly_execution"]["level_counts"],
        "row_count": stage1_record["readonly_execution"]["row_count"],
        "period": stage1_record["QueryPlan"]["time_range"],
        "data_direction": data_direction,
        "sheet_url": sheet_url,
        "message_id": (dispatch_record or {}).get("message_id"),
        "target_chat_id": args.send_chat_id,
        "target_chat_name": TEST_GROUP_NAME
        if args.send_chat_id == TEST_GROUP_CHAT_ID
        else None,
        "skill_path_mode": active_path_mode(),
        "skill_paths": {
            "perception": str(PERCEPTION_SCRIPTS.relative_to(REPO_ROOT)),
            "analysis": str(ANALYSIS_SCRIPTS.relative_to(REPO_ROOT)),
            "notification_artifacts": str(NOTIFICATION_SCRIPTS.relative_to(REPO_ROOT)),
            "poc_routing": str(POC_ROUTING_SCRIPTS.relative_to(REPO_ROOT)),
        },
        "validators": [],
    }
    write_json(base / "formal_flow_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def run_perception(request: str) -> dict[str, Any]:
    return detect_label_rate_perception(raw_user_request=request)


def assert_notification_intent_or_raise(payload: dict[str, Any]) -> None:
    if payload.get("scenario_key") != SCENARIO_KEY:
        raise RuntimeError(f"perception did not identify {SCENARIO_KEY}: {payload}")
    workflow = payload.get("workflow_plan", {})
    if workflow.get("intent_type") not in {"analysis_then_notification", "analysis"}:
        raise RuntimeError(f"unsupported workflow_plan: {workflow}")


def build_analysis_request(perception: dict[str, Any], data_direction: str) -> str:
    time_window = perception.get("time_window") or "近7天"
    if data_direction == "combined":
        return (
            f"分别查询{time_window}人审数据集与举报场景低效打标全等级结果，"
            "举报风险域固定为举报，策略ID和策略名称均使用 enpool_reason，"
            "最终按统一字段合并输出。"
        )
    if data_direction == "report_flow":
        return (
            f"查询举报场景{time_window}低效打标 enpool_reason，"
            "按P0/P1/P2/notice分级；风险域固定为举报，"
            "策略ID和策略名称均使用 enpool_reason。"
        )
    return (
        f"查询{time_window}低效打标策略，按P0/P1/P2/notice分级，"
        "默认按机审一级标签、策略ID、策略名称三维分级。"
    )


def resolve_grading_time_range(
    args: argparse.Namespace,
    perception: dict[str, Any],
) -> dict[str, Any] | None:
    if bool(args.start_date) != bool(args.end_date):
        raise RuntimeError("--start-date and --end-date must be provided together.")
    if args.start_date and args.end_date:
        return label_rate_analysis.build_grading_time_range(
            start_date=parse_date(args.start_date),
            end_date=parse_date(args.end_date),
        )
    for raw_text in (args.request, perception.get("time_window")):
        time_range = label_rate_analysis.parse_user_period(raw_text)
        if time_range:
            return time_range
    return None


def resolve_data_direction(
    args: argparse.Namespace,
    perception: dict[str, Any],
) -> str:
    if args.data_direction != "auto":
        return args.data_direction
    direction = perception.get("data_direction")
    if direction in {"manual_review_detail", "report_flow"}:
        return str(direction)
    return "manual_review_detail"


def parse_date(raw_value: str) -> date:
    return date.fromisoformat(raw_value.strip().replace("/", "-"))


def assert_analysis_ready_or_raise(payload: dict[str, Any]) -> None:
    if payload.get("scenario_key") != SCENARIO_KEY:
        raise RuntimeError(f"analysis prerequisite scenario mismatch: {payload}")
    if payload.get("task_type") != "low_label_rate_grading":
        raise RuntimeError(f"analysis prerequisite task mismatch: {payload}")
    if payload.get("readiness", {}).get("status") != "ready":
        raise RuntimeError(f"analysis prerequisite is not ready: {payload}")


def run_analysis(
    args: argparse.Namespace,
    base: Path,
    stage1_path: Path,
    *,
    time_range: dict[str, Any] | None,
    data_direction: str,
) -> dict[str, Any]:
    if data_direction == "combined":
        return run_combined_analysis(
            args=args,
            base=base,
            stage1_path=stage1_path,
            time_range=time_range,
        )

    records = execute_direction_analysis(
        args=args,
        base=base,
        time_range=time_range,
        data_direction=data_direction,
        artifact_prefix="",
    )
    write_stage1_records(stage1_path, records)
    sample = records[1]
    write_json(
        base / "analysis_summary.json",
        {
            "stage1_result": str(stage1_path),
            "freshness": load_optional_json(base / "analysis_freshness_check.json")
            .get("data", {})
            .get("rows", []),
            "level_counts": sample["readonly_execution"]["level_counts"],
            "row_count": sample["readonly_execution"]["row_count"],
            "source_footer": sample["source_footer"],
            "data_direction": data_direction,
        },
    )
    return sample


def execute_direction_analysis(
    *,
    args: argparse.Namespace,
    base: Path,
    time_range: dict[str, Any] | None,
    data_direction: str,
    artifact_prefix: str,
) -> list[dict[str, Any]]:
    levels = label_rate_analysis.parse_levels(args.levels)
    if data_direction == "report_flow":
        sql_map = label_rate_analysis.report_flow_sql_by_level(time_range)
        query_plan = label_rate_analysis.build_report_flow_grading_query_plan(
            levels,
            sql_map,
            time_range=time_range,
        )
    else:
        sql_map = label_rate_analysis.sql_by_level(time_range)
        query_plan = label_rate_analysis.build_query_plan(
            levels,
            sql_map,
            time_range=time_range,
        )
    prefix = f"{artifact_prefix}_" if artifact_prefix else ""
    write_json(base / f"analysis_query_plan{prefixed_suffix(artifact_prefix)}.json", query_plan)
    write_json(base / f"analysis_sql_by_level{prefixed_suffix(artifact_prefix)}.json", sql_map)

    freshness_sql = build_freshness_sql(time_range, data_direction=data_direction)
    freshness = run_aeolus_query(
        freshness_sql,
        limit="10",
        dataset_id=dataset_id_for_data_direction(data_direction),
    )
    write_json(base / f"analysis_freshness_check{prefixed_suffix(artifact_prefix)}.json", freshness)

    mapping_index = poc_mapping_index(load_poc_mapping())
    payloads: dict[str, dict[str, Any]] = {}
    for level in levels:
        payload = run_aeolus_query(
            sql_map[level],
            limit=QUERY_LIMIT,
            dataset_id=dataset_id_for_data_direction(data_direction),
        )
        payloads[level] = payload
        write_json(base / f"analysis_payload_{prefix}{level}.json", payload, compact=True)

    records = label_rate_analysis.build_records(
        payloads,
        levels,
        sql_map,
        row_enricher=lambda row: build_poc_row_enrichment(row, mapping_index),
        time_range=time_range,
        data_direction=data_direction,
    )
    write_json(
        base / f"analysis_summary{prefixed_suffix(artifact_prefix)}.json",
        {
            "freshness": freshness["data"]["rows"],
            "level_counts": records[1]["readonly_execution"]["level_counts"],
            "row_count": records[1]["readonly_execution"]["row_count"],
            "source_footer": records[1]["source_footer"],
            "data_direction": data_direction,
        },
    )
    return records


def run_combined_analysis(
    *,
    args: argparse.Namespace,
    base: Path,
    stage1_path: Path,
    time_range: dict[str, Any] | None,
) -> dict[str, Any]:
    direction_records = [
        execute_direction_analysis(
            args=args,
            base=base,
            time_range=time_range,
            data_direction="manual_review_detail",
            artifact_prefix="manual_review_detail",
        ),
        execute_direction_analysis(
            args=args,
            base=base,
            time_range=time_range,
            data_direction="report_flow",
            artifact_prefix="report_flow",
        ),
    ]
    combined_records = build_combined_records(direction_records)
    write_stage1_records(stage1_path, combined_records)
    sample = combined_records[1]
    write_json(
        base / "analysis_query_plan.json",
        sample["QueryPlan"],
    )
    write_json(
        base / "analysis_summary.json",
        {
            "stage1_result": str(stage1_path),
            "direction_summaries": {
                records[1]["data_direction"]: {
                    "level_counts": records[1]["readonly_execution"]["level_counts"],
                    "row_count": records[1]["readonly_execution"]["row_count"],
                    "source_footer": records[1]["source_footer"],
                }
                for records in direction_records
            },
            "level_counts": sample["readonly_execution"]["level_counts"],
            "row_count": sample["readonly_execution"]["row_count"],
            "source_footer": sample["source_footer"],
            "data_direction": "combined",
        },
    )
    return sample


def build_combined_records(
    direction_records: list[list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    samples = [records[1] for records in direction_records]
    assert_combined_sources_ready(samples)
    levels = samples[0]["QueryPlan"]["levels"]
    time_range = samples[0]["QueryPlan"]["time_range"]
    query_plan = build_combined_query_plan(samples)
    level_results = build_combined_level_results(samples, levels)
    comprehensive_results = label_rate_analysis.build_comprehensive_results(level_results)
    level_counts = {
        level: level_results[level]["row_count"]
        for level in levels
    }
    source_footer = build_combined_source_footer(samples, query_plan)
    readonly_execution = {
        "execution_id": f"ROE-{query_plan['query_plan_id']}",
        "execution_mode": "real_readonly_query",
        "analysis_mode": "low_label_rate_grading",
        "status": "success",
        "source_tier": "governed_dataset",
        "source_name": "人审明细 + 举报流转",
        "data_freshness": source_footer["data_freshness"],
        "level_counts": level_counts,
        "row_count": len(comprehensive_results),
        "truncated": any(
            level_results[level]["truncated"] is not False
            for level in levels
        ),
        "level_results": level_results,
        "comprehensive_results": comprehensive_results,
        "evidence_fields": [
            "data_source",
            "warning_dimension",
            "severity_level",
            "mach_root_label_name",
            "strategy_id",
            "strategy_name",
            "max_data_date",
            "POC",
            "poc_name",
            "avg_review_in_cnt",
            "avg_review_done_cnt",
            "avg_label_cnt",
            "label_rate",
            "is_plus1_agreed",
            "plus1_update_date",
            "plus1_agreed_before_current_period",
            "hit_rule_ids",
            "hit_conditions",
        ],
        "metric_formula": (
            "manual_review_detail: "
            f"{label_rate_analysis.METRIC_FORMULA}; report_flow: "
            "`report_label_rate` = SUM(`[打标量_report_id]`) / "
            "SUM(`[人审完结量_report_id]`)"
        ),
        "rule_source": label_rate_analysis.RULE_SOURCE,
        "quality_checks": {
            "freshness_gate": "passed_for_both_sources",
            "denominator_not_zero": "passed",
            "field_mapping_check": "passed_for_manual_and_report_flow",
            "grain_check": "passed_combined_manual_strategy_and_report_reason",
            "risk_domain_rollup": "passed_pre_period_plus1_exclusion_by_source",
            "poc_name_mapping": "passed_name_only",
            "forbidden_source_check": "passed",
            "truncation_check": "passed",
            "grading_rule_check": "passed",
        },
        "limitations": sorted(
            {
                limitation
                for sample in samples
                for limitation in sample["readonly_execution"].get("limitations", [])
            }
        ),
    }
    query_plan["tool_calls"] = [
        tool_call
        for sample in samples
        for tool_call in sample["QueryPlan"].get("tool_calls", [])
    ]
    provenance = {
        "provenance_id": f"PROV-{query_plan['query_plan_id']}",
        "scenario_key": SCENARIO_KEY,
        "query_plan_id": query_plan["query_plan_id"],
        "execution_id": readonly_execution["execution_id"],
        "execution_mode": "real_readonly_query",
        "analysis_mode": "low_label_rate_grading",
        "source_tier": "governed_dataset",
        "source_name": readonly_execution["source_name"],
        "region": REGION,
        "app_id": f"{label_rate_analysis.APP_ID}+{label_rate_analysis.REPORT_FLOW_APP_ID}",
        "dataset_id": f"{DATASET_ID}+{label_rate_analysis.REPORT_FLOW_DATASET_ID}",
        "metric_id": query_plan["metric_id"],
        "metric_formula": readonly_execution["metric_formula"],
        "time_range": time_range,
        "dimensions": query_plan["dimensions"],
        "filters": query_plan["filters"],
        "levels": query_plan["levels"],
        "level_priority": query_plan["level_priority"],
        "required_hygiene_filters": query_plan["required_hygiene_filters"],
        "quality_checks": readonly_execution["quality_checks"],
        "tool_call_ids": query_plan["tool_calls"],
        "sql_by_level": query_plan["sql_by_level"],
        "references": {
            "metric_contract": label_rate_analysis.METRIC_CONTRACT_PATH,
            "dataset_reference": label_rate_analysis.DATASET_REFERENCE_PATH,
            "analysis_rule": label_rate_analysis.ANALYSIS_RULE_PATH,
        },
        "limitations": readonly_execution["limitations"],
        "source_footer": source_footer,
    }
    analysis_result = label_rate_analysis.build_analysis_result(
        query_plan=query_plan,
        readonly_execution=readonly_execution,
        source_footer=source_footer,
        provenance=provenance,
    )
    environment = {
        "record_type": "environment",
        "scenario_key": SCENARIO_KEY,
        "id": f"{label_rate_analysis.event_id_for_time_range(time_range)}-COMBINED",
        "period": time_range,
        "run_mode": "debug_only",
        "execution_mode": "real_readonly_query",
        "analysis_mode": "low_label_rate_grading",
        "data_direction": "combined",
        "real_query_executed": True,
        "real_notification_blocked": True,
        "online_write_blocked": True,
        "result": "pass",
    }
    sample = {
        "record_type": "sample",
        "id": f"{label_rate_analysis.event_id_for_time_range(time_range)}-COMBINED",
        "input": "人审明细与举报流转低打标率全等级结果合并",
        "run_mode": "debug_only",
        "scenario_key": SCENARIO_KEY,
        "task_type": "low_label_rate_grading",
        "analysis_mode": "low_label_rate_grading",
        "data_direction": "combined",
        "source_profile": "manual_review_detail+report_flow_review",
        "QueryPlan": query_plan,
        "tool_call_records": [
            tool_call
            for sample_item in samples
            for tool_call in sample_item.get("tool_call_records", [])
        ],
        "readonly_execution": readonly_execution,
        "analysis_result": analysis_result,
        "source_footer": source_footer,
        "provenance": provenance,
        "outputs": [
            "QueryPlan",
            "tool_call_record",
            "readonly_execution",
            "analysis_result",
            "source_footer",
            "provenance",
        ],
        "permission_checks": {
            "tool_calls": query_plan["tool_calls"],
            "read_only": True,
            "real_query_executed": True,
            "real_notification_blocked": True,
            "online_write_blocked": True,
        },
        "result": "pass",
    }
    return [environment, sample]


def assert_combined_sources_ready(samples: list[dict[str, Any]]) -> None:
    expected = {"manual_review_detail", "report_flow"}
    actual = {str(sample.get("data_direction")) for sample in samples}
    if actual != expected:
        raise RuntimeError(f"combined flow requires sources {expected}, got {actual}")
    for sample in samples:
        execution = sample.get("readonly_execution", {})
        direction = sample.get("data_direction")
        if execution.get("status") != "success":
            raise RuntimeError(
                f"combined flow source {direction} did not succeed: "
                f"{execution.get('status')}"
            )
        if execution.get("truncated") is not False:
            raise RuntimeError(f"combined flow source {direction} was truncated")


def build_combined_query_plan(samples: list[dict[str, Any]]) -> dict[str, Any]:
    manual = next(item for item in samples if item["data_direction"] == "manual_review_detail")
    report = next(item for item in samples if item["data_direction"] == "report_flow")
    time_range = manual["QueryPlan"]["time_range"]
    if time_range.get("current_start") and time_range.get("current_end"):
        start = str(time_range["current_start"]).replace("-", "")
        end = str(time_range["current_end"]).replace("-", "")
        query_plan_id = f"QP-ELR-COMBINED-LOW-LABEL-RATE-GRADING-{start}-{end}"
    else:
        query_plan_id = "QP-ELR-COMBINED-LOW-LABEL-RATE-GRADING-7D"
    return {
        "query_plan_id": query_plan_id,
        "scenario_key": SCENARIO_KEY,
        "task_type": "low_label_rate_grading",
        "analysis_mode": "low_label_rate_grading",
        "metric_id": "combined_label_rate",
        "data_direction": "combined",
        "source_profile": "manual_review_detail+report_flow_review",
        "metric_entities": (
            manual["QueryPlan"]["metric_entities"]
            + report["QueryPlan"]["metric_entities"]
        ),
        "time_range": time_range,
        "dimensions": list(label_rate_analysis.DIMENSIONS),
        "filters": sorted(
            {
                "combined_manual_review_and_report_flow",
                *manual["QueryPlan"]["filters"],
                *report["QueryPlan"]["filters"],
            }
        ),
        "levels": manual["QueryPlan"]["levels"],
        "level_priority": label_rate_analysis.LEVEL_PRIORITY,
        "required_hygiene_filters": {
            "manual_review_detail": manual["QueryPlan"]["required_hygiene_filters"],
            "report_flow": report["QueryPlan"]["required_hygiene_filters"],
        },
        "source_priority": ["governed_dataset", "curated_raw_sql"],
        "allowed_sources": (
            manual["QueryPlan"]["allowed_sources"]
            + report["QueryPlan"]["allowed_sources"]
        ),
        "forbidden_sources": sorted(
            set(manual["QueryPlan"]["forbidden_sources"])
            | set(report["QueryPlan"]["forbidden_sources"])
        ),
        "fallback_reason": "combined_manual_review_and_report_flow_grading",
        "quality_checks": sorted(
            set(manual["QueryPlan"]["quality_checks"])
            | set(report["QueryPlan"]["quality_checks"])
        ),
        "review_required": False,
        "execution_mode": "real_readonly_query",
        "sql_by_level": {
            "manual_review_detail": manual["QueryPlan"]["sql_by_level"],
            "report_flow": report["QueryPlan"]["sql_by_level"],
        },
        "tool_calls": [],
    }


def build_combined_level_results(
    samples: list[dict[str, Any]],
    levels: list[str],
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for level in levels:
        rows: list[dict[str, Any]] = []
        source_row_count = 0
        truncated = False
        columns: list[str] = []
        for sample in samples:
            level_result = sample["readonly_execution"]["level_results"][level]
            rows.extend(dict(row) for row in level_result["rows"])
            source_row_count += int(level_result.get("source_row_count", 0) or 0)
            truncated = truncated or level_result.get("truncated") is not False
            for column in level_result.get("columns", []):
                if column not in columns:
                    columns.append(column)
        deduped_rows = label_rate_analysis.dedupe_level_rows(rows, level)
        results[level] = {
            "severity_level": level,
            "severity_priority": label_rate_analysis.LEVEL_PRIORITY[level],
            "row_count": len(deduped_rows),
            "source_row_count": source_row_count,
            "truncated": truncated,
            "columns": columns,
            "rows": deduped_rows,
        }
    return results


def build_combined_source_footer(
    samples: list[dict[str, Any]],
    query_plan: dict[str, Any],
) -> dict[str, Any]:
    time_range = query_plan["time_range"]
    return {
        "source_tier": "governed_dataset",
        "metric_definition_version": "draft",
        "data_freshness": " | ".join(
            sample["source_footer"]["data_freshness"] for sample in samples
        ),
        "owner": "人审效率域数据 Owner",
        "confidence_tier": "high",
        "review_status": "real_readonly_query_executed",
        "scenario_key": SCENARIO_KEY,
        "metric_id": query_plan["metric_id"],
        "data_direction": "combined",
        "source_profile": "manual_review_detail+report_flow_review",
        "quality_checks": query_plan["quality_checks"],
        "metric_contract_ref": label_rate_analysis.METRIC_CONTRACT_PATH,
        "dataset_reference_ref": label_rate_analysis.DATASET_REFERENCE_PATH,
        "analysis_ref": label_rate_analysis.ANALYSIS_RULE_PATH,
        "query_plan_id": query_plan["query_plan_id"],
        "time_window": time_range,
        "data_lag": "uses closed values from each source for the requested period",
        "source_priority": query_plan["source_priority"],
        "actual_source": (
            f"aeolus_dataset:{DATASET_ID}; "
            f"aeolus_dataset:{label_rate_analysis.REPORT_FLOW_DATASET_ID}"
        ),
        "filters": query_plan["filters"],
        "dimensions": query_plan["dimensions"],
        "limitations": sorted(
            {
                limitation
                for sample in samples
                for limitation in sample["source_footer"].get("limitations", [])
            }
        ),
        "run_mode": "debug_only",
    }


def write_stage1_records(stage1_path: Path, records: list[dict[str, Any]]) -> None:
    stage1_path.parent.mkdir(parents=True, exist_ok=True)
    stage1_path.write_text(
        "\n".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            for record in records
        )
        + "\n",
        encoding="utf-8",
    )


def prefixed_suffix(prefix: str) -> str:
    return f"_{prefix}" if prefix else ""


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_freshness_sql(
    time_range: dict[str, Any] | None,
    *,
    data_direction: str,
) -> str:
    if data_direction == "report_flow":
        if time_range and time_range.get("current_start") and time_range.get("current_end_exclusive"):
            where = (
                f"`[进审日期]` >= '{time_range['current_start']}' "
                f"AND `[进审日期]` < '{time_range['current_end_exclusive']}'"
            )
        else:
            where = "`[进审日期]` >= today() - 3"
        return (
            "SELECT `[进审日期]` AS max_dt, count() AS c "
            f"FROM {label_rate_analysis.REPORT_FLOW_PHYSICAL_TABLE} "
            f"WHERE {where} "
            "GROUP BY max_dt ORDER BY max_dt DESC LIMIT 1"
        )
    if time_range and time_range.get("current_start") and time_range.get("current_end_exclusive"):
        where = (
            f"`[p_date]` >= '{time_range['current_start']}' "
            f"AND `[p_date]` < '{time_range['current_end_exclusive']}'"
        )
    else:
        where = "`[p_date]` >= today() - 3"
    return (
        "SELECT max(`[p_date]`) AS max_dt, count() AS c "
        "FROM olap_content_security_community.dws_sft_tcs_review_task_detail_di "
        f"WHERE {where}"
    )


def dataset_id_for_data_direction(data_direction: str) -> str:
    if data_direction == "report_flow":
        return label_rate_analysis.REPORT_FLOW_DATASET_ID
    return DATASET_ID


def run_aeolus_query(
    sql: str,
    *,
    limit: str,
    dataset_id: str = DATASET_ID,
) -> dict[str, Any]:
    command = [
        "bytedcli",
        "-j",
        "aeolus",
        "query",
        "-r",
        REGION,
        dataset_id,
        sql,
        "--limit",
        limit,
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            "Aeolus query failed:\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    payload = json.loads(completed.stdout)
    if payload.get("status") != "success":
        raise RuntimeError(f"Aeolus query returned non-success: {payload}")
    return payload


def build_poc_row_enrichment(
    row: dict[str, Any],
    mapping_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    poc = resolve_row_poc(row, mapping_index)
    poc_name = poc.get("poc_name") or "未映射"
    return {
        "poc_name": poc_name,
        "POC": poc_name,
        "poc_open_id": poc.get("poc_open_id"),
        "poc_mapping_status": poc.get("mapping_status"),
    }


def build_notification(
    *,
    args: argparse.Namespace,
    base: Path,
    stage1_path: Path,
    sheet_url: str | None,
    sent_payload: dict[str, Any] | None,
) -> Any:
    return build_label_rate_notification_artifacts(
        source_path=stage1_path,
        output_dir=base,
        top_n=args.top_n,
        sheet_url=sheet_url,
        identity=args.send_identity,
        title=build_report_title(stage1_path),
        self_send_requested=bool(args.send_chat_id),
        sent_payload=sent_payload,
        target_user_id=None,
        target_chat_id=args.send_chat_id,
        auto_import_sheet=not args.no_import_workbook,
    )


def build_report_title(stage1_path: Path) -> str:
    try:
        sample = next(
            json.loads(line)
            for line in stage1_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and json.loads(line).get("record_type") == "sample"
        )
        period = sample.get("QueryPlan", {}).get("time_range", {})
        if period.get("current_start") and period.get("current_end"):
            return f"低效打标全等级结果（{period['current_start']}~{period['current_end']}）"
    except Exception:
        pass
    return "正规流程复跑：近7天低效打标策略全等级结果"


def import_workbook(workbook_path: Path, *, name: str, base: Path) -> str:
    payload = run_lark_cli(
        [
            "lark-cli",
            "sheets",
            "+workbook-import",
            "--json",
            "--as",
            "user",
            "--file",
            relative_to_repo(workbook_path),
            "--name",
            name,
        ]
    )
    write_json(base / "sheet_import_result.json", payload)
    url = payload.get("data", {}).get("url")
    if not url:
        raise RuntimeError(f"workbook import did not return url: {payload}")
    return str(url)


def dispatch_to_lark(
    *,
    args: argparse.Namespace,
    base: Path,
    artifacts: Any,
    sheet_url: str | None,
) -> dict[str, Any]:
    checks = run_pre_send_checks(args=args, artifacts=artifacts, sheet_url=sheet_url)
    card_content = artifacts.card.card_path.read_text(encoding="utf-8")
    idempotency_key = args.idempotency_key or safe_idempotency_key(
        f"formalflow-{args.run_id}-{args.send_chat_id}"
    )
    dry_run = run_lark_cli(
        [
            "lark-cli",
            "im",
            "+messages-send",
            "--as",
            args.send_identity,
            "--chat-id",
            str(args.send_chat_id),
            "--msg-type",
            "interactive",
            "--content",
            card_content,
            "--idempotency-key",
            idempotency_key,
            "--dry-run",
        ],
        expect_json=False,
    )
    write_text(base / "lark_send_dry_run.txt", dry_run)
    sent_payload = run_lark_cli(
        [
            "lark-cli",
            "im",
            "+messages-send",
            "--json",
            "--as",
            args.send_identity,
            "--chat-id",
            str(args.send_chat_id),
            "--msg-type",
            "interactive",
            "--content",
            card_content,
            "--idempotency-key",
            idempotency_key,
        ]
    )
    write_json(base / "lark_send_result.json", sent_payload)
    if not sent_payload.get("ok"):
        raise RuntimeError(f"lark send failed: {sent_payload}")
    data = sent_payload.get("data", {})
    record = {
        "schema_version": "formal_flow_host_dispatch.v1",
        "confirmed_by_user": args.confirm_send,
        "target_chat_id": args.send_chat_id,
        "target_chat_name": TEST_GROUP_NAME
        if args.send_chat_id == TEST_GROUP_CHAT_ID
        else None,
        "identity": args.send_identity,
        "idempotency_key": idempotency_key,
        "pre_send_checks": checks,
        "dry_run_request_captured": True,
        "send_result": sent_payload,
        "message_id": data.get("message_id"),
        "chat_id": data.get("chat_id"),
        "create_time": data.get("create_time"),
        "online_write_executed": False,
    }
    write_json(base / "host_dispatch_record.json", record)
    return record


def run_pre_send_checks(
    *,
    args: argparse.Namespace,
    artifacts: Any,
    sheet_url: str | None,
) -> list[dict[str, Any]]:
    checks = [
        check("confirm_send", args.confirm_send, "real group send requires --confirm-send"),
        check(
            "target_is_test_group",
            args.send_chat_id == TEST_GROUP_CHAT_ID,
            f"target chat must be {TEST_GROUP_NAME}",
        ),
        check("sheet_url_present", bool(sheet_url), "sent card requires sheet_url"),
        check("card_hash_ok", artifacts.card.hash_check.get("ok") is True, "card hash mismatch"),
        check(
            "poc_routing_complete",
            not artifacts.notification_draft.get("poc_routing", {}).get("unmapped_labels"),
            "POC routing has unmapped labels",
        ),
    ]
    failed = [item for item in checks if item["status"] != "pass"]
    if failed:
        raise RuntimeError(f"pre-send checks failed: {failed}")
    return checks


def check(check_id: str, passed: bool, message: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "message": message,
    }


def run_lark_cli(
    command: list[str],
    *,
    expect_json: bool = True,
) -> dict[str, Any] | str:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "LARKSUITE_CLI_NO_UPDATE_NOTIFIER": "1",
            "LARKSUITE_CLI_NO_SKILLS_NOTIFIER": "1",
        },
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "lark-cli command failed:\n"
            f"args={command}\nstdout={completed.stdout}\nstderr={completed.stderr}"
        )
    if not expect_json:
        return completed.stdout
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"lark-cli returned non-json output: {completed.stdout}") from exc


def safe_idempotency_key(raw: str) -> str:
    key = re.sub(r"[^A-Za-z0-9]+", "", raw)
    return (key[-48:] or "formalflow")


def relative_to_repo(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def write_json(path: Path, value: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        if compact
        else json.dumps(value, ensure_ascii=False, indent=2)
    )
    path.write_text(text + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


if __name__ == "__main__":
    main()
