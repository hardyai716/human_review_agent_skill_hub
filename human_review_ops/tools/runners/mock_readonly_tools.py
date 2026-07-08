"""Mock readonly tool adapters for stage 1 debug runs.

These helpers do not connect to Semantic Layer, Aeolus, Hive, ClickHouse, or
any online system. They only produce auditable tool_call_record objects for the
future readonly-tool contract.
"""

from __future__ import annotations

from typing import Any


CALLER = "analyzing-ops-metrics"
EXECUTION_MODE = "mock_readonly_no_real_query"
SCENARIO_KEY = "efficiency-label-rate"

CURATED_SQL_FALLBACK_REASONS = {
    "complex_grading_rule_not_covered_by_semantic_layer",
    "dimension_reason_breakdown_requires_curated_sql",
}


def build_tool_call_records(query_plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Build mock readonly tool_call_record entries for a QueryPlan."""

    records = [
        _build_record(
            query_plan=query_plan,
            index=1,
            tool_name="mock_semantic_layer_catalog",
            command_name="lookup_metric_dimension_freshness",
            source_tier="semantic_layer",
            status="success",
            input_summary=_semantic_input_summary(query_plan),
            output_summary=(
                "Mock preflight confirmed label_rate metric metadata path and "
                "planned freshness checks. No real query executed."
            ),
        )
    ]

    dimension_discovery = query_plan.get("dimension_discovery")
    if dimension_discovery:
        requested_dimensions = ", ".join(
            dimension_discovery.get("requested_dimensions", [])
        )
        records.append(
            _build_record(
                query_plan=query_plan,
                index=len(records) + 1,
                tool_name="mock_governed_dataset_catalog",
                command_name="describe_dimension_candidates",
                source_tier="governed_dataset",
                status="degraded",
                input_summary=(
                    f"Discover unsupported dimensions: {requested_dimensions or 'unknown'}."
                ),
                output_summary=(
                    "Mock field discovery requires semantic metadata, grain impact, "
                    "and owner confirmation before the dimension can be queried. "
                    "No real query executed."
                ),
                error_reason="dimension_metadata_requires_owner_confirmation",
            )
        )

    fallback_reason = query_plan.get("fallback_reason")
    if fallback_reason in CURATED_SQL_FALLBACK_REASONS:
        records.append(
            _build_record(
                query_plan=query_plan,
                index=len(records) + 1,
                tool_name="mock_curated_sql_guard",
                command_name="compile_readonly_template_preflight",
                source_tier="curated_raw_sql",
                status="blocked",
                input_summary=(
                    f"Evaluate curated SQL fallback guard for {fallback_reason}."
                ),
                output_summary=(
                    "Mock guard identified a controlled SQL fallback path, but real "
                    "query execution is blocked until human confirmation. "
                    "No real query executed."
                ),
                error_reason="real_query_requires_human_confirmation",
            )
        )

    return records


def build_permission_checks(
    base_permission_checks: dict[str, Any],
    tool_call_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge base permission checks with mock readonly tool-call evidence."""

    permission_checks = dict(base_permission_checks)
    permission_checks.update(
        {
            "tool_calls": [
                record["tool_call_id"] for record in tool_call_records
            ],
            "tool_mode": EXECUTION_MODE,
            "tool_call_record_count": len(tool_call_records),
            "mock_or_readonly_tool_only": True,
            "real_query_blocked": True,
            "real_notification_blocked": True,
            "online_write_blocked": True,
        }
    )
    return permission_checks


def _build_record(
    *,
    query_plan: dict[str, Any],
    index: int,
    tool_name: str,
    command_name: str,
    source_tier: str,
    status: str,
    input_summary: str,
    output_summary: str,
    error_reason: str | None = None,
) -> dict[str, Any]:
    record = {
        "tool_call_id": f"TCR-{query_plan['query_plan_id']}-{index:02d}",
        "caller": CALLER,
        "tool_name": tool_name,
        "command_name": command_name,
        "permission_level": "readonly",
        "source_tier": source_tier,
        "scenario_key": SCENARIO_KEY,
        "metric_id": query_plan["metric_id"],
        "review_required": query_plan["review_required"],
        "fallback_reason": query_plan["fallback_reason"],
        "execution_mode": EXECUTION_MODE,
        "real_query_executed": False,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "status": status,
        "latency_ms": 0,
    }
    if error_reason:
        record["error_reason"] = error_reason
    return record


def _semantic_input_summary(query_plan: dict[str, Any]) -> str:
    dimensions = ", ".join(query_plan.get("dimensions", [])) or "none"
    quality_checks = ", ".join(query_plan.get("quality_checks", [])) or "none"
    return (
        f"Preflight metric={query_plan['metric_id']}, "
        f"analysis_mode={query_plan['analysis_mode']}, "
        f"dimensions={dimensions}, quality_checks={quality_checks}."
    )
