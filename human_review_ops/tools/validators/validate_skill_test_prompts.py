#!/usr/bin/env python3
"""Execute every published Skill test-prompt contract without external effects."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"
SKILL_NAMES = (
    "perception",
    "analysis",
    "notification",
    "resolution",
    "efficiency-label-rate-ops",
)


def import_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_cases(skill_name: str) -> list[dict[str, Any]]:
    path = SKILLS / skill_name / "assets" / "test-prompts.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise AssertionError(f"{skill_name}: cases must be a list")
    return cases


def expected_selected(case: dict[str, Any]) -> bool:
    return bool(case.get("expected", {}).get("trigger"))


def validate_perception_cases(skill_name: str, cases: list[dict[str, Any]]) -> None:
    module = import_module(
        f"{skill_name}_perception",
        SKILLS / skill_name / "scripts" / "label_rate_perception.py",
    )
    for case in cases:
        expected = case["expected"]
        payload = module.detect_label_rate_perception(
            raw_user_request=case["prompt"]
        )
        selected = payload["scenario_key"] != "unknown"
        if selected != expected_selected(case):
            raise AssertionError(
                f"{skill_name}:{case['id']} trigger mismatch: {payload['scenario_key']}"
            )
        for field in ("scenario_key", "task_type", "run_mode", "data_direction"):
            if field in expected and payload.get(field) != expected[field]:
                raise AssertionError(
                    f"{skill_name}:{case['id']} {field} mismatch: "
                    f"{payload.get(field)!r} != {expected[field]!r}"
                )
        if "dimensions" in expected and set(payload.get("dimensions", [])) != set(
            expected["dimensions"]
        ):
            raise AssertionError(f"{skill_name}:{case['id']} dimensions mismatch")
        if expected.get("action_allowed") is False:
            if payload["readiness"]["status"] != "blocked":
                raise AssertionError(
                    f"{skill_name}:{case['id']} prohibited action must be blocked"
                )
            if payload["handoff"]["next_skill"] is not None:
                raise AssertionError(
                    f"{skill_name}:{case['id']} blocked action must not hand off"
                )


def validate_analysis_cases(cases: list[dict[str, Any]]) -> None:
    scripts = SKILLS / "analysis" / "scripts"
    analysis = import_module("prompt_analysis", scripts / "label_rate_analysis.py")
    quality = import_module(
        "prompt_quality",
        scripts / "quality_inspection_accuracy_query.py",
    )
    for case in cases:
        if not expected_selected(case):
            continue
        expected = case["expected"]
        scenario = expected.get("scenario_key")
        if scenario == "efficiency-label-rate":
            if expected.get("task_type") == "dimension_breakdown":
                reference = (
                    SKILLS
                    / "analysis"
                    / "references"
                    / "scenarios"
                    / "efficiency-label-rate.md"
                ).read_text(encoding="utf-8")
                for dimension in expected.get("dimensions", []):
                    if dimension not in reference:
                        raise AssertionError(
                            f"analysis:{case['id']} unsupported dimension {dimension}"
                        )
            else:
                time_range = analysis.build_grading_time_range(
                    start_date="2026-07-08",
                    end_date="2026-07-14",
                )
                query_plan = analysis.build_query_plan(
                    list(analysis.DEFAULT_LEVELS),
                    analysis.sql_by_level(time_range),
                    time_range=time_range,
                )
                if query_plan["task_type"] != expected.get("task_type"):
                    raise AssertionError(
                        f"analysis:{case['id']} task_type mismatch"
                    )
        elif scenario == "efficiency-auto-disposal-accuracy":
            reference = (
                SKILLS
                / "analysis"
                / "references"
                / "scenarios"
                / "efficiency-auto-disposal-accuracy.md"
            ).read_text(encoding="utf-8")
            if "sum(rlabel_acc_weight_rate) / count" in reference:
                raise AssertionError("analysis:auto-disposal still averages daily rates")
            if "nullIf(sum(`[一级标签准确量]`)" not in reference:
                raise AssertionError("analysis:auto-disposal weighted formula missing")
        elif scenario == "quality-inspection-accuracy":
            sql = quality.build_sql("2026-07-08", "2026-07-07")
            if "queue_category_summary_key" not in sql:
                raise AssertionError("analysis:quality stable key missing")


def validate_notification_cases(cases: list[dict[str, Any]]) -> None:
    scripts = SKILLS / "notification" / "scripts"
    module = import_module(
        "prompt_notification",
        scripts / "resolve_label_rate_poc_routing.py",
    )
    mapping = module.poc_mapping_index(module.load_poc_mapping())
    for case in cases:
        expected = case["expected"]
        if not expected_selected(case):
            continue
        if "report-flow" in case.get("coverage", []):
            result = module.resolve_row_poc(
                {
                    "data_direction": "report_flow",
                    "enpool_reason": "举报专项低打标",
                },
                mapping,
            )
            expected_routing = expected.get("poc_routing", {})
            if result.get("poc_name") != expected_routing.get("poc_name"):
                raise AssertionError(f"notification:{case['id']} POC fallback mismatch")
        if expected.get("action_allowed") is False:
            if "group_send_blocked=true" not in expected.get("rationale", ""):
                raise AssertionError(
                    f"notification:{case['id']} missing blocked action evidence"
                )


def validate_resolution_cases(cases: list[dict[str, Any]]) -> None:
    module = import_module(
        "prompt_resolution",
        SKILLS / "resolution" / "scripts" / "build_label_rate_manual_tracking.py",
    )
    draft = {
        "scenario_key": "efficiency-label-rate",
        "level_counts": {"notice": 1},
        "data_link": {"csv_files": {}},
        "poc_routing": {"routing_rules": {}},
        "methodology": {"source_footer": {"query_plan_id": "smoke"}},
    }
    send_plan = {
        "scenario_key": "efficiency-label-rate",
        "requires_confirmation": True,
        "group_send_blocked": True,
        "sent": False,
        "real_group_send_executed": False,
        "online_write_executed": False,
        "content_source": {},
    }
    for case in cases:
        expected = case["expected"]
        if not expected_selected(case):
            continue
        closed_requested = case["id"] == "resolution-should-trigger-label-rate-manual-tracking"
        result = module.build_manual_tracking(
            notification_draft=draft,
            send_plan=send_plan,
            state_machine_ref="references/scenario_contract.md#state_machine.md",
            manual_action="处理动作" if closed_requested else None,
            resolution_note="处理结论" if closed_requested else None,
            evidence_refs=["evidence://smoke"] if closed_requested else [],
            operator_confirmation=closed_requested,
        )
        expected_closure = expected.get("closure_check", {}).get("can_close")
        if expected_closure is not None and (
            result["closure_check"]["can_close"] is not expected_closure
        ):
            raise AssertionError(f"resolution:{case['id']} closure mismatch")
        if expected.get("action_allowed") is False:
            if result["safety"]["online_state_write_allowed"] is not False:
                raise AssertionError(
                    f"resolution:{case['id']} online write must stay blocked"
                )


def main() -> None:
    all_cases = {name: load_cases(name) for name in SKILL_NAMES}
    validate_perception_cases("perception", all_cases["perception"])
    validate_analysis_cases(all_cases["analysis"])
    validate_notification_cases(all_cases["notification"])
    validate_resolution_cases(all_cases["resolution"])
    validate_perception_cases(
        "efficiency-label-rate-ops",
        all_cases["efficiency-label-rate-ops"],
    )
    count = sum(len(cases) for cases in all_cases.values())
    print(f"Skill test prompts OK: skills={len(all_cases)}, cases={count}")


if __name__ == "__main__":
    main()
