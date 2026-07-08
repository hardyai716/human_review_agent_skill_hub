#!/usr/bin/env python3
"""Check whether stage 1 is ready for real readonly tool integration."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_KEY = "efficiency-label-rate"
EVAL_DIR = ROOT / "evals" / SCENARIO_KEY
SCENARIO_DIR = ROOT / "references" / "scenarios" / SCENARIO_KEY
TOOL_POLICY = ROOT / "tools" / "policies" / "efficiency-label-rate.tool-policy.md"
DEFAULT_OUTPUT = EVAL_DIR / "stage_1_runs" / "20260708_real_readonly_readiness.json"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_check(
    *,
    check_id: str,
    status: str,
    summary: str,
    evidence: list[str],
    required_for_real_tool: bool = True,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": status,
        "required_for_real_tool": required_for_real_tool,
        "summary": summary,
        "evidence": evidence,
    }


def run_readiness() -> dict[str, Any]:
    metric_contract = read_text(SCENARIO_DIR / "metric_contract.md")
    dataset_reference = read_text(SCENARIO_DIR / "dataset_reference.md")
    tool_policy = read_text(TOOL_POLICY)

    checks = [
        check_local_metric_contract(metric_contract),
        check_real_semantic_metric_id(metric_contract, dataset_reference),
        check_governed_dataset_id(dataset_reference),
        check_curated_raw_source(dataset_reference),
        check_readonly_tool_binding(tool_policy),
        check_freshness_gate(dataset_reference),
        check_field_mapping(dataset_reference),
        check_sensitive_scope_guard(dataset_reference, tool_policy),
        check_specific_owner(metric_contract),
    ]
    blockers = [
        check
        for check in checks
        if check["status"] == "block" and check["required_for_real_tool"]
    ]
    warnings = [check for check in checks if check["status"] == "warn"]
    status = "ready" if not blockers else "blocked"

    return {
        "record_type": "real_readonly_readiness",
        "scenario_key": SCENARIO_KEY,
        "status": status,
        "principle": "YAGNI",
        "decision": (
            "Do not build a real readonly adapter until blockers are resolved."
            if blockers
            else "Real readonly adapter can be implemented with current assets."
        ),
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings,
        "next_required_inputs": [
            "real Semantic Layer metric ID or Aeolus dataset/report ID",
            "pre-registered readonly tool binding or CLI command",
            "specific data/metric owner or approved ownership mechanism",
        ],
    }


def check_local_metric_contract(metric_contract: str) -> dict[str, Any]:
    has_metric = "`metric_id`：`label_rate`" in metric_contract
    has_formula = "SUM(打标量) / SUM(完审量)" in metric_contract
    return build_check(
        check_id="local_metric_contract",
        status="pass" if has_metric and has_formula else "block",
        summary="Local metric contract defines label_rate and its formula.",
        evidence=[
            "`metric_id`：`label_rate`" if has_metric else "metric_id missing",
            "SUM(打标量) / SUM(完审量)" if has_formula else "formula missing",
        ],
    )


def check_real_semantic_metric_id(
    metric_contract: str,
    dataset_reference: str,
) -> dict[str, Any]:
    patterns = [
        r"semantic_metric_id\s*[:：]\s*`?[\w.\-]+`?",
        r"canonical_metric_id\s*[:：]\s*`?[\w.\-]+`?",
        r"machine_review\.label_rate",
    ]
    evidence = []
    for pattern in patterns:
        match = re.search(pattern, metric_contract) or re.search(pattern, dataset_reference)
        if match:
            evidence.append(match.group(0))
    return build_check(
        check_id="real_semantic_metric_id",
        status="pass" if evidence else "block",
        summary="Real Semantic Layer metric ID is required before replacing mock fixtures.",
        evidence=evidence or ["no concrete semantic_metric_id / canonical_metric_id found"],
    )


def check_governed_dataset_id(dataset_reference: str) -> dict[str, Any]:
    patterns = [
        r"aeolus_dataset_id\s*[:：]\s*`?[\w.\-]+`?",
        r"dataset_id\s*[:：]\s*`?[\w.\-]+`?",
        r"https?://[^\s`)]*(aeolus|data\.bytedance)[^\s`)]*",
    ]
    evidence = []
    for pattern in patterns:
        match = re.search(pattern, dataset_reference)
        if match:
            evidence.append(match.group(0))
    return build_check(
        check_id="governed_dataset_id",
        status="pass" if evidence else "block",
        summary="Governed dataset/report ID is required for a real governed source fallback.",
        evidence=evidence or ["no concrete Aeolus governed dataset/report ID found"],
    )


def check_curated_raw_source(dataset_reference: str) -> dict[str, Any]:
    table = "olap_content_security_community.dws_sft_tcs_review_task_detail_di"
    has_table = table in dataset_reference
    has_engine = "ClickHouse" in dataset_reference
    return build_check(
        check_id="curated_raw_source",
        status="pass" if has_table and has_engine else "block",
        summary="Curated raw source is documented for controlled fallback.",
        evidence=[
            table if has_table else "curated table missing",
            "ClickHouse" if has_engine else "engine missing",
        ],
    )


def check_readonly_tool_binding(tool_policy: str) -> dict[str, Any]:
    binding_patterns = [
        r"readonly_tool\s*[:：]",
        r"tool_name\s*[:：]",
        r"allowed_cli_commands",
        r"bytedcli\s+",
        r"sqless\s+",
        r"aeolus\s+",
    ]
    evidence = []
    for pattern in binding_patterns:
        match = re.search(pattern, tool_policy)
        if match:
            evidence.append(match.group(0).strip())
    return build_check(
        check_id="readonly_tool_binding",
        status="pass" if evidence else "block",
        summary="Real readonly execution requires an explicit Tool/MCP/CLI binding.",
        evidence=evidence or ["no pre-registered readonly tool or CLI binding found"],
    )


def check_freshness_gate(dataset_reference: str) -> dict[str, Any]:
    has_max_partition = "MAX(p_date)" in dataset_reference
    has_row_count = "目标分区行数" in dataset_reference
    return build_check(
        check_id="freshness_gate",
        status="pass" if has_max_partition and has_row_count else "block",
        summary="Freshness gate must be defined before real readonly execution.",
        evidence=[
            "MAX(p_date)" if has_max_partition else "MAX(p_date) missing",
            "目标分区行数" if has_row_count else "partition row count check missing",
        ],
    )


def check_field_mapping(dataset_reference: str) -> dict[str, Any]:
    required_fields = [
        "reason",
        "p_date",
        "project_title",
        "scene",
        "mach_root_label_name",
        "review_done_cnt",
        "label_cnt",
    ]
    missing = [field for field in required_fields if field not in dataset_reference]
    return build_check(
        check_id="field_mapping",
        status="pass" if not missing else "block",
        summary="Required logical field mapping must be available.",
        evidence=required_fields if not missing else [f"missing: {', '.join(missing)}"],
    )


def check_sensitive_scope_guard(
    dataset_reference: str,
    tool_policy: str,
) -> dict[str, Any]:
    guards = [
        "人员明细" in dataset_reference,
        "open_id" in dataset_reference,
        "敏感" in tool_policy,
    ]
    return build_check(
        check_id="sensitive_scope_guard",
        status="pass" if all(guards) else "block",
        summary="Sensitive detail scope must be excluded before real readonly execution.",
        evidence=[
            "person detail excluded" if guards[0] else "person detail guard missing",
            "open_id excluded" if guards[1] else "open_id guard missing",
            "sensitive detail policy present" if guards[2] else "sensitive policy missing",
        ],
    )


def check_specific_owner(metric_contract: str) -> dict[str, Any]:
    role_level = "当前先使用角色级 Owner" in metric_contract
    return build_check(
        check_id="specific_owner",
        status="warn" if role_level else "pass",
        required_for_real_tool=False,
        summary="Specific owner is not required for mock execution, but should be resolved before production use.",
        evidence=[
            "role-level Owner only" if role_level else "specific owner mechanism present",
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    payload = run_readiness()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Stage 1 real readonly readiness: {payload['status']} ({output_path})")


if __name__ == "__main__":
    main()
