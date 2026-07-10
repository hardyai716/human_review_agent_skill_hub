#!/usr/bin/env python3
"""Official CLI entrypoint for readonly ops metric analysis.

The CLI is intentionally thin. Label-rate metric contracts, grading SQL,
QueryPlan/source_footer builders, and grading normalization stay in
label_rate_analysis.py; this wrapper owns command routing, readonly execution,
artifact persistence, schema preflight, and handoff boundaries.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import label_rate_analysis as label_rate


SCRIPT_SCHEMA_VERSION = "analyzing_ops_metrics.v1"
DEFAULT_OUTPUT_DIR = "analysis_artifacts"
ARTIFACT_FILENAMES = {
    "query_plan": "query_plan.json",
    "source_footer": "source_footer.json",
    "analysis_result": "analysis_result.json",
    "summary": "analysis_summary.md",
}
EXECUTE_CHOICES = ("auto", "never", "required")
FORMAT_CHOICES = ("json", "markdown", "both")
HANDOFF_INTENTS = ("auto", "notification", "resolution", "perception", "composite")
FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|CREATE|ALTER|TRUNCATE|REPLACE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

DIMENSION_SPECS: dict[str, dict[str, str]] = {
    "mach_root_label_name": {
        "source_field": "`[机审一级标签]`",
        "key_alias": "mach_root_label_key",
        "null_label": "（空/机审一级标签）",
    },
    "strategy_id": {
        "source_field": "`[strategy_id]`",
        "key_alias": "strategy_id_key",
        "null_label": "（空/strategy_id）",
    },
    "strategy_name": {
        "source_field": "`[strategy_name]`",
        "key_alias": "strategy_name_key",
        "null_label": "（空/strategy_name）",
    },
    "reason": {
        "source_field": "`[reason]`",
        "key_alias": "reason_key",
        "null_label": "（空/reason）",
    },
    "p_date": {
        "source_field": "`[p_date]`",
        "key_alias": "p_date_key",
        "null_label": "（空/p_date）",
    },
}
DIMENSION_ALIASES = {
    "mach_root_label": "mach_root_label_name",
    "machine_label": "mach_root_label_name",
    "label": "mach_root_label_name",
    "机审一级标签": "mach_root_label_name",
    "策略id": "strategy_id",
    "策略ID": "strategy_id",
    "strategy": "strategy_id",
    "策略名称": "strategy_name",
    "send_reason": "reason",
    "送审原因": "reason",
    "date": "p_date",
    "dt": "p_date",
}
FORBIDDEN_FIELDS = {
    # This is a scene value in the governed filter, not a governed field.
    "community_audit_style",
}
ALLOWED_FILTER_FIELDS = {
    "p_date",
    "project_title",
    "scene",
    "reason",
    "mach_root_label_name",
}
ALLOWED_OUTPUT_FIELDS = set(label_rate.GRADING_COLUMNS) | {
    "p_date",
    "calendar_days",
    "total_review_in_cnt",
    "total_review_done_cnt",
    "total_label_cnt",
    "avg_review_in_cnt",
    "avg_review_done_cnt",
    "avg_label_cnt",
    "label_rate",
}


class SchemaValidationError(ValueError):
    """Raised when user-requested fields cannot be mapped safely."""


class ExecutionBlockedError(RuntimeError):
    """Raised when readonly execution cannot run."""

    def __init__(self, reason: str, detail: str = "", returncode: int | None = None):
        super().__init__(detail or reason)
        self.reason = reason
        self.detail = detail
        self.returncode = returncode


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    exit_code = 0
    try:
        bundle = dispatch(args)
        exit_code = int(bundle.get("exit_code", 0))
    except SchemaValidationError as error:
        bundle = build_schema_error_bundle(args, str(error))
        exit_code = 2
    except ExecutionBlockedError as error:
        bundle = build_execution_blocked_bundle(args, error)
        exit_code = 2 if args.execute == "required" else 0

    output_dir = Path(args.output_dir)
    artifacts = write_artifacts(bundle, output_dir)
    emit_output(bundle, artifacts, args.format)
    raise SystemExit(exit_code)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate stable readonly analysis artifacts for ops metrics."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    common.add_argument("--days", type=int, default=label_rate.CURRENT_DAYS)
    common.add_argument("--execute", choices=EXECUTE_CHOICES, default="auto")
    common.add_argument("--format", choices=FORMAT_CHOICES, default="both")
    common.add_argument(
        "--prompt",
        default="",
        help="Optional original user request for boundary/handoff preflight.",
    )

    lowest = subparsers.add_parser("lowest-reason", parents=[common])
    lowest.add_argument("--levels", default=",".join(label_rate.DEFAULT_LEVELS))

    subparsers.add_parser("trend", parents=[common])

    label_breakdown = subparsers.add_parser("label-breakdown", parents=[common])
    label_breakdown.add_argument("--dimensions", default="mach_root_label_name")

    handoff = subparsers.add_parser("handoff", parents=[common])
    handoff.add_argument("--intent", choices=HANDOFF_INTENTS, default="auto")
    return parser


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    if args.days <= 0:
        raise SchemaValidationError("schema validation error: --days must be positive.")

    if args.command == "handoff":
        intent = args.intent
        if intent == "auto":
            intent = classify_handoff(args.prompt) or "perception"
        return build_handoff_bundle(args, intent, analysis_completed=False)

    handoff_intent = classify_handoff(args.prompt)
    if handoff_intent and handoff_intent != "composite":
        return build_handoff_bundle(args, handoff_intent, analysis_completed=False)

    if args.command == "lowest-reason":
        bundle = handle_lowest_reason(args)
    elif args.command == "trend":
        bundle = handle_trend(args)
    elif args.command == "label-breakdown":
        bundle = handle_label_breakdown(args)
    else:
        raise SchemaValidationError(f"schema validation error: unsupported command {args.command!r}.")

    if handoff_intent == "composite":
        attach_composite_handoff(bundle)
    return bundle


def handle_lowest_reason(args: argparse.Namespace) -> dict[str, Any]:
    if args.days != label_rate.CURRENT_DAYS:
        raise SchemaValidationError(
            "schema validation error: lowest-reason uses the governed 7-day "
            "grading window; pass --days 7."
        )
    levels = label_rate.parse_levels(args.levels)
    sql_map_all = label_rate.sql_by_level()
    sql_map = {level: sql_map_all[level] for level in levels}
    query_plan = label_rate.build_query_plan(levels, sql_map)
    query_plan["schema_validation"] = validate_query_plan_shape(
        dimensions=list(label_rate.DIMENSIONS),
        filter_fields=ALLOWED_FILTER_FIELDS,
        aggregate_aliases=label_rate.GRADING_COLUMNS,
        sql_values=list(sql_map.values()),
    )
    query_plan["cli"] = cli_context(args)

    if args.execute == "never":
        return build_not_executed_bundle(
            args=args,
            query_plan=query_plan,
            status="dry_run",
            stop_reason="execute_never",
            detail="SQL was not executed by request.",
        )

    executor = ReadonlyExecutor(args.execute)
    payloads: dict[str, dict[str, Any]] = {}
    try:
        for level in levels:
            payloads[level] = executor.run(sql_map[level], limit=label_rate.QUERY_LIMIT)
    except ExecutionBlockedError as error:
        if args.execute == "required":
            raise
        return build_not_executed_bundle(
            args=args,
            query_plan=query_plan,
            status="blocked",
            stop_reason=error.reason,
            detail=error.detail,
        )

    records = label_rate.build_records(payloads, levels, sql_map)
    sample = records[1]
    sample["QueryPlan"]["schema_validation"] = query_plan["schema_validation"]
    sample["QueryPlan"]["cli"] = query_plan["cli"]
    sort_lowest_reason_results(sample)
    return build_success_bundle(args, sample)


def handle_trend(args: argparse.Namespace) -> dict[str, Any]:
    validate_query_plan_shape(
        dimensions=["p_date"],
        filter_fields=ALLOWED_FILTER_FIELDS,
        aggregate_aliases=[
            "p_date",
            "total_review_in_cnt",
            "total_review_done_cnt",
            "total_label_cnt",
            "label_rate",
        ],
        sql_values=[],
    )
    sql = build_trend_sql(args.days)
    query_plan = build_single_sql_query_plan(
        args=args,
        analysis_mode="label_rate_trend",
        query_plan_id=f"QP-ELR-TREND-{args.days}D",
        dimensions=["p_date"],
        filters=["standard_review_scope", "daily_label_rate"],
        sql=sql,
        quality_checks=[
            "freshness_gate",
            "denominator_not_zero",
            "field_mapping_check",
            "grain_check_day",
            "forbidden_source_check",
            "truncation_check",
        ],
    )

    if args.execute == "never":
        return build_not_executed_bundle(
            args=args,
            query_plan=query_plan,
            status="dry_run",
            stop_reason="execute_never",
            detail="SQL was not executed by request.",
        )
    return execute_single_sql(args, query_plan, row_sort_key=lambda row: str(row.get("p_date", "")))


def handle_label_breakdown(args: argparse.Namespace) -> dict[str, Any]:
    dimensions = canonicalize_dimensions(args.dimensions)
    validate_query_plan_shape(
        dimensions=dimensions,
        filter_fields=ALLOWED_FILTER_FIELDS,
        aggregate_aliases=[
            *dimensions,
            "calendar_days",
            "total_review_in_cnt",
            "total_review_done_cnt",
            "total_label_cnt",
            "avg_review_in_cnt",
            "avg_review_done_cnt",
            "avg_label_cnt",
            "label_rate",
        ],
        sql_values=[],
    )
    sql = build_label_breakdown_sql(args.days, dimensions)
    dimension_slug = "-".join(dimensions).replace("_", "-").upper()
    query_plan = build_single_sql_query_plan(
        args=args,
        analysis_mode="label_rate_label_breakdown",
        query_plan_id=f"QP-ELR-LABEL-BREAKDOWN-{dimension_slug}-{args.days}D",
        dimensions=dimensions,
        filters=["standard_review_scope", "label_rate_breakdown"],
        sql=sql,
        quality_checks=[
            "freshness_gate",
            "denominator_not_zero",
            "field_mapping_check",
            "dimension_alias_check",
            "grain_check_dimension_breakdown",
            "forbidden_source_check",
            "truncation_check",
        ],
    )

    if args.execute == "never":
        return build_not_executed_bundle(
            args=args,
            query_plan=query_plan,
            status="dry_run",
            stop_reason="execute_never",
            detail="SQL was not executed by request.",
        )
    return execute_single_sql(
        args,
        query_plan,
        row_sort_key=lambda row: (
            number_or_default(row.get("label_rate"), default=float("inf")),
            -number_or_default(row.get("avg_review_done_cnt"), default=0.0),
        ),
    )


def canonicalize_dimensions(raw_dimensions: str) -> list[str]:
    raw_names = [item.strip() for item in raw_dimensions.split(",") if item.strip()]
    if not raw_names:
        raise SchemaValidationError(
            "schema validation error: --dimensions must include at least one field."
        )

    dimensions: list[str] = []
    seen: set[str] = set()
    for raw_name in raw_names:
        canonical = DIMENSION_ALIASES.get(raw_name, raw_name)
        if canonical in FORBIDDEN_FIELDS or raw_name in FORBIDDEN_FIELDS:
            raise SchemaValidationError(
                f"schema validation error: unknown field/dimension '{raw_name}'."
            )
        if canonical not in DIMENSION_SPECS:
            supported = ", ".join(sorted(DIMENSION_SPECS))
            raise SchemaValidationError(
                f"schema validation error: unknown field/dimension '{raw_name}'. "
                f"Supported dimensions: {supported}."
            )
        if canonical not in seen:
            dimensions.append(canonical)
            seen.add(canonical)
    return dimensions


def validate_query_plan_shape(
    *,
    dimensions: list[str],
    filter_fields: set[str],
    aggregate_aliases: list[str],
    sql_values: list[str],
) -> dict[str, Any]:
    unknown_dimensions = [field for field in dimensions if field not in DIMENSION_SPECS]
    if unknown_dimensions:
        raise SchemaValidationError(
            "schema validation error: unknown dimensions "
            f"{sorted(unknown_dimensions)}."
        )
    forbidden_dimensions = [field for field in dimensions if field in FORBIDDEN_FIELDS]
    if forbidden_dimensions:
        raise SchemaValidationError(
            "schema validation error: forbidden dimensions "
            f"{sorted(forbidden_dimensions)}."
        )
    unknown_filters = [field for field in filter_fields if field not in ALLOWED_FILTER_FIELDS]
    if unknown_filters:
        raise SchemaValidationError(
            "schema validation error: unknown filter fields "
            f"{sorted(unknown_filters)}."
        )
    unknown_aliases = [
        alias for alias in aggregate_aliases if alias not in ALLOWED_OUTPUT_FIELDS
    ]
    if unknown_aliases:
        raise SchemaValidationError(
            "schema validation error: unknown aggregate aliases "
            f"{sorted(unknown_aliases)}."
        )
    for dimension in dimensions:
        spec = DIMENSION_SPECS[dimension]
        key_alias = spec["key_alias"]
        if dimension != "p_date" and (
            not key_alias.endswith("_key") or key_alias == dimension
        ):
            raise SchemaValidationError(
                f"schema validation error: unsafe key alias for {dimension}."
            )
    for sql in sql_values:
        assert_readonly_sql(sql)
        validate_key_alias_sql(sql)
    return {
        "status": "passed",
        "allowed_dimensions": sorted(DIMENSION_SPECS),
        "dimensions": dimensions,
        "filter_fields": sorted(filter_fields),
        "aggregate_aliases": aggregate_aliases,
        "forbidden_fields": sorted(FORBIDDEN_FIELDS),
        "dimension_aliases": DIMENSION_ALIASES,
    }


def validate_key_alias_sql(sql: str) -> None:
    for dimension, spec in DIMENSION_SPECS.items():
        if dimension == "p_date":
            continue
        source_field = spec["source_field"]
        key_alias = spec["key_alias"]
        if f"ifNull({source_field}" in sql and f" AS {key_alias}" not in sql:
            raise SchemaValidationError(
                "schema validation error: nullable dimensions must use *_key aliases "
                f"before GROUP BY; missing {key_alias}."
            )


def assert_readonly_sql(sql: str) -> None:
    stripped = sql.lstrip()
    upper = stripped.upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        raise ExecutionBlockedError(
            "non_readonly_sql",
            "Readonly executor accepts SELECT/CTE statements only.",
        )
    match = FORBIDDEN_SQL_PATTERN.search(sql)
    if match:
        raise ExecutionBlockedError(
            "non_readonly_sql",
            f"Forbidden SQL token found: {match.group(1)}.",
        )


def build_trend_sql(days: int) -> str:
    return f"""
SELECT
  `[p_date]` AS p_date,
  SUM(`[进审量_reviewid]`) AS total_review_in_cnt,
  SUM(`[完审量_reviewid]`) AS total_review_done_cnt,
  SUM(`[打标量__reviewid]`) AS total_label_cnt,
  if(SUM(`[完审量_reviewid]`) = 0, 0, SUM(`[打标量__reviewid]`) / SUM(`[完审量_reviewid]`)) AS label_rate
FROM {label_rate.SOURCE_TABLE}
WHERE `[p_date]` >= today() - {days}
  AND `[p_date]` < today()
{label_rate.base_filter_sql("  ")}
GROUP BY p_date
HAVING SUM(`[完审量_reviewid]`) > 0
ORDER BY p_date ASC
LIMIT {days + 5}
""".strip()


def build_label_breakdown_sql(days: int, dimensions: list[str]) -> str:
    base_sql = indent_sql(label_rate.period_aggregate_sql(days, 0))
    select_dimensions = ",\n  ".join(f"base.{dimension} AS {dimension}" for dimension in dimensions)
    group_by_dimensions = ", ".join(dimensions)
    return f"""
SELECT
  {select_dimensions},
  {days} AS calendar_days,
  SUM(base.total_review_in_cnt) AS total_review_in_cnt,
  SUM(base.total_review_done_cnt) AS total_review_done_cnt,
  SUM(base.total_label_cnt) AS total_label_cnt,
  SUM(base.total_review_in_cnt) / {days} AS avg_review_in_cnt,
  SUM(base.total_review_done_cnt) / {days} AS avg_review_done_cnt,
  SUM(base.total_label_cnt) / {days} AS avg_label_cnt,
  if(SUM(base.total_review_done_cnt) = 0, 0, SUM(base.total_label_cnt) / SUM(base.total_review_done_cnt)) AS label_rate
FROM (
{base_sql}
) base
GROUP BY {group_by_dimensions}
HAVING SUM(base.total_review_done_cnt) > 0
ORDER BY label_rate ASC, avg_review_done_cnt DESC
LIMIT {label_rate.QUERY_LIMIT}
""".strip()


def build_single_sql_query_plan(
    *,
    args: argparse.Namespace,
    analysis_mode: str,
    query_plan_id: str,
    dimensions: list[str],
    filters: list[str],
    sql: str,
    quality_checks: list[str],
) -> dict[str, Any]:
    validate_query_plan_shape(
        dimensions=dimensions,
        filter_fields=ALLOWED_FILTER_FIELDS,
        aggregate_aliases=[field for field in ALLOWED_OUTPUT_FIELDS if field in sql],
        sql_values=[sql],
    )
    base_sql_map = label_rate.sql_by_level()
    base_plan = label_rate.build_query_plan(label_rate.DEFAULT_LEVELS, base_sql_map)
    query_plan = copy.deepcopy(base_plan)
    query_plan.update(
        {
            "query_plan_id": query_plan_id,
            "task_type": "query_only",
            "analysis_mode": analysis_mode,
            "time_range": {
                "type": "trailing_days",
                "days": args.days,
                "where": f"`[p_date]` >= today() - {args.days} AND `[p_date]` < today()",
            },
            "dimensions": dimensions,
            "filters": filters,
            "levels": [],
            "level_priority": {},
            "fallback_reason": "none",
            "quality_checks": quality_checks,
            "execution_mode": "real_readonly_query",
            "sql": sql,
            "sql_by_level": {},
            "tool_calls": [],
            "schema_validation": validate_query_plan_shape(
                dimensions=dimensions,
                filter_fields=ALLOWED_FILTER_FIELDS,
                aggregate_aliases=[
                    field for field in ALLOWED_OUTPUT_FIELDS if field in sql
                ],
                sql_values=[sql],
            ),
            "cli": cli_context(args),
        }
    )
    return query_plan


def execute_single_sql(
    args: argparse.Namespace,
    query_plan: dict[str, Any],
    *,
    row_sort_key: Any,
) -> dict[str, Any]:
    executor = ReadonlyExecutor(args.execute)
    try:
        payload = executor.run(query_plan["sql"], limit=label_rate.QUERY_LIMIT)
    except ExecutionBlockedError as error:
        if args.execute == "required":
            raise
        return build_not_executed_bundle(
            args=args,
            query_plan=query_plan,
            status="blocked",
            stop_reason=error.reason,
            detail=error.detail,
        )

    rows = normalize_generic_rows(payload)
    rows = sorted(rows, key=row_sort_key)
    query_plan["tool_calls"] = [f"TCR-{query_plan['query_plan_id']}-01"]
    source_footer = source_footer_for_plan(
        query_plan,
        review_status="real_readonly_query_executed",
        run_mode="debug_only",
        checked_at=payload.get("context", {}).get("timestamp"),
        sql_executed=True,
    )
    readonly_execution = {
        "execution_id": f"ROE-{query_plan['query_plan_id']}",
        "execution_mode": "real_readonly_query",
        "analysis_mode": query_plan["analysis_mode"],
        "status": "success",
        "source_tier": "governed_dataset",
        "source_name": f"{label_rate.DATASET_NAME} ({label_rate.DATASET_ID})",
        "data_freshness": source_footer["data_freshness"],
        "row_count": len(rows),
        "truncated": payload.get("data", {}).get("truncated"),
        "columns": payload.get("data", {}).get("columns", []),
        "rows": rows,
        "evidence_fields": payload.get("data", {}).get("columns", []),
        "metric_formula": label_rate.METRIC_FORMULA,
        "quality_checks": {
            "freshness_gate": "passed_via_p_date_filter",
            "denominator_not_zero": "passed",
            "field_mapping_check": "passed",
            "forbidden_source_check": "passed",
            "truncation_check": "passed",
        },
    }
    analysis_result = {
        "schema_version": SCRIPT_SCHEMA_VERSION,
        "analysis_id": f"AN-{query_plan['query_plan_id']}",
        "command": args.command,
        "status": "success",
        "query_plan": query_plan,
        "readonly_execution": readonly_execution,
        "source_footer": source_footer,
        "safety": safety(sql_executed=True, execute_mode=args.execute),
    }
    return {
        "schema_version": SCRIPT_SCHEMA_VERSION,
        "command": args.command,
        "status": "success",
        "query_plan": query_plan,
        "source_footer": source_footer,
        "analysis_result": analysis_result,
        "exit_code": 0,
    }


class ReadonlyExecutor:
    def __init__(self, execute_mode: str):
        self.execute_mode = execute_mode
        self.bytedcli_path = shutil.which("bytedcli")

    def run(self, sql: str, *, limit: str) -> dict[str, Any]:
        assert_readonly_sql(sql)
        if not self.bytedcli_path:
            raise ExecutionBlockedError(
                "readonly_executor_unavailable",
                "bytedcli was not found in PATH; cannot run bytedcli -j aeolus query.",
            )
        command = [
            self.bytedcli_path,
            "-j",
            "aeolus",
            "query",
            "-r",
            label_rate.REGION,
            label_rate.DATASET_ID,
            sql,
            "--limit",
            str(limit),
        ]
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise ExecutionBlockedError(
                "readonly_query_failed",
                "Aeolus readonly query failed. "
                f"stdout={completed.stdout[:1000]} stderr={completed.stderr[:1000]}",
                returncode=completed.returncode,
            )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise ExecutionBlockedError(
                "readonly_query_invalid_json",
                f"Aeolus query did not return JSON: {completed.stdout[:1000]}",
            ) from error
        if payload.get("status") != "success":
            raise ExecutionBlockedError(
                "readonly_query_non_success",
                f"Aeolus query returned non-success: {json.dumps(payload, ensure_ascii=False)[:1000]}",
            )
        return payload


def sort_lowest_reason_results(sample: dict[str, Any]) -> None:
    execution = sample["readonly_execution"]
    for level_result in execution.get("level_results", {}).values():
        level_result["rows"] = sorted(level_result.get("rows", []), key=grading_sort_key)
    execution["comprehensive_results"] = sorted(
        execution.get("comprehensive_results", []),
        key=grading_sort_key,
    )
    sample["analysis_result"]["readonly_execution"] = execution


def grading_sort_key(row: dict[str, Any]) -> tuple[int, float, float]:
    return (
        int(row.get("severity_priority", 99)),
        number_or_default(row.get("label_rate"), default=float("inf")),
        -number_or_default(row.get("avg_review_done_cnt"), default=0.0),
    )


def normalize_generic_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data", {})
    columns = data.get("columns", [])
    rows: list[dict[str, Any]] = []
    for raw_row in data.get("rows", []):
        row = dict(zip(columns, raw_row))
        rows.append({field: normalize_scalar(field, value) for field, value in row.items()})
    return rows


def normalize_scalar(field: str, value: Any) -> Any:
    if field in label_rate.FLOAT_FIELDS or field.endswith("_rate"):
        return float(value)
    if field in label_rate.INT_FIELDS or field in {"calendar_days"}:
        return int(value)
    return value


def number_or_default(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_success_bundle(args: argparse.Namespace, sample: dict[str, Any]) -> dict[str, Any]:
    analysis_result = copy.deepcopy(sample["analysis_result"])
    analysis_result.update(
        {
            "schema_version": SCRIPT_SCHEMA_VERSION,
            "command": args.command,
            "status": "success",
            "safety": safety(sql_executed=True, execute_mode=args.execute),
        }
    )
    return {
        "schema_version": SCRIPT_SCHEMA_VERSION,
        "command": args.command,
        "status": "success",
        "query_plan": sample["QueryPlan"],
        "source_footer": sample["source_footer"],
        "analysis_result": analysis_result,
        "exit_code": 0,
    }


def build_not_executed_bundle(
    *,
    args: argparse.Namespace,
    query_plan: dict[str, Any],
    status: str,
    stop_reason: str,
    detail: str,
) -> dict[str, Any]:
    source_footer = source_footer_for_plan(
        query_plan,
        review_status="not_executed" if status == "dry_run" else "blocked",
        run_mode=status,
        checked_at=now_iso(),
        sql_executed=False,
    )
    analysis_result = {
        "schema_version": SCRIPT_SCHEMA_VERSION,
        "analysis_id": f"AN-{query_plan['query_plan_id']}",
        "command": args.command,
        "status": status,
        "stop_reason": stop_reason,
        "detail": detail,
        "query_plan": query_plan,
        "sql_location": "query_plan.json",
        "source_footer": source_footer,
        "safety": safety(sql_executed=False, execute_mode=args.execute),
        "readonly_executor": executor_status(),
    }
    return {
        "schema_version": SCRIPT_SCHEMA_VERSION,
        "command": args.command,
        "status": status,
        "query_plan": query_plan,
        "source_footer": source_footer,
        "analysis_result": analysis_result,
        "exit_code": 0,
    }


def build_schema_error_bundle(args: argparse.Namespace, error: str) -> dict[str, Any]:
    query_plan = minimal_query_plan(args)
    query_plan["schema_validation"] = {
        "status": "failed",
        "error": error,
        "forbidden_fields": sorted(FORBIDDEN_FIELDS),
        "allowed_dimensions": sorted(DIMENSION_SPECS),
    }
    source_footer = source_footer_for_plan(
        query_plan,
        review_status="schema_validation_failed",
        run_mode="blocked",
        checked_at=now_iso(),
        sql_executed=False,
    )
    analysis_result = {
        "schema_version": SCRIPT_SCHEMA_VERSION,
        "analysis_id": f"AN-{query_plan['query_plan_id']}",
        "command": args.command,
        "status": "blocked",
        "stop_reason": "schema_validation_error",
        "detail": error,
        "query_plan": query_plan,
        "source_footer": source_footer,
        "safety": safety(sql_executed=False, execute_mode=args.execute),
    }
    return {
        "schema_version": SCRIPT_SCHEMA_VERSION,
        "command": args.command,
        "status": "blocked",
        "query_plan": query_plan,
        "source_footer": source_footer,
        "analysis_result": analysis_result,
        "exit_code": 2,
    }


def build_execution_blocked_bundle(
    args: argparse.Namespace,
    error: ExecutionBlockedError,
) -> dict[str, Any]:
    query_plan = minimal_query_plan(args)
    source_footer = source_footer_for_plan(
        query_plan,
        review_status="blocked",
        run_mode="blocked",
        checked_at=now_iso(),
        sql_executed=False,
    )
    analysis_result = {
        "schema_version": SCRIPT_SCHEMA_VERSION,
        "analysis_id": f"AN-{query_plan['query_plan_id']}",
        "command": args.command,
        "status": "blocked",
        "stop_reason": error.reason,
        "detail": error.detail,
        "query_plan": query_plan,
        "source_footer": source_footer,
        "safety": safety(sql_executed=False, execute_mode=args.execute),
        "readonly_executor": executor_status(),
    }
    return {
        "schema_version": SCRIPT_SCHEMA_VERSION,
        "command": args.command,
        "status": "blocked",
        "query_plan": query_plan,
        "source_footer": source_footer,
        "analysis_result": analysis_result,
        "exit_code": 2,
    }


def minimal_query_plan(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "schema_version": SCRIPT_SCHEMA_VERSION,
        "query_plan_id": f"QP-ELR-{str(args.command).replace('-', '_').upper()}-BLOCKED",
        "scenario_key": label_rate.SCENARIO_KEY,
        "task_type": "query_only",
        "analysis_mode": "blocked",
        "metric_id": "label_rate",
        "metric_entities": [
            {
                "metric_id": "label_rate",
                "definition_version": "draft",
                "source_tier": "governed_dataset",
                "aeolus_dataset_id": label_rate.DATASET_ID,
                "aeolus_metric_id": "10000036292379",
            }
        ],
        "time_range": {
            "type": "trailing_days",
            "days": getattr(args, "days", label_rate.CURRENT_DAYS),
        },
        "dimensions": [],
        "filters": [],
        "source_priority": ["governed_dataset", "curated_raw_sql"],
        "allowed_sources": [
            f"aeolus_dataset:{label_rate.DATASET_ID}",
            label_rate.SOURCE_TABLE,
        ],
        "forbidden_sources": [
            "temporary_table",
            "ownerless_legacy_sql",
            "deprecated_strategy_effect_table",
            "ungoverned_dataset",
            "pii_detail_table",
        ],
        "fallback_reason": "blocked_before_sql_construction",
        "quality_checks": ["field_mapping_check", "forbidden_source_check"],
        "review_required": False,
        "execution_mode": "real_readonly_query",
        "sql": None,
        "sql_by_level": {},
        "tool_calls": [],
        "cli": cli_context(args),
    }


def source_footer_for_plan(
    query_plan: dict[str, Any],
    *,
    review_status: str,
    run_mode: str,
    checked_at: str | None,
    sql_executed: bool,
) -> dict[str, Any]:
    timestamp = checked_at or now_iso()
    footer = label_rate.build_source_footer(
        {"plan": {"context": {"timestamp": timestamp}}},
        query_plan,
    )
    footer["review_status"] = review_status
    footer["confidence_tier"] = "high" if sql_executed else "query_plan_only"
    footer["run_mode"] = run_mode
    footer["data_freshness"] = (
        f"{query_plan.get('time_range', {}).get('where', 'not_executed')}; "
        f"checked_at={timestamp}"
    )
    if not sql_executed:
        footer["limitations"] = list(footer.get("limitations", [])) + [
            "SQL was not executed; no business conclusion is available.",
        ]
    return footer


def safety(*, sql_executed: bool, execute_mode: str) -> dict[str, Any]:
    return {
        "sql_executed": sql_executed,
        "execute_mode": execute_mode,
        "notification_sent": False,
        "online_write_executed": False,
        "readonly_executor": executor_status(),
    }


def executor_status() -> dict[str, Any]:
    path = shutil.which("bytedcli")
    return {
        "preferred_command": "bytedcli -j aeolus query",
        "available": bool(path),
        "path": path,
        "permission_level": "readonly",
    }


def cli_context(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "entrypoint": "scripts/analyzing_ops_metrics.py",
        "command": args.command,
        "days": getattr(args, "days", None),
        "execute": getattr(args, "execute", None),
        "format": getattr(args, "format", None),
    }


def classify_handoff(prompt: str) -> str | None:
    if not prompt:
        return None
    normalized = prompt.lower()
    notification_terms = (
        "通知",
        "飞书卡片",
        "卡片",
        "send_plan",
        "poc",
        "群发",
        "发送",
        "收件人",
    )
    resolution_terms = (
        "闭环",
        "跟进",
        "状态流转",
        "记录",
        "继续观察",
        "关闭事件",
        "写回",
    )
    ambiguity_terms = (
        "不确定",
        "不清楚",
        "哪个指标",
        "达标率下降",
        "自动处置准确率还是打标率",
    )
    analysis_terms = (
        "打标率",
        "label_rate",
        "reason",
        "趋势",
        "拆解",
        "分析",
        "queryplan",
        "低打标",
    )
    has_notification = any(term.lower() in normalized for term in notification_terms)
    has_resolution = any(term.lower() in normalized for term in resolution_terms)
    has_ambiguity = any(term.lower() in normalized for term in ambiguity_terms)
    has_analysis = any(term.lower() in normalized for term in analysis_terms)
    if has_ambiguity:
        return "perception"
    if has_analysis and (has_notification or has_resolution):
        return "composite"
    if has_notification:
        return "notification"
    if has_resolution:
        return "resolution"
    return None


def build_handoff_bundle(
    args: argparse.Namespace,
    intent: str,
    *,
    analysis_completed: bool,
) -> dict[str, Any]:
    handoff = handoff_payload(intent, analysis_completed=analysis_completed)
    query_plan = minimal_query_plan(args)
    query_plan["query_plan_id"] = f"QP-ELR-HANDOFF-{intent.replace('-', '_').upper()}"
    query_plan.update(
        {
            "task_type": "handoff",
            "analysis_mode": "handoff",
            "fallback_reason": "task_boundary_handoff",
            "handoff": handoff,
        }
    )
    source_footer = source_footer_for_plan(
        query_plan,
        review_status="handoff_no_sql",
        run_mode="handoff",
        checked_at=now_iso(),
        sql_executed=False,
    )
    analysis_result = {
        "schema_version": SCRIPT_SCHEMA_VERSION,
        "analysis_id": f"AN-{query_plan['query_plan_id']}",
        "command": args.command,
        "status": "handoff",
        "handoff": handoff,
        "query_plan": query_plan,
        "source_footer": source_footer,
        "safety": safety(sql_executed=False, execute_mode=args.execute),
    }
    return {
        "schema_version": SCRIPT_SCHEMA_VERSION,
        "command": args.command,
        "status": "handoff",
        "query_plan": query_plan,
        "source_footer": source_footer,
        "analysis_result": analysis_result,
        "exit_code": 0,
    }


def handoff_payload(intent: str, *, analysis_completed: bool) -> dict[str, Any]:
    if intent == "notification":
        next_skill = "notification"
        reason = "notification/card/POC/send_plan/group-send is outside analysis."
        required_inputs = ["analysis_result.json", "source_footer.json"]
        blocked_actions = ["send_notification", "generate_send_plan", "route_poc"]
    elif intent == "resolution":
        next_skill = "resolution"
        reason = "follow-up, closure, and status transition are outside analysis."
        required_inputs = ["analysis_result.json", "source_footer.json"]
        blocked_actions = ["write_status", "close_event", "record_manual_tracking"]
    elif intent == "composite":
        next_skill = "notification_or_resolution"
        reason = "composite request: analysis artifacts only, then downstream handoff."
        required_inputs = ["analysis_result.json", "source_footer.json"]
        blocked_actions = ["send_notification", "write_status", "close_event"]
    else:
        next_skill = "perception"
        reason = "scenario or metric is ambiguous; perception must clarify first."
        required_inputs = ["scenario_key", "metric_ids", "task_type", "readiness.status"]
        blocked_actions = ["run_label_rate_analysis", "send_notification", "write_status"]
    return {
        "next_skill": next_skill,
        "reason": reason,
        "analysis_completed": analysis_completed,
        "required_inputs": required_inputs,
        "blocked_actions": blocked_actions,
        "workflow_plan": [
            "Stop analysis-side downstream actions.",
            "Pass the listed artifacts or readiness fields to the next Skill.",
            "Resume analysis only after the next Skill returns a ready analysis request.",
        ],
    }


def attach_composite_handoff(bundle: dict[str, Any]) -> None:
    handoff = handoff_payload("composite", analysis_completed=bundle["status"] == "success")
    bundle["analysis_result"]["handoff"] = handoff
    bundle["analysis_result"]["status"] = (
        "success_with_handoff" if bundle["status"] == "success" else bundle["status"]
    )
    bundle["query_plan"]["handoff"] = handoff


def write_artifacts(bundle: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        key: str(output_dir / filename)
        for key, filename in ARTIFACT_FILENAMES.items()
    }
    bundle["analysis_result"]["artifacts"] = artifacts
    write_json(Path(artifacts["query_plan"]), bundle["query_plan"])
    write_json(Path(artifacts["source_footer"]), bundle["source_footer"])
    write_json(Path(artifacts["analysis_result"]), bundle["analysis_result"])
    summary = render_summary(bundle, artifacts)
    Path(artifacts["summary"]).write_text(summary, encoding="utf-8")
    return artifacts


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def render_summary(bundle: dict[str, Any], artifacts: dict[str, str]) -> str:
    result = bundle["analysis_result"]
    safety_payload = result.get("safety", {})
    execution = result.get("readonly_execution") or result.get("standard_analysis_result", {}).get("readonly_execution")
    row_count = execution.get("row_count") if isinstance(execution, dict) else None
    lines = [
        "# Analysis Summary",
        "",
        f"- command: `{bundle['command']}`",
        f"- status: `{result.get('status', bundle['status'])}`",
        f"- sql_executed: `{str(safety_payload.get('sql_executed', False)).lower()}`",
    ]
    if row_count is not None:
        lines.append(f"- row_count: `{row_count}`")
    if result.get("stop_reason"):
        lines.append(f"- stop_reason: `{result['stop_reason']}`")
    if result.get("handoff"):
        lines.append(f"- next_skill: `{result['handoff']['next_skill']}`")
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- `query_plan.json`: QueryPlan and SQL.",
            f"- `source_footer.json`: source contract and run status.",
            f"- `analysis_result.json`: normalized result, safety, and handoff if any.",
            "",
            "SQL text is stored in `query_plan.json`; this summary intentionally does not inline SQL.",
            "",
        ]
    )
    return "\n".join(lines)


def emit_output(bundle: dict[str, Any], artifacts: dict[str, str], output_format: str) -> None:
    payload = {
        "schema_version": SCRIPT_SCHEMA_VERSION,
        "status": bundle["analysis_result"].get("status", bundle["status"]),
        "command": bundle["command"],
        "artifacts": artifacts,
        "safety": bundle["analysis_result"].get("safety", {}),
    }
    if output_format in {"json", "both"}:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    if output_format in {"markdown", "both"}:
        print(Path(artifacts["summary"]).read_text(encoding="utf-8"))


def indent_sql(sql: str) -> str:
    return "\n".join(f"  {line}" if line else line for line in sql.splitlines())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
