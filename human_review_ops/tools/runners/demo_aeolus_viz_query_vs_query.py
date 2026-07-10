#!/usr/bin/env python3
"""Demonstrate Aeolus viz-query and aeolus query for the same task.

Demo task:
  For Aeolus dataset 3888816, query yesterday's machine root label rows with
  review_done count, label count, and label rate.

Note:
  The viz-query path mirrors the front-end semantic query. The aeolus query SQL
  path demonstrates explicit SQL controls such as ORDER BY.

The script is dry-run by default. Pass --execute to run bytedcli commands.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_REGION = "cn"
DEFAULT_APP_ID = "1128"
DEFAULT_DATASET_ID = "3888816"
DEFAULT_SOURCE_TABLE = "olap_content_security_community.dws_sft_tcs_review_task_detail_di"

DIM_MACHINE_ROOT_LABEL = "机审一级标签"
DIM_PARTITION_DATE = "p_date"
METRIC_REVIEW_DONE = "完审量_reviewid"
METRIC_LABEL = "打标量__reviewid"
METRIC_LABEL_RATE = "打标率__reviewid"

# Snapshot of the required dimMet metadata for the default dataset. When
# --execute is used, the script refreshes this via `dataset-fields` first.
DEFAULT_FIELD_SNAPSHOT: dict[str, list[dict[str, Any]]] = {
    "dimensions": [
        {
            "id": 1700075931372,
            "name": DIM_PARTITION_DATE,
            "expr": "`p_date`",
            "dataTypeName": "date",
        },
        {
            "id": 1700075931425,
            "name": DIM_MACHINE_ROOT_LABEL,
            "expr": "`mach_root_label_name`",
            "dataTypeName": "string",
        },
    ],
    "metrics": [
        {
            "id": 10000006921909,
            "name": METRIC_REVIEW_DONE,
            "expr": (
                "count(\n"
                "  distinct if(\n"
                "    `is_closed`=1\n"
                "    and `review_status`='3',\n"
                "    review_id,\n"
                "    null\n"
                "  )\n"
                ")"
            ),
            "dataTypeName": "int",
        },
        {
            "id": 10000008643578,
            "name": METRIC_LABEL,
            "expr": (
                "count(\n"
                "  distinct if(\n"
                "    [review_status]=3\n"
                "    and length([verify_label_id])>6\n"
                "    and is_closed=1,\n"
                "    review_id,\n"
                "    null\n"
                "  )\n"
                ")"
            ),
            "dataTypeName": "int",
        },
        {
            "id": 10000036292379,
            "name": METRIC_LABEL_RATE,
            "expr": "[打标量__reviewid]/[完审量_reviewid]",
            "dataTypeName": "float",
        },
    ],
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default=DEFAULT_REGION)
    parser.add_argument("--app-id", default=DEFAULT_APP_ID)
    parser.add_argument("--dataset-id", default=DEFAULT_DATASET_ID)
    parser.add_argument("--source-table", default=DEFAULT_SOURCE_TABLE)
    parser.add_argument("--last-sync-days", type=int, default=1)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--timeout-ms", type=int, default=90000)
    parser.add_argument("--bytedcli", default="bytedcli")
    parser.add_argument("--site", help="Optional bytedcli --site, e.g. i18n-bd.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run bytedcli commands. Default only prints the commands.",
    )
    args = parser.parse_args()

    if args.last_sync_days <= 0:
        raise SystemExit("--last-sync-days must be positive.")
    if args.limit <= 0:
        raise SystemExit("--limit must be positive.")

    fields = (
        load_dataset_fields(args)
        if args.execute
        else DEFAULT_FIELD_SNAPSHOT
    )
    viz_command = build_viz_query_command(args, fields)
    sql = build_physical_table_sql(args)
    query_command = build_aeolus_query_command(args, sql)

    print("# Demo task")
    print(
        "Query machine root labels for yesterday, including review_done_cnt, "
        "label_cnt, and label_rate. The SQL path also demonstrates ORDER BY.\n",
        flush=True,
    )

    print("# 1) Metadata discovery used by viz-query", flush=True)
    print_command(build_dataset_fields_command(args))
    print()

    print("# 2) Dataset VizQuery path: front-end style query, no SQL", flush=True)
    print_command(viz_command)
    print()

    print("# 3) Dataset SQL path: aeolus query with explicit ORDER BY", flush=True)
    print(sql, flush=True)
    print(flush=True)
    print_command(query_command)
    print()

    if not args.execute:
        print("Dry-run only. Re-run with --execute to call bytedcli.", flush=True)
        return

    print("# Executing viz-query", flush=True)
    run(viz_command)
    print("\n# Executing aeolus query", flush=True)
    run(query_command)


def build_bytedcli_prefix(args: argparse.Namespace) -> list[str]:
    command = [args.bytedcli]
    if args.site:
        command.extend(["--site", args.site])
    command.append("--json")
    return command


def build_dataset_fields_command(args: argparse.Namespace) -> list[str]:
    return [
        *build_bytedcli_prefix(args),
        "aeolus",
        "dataset-fields",
        "-r",
        args.region,
        str(args.dataset_id),
    ]


def load_dataset_fields(args: argparse.Namespace) -> dict[str, list[dict[str, Any]]]:
    result = subprocess.run(
        build_dataset_fields_command(args),
        cwd=Path.cwd(),
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise SystemExit(
            "dataset-fields failed:\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    payload = json.loads(result.stdout)
    data = payload.get("data") or {}
    return {
        "dimensions": data.get("dimensions") or [],
        "metrics": data.get("metrics") or [],
    }


def build_viz_query_command(
    args: argparse.Namespace,
    fields: dict[str, list[dict[str, Any]]],
) -> list[str]:
    machine_root_label = find_field(fields["dimensions"], DIM_MACHINE_ROOT_LABEL)
    partition_date = find_field(fields["dimensions"], DIM_PARTITION_DATE)
    review_done = find_field(fields["metrics"], METRIC_REVIEW_DONE)
    label = find_field(fields["metrics"], METRIC_LABEL)
    label_rate = find_field(fields["metrics"], METRIC_LABEL_RATE)

    dim_met_entries = [
        dim_met(machine_root_label, role_type=0),
        dim_met(review_done, role_type=1),
        dim_met(label, role_type=1),
        dim_met(label_rate, role_type=1),
    ]
    where = {
        "dimMetId": field_id(partition_date),
        "name": partition_date["name"],
        "op": "lastSync",
        "val": [args.last_sync_days],
        "valOption": {
            "datetimeUnit": "day",
            "anchorOffset": 0,
        },
    }

    command = [
        *build_bytedcli_prefix(args),
        "aeolus",
        "viz-query",
        "-r",
        args.region,
        "--app-id",
        str(args.app_id),
        "--dataset-id",
        str(args.dataset_id),
    ]
    for entry in dim_met_entries:
        command.extend(["--dim-met", json.dumps(entry, ensure_ascii=False)])
    command.extend(
        [
            "--where",
            json.dumps(where, ensure_ascii=False),
            "--limit",
            str(args.limit),
            "--timeout-ms",
            str(args.timeout_ms),
        ]
    )
    return command


def build_aeolus_query_command(args: argparse.Namespace, sql: str) -> list[str]:
    return [
        *build_bytedcli_prefix(args),
        "aeolus",
        "query",
        "-r",
        args.region,
        str(args.dataset_id),
        sql,
        "--limit",
        str(args.limit),
    ]


def build_physical_table_sql(args: argparse.Namespace) -> str:
    days = args.last_sync_days
    return f"""
SELECT
  ifNull(`[机审一级标签]`, '（空/机审一级标签）') AS mach_root_label_name,
  `[完审量_reviewid]` AS review_done_cnt,
  `[打标量__reviewid]` AS label_cnt,
  if(
    `[完审量_reviewid]` = 0,
    0,
    `[打标量__reviewid]` / `[完审量_reviewid]`
  ) AS label_rate
FROM {args.source_table}
WHERE `[p_date]` = today() - {days}
GROUP BY mach_root_label_name
HAVING review_done_cnt > 0
ORDER BY review_done_cnt DESC
LIMIT {args.limit}
""".strip()


def find_field(fields: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for field in fields:
        if field.get("name") == name:
            return field
    available = ", ".join(str(field.get("name")) for field in fields[:20])
    raise SystemExit(f"Field not found: {name}. Available sample: {available}")


def dim_met(field: dict[str, Any], *, role_type: int) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "dimMetId": field_id(field),
        "name": field["name"],
        "expr": field["expr"],
        "roleType": role_type,
    }
    if field.get("dataTypeName"):
        entry["dataType"] = field["dataTypeName"]
    if role_type == 1 and needs_metric_aggregation(str(field.get("expr", ""))):
        entry["aggregation"] = "sum("
    return entry


def field_id(field: dict[str, Any]) -> int:
    value = field.get("id", field.get("dimMetId"))
    if value is None:
        raise SystemExit(f"Field has no id/dimMetId: {field}")
    return int(value)


def needs_metric_aggregation(expr: str) -> bool:
    lowered = expr.lower()
    aggregate_markers = ("sum(", "count(", "avg(", "min(", "max(", "[")
    return not any(marker in lowered for marker in aggregate_markers)


def print_command(command: list[str]) -> None:
    print(shlex.join(command), flush=True)


def run(command: list[str]) -> None:
    print_command(command)
    subprocess.run(command, check=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
