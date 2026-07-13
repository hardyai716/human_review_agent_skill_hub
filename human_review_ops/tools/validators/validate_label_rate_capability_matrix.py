#!/usr/bin/env python3
"""Validate label-rate capability coverage across scenario and legacy Skill paths."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = ROOT / "skills"

SKILL_PATHS = {
    "perception": SKILLS_ROOT / "perception",
    "analysis": SKILLS_ROOT / "analysis",
    "notification": SKILLS_ROOT / "notification",
    "resolution": SKILLS_ROOT / "resolution",
    "efficiency-label-rate-ops": SKILLS_ROOT / "efficiency-label-rate-ops",
}

MATRIX_FILES = (
    "SKILL.md",
    "references/scenarios/efficiency-label-rate.md",
    "assets/test-prompts.json",
)

CAPABILITIES: dict[str, tuple[str, ...]] = {
    "manual_review_detail": (
        "manual_review_detail",
        "community_manual_review",
        "3888816",
    ),
    "report_flow": (
        "report_flow",
        "report_flow_review",
        "3952594",
        "enpool_reason",
    ),
    "default_three_dim_reason_not_default": (
        "mach_root_label_name × strategy_id × strategy_name",
        "reason` 不作为默认分组",
        "dimension_breakdown",
    ),
    "risk_domain_dimension": (
        "风险域维度",
        "单策略维度",
    ),
    "plus1_agreed": (
        "是否+1同意",
        "更新日期",
        "+1同意日期是否在本次统计周期前",
    ),
    "excluded_reports": (
        "综合_剔除+1同意",
        "汇总统计_剔除+1同意",
    ),
    "poc_routing": (
        "POC",
        "fallback 到 `举报` POC",
    ),
    "online_import_gate": (
        "--import-sheet",
        "auto_import_sheet=true",
        "默认关闭",
    ),
    "manual_tracking": (
        "manual tracking",
        "manual_tracking",
    ),
}

FORBIDDEN_DEFAULT_REASON_PATTERNS = (
    "标准分析粒度为 `mach_root_label_name × strategy_id × strategy_name × reason`",
    "综合清单按 `P0 > P1 > P2 > notice` 对同一 reason 取最高等级",
    "复用指标契约中的样本池过滤、四维粒度",
    "机审一级标签、策略 ID、策略名称、送审原因拆分低打标率分级",
    "机审一级标签、策略ID、策略名称、送审原因拆解，并分",
)

REASON_PATTERN = re.compile(r"送审原因|(?<!enpool_)reason")
REQUIRES_REASON_BREAKDOWN_SAMPLE = {
    "analysis",
    "perception",
    "efficiency-label-rate-ops",
}


def main() -> None:
    failures: list[str] = []
    failures.extend(validate_skill_matrix())
    failures.extend(validate_prompt_contracts())
    failures.extend(validate_poc_routing_fallback())
    if failures:
        raise SystemExit(
            "Label-rate capability matrix validation failed:\n"
            + "\n".join(f"- {failure}" for failure in failures)
        )
    print("Label-rate capability matrix OK")


def validate_skill_matrix() -> list[str]:
    failures: list[str] = []
    for skill_name, skill_root in SKILL_PATHS.items():
        text = collect_skill_text(skill_root)
        for capability, required_terms in CAPABILITIES.items():
            missing = [term for term in required_terms if term not in text]
            if missing:
                failures.append(
                    f"{skill_name} missing {capability}: {', '.join(missing)}"
                )
        for forbidden in FORBIDDEN_DEFAULT_REASON_PATTERNS:
            if forbidden in text:
                failures.append(
                    f"{skill_name} contains outdated default reason grouping: {forbidden}"
                )
    return failures


def collect_skill_text(skill_root: Path) -> str:
    parts: list[str] = []
    for relative in MATRIX_FILES:
        path = skill_root / relative
        if path.exists():
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def validate_prompt_contracts() -> list[str]:
    failures: list[str] = []
    for skill_name, skill_root in SKILL_PATHS.items():
        prompt_path = skill_root / "assets" / "test-prompts.json"
        if not prompt_path.exists():
            failures.append(f"{skill_name} missing assets/test-prompts.json")
            continue
        try:
            payload = json.loads(prompt_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{skill_name} test-prompts.json is invalid JSON: {exc}")
            continue
        cases = payload.get("cases")
        if not isinstance(cases, list):
            failures.append(f"{skill_name} test-prompts.json cases must be a list")
            continue
        failures.extend(validate_prompt_cases(skill_name, cases))
    return failures


def validate_prompt_cases(skill_name: str, cases: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    has_reason_breakdown = False
    for case in cases:
        case_id = str(case.get("id") or "<missing-id>")
        prompt = str(case.get("prompt") or "")
        coverage = {str(item) for item in case.get("coverage", [])}
        expected = case.get("expected") if isinstance(case.get("expected"), dict) else {}
        task_type = str(expected.get("task_type") or "")
        data_direction = str(expected.get("data_direction") or "")
        mentions_reason = bool(REASON_PATTERN.search(prompt))
        is_dimension_breakdown = (
            task_type == "dimension_breakdown" or "dimension_breakdown" in coverage
        )
        is_report_flow = (
            data_direction == "report_flow"
            or task_type == "report_flow_low_label_rate"
            or "report-flow" in coverage
            or "enpool_reason" in prompt
        )
        if mentions_reason and not is_dimension_breakdown and not is_report_flow:
            failures.append(
                f"{skill_name}:{case_id} mentions reason without explicit "
                "dimension_breakdown or report_flow"
            )
        if is_dimension_breakdown and mentions_reason:
            has_reason_breakdown = True
        dimensions = expected.get("dimensions")
        if task_type == "low_label_rate_grading" and isinstance(dimensions, list):
            if "reason" in dimensions:
                failures.append(
                    f"{skill_name}:{case_id} default low_label_rate_grading "
                    "must not include reason in dimensions"
                )
            expected_dims = {
                "mach_root_label_name",
                "strategy_id",
                "strategy_name",
            }
            if dimensions and set(dimensions) != expected_dims:
                failures.append(
                    f"{skill_name}:{case_id} default dimensions mismatch: {dimensions}"
                )
    if skill_name in REQUIRES_REASON_BREAKDOWN_SAMPLE and not has_reason_breakdown:
        failures.append(
            f"{skill_name} must include an explicit reason dimension_breakdown prompt"
        )
    return failures


def validate_poc_routing_fallback() -> list[str]:
    failures: list[str] = []
    script_paths = {
        "notification": SKILLS_ROOT
        / "notification"
        / "scripts"
        / "resolve_label_rate_poc_routing.py",
        "efficiency-label-rate-ops": SKILLS_ROOT
        / "efficiency-label-rate-ops"
        / "scripts"
        / "resolve_label_rate_poc_routing.py",
    }
    for name, script_path in script_paths.items():
        try:
            module = import_module_from_path(f"{name}_poc_routing", script_path)
            mapping = module.load_poc_mapping()
            index = module.poc_mapping_index(mapping)
            result = module.resolve_row_poc({"enpool_reason": "举报专项低打标"}, index)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{name} report_flow fallback raised {exc!r}")
            continue
        expected = {
            "mach_root_label_name": "举报",
            "poc_name": "韩晶晶",
            "mapping_status": "mapped_report_flow_fallback",
            "routing_fallback": "report_flow_enpool_reason_to_举报",
        }
        for field, expected_value in expected.items():
            if result.get(field) != expected_value:
                failures.append(
                    f"{name} report_flow fallback {field} mismatch: {result.get(field)!r}"
                )
    return failures


def import_module_from_path(module_name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    main()
