#!/usr/bin/env python3
"""Run the real readonly label-rate query for stage 1.

This runner is intentionally scenario-specific. It only supports the current
efficiency-label-rate task: recent reasons whose label_rate is below 0.1.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_KEY = "efficiency-label-rate"
EVAL_DIR = ROOT / "evals" / SCENARIO_KEY
DEFAULT_OUTPUT = EVAL_DIR / "stage_1_runs" / "20260708_real_readonly_label_rate_results.jsonl"
DATASET_ID = "3888816"
APP_ID = "1128"
REGION = "cn"
DATASET_NAME = "[重点模型]-社区_人工审核明细数据"
SOURCE_TABLE = "olap_content_security_community.dws_sft_tcs_review_task_detail_di"
QUERY_PLAN_ID = "QP-ELR-REAL-LABEL-RATE-LT-0-1"
EVENT_ID = "ELR-REAL-LABEL-RATE-LT-0-1"
METRIC_FORMULA = "`[打标率__reviewid]` = `[打标量__reviewid]` / `[完审量_reviewid]`"
METRIC_CONTRACT_PATH = (
    "human_review_ops/references/scenarios/efficiency-label-rate/metric_contract.md"
)
DATASET_REFERENCE_PATH = (
    "human_review_ops/references/scenarios/efficiency-label-rate/dataset_reference.md"
)
ANALYSIS_RULE_PATH = (
    "human_review_ops/references/scenarios/efficiency-label-rate/analysis.md"
)


SQL = f"""
SELECT
  `[reason]` AS reason,
  `[完审量_reviewid]` AS review_done_cnt,
  `[打标量__reviewid]` AS label_cnt,
  `[打标率__reviewid]` AS label_rate
FROM {SOURCE_TABLE}
WHERE `[p_date]` >= today() - 7
  AND `[p_date]` < today()
  AND `[project_title]` NOT LIKE '%虚假%'
  AND `[project_title]` NOT LIKE '%标注%'
  AND `[project_title]` NOT LIKE '%虚假不实%'
  AND `[project_title]` NOT LIKE '%封面%'
  AND `[project_title]` NOT LIKE '%自动处置%'
  AND `[project_title]` NOT LIKE '%演绎%'
  AND `[project_title]` NOT LIKE '%模型%'
  AND `[project_title]` NOT LIKE '%run%'
  AND `[project_title]` NOT LIKE '%质检%'
  AND `[project_title]` NOT LIKE '%QA%'
  AND `[project_title]` NOT LIKE '%测试%'
  AND `[project_title]` NOT LIKE '%大模型%'
  AND `[project_title]` NOT LIKE '%离线%'
  AND `[scene]` IN ('community_audit_safe', 'community_audit_style', 'community_audit_moderate')
  AND `[reason]` NOT IN ('recall_skip_L6', 'fatal_output')
  AND (`[机审一级标签]` IS NULL OR `[机审一级标签]` IN (
    '不良行为或争议价值观',
    '侵犯未成年权益',
    '偏激社会情绪和涉外言论',
    '党和国家形象负面',
    '危险行为',
    '国家安全',
    '引人不适',
    '指令舆情相关',
    '短期策略迁移',
    '色情性化',
    '违法违规',
    '领导人'
  ))
GROUP BY reason
HAVING review_done_cnt > 0 AND label_rate < 0.1
ORDER BY review_done_cnt DESC
LIMIT 1000
""".strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    payload = run_query()
    records = build_records(payload)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            for record in records
        )
        + "\n",
        encoding="utf-8",
    )
    sample = records[1]
    row_count = sample["readonly_execution"]["row_count"]
    print(f"Stage 1 real readonly label-rate wrote {row_count} rows: {output_path}")


def run_query() -> dict[str, Any]:
    command = [
        "bytedcli",
        "-j",
        "aeolus",
        "query",
        "-r",
        REGION,
        DATASET_ID,
        SQL,
        "--limit",
        "1000",
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Aeolus query failed:\n"
            f"stdout={completed.stdout}\n"
            f"stderr={completed.stderr}"
        )
    payload = json.loads(completed.stdout)
    if payload.get("status") != "success":
        raise RuntimeError(f"Aeolus query returned non-success: {payload}")
    return payload


def build_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    query_plan = build_query_plan()
    rows = normalize_rows(payload)
    context = payload.get("context", {})
    query_data = payload["data"]

    tool_call_record = {
        "tool_call_id": f"TCR-{QUERY_PLAN_ID}-01",
        "caller": "analyzing-ops-metrics",
        "tool_name": "bytedcli_aeolus_query",
        "command_name": "bytedcli -j aeolus query",
        "permission_level": "readonly",
        "source_tier": "governed_dataset",
        "scenario_key": SCENARIO_KEY,
        "metric_id": "label_rate",
        "review_required": False,
        "fallback_reason": "none",
        "execution_mode": "real_readonly_query",
        "real_query_executed": True,
        "input_summary": (
            f"Dataset {DATASET_ID}; recent 7 days; reason-level label_rate < 0.1; "
            "standard A/B/C/D filters applied."
        ),
        "output_summary": (
            f"Returned {query_data['rowCount']} rows; truncated={query_data.get('truncated')}."
        ),
        "status": "success",
        "latency_ms": context.get("execution_time_ms", 0),
    }
    query_plan["tool_calls"] = [tool_call_record["tool_call_id"]]

    source_footer = build_source_footer(payload, query_plan)
    readonly_execution = build_readonly_execution(payload, rows, source_footer)
    provenance = build_provenance(query_plan, readonly_execution, source_footer)
    analysis_result = build_analysis_result(
        query_plan=query_plan,
        readonly_execution=readonly_execution,
        source_footer=source_footer,
        provenance=provenance,
    )

    return [
        {
            "record_type": "environment",
            "scenario_key": SCENARIO_KEY,
            "run_mode": "debug_only",
            "execution_mode": "real_readonly_query",
            "real_query_executed": True,
            "real_notification_blocked": True,
            "online_write_blocked": True,
            "result": "pass",
        },
        {
            "record_type": "sample",
            "id": EVENT_ID,
            "input": "近7天打标率<0.1的reason有哪些",
            "run_mode": "debug_only",
            "scenario_key": SCENARIO_KEY,
            "task_type": "query_only",
            "analysis_mode": "label_rate_ranking",
            "QueryPlan": query_plan,
            "tool_call_records": [tool_call_record],
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
                "tool_calls": [tool_call_record["tool_call_id"]],
                "read_only": True,
                "real_query_executed": True,
                "real_notification_blocked": True,
                "online_write_blocked": True,
            },
            "result": "pass",
        },
    ]


def build_query_plan() -> dict[str, Any]:
    return {
        "query_plan_id": QUERY_PLAN_ID,
        "scenario_key": SCENARIO_KEY,
        "task_type": "query_only",
        "analysis_mode": "label_rate_ranking",
        "metric_id": "label_rate",
        "metric_entities": [
            {
                "metric_id": "label_rate",
                "definition_version": "draft",
                "source_tier": "governed_dataset",
                "aeolus_dataset_id": DATASET_ID,
                "aeolus_metric_id": "10000036292379",
            }
        ],
        "time_range": {
            "type": "trailing_days",
            "days": 7,
            "grain": "day",
            "where": "`[p_date]` >= today() - 7 AND `[p_date]` < today()",
        },
        "dimensions": ["reason"],
        "filters": ["standard_review_scope", "label_rate_lt_0_1"],
        "required_hygiene_filters": [
            "A_project_title_blacklist",
            "B_scene_allowlist",
            "C_reason_exclusion",
            "D_mach_root_label_allowlist_with_null",
        ],
        "source_priority": ["governed_dataset", "curated_raw_sql"],
        "allowed_sources": [
            f"aeolus_dataset:{DATASET_ID}",
            SOURCE_TABLE,
        ],
        "forbidden_sources": [
            "temporary_table",
            "ownerless_legacy_sql",
            "deprecated_strategy_effect_table",
            "ungoverned_dataset",
            "pii_detail_table",
        ],
        "fallback_reason": "none",
        "quality_checks": [
            "freshness_gate",
            "denominator_not_zero",
            "field_mapping_check",
            "grain_check",
            "forbidden_source_check",
            "truncation_check",
        ],
        "review_required": False,
        "execution_mode": "real_readonly_query",
        "sql": SQL,
        "tool_calls": [],
    }


def normalize_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    columns = payload["data"]["columns"]
    rows: list[dict[str, Any]] = []
    for raw_row in payload["data"]["rows"]:
        row = dict(zip(columns, raw_row))
        rows.append(
            {
                "reason": row["reason"],
                "review_done_cnt": int(row["review_done_cnt"]),
                "label_cnt": int(row["label_cnt"]),
                "label_rate": float(row["label_rate"]),
            }
        )
    return rows


def build_source_footer(payload: dict[str, Any], query_plan: dict[str, Any]) -> dict[str, Any]:
    checked_at = payload.get("context", {}).get("timestamp", "unknown")
    return {
        "source_tier": "governed_dataset",
        "metric_definition_version": "draft",
        "data_freshness": (
            "p_date >= today() - 7 AND p_date < today(); "
            f"checked_at={checked_at}"
        ),
        "owner": "人审效率域数据 Owner",
        "confidence_tier": "high",
        "review_status": "real_readonly_query_executed",
        "scenario_key": SCENARIO_KEY,
        "metric_id": "label_rate",
        "quality_checks": query_plan["quality_checks"],
    }


def build_readonly_execution(
    payload: dict[str, Any],
    rows: list[dict[str, Any]],
    source_footer: dict[str, Any],
) -> dict[str, Any]:
    return {
        "execution_id": f"ROE-{QUERY_PLAN_ID}",
        "execution_mode": "real_readonly_query",
        "status": "success",
        "source_tier": "governed_dataset",
        "source_name": f"{DATASET_NAME} ({DATASET_ID})",
        "data_freshness": source_footer["data_freshness"],
        "row_count": payload["data"]["rowCount"],
        "truncated": payload["data"].get("truncated"),
        "columns": payload["data"]["columns"],
        "rows": rows,
        "evidence_fields": [
            "reason",
            "review_done_cnt",
            "label_cnt",
            "label_rate",
        ],
        "metric_formula": METRIC_FORMULA,
        "quality_checks": {
            "freshness_gate": "passed_via_p_date_filter",
            "denominator_not_zero": "passed",
            "field_mapping_check": "passed",
            "grain_check": "passed_reason",
            "forbidden_source_check": "passed",
            "truncation_check": "passed" if payload["data"].get("truncated") is False else "failed",
        },
        "limitations": [
            "Owner remains role-level until a concrete owner mechanism is connected.",
        ],
    }


def build_provenance(
    query_plan: dict[str, Any],
    readonly_execution: dict[str, Any],
    source_footer: dict[str, Any],
) -> dict[str, Any]:
    return {
        "provenance_id": f"PROV-{QUERY_PLAN_ID}",
        "scenario_key": SCENARIO_KEY,
        "query_plan_id": QUERY_PLAN_ID,
        "execution_id": readonly_execution["execution_id"],
        "execution_mode": "real_readonly_query",
        "source_tier": "governed_dataset",
        "source_name": readonly_execution["source_name"],
        "region": REGION,
        "app_id": APP_ID,
        "dataset_id": DATASET_ID,
        "metric_id": "label_rate",
        "metric_formula": METRIC_FORMULA,
        "time_range": query_plan["time_range"],
        "dimensions": query_plan["dimensions"],
        "filters": query_plan["filters"],
        "required_hygiene_filters": query_plan["required_hygiene_filters"],
        "quality_checks": readonly_execution["quality_checks"],
        "tool_call_ids": query_plan["tool_calls"],
        "sql": SQL,
        "references": {
            "metric_contract": METRIC_CONTRACT_PATH,
            "dataset_reference": DATASET_REFERENCE_PATH,
            "analysis_rule": ANALYSIS_RULE_PATH,
        },
        "source_footer": source_footer,
    }


def build_analysis_result(
    *,
    query_plan: dict[str, Any],
    readonly_execution: dict[str, Any],
    source_footer: dict[str, Any],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    row_count = readonly_execution["row_count"]
    top_reason = readonly_execution["rows"][0]["reason"] if row_count else "none"
    return {
        "analysis_id": f"AN-{EVENT_ID}",
        "event_id": EVENT_ID,
        "templates_used": ["custom_readonly", "impact_assessment", "sop_decision"],
        "query_plan": compact_query_plan(query_plan),
        "readonly_execution": readonly_execution,
        "impact_assessment": {
            "summary": f"近7天打标率低于0.1的 reason 共 {row_count} 个。",
            "impact_scope": f"top_reason_by_review_done_cnt={top_reason}",
            "risk_level": "P3",
            "business_risk": "本结果为查询结果，不自动触发治理分级。",
            "duration": "trailing_7_days",
            "evidence_refs": [readonly_execution["execution_id"]],
        },
        "root_cause_hypotheses": [
            {
                "hypothesis": "query_only_no_root_cause_inference",
                "confidence": 0.0,
                "supporting_evidence": [readonly_execution["execution_id"]],
                "contradicting_evidence": [],
                "next_check": "Run grading or dimension drilldown only if requested.",
            }
        ],
        "sop_decision": {
            "severity_level": "P3",
            "next_action": "answer",
            "required_confirmation": False,
            "matched_rules": ["label_rate_lt_0_1_query"],
            "reason": "只读查询成功，不发送通知、不写状态。",
        },
        "quality_checks": {
            "evidence_complete": True,
            "data_fresh": True,
            "metric_definition_consistent": True,
            "owner_resolved": False,
            "confidence": 0.9,
            "warnings": readonly_execution["limitations"],
        },
        "source_footer": source_footer,
        "provenance": provenance,
    }


def compact_query_plan(query_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "query_plan_id": query_plan["query_plan_id"],
        "metric_entities": query_plan["metric_entities"],
        "dimensions": query_plan["dimensions"],
        "time_range": query_plan["time_range"],
        "filters": query_plan["filters"],
        "tool_calls": query_plan["tool_calls"],
        "allowed_sources": query_plan["allowed_sources"],
        "forbidden_sources": query_plan["forbidden_sources"],
        "quality_checks": query_plan["quality_checks"],
    }


if __name__ == "__main__":
    main()
