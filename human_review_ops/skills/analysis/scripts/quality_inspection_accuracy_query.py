#!/usr/bin/env python3
"""Build quality-inspection accuracy SQL from Aeolus semantic fields.

This script is intentionally side-effect free by default. The emitted SQL keeps
dataset fields such as `[审核准确率]` in Aeolus semantic syntax and must be run
through `bytedcli -j aeolus query -r cn 3533559 "<SQL>" --limit 100`, which
compiles those fields to the backing ClickHouse expressions.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from textwrap import dedent


SCHEMA_VERSION = "quality_inspection_accuracy_query.v2"
SCENARIO_KEY = "quality-inspection-accuracy"
DATASET_ID = "3533559"
APP_ID = "555137"
REGION = "cn"
REPORT_ID = "13057301"
BACKING_TABLE = (
    "`aeolus_data_db_cqc_core_202509`.`aeolus_data_table_8_2974603_migrate_v2_prod`"
)
DEFAULT_LAG_DAYS = 3

# `aeolus query` compiles bracketed dataset fields by dataset id. The FROM table
# still uses the backing table because logical table `3533559` is not accepted.
def semantic_field(field_name: str) -> str:
    return f"`[{field_name}]`"


FIELD_DATE = semantic_field("p_date")
DIM_QUEUE_SUMMARY = semantic_field("队列分类汇总")
DIM_QUEUE_GROUP = semantic_field("队列分类 (上游+群组)")
FILTER_QUALITY_MODE = semantic_field("质检模式")
FILTER_VIDEO_SCOPE = semantic_field("视频质量_队列范围")
FILTER_EXCLUDE_FLAG = semantic_field("抽检质量-是否剔除")
METRIC_AUDIT_ACCURACY = semantic_field("审核准确率")
METRIC_SAMPLE_CNT = semantic_field("抽检量")
METRIC_ERROR_CNT = semantic_field("审核错误量")
METRIC_PASS_ACCURACY = semantic_field("通过准确率")
METRIC_PASS_SAMPLE_CNT = semantic_field("通过抽检量")
METRIC_LABEL_ACCURACY = semantic_field("打标准确率")
METRIC_LABEL_SAMPLE_CNT = semantic_field("打标抽检量")


def default_current_date() -> str:
    return (date.today() - timedelta(days=DEFAULT_LAG_DAYS)).isoformat()


def previous_date(current_date: str) -> str:
    return (date.fromisoformat(current_date) - timedelta(days=1)).isoformat()


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def build_sql(current_date: str, previous_date_value: str) -> str:
    current_lit = sql_literal(current_date)
    previous_lit = sql_literal(previous_date_value)

    return dedent(
        f"""
        WITH agg AS (
          SELECT
            if({FIELD_DATE} = {current_lit}, 'cur', 'prev') AS period,
            {DIM_QUEUE_SUMMARY} AS queue_category_summary,
            {DIM_QUEUE_GROUP} AS queue_category_group,
            {METRIC_AUDIT_ACCURACY} AS audit_accuracy,
            {METRIC_SAMPLE_CNT} / count(DISTINCT {FIELD_DATE}) AS avg_daily_sample_cnt,
            {METRIC_ERROR_CNT} / count(DISTINCT {FIELD_DATE}) AS avg_daily_error_cnt,
            {METRIC_PASS_ACCURACY} AS pass_accuracy,
            {METRIC_PASS_SAMPLE_CNT} / count(DISTINCT {FIELD_DATE}) AS avg_daily_pass_sample_cnt,
            {METRIC_LABEL_ACCURACY} AS label_accuracy,
            {METRIC_LABEL_SAMPLE_CNT} / count(DISTINCT {FIELD_DATE}) AS avg_daily_label_sample_cnt
          FROM {BACKING_TABLE}
          WHERE {FIELD_DATE} IN ({current_lit}, {previous_lit})
            AND {FILTER_QUALITY_MODE} = '抽检模式'
            AND {FILTER_VIDEO_SCOPE} IN ('【大盘】安全', '【大盘】画风')
            AND {FILTER_EXCLUDE_FLAG} NOT LIKE '%剔除%'
          GROUP BY period, queue_category_summary, queue_category_group
        )
        SELECT
          cur.queue_category_summary,
          cur.queue_category_group,
          cur.audit_accuracy,
          cur.audit_accuracy - prev.audit_accuracy AS audit_accuracy_diff_1d,
          cur.avg_daily_sample_cnt,
          cur.avg_daily_error_cnt,
          cur.pass_accuracy,
          cur.avg_daily_pass_sample_cnt,
          cur.label_accuracy,
          cur.avg_daily_label_sample_cnt
        FROM agg AS cur
        ANY LEFT JOIN agg AS prev
          ON cur.queue_category_summary = prev.queue_category_summary
         AND cur.queue_category_group = prev.queue_category_group
         AND prev.period = 'prev'
        WHERE cur.period = 'cur'
        ORDER BY cur.queue_category_summary, cur.queue_category_group
        LIMIT 100
        SETTINGS
          enable_case_when_prop = 1,
          enable_sharding_optimize = 1,
          max_plan_segment_num = 50,
          enable_optimizer = 1,
          enable_split_countd_to_state_merge = 1
        """
    ).strip()


def build_payload(current_date: str, previous_date_value: str) -> dict[str, object]:
    sql = build_sql(current_date, previous_date_value)
    return {
        "schema_version": SCHEMA_VERSION,
        "scenario_key": SCENARIO_KEY,
        "dataset": {
            "region": REGION,
            "app_id": APP_ID,
            "dataset_id": DATASET_ID,
            "report_id": REPORT_ID,
            "backing_table": BACKING_TABLE.replace("`", ""),
        },
        "filters": {
            "p_date": current_date,
            "previous_date": previous_date_value,
            "quality_mode": "抽检模式",
            "video_quality_scope": ["【大盘】安全", "【大盘】画风"],
            "exclude_flag": "NOT LIKE '%剔除%'",
        },
        "sql": sql,
        "execution_hint": (
            "bytedcli -j aeolus query -r cn 3533559 \"<semantic SQL>\" --limit 100"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build quality-inspection accuracy SQL from Aeolus semantic fields."
    )
    parser.add_argument("--current-date", default=default_current_date())
    parser.add_argument("--previous-date")
    parser.add_argument("--format", choices=("json", "sql"), default="json")
    args = parser.parse_args()

    current = args.current_date
    previous = args.previous_date or previous_date(current)
    payload = build_payload(current, previous)
    if args.format == "sql":
        print(payload["sql"])
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
