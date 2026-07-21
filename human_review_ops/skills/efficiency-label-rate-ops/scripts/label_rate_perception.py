#!/usr/bin/env python3
"""Dry-run perception for the efficiency label-rate scenario."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "label_rate_perception.v1"
SCENARIO_KEY = "efficiency-label-rate"
DEFAULT_RUN_MODE = "debug_only"
ALLOWED_RUN_MODES = {
    "debug_only",
    "query_only",
    "notification_only",
    "resolution_only",
    "partial_workflow",
}
ANALYSIS_TASK_TYPES = {
    "label_rate_trend",
    "label_rate_ranking",
    "low_label_rate_grading",
    "report_flow_low_label_rate",
    "dimension_breakdown",
    "auto_disposal_accuracy_trend",
    "auto_disposal_root_label_accuracy_breakdown",
    "auto_disposal_alert_grading",
    "quality_inspection_trend",
    "quality_market_no_report_accuracy",
}
REFERENCE_FILES = [
    "references/common.md",
    "references/scenario-index.md",
    "references/scenario_contract.md",
]
SCENARIO_REFERENCE_FILES = ["references/scenario_contract.md"]
REFERENCE_BY_SCENARIO = {
    "efficiency-label-rate": "references/scenario_contract.md",
    "efficiency-auto-disposal-accuracy": (
        "references/scenarios/efficiency-auto-disposal-accuracy.md"
    ),
    "quality-inspection-accuracy": (
        "references/scenarios/quality-inspection-accuracy.md"
    ),
}
LABEL_RATE_KEYWORDS = (
    "打标率",
    "低效打标",
    "打标全等级",
    "低效打标全等级",
    "低打标",
    "高打标",
    "打标量",
    "完审量",
    "进审量",
    "送审" + "原因",
    "reason",
    "labelrate",
    "label_rate",
    "汇总统计_剔除+1同意",
    "汇总统计剔除+1同意",
)
REPORT_FLOW_KEYWORDS = (
    "举报",
    "举报场景",
    "举报流转",
    "enpool_reason",
    "report_id",
    "一轮队列",
    "终轮队列",
    "举报流转任务明细数据集",
    "3952594",
)
REPORT_FLOW_METRIC_KEYWORDS = {
    "report_review_in_cnt": ("进审量_report_id",),
    "report_review_done_cnt": ("人审完结量_report_id", "日均人审完结量", "人审完结量"),
    "report_label_cnt": ("打标量_report_id", "日均打标量"),
}
AMBIGUOUS_LABEL_RATE_KEYWORDS = (
    "达标率",
)
HUMAN_REVIEW_CONTEXT_KEYWORDS = (
    "人审",
    "审核",
    "完审",
    "进审",
    "策略",
    "reason",
    "送审",
    "低效",
    "分级",
    "p0",
    "p1",
    "p2",
    "notice",
)
GRADING_KEYWORDS = (
    "低打标",
    "低效",
    "全等级",
    "分级",
    "p0",
    "p1",
    "p2",
    "notice",
)
SEVERITY_KEYWORDS = ("p0", "p1", "p2", "notice")
GRADING_CONTEXT_KEYWORDS = ("策略", "reason", "低效", "分级", "打标")
TREND_KEYWORDS = ("趋势", "环比", "同比", "波动", "变化")
RANKING_KEYWORDS = ("最高", "最低", "top", "排序", "排行", "排名", "高打标")
NOTIFICATION_KEYWORDS = (
    "通知",
    "卡片",
    "飞书",
    "群发",
    "发送",
    "推送",
    "测试群",
    "触达",
    "poc",
    "sendplan",
)
RESOLUTION_KEYWORDS = ("闭环", "跟进", "状态", "已处理", "关闭", "tracking", "工单")
TIME_WINDOW_PATTERNS = (
    r"近\s*\d+\s*(天|日|周|月)",
    r"近\s*[一二三四五六七八九十两]+\s*(天|日|周|月)",
    r"最近\s*\d+\s*(天|日|周|月)",
    r"最近\s*[一二三四五六七八九十两]+\s*(天|日|周|月)",
    r"\d{4}[-/]\d{1,2}[-/]\d{1,2}\s*(至|到|~|—)\s*\d{4}[-/]\d{1,2}[-/]\d{1,2}",
    r"(今天|昨天|前天|本周|上周|本月|上月|近一周|近两周|近一个月)",
)
ADJACENT_SCENARIOS = {
    "efficiency-auto-disposal-accuracy": ("自动处置准确率", "自动处置"),
    "quality-inspection-accuracy": ("质检准确率", "质量准确率"),
    "baseline-incident": ("底线事故", "事故数"),
}
ROUTE_ADJACENT_SCENARIOS = False
DIMENSION_KEYWORDS = {
    "enpool_reason": ("enpool_reason", "举报入池原因", "入池原因"),
    "mach_root_label_name": ("机审一级标签", "机审标签", "一级标签", "mach_root_label"),
    "strategy_id": ("策略id", "策略ID", "规则id", "规则ID", "strategy_id", "strategyid"),
    "strategy_name": ("策略名称", "规则名称", "strategy_name", "strategyname"),
    "reason": ("送审" + "原因", "reason"),
    "scene": ("审核场景", "scene"),
    "project_title": ("项目标题", "项目", "project_title", "projecttitle"),
}
UNKNOWN_DIMENSION_HINTS = ("业务线", "达人", "作者", "审核员", "国家", "地区")
METRIC_KEYWORDS = {
    "review_in_cnt": ("进审量", "进入人审"),
    "review_done_cnt": ("完审量", "完成人审"),
    "label_cnt": ("打标量",),
}
RISK_PATTERNS = {
    "sql_execution_requested": (
        r"直接.*(跑|执行|查).*(sql|查询|查库)",
        r"(跑|执行).*(线上)?\s*sql",
        r"真实查询",
    ),
    "real_group_send_requested": (
        r"群发",
        r"真实发送",
        r"发到.*群",
        r"发送.*群",
        r"推送.*群",
        r"飞书.*群",
        r"测试群",
    ),
    "auto_group_invite_requested": (r"拉.*入群", r"自动拉人"),
    "online_write_requested": (r"写.*线上.*状态", r"状态写成", r"关闭.*事件"),
    "sensitive_detail_export_requested": (r"手机号", r"open_id", r"审核员.*明细", r"个人明细"),
    "sample_pool_override_requested": (r"覆盖.*样本池", r"不要.*默认样本池"),
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dry-run label-rate scenario perception and readiness routing."
    )
    parser.add_argument("--request", help="Raw user request. stdin is used if omitted.")
    parser.add_argument("--scenario-hint")
    parser.add_argument("--run-mode", default=DEFAULT_RUN_MODE)
    parser.add_argument("--time-window")
    parser.add_argument("--metric-hint", action="append", default=[])
    parser.add_argument("--dimension-hint", action="append", default=[])
    parser.add_argument("--source-ref", action="append", default=[])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Accepted for explicitness; this script never performs side effects.",
    )
    args = parser.parse_args()

    request = args.request
    if not request and not sys.stdin.isatty():
        request = sys.stdin.read().strip()
    if not request:
        parser.error("--request is required unless stdin provides text")

    payload = detect_label_rate_perception(
        raw_user_request=request,
        scenario_hint=args.scenario_hint,
        run_mode=args.run_mode,
        time_window=args.time_window,
        metric_hint=args.metric_hint,
        dimension_hint=args.dimension_hint,
        source_refs=args.source_ref,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def detect_label_rate_perception(
    *,
    raw_user_request: str,
    scenario_hint: str | None = None,
    run_mode: str | None = None,
    time_window: str | None = None,
    metric_hint: list[str] | None = None,
    dimension_hint: list[str] | None = None,
    source_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Return structured dry-run perception output for label-rate work."""
    request = raw_user_request.strip()
    combined_text = " ".join(
        [
            request,
            scenario_hint or "",
            " ".join(metric_hint or []),
            " ".join(dimension_hint or []),
        ]
    )
    canonical = canonicalize(combined_text)
    request_canonical = canonicalize(request)
    scenario_matches = detect_scenario_matches(request_canonical)
    hint_scenario = normalize_scenario_hint(scenario_hint)
    if hint_scenario:
        scenario_matches = dedupe([*scenario_matches, hint_scenario])
    scenario_key = scenario_matches[0] if len(scenario_matches) == 1 else "unknown"
    scenario_candidates = detect_scenario_candidates(
        request_canonical,
        scenario_matches,
    )
    task_type = detect_task_type(canonical, scenario_key)
    metrics = detect_metric_ids(canonical, scenario_key)
    dimensions = detect_dimensions(combined_text, dimension_hint or [])
    unsupported_dimensions = detect_unsupported_dimensions(
        canonical,
        dimensions,
        dimension_hint or [],
    )
    resolved_time_window = time_window or extract_time_window(request)
    source_refs = source_refs or []
    data_direction = detect_data_direction(canonical)
    source_profile = source_profile_for(data_direction, scenario_key)
    missing_refs = missing_reference_files(scenario_key)
    risk_flags = detect_risk_flags(request)
    invalid_source_refs = validate_source_refs(source_refs, scenario_key)
    resolved_run_mode = run_mode or DEFAULT_RUN_MODE
    readiness = build_readiness(
        raw_user_request=request,
        scenario_key=scenario_key,
        task_type=task_type,
        time_window=resolved_time_window,
        source_refs=source_refs,
        scenario_ambiguous=len(scenario_matches) > 1,
        unsupported_dimensions=unsupported_dimensions,
        missing_refs=missing_refs,
        risk_flags=risk_flags,
        run_mode=resolved_run_mode,
        invalid_source_refs=invalid_source_refs,
    )

    handoff = build_handoff(task_type, scenario_key, readiness)
    return {
        "schema_version": SCHEMA_VERSION,
        "dry_run": True,
        "scenario_key": scenario_key,
        "scenario_candidates": scenario_candidates,
        "task_type": task_type,
        "run_mode": resolved_run_mode,
        "data_direction": data_direction,
        "source_profile": source_profile,
        "date_field": "进审日期" if data_direction == "report_flow" else "p_date",
        "metric_ids": metrics,
        "time_window": resolved_time_window,
        "dimensions": dimensions,
        "unsupported_dimensions": unsupported_dimensions,
        "retrieval_policy": build_retrieval_policy(),
        "readiness": readiness,
        "handoff": handoff,
        "workflow_plan": build_workflow_plan(
            scenario_key=scenario_key,
            scenario_candidates=scenario_candidates,
            task_type=task_type,
            readiness=readiness,
            handoff=handoff,
            risk_flags=risk_flags,
        ),
        "reference_loading": {
            "skill_reference_root": "references",
            "required_refs": reference_files_for(scenario_key),
            "missing_refs": missing_refs,
        },
        "safety": {
            "sql_executed": False,
            "notification_sent": False,
            "online_write_executed": False,
            "sensitive_detail_exported": False,
        },
    }


def canonicalize(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def contains_any(canonical: str, keywords: tuple[str, ...]) -> bool:
    return any(canonicalize(keyword) in canonical for keyword in keywords)


def detect_data_direction(canonical: str) -> str:
    if contains_any(canonical, REPORT_FLOW_KEYWORDS):
        return "report_flow"
    return "manual_review_detail"


def source_profile_for(data_direction: str, scenario_key: str = SCENARIO_KEY) -> str:
    if scenario_key == "efficiency-auto-disposal-accuracy":
        return "auto_disposal_accuracy"
    if scenario_key == "quality-inspection-accuracy":
        return "quality_inspection_accuracy"
    if data_direction == "report_flow":
        return "report_flow_review"
    return "community_manual_review"


def detect_scenario_matches(canonical: str) -> list[str]:
    matches: list[str] = []
    if contains_any(canonical, LABEL_RATE_KEYWORDS) or looks_like_label_rate_grading(
        canonical
    ):
        matches.append(SCENARIO_KEY)
    if ROUTE_ADJACENT_SCENARIOS:
        for scenario, keywords in ADJACENT_SCENARIOS.items():
            if contains_any(canonical, keywords):
                matches.append(scenario)
    return dedupe(matches)


def normalize_scenario_hint(scenario_hint: str | None) -> str | None:
    hint = canonicalize(scenario_hint or "")
    aliases = {
        SCENARIO_KEY: SCENARIO_KEY,
        "labelrate": SCENARIO_KEY,
        "label_rate": SCENARIO_KEY,
        "打标率": SCENARIO_KEY,
        "efficiency-auto-disposal-accuracy": "efficiency-auto-disposal-accuracy",
        "自动处置准确率": "efficiency-auto-disposal-accuracy",
        "quality-inspection-accuracy": "quality-inspection-accuracy",
        "质检准确率": "quality-inspection-accuracy",
    }
    return aliases.get(hint)


def detect_scenario_candidates(
    canonical: str,
    scenario_matches: list[str],
) -> list[dict[str, Any]]:
    if scenario_matches:
        return [
            {
                "scenario_key": scenario,
                "confidence": "high",
                "reason": "matched_scenario_keywords",
                "needs_confirmation": len(scenario_matches) > 1,
            }
            for scenario in scenario_matches
        ]
    if contains_any(canonical, AMBIGUOUS_LABEL_RATE_KEYWORDS):
        confidence = (
            "medium"
            if contains_any(canonical, HUMAN_REVIEW_CONTEXT_KEYWORDS)
            else "low"
        )
        return [
            {
                "scenario_key": SCENARIO_KEY,
                "confidence": confidence,
                "reason": "possible_mistyped_label_rate_keyword:达标率",
                "needs_confirmation": True,
                "clarification_question": "这里的“达标率”是否指人审效率指标“打标率”？",
            }
        ]
    return []


def looks_like_label_rate_grading(canonical: str) -> bool:
    return contains_any(canonical, SEVERITY_KEYWORDS) and contains_any(
        canonical,
        GRADING_CONTEXT_KEYWORDS,
    )


def is_low_label_rate_request(canonical: str) -> bool:
    return contains_any(canonical, GRADING_KEYWORDS) or any(
        token in canonical
        for token in (
            "打标率<10",
            "打标率小于10",
            "打标率低于10",
            "打标率不足10",
            "打标率<0.1",
            "打标率小于0.1",
            "打标率低于0.1",
        )
    )


def detect_task_type(canonical: str, scenario_key: str) -> str:
    if scenario_key == "unknown":
        return "unknown"
    intent_text = strip_negated_actions(canonical)
    if contains_any(intent_text, NOTIFICATION_KEYWORDS):
        return "notification_request"
    if contains_any(intent_text, RESOLUTION_KEYWORDS):
        return "resolution_tracking"

    if scenario_key == "efficiency-auto-disposal-accuracy":
        if contains_any(canonical, SEVERITY_KEYWORDS) or "预警" in canonical:
            return "auto_disposal_alert_grading"
        if any(token in canonical for token in ("一级风险标签", "一级标签", "三级标签", "拆解")):
            return "auto_disposal_root_label_accuracy_breakdown"
        return "auto_disposal_accuracy_trend"

    if scenario_key == "quality-inspection-accuracy":
        if any(token in canonical for token in ("队列", "大盘", "不含举报", "分类汇总")):
            return "quality_market_no_report_accuracy"
        return "quality_inspection_trend"

    data_direction = detect_data_direction(canonical)
    explicit_breakdown = (
        "reason" in detect_dimensions(canonical, [])
        and any(token in canonical for token in ("拆解", "拆分", "明细和汇总", "不要作为默认"))
    )
    if explicit_breakdown:
        return "dimension_breakdown"
    if data_direction == "report_flow" and is_low_label_rate_request(canonical):
        return "report_flow_low_label_rate"
    if is_low_label_rate_request(canonical):
        return "low_label_rate_grading"
    if contains_any(canonical, TREND_KEYWORDS):
        return "label_rate_trend"
    if contains_any(canonical, RANKING_KEYWORDS):
        return "label_rate_ranking"
    if detect_dimensions(canonical, []):
        return "dimension_breakdown"
    if "打标率" in canonical or "labelrate" in canonical or "label_rate" in canonical:
        return "label_rate_trend"
    return "unknown"


def strip_negated_actions(canonical: str) -> str:
    return re.sub(
        r"(不要|无需|不需要|别)(通知|发送|推送|群发|飞书卡片|卡片|关闭|写状态)",
        "",
        canonical,
    )


def detect_metric_ids(canonical: str, scenario_key: str) -> list[str]:
    if scenario_key == "efficiency-auto-disposal-accuracy":
        return ["auto_disposal_accuracy"]
    if scenario_key == "quality-inspection-accuracy":
        metrics = ["quality_inspection_accuracy"]
        if "通过" in canonical:
            metrics.append("pass_accuracy")
        if "打标" in canonical:
            metrics.append("label_accuracy")
        return metrics
    if scenario_key != SCENARIO_KEY:
        return []
    if detect_data_direction(canonical) == "report_flow":
        metric_ids = ["report_label_rate"]
        for metric_id, keywords in REPORT_FLOW_METRIC_KEYWORDS.items():
            if contains_any(canonical, keywords):
                metric_ids.append(metric_id)
        return dedupe(metric_ids)
    metric_ids = ["label_rate"]
    for metric_id, keywords in METRIC_KEYWORDS.items():
        if contains_any(canonical, keywords):
            metric_ids.append(metric_id)
    return dedupe(metric_ids)


def detect_dimensions(text: str, dimension_hints: list[str]) -> list[str]:
    combined = canonicalize(" ".join([text, " ".join(dimension_hints)]))
    dimensions: list[str] = []
    for dimension, keywords in DIMENSION_KEYWORDS.items():
        if contains_any(combined, keywords):
            dimensions.append(dimension)
    if detect_data_direction(combined) == "report_flow" and "enpool_reason" in dimensions:
        # `enpool_reason` contains the substring `reason`; keep the governed
        #举报方向维度，避免误落到人工审核明细的 reason。
        dimensions = [dimension for dimension in dimensions if dimension != "reason"]
    return dedupe(dimensions)


def detect_unsupported_dimensions(
    canonical: str,
    _known_dimensions: list[str],
    dimension_hints: list[str],
) -> list[str]:
    unsupported = [
        keyword
        for keyword in UNKNOWN_DIMENSION_HINTS
        if canonicalize(keyword) in canonical
    ]
    for hint in dimension_hints:
        hint_canonical = canonicalize(hint)
        if not hint_canonical:
            continue
        if not any(
            contains_any(hint_canonical, keywords)
            for keywords in DIMENSION_KEYWORDS.values()
        ):
            unsupported.append(hint)
    return dedupe(unsupported)


def extract_time_window(text: str) -> str | None:
    for pattern in TIME_WINDOW_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def detect_risk_flags(text: str) -> list[str]:
    flags: list[str] = []
    for flag, patterns in RISK_PATTERNS.items():
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            flags.append(flag)
    return flags


def reference_files_for(scenario_key: str) -> list[str]:
    scenario_ref = REFERENCE_BY_SCENARIO.get(scenario_key)
    return [
        "references/common.md",
        "references/scenario-index.md",
        *([scenario_ref] if scenario_ref else []),
    ]


def missing_reference_files(scenario_key: str) -> list[str]:
    skill_root = Path(__file__).resolve().parents[1]
    return [
        ref for ref in reference_files_for(scenario_key) if not (skill_root / ref).exists()
    ]


def validate_source_refs(source_refs: list[str], scenario_key: str) -> list[str]:
    invalid: list[str] = []
    for source_ref in source_refs:
        path = Path(source_ref).expanduser()
        if not path.is_file():
            invalid.append(source_ref)
            continue
        try:
            text = path.read_text(encoding="utf-8")
            if path.suffix == ".jsonl":
                values = [
                    json.loads(line) for line in text.splitlines() if line.strip()
                ]
                payload = next(
                    (
                        value
                        for value in values
                        if isinstance(value, dict)
                        and value.get("record_type") == "sample"
                    ),
                    None,
                )
            else:
                payload = json.loads(text)
        except (OSError, json.JSONDecodeError):
            invalid.append(source_ref)
            continue
        if not isinstance(payload, dict) or payload.get("scenario_key") != scenario_key:
            invalid.append(source_ref)
    return invalid


def build_readiness(
    *,
    raw_user_request: str,
    scenario_key: str,
    task_type: str,
    time_window: str | None,
    source_refs: list[str],
    scenario_ambiguous: bool,
    unsupported_dimensions: list[str],
    missing_refs: list[str],
    risk_flags: list[str],
    run_mode: str,
    invalid_source_refs: list[str],
) -> dict[str, Any]:
    reasons: list[str] = []
    clarification_fields: list[str] = []
    human_confirmation_required = False

    if not raw_user_request.strip():
        reasons.append("missing_raw_user_request")
        clarification_fields.append("raw_user_request")
    if scenario_ambiguous:
        reasons.append("scenario_not_unique")
        clarification_fields.append("scenario_key")
    if scenario_key == "unknown":
        reasons.append("scenario_not_recognized")
        clarification_fields.extend(["scenario_key", "metric_ids"])
    if scenario_key != "unknown" and task_type == "unknown":
        reasons.append("task_type_not_clear")
        clarification_fields.append("task_type")
    if run_mode not in ALLOWED_RUN_MODES:
        reasons.append(f"invalid_run_mode:{run_mode}")
        clarification_fields.append("run_mode")
    if risk_flags:
        reasons.extend(risk_flags)
        human_confirmation_required = True
    if missing_refs:
        reasons.append("missing_reference_files")
    if unsupported_dimensions:
        reasons.append("unsupported_dimension_requires_field_discovery")
        clarification_fields.append("dimension_hint")
        human_confirmation_required = True
    if invalid_source_refs:
        reasons.append("invalid_source_refs")
        clarification_fields.append("source_refs")

    if task_type in ANALYSIS_TASK_TYPES and not time_window:
        reasons.append("missing_time_window")
        clarification_fields.append("time_window")
    if task_type == "notification_request" and not source_refs:
        reasons.append("missing_analysis_artifact")
        clarification_fields.append("source_refs")
    if task_type == "resolution_tracking" and not source_refs:
        reasons.append("missing_notification_or_tracking_source")
        clarification_fields.append("source_refs")

    blocking_reasons = dedupe(reasons)
    clarification_fields = dedupe(clarification_fields)
    if risk_flags or missing_refs or scenario_ambiguous or invalid_source_refs:
        status = "blocked"
    elif blocking_reasons:
        status = "needs_clarification"
    else:
        status = "ready"

    return {
        "status": status,
        "blocking_reasons": blocking_reasons,
        "clarification_fields": clarification_fields,
        "human_confirmation_required": human_confirmation_required,
        "checks": build_readiness_checks(
            scenario_key=scenario_key,
            task_type=task_type,
            time_window=time_window,
            blocking_reasons=blocking_reasons,
            risk_flags=risk_flags,
        ),
    }


def build_readiness_checks(
    *,
    scenario_key: str,
    task_type: str,
    time_window: str | None,
    blocking_reasons: list[str],
    risk_flags: list[str],
) -> list[dict[str, Any]]:
    return [
        {
            "check_id": "scenario_detection",
            "status": "pass" if scenario_key in REFERENCE_BY_SCENARIO else "block",
            "value": scenario_key,
        },
        {
            "check_id": "task_type_detection",
            "status": "pass" if task_type != "unknown" else "warn",
            "value": task_type,
        },
        {
            "check_id": "time_window",
            "status": "pass" if time_window else "warn",
            "value": time_window,
        },
        {
            "check_id": "side_effect_guard",
            "status": "block" if risk_flags else "pass",
            "value": risk_flags,
        },
        {
            "check_id": "clarification_gate",
            "status": "pass" if not blocking_reasons else "warn",
            "value": blocking_reasons,
        },
    ]


def build_retrieval_policy() -> dict[str, Any]:
    return {
        "reference_first": True,
        "semantic_layer_first": True,
        "allowed_source_tiers": [
            "semantic_layer",
            "governed_dataset",
            "curated_raw_sql",
        ],
        "allow_readonly_query_after_query_plan": True,
        "requires_query_plan_before_readonly_query": True,
        "forbid_sql_execution_in_perception": True,
        "forbid_notification": True,
        "forbid_online_write": True,
        "forbid_sensitive_detail_export": True,
    }


def build_handoff(
    task_type: str,
    scenario_key: str,
    readiness: dict[str, Any],
) -> dict[str, Any]:
    candidate_next_skill = None
    if scenario_key in REFERENCE_BY_SCENARIO:
        if task_type in ANALYSIS_TASK_TYPES:
            candidate_next_skill = "analysis"
        elif task_type == "notification_request":
            candidate_next_skill = "notification"
        elif task_type == "resolution_tracking":
            candidate_next_skill = "resolution"

    return {
        "next_skill": candidate_next_skill
        if readiness.get("status") == "ready"
        else None,
        "candidate_next_skill": candidate_next_skill,
        "required_refs": (
            [REFERENCE_BY_SCENARIO[scenario_key]]
            if scenario_key in REFERENCE_BY_SCENARIO
            else []
        ),
        "required_inputs": readiness.get("clarification_fields", []),
        "blocked_until": readiness.get("blocking_reasons", []),
    }


def build_workflow_plan(
    *,
    scenario_key: str,
    scenario_candidates: list[dict[str, Any]],
    task_type: str,
    readiness: dict[str, Any],
    handoff: dict[str, Any],
    risk_flags: list[str],
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = [
        {
            "step": 1,
            "skill": "perception",
            "task_type": "intent_routing",
            "status": "completed",
        }
    ]
    prerequisites: list[dict[str, Any]] = []
    requires_host_send_confirmation = "real_group_send_requested" in risk_flags

    if scenario_key == "unknown":
        return {
            "status": "blocked",
            "intent_type": "unknown",
            "steps": steps,
            "prerequisites": [],
            "requires_host_send_confirmation": requires_host_send_confirmation,
            "candidate_scenarios": scenario_candidates,
            "next_action": "clarify_scenario_or_metric",
        }

    if task_type == "notification_request":
        missing_analysis = "missing_analysis_artifact" in readiness.get(
            "blocking_reasons", []
        )
        if missing_analysis:
            prerequisites.append(
                {
                    "skill": "analysis",
                    "task_type": "low_label_rate_grading",
                    "required_before": "notification",
                    "reason": "notification_requires_analysis_artifact",
                }
            )
            steps.append(
                {
                    "step": 2,
                    "skill": "analysis",
                    "task_type": "low_label_rate_grading",
                    "status": "required",
                }
            )
        steps.append(
            {
                "step": 3 if missing_analysis else 2,
                "skill": "notification",
                "task_type": "notification_request",
                "status": (
                    "blocked_until_analysis_artifact"
                    if missing_analysis
                    else "ready"
                ),
            }
        )
        return {
            "status": "blocked"
            if readiness.get("status") == "blocked"
            else (
                "ready_with_prerequisite"
                if missing_analysis
                else readiness.get("status")
            ),
            "intent_type": (
                "analysis_then_notification" if missing_analysis else "notification"
            ),
            "steps": steps,
            "prerequisites": prerequisites,
            "requires_host_send_confirmation": True,
            "candidate_scenarios": scenario_candidates,
            "next_action": (
                "run_analysis_prerequisite"
                if missing_analysis
                else handoff.get("next_skill") or "clarify_inputs"
            ),
        }

    if task_type == "resolution_tracking":
        steps.append(
            {
                "step": 2,
                "skill": "resolution",
                "task_type": task_type,
                "status": "ready"
                if handoff.get("next_skill") == "resolution"
                else "blocked",
            }
        )
        return {
            "status": readiness.get("status"),
            "intent_type": "resolution",
            "steps": steps,
            "prerequisites": [],
            "requires_host_send_confirmation": requires_host_send_confirmation,
            "candidate_scenarios": scenario_candidates,
            "next_action": handoff.get("next_skill") or "clarify_inputs",
        }

    if task_type in ANALYSIS_TASK_TYPES:
        steps.append(
            {
                "step": 2,
                "skill": "analysis",
                "task_type": task_type,
                "status": "ready"
                if handoff.get("next_skill") == "analysis"
                else "blocked",
            }
        )
        return {
            "status": readiness.get("status"),
            "intent_type": "analysis",
            "steps": steps,
            "prerequisites": [],
            "requires_host_send_confirmation": requires_host_send_confirmation,
            "candidate_scenarios": scenario_candidates,
            "next_action": handoff.get("next_skill") or "clarify_inputs",
        }

    return {
        "status": readiness.get("status"),
        "intent_type": "unknown",
        "steps": steps,
        "prerequisites": [],
        "requires_host_send_confirmation": requires_host_send_confirmation,
        "candidate_scenarios": scenario_candidates,
        "next_action": "clarify_task_type",
    }


def dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


if __name__ == "__main__":
    main()
