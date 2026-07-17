#!/usr/bin/env python3
"""Render a label-rate grading report as a Lark Card 2.0 payload."""

from __future__ import annotations

from typing import Any

from card_hash import compute_hits_hash, embed_hash_in_card


LEVELS = ["P0", "P1", "P2", "notice"]
LEVEL_COLORS = {"P0": "red", "P1": "orange", "P2": "yellow", "notice": "blue"}


def int_text(value: Any) -> str:
    try:
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return str(value)


def pct_text(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return str(value)


def text_tag(text: str, color: str = "blue") -> dict[str, Any]:
    return {
        "tag": "text_tag",
        "text": {"tag": "plain_text", "content": text},
        "color": color,
    }


def card_base(title: str, subtitle: str) -> dict[str, Any]:
    return {
        "schema": "2.0",
        "config": {
            "update_multi": True,
            "width_mode": "fill",
            "summary": {"content": title},
            "style": {
                "text_size": {
                    "title": {
                        "default": "heading-2",
                        "pc": "heading-2",
                        "mobile": "heading-3",
                    },
                    "body": {
                        "default": "normal",
                        "pc": "normal",
                        "mobile": "normal",
                    },
                    "caption": {
                        "default": "notation",
                        "pc": "notation",
                        "mobile": "notation",
                    },
                }
            },
        },
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "subtitle": {"tag": "plain_text", "content": subtitle},
            "template": "blue",
            "icon": {"tag": "standard_icon", "token": "chart_colorful"},
            "text_tag_list": [
                text_tag("全等级"),
                text_tag("P0/P1/P2/notice", "wathet"),
            ],
        },
        "body": {
            "direction": "vertical",
            "padding": "12px 12px 20px 12px",
            "vertical_spacing": "12px",
            "elements": [],
        },
    }


def metric_column(value: Any, label: str, *, color: str = "blue") -> dict[str, Any]:
    return {
        "tag": "column",
        "width": "weighted",
        "weight": 1,
        "background_style": f"{color}-50",
        "padding": "12px",
        "vertical_spacing": "2px",
        "elements": [
            {
                "tag": "markdown",
                "content": f"## <font color='{color}'>{int_text(value)}</font>",
                "text_align": "center",
            },
            {
                "tag": "markdown",
                "content": f"<font color='grey'>{label}</font>",
                "text_align": "center",
                "text_size": "notation",
            },
        ],
    }


def metrics_block(level_counts: dict[str, int]) -> dict[str, Any]:
    return {
        "tag": "column_set",
        "flex_mode": "flow",
        "horizontal_spacing": "12px",
        "columns": [
            metric_column(level_counts.get(level, 0), level, color=LEVEL_COLORS[level])
            for level in LEVELS
        ],
    }


def table_columns() -> list[dict[str, Any]]:
    return [
        {"name": "rank", "display_name": "排名", "data_type": "number", "width": "80px"},
        {
            "name": "level",
            "display_name": "最高等级",
            "data_type": "options",
            "width": "100px",
        },
        {
            "name": "warning_dimension",
            "display_name": "预警维度",
            "data_type": "text",
            "width": "110px",
        },
        {"name": "poc_name", "display_name": "POC", "data_type": "text", "width": "100px"},
        {
            "name": "mach_root_label_name",
            "display_name": "机审一级标签",
            "data_type": "text",
            "width": "140px",
        },
        {
            "name": "strategy_id",
            "display_name": "策略ID",
            "data_type": "text",
            "width": "120px",
        },
        {
            "name": "strategy_name",
            "display_name": "策略名称",
            "data_type": "text",
            "width": "200px",
        },
        {
            "name": "max_data_date",
            "display_name": "最大有数日期",
            "data_type": "text",
            "width": "120px",
        },
        {
            "name": "avg_in",
            "display_name": "日均进审量",
            "data_type": "number",
            "width": "110px",
            "format": {"precision": 0, "separator": True},
        },
        {
            "name": "avg_done",
            "display_name": "日均完审量",
            "data_type": "number",
            "width": "110px",
            "format": {"precision": 0, "separator": True},
        },
        {
            "name": "avg_labeled",
            "display_name": "日均打标量",
            "data_type": "number",
            "width": "110px",
            "format": {"precision": 0, "separator": True},
        },
        {
            "name": "label_rate",
            "display_name": "打标率",
            "data_type": "text",
            "width": "90px",
        },
        {
            "name": "hit_reason",
            "display_name": "命中原因",
            "data_type": "text",
            "width": "260px",
        },
    ]


def summary_table_columns() -> list[dict[str, Any]]:
    return [
        {
            "name": "mach_root_label_name",
            "display_name": "机审一级标签",
            "data_type": "text",
            "width": "150px",
        },
        {"name": "POC", "display_name": "POC", "data_type": "text", "width": "100px"},
        {
            "name": "low_efficiency_strategy_count",
            "display_name": "低效策略数",
            "data_type": "number",
            "width": "110px",
            "format": {"precision": 0, "separator": True},
        },
        {
            "name": "avg_review_in_cnt",
            "display_name": "日均进审量",
            "data_type": "number",
            "width": "120px",
            "format": {"precision": 0, "separator": True},
        },
        {
            "name": "avg_review_done_cnt",
            "display_name": "日均完审量",
            "data_type": "number",
            "width": "120px",
            "format": {"precision": 0, "separator": True},
        },
        {
            "name": "avg_label_cnt",
            "display_name": "日均打标量",
            "data_type": "number",
            "width": "120px",
            "format": {"precision": 0, "separator": True},
        },
        {
            "name": "label_rate",
            "display_name": "打标率",
            "data_type": "text",
            "width": "90px",
        },
    ]


def table_block(top_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "tag": "table",
        "page_size": min(10, max(1, len(top_rows))),
        "row_height": "auto",
        "freeze_first_column": True,
        "header_style": {
            "background_style": "grey",
            "bold": True,
            "text_size": "notation",
            "lines": 1,
        },
        "columns": table_columns(),
        "rows": top_rows,
    }


def summary_table_block(summary_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "tag": "table",
        "page_size": min(20, max(1, len(summary_rows))),
        "row_height": "auto",
        "freeze_first_column": True,
        "header_style": {
            "background_style": "grey",
            "bold": True,
            "text_size": "notation",
            "lines": 1,
        },
        "columns": summary_table_columns(),
        "rows": summary_rows,
    }


def summary_title_block(row_count: int) -> dict[str, Any]:
    return {
        "tag": "markdown",
        "content": f"### 汇总统计（机审一级标签 × POC，共 {row_count} 行）",
    }


def level_title_block(level: str, row_count: int) -> dict[str, Any]:
    display = "Notice" if level == "notice" else level
    return {
        "tag": "markdown",
        "content": (
            f"### <font color='{LEVEL_COLORS[level]}'>{display} 等级 Top {row_count}</font>"
        ),
    }


def level_table_blocks(
    level_top_rows: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for level in LEVELS:
        rows = level_top_rows.get(level, [])
        blocks.append(level_title_block(level, len(rows)))
        blocks.append(table_block(rows))
    return blocks


def sheet_button(sheet_url: str | None) -> dict[str, Any] | None:
    if not sheet_url:
        return None
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": "查看完整飞书电子表格"},
        "type": "primary_filled",
        "width": "fill",
        "behaviors": [
            {
                "type": "open_url",
                "default_url": sheet_url,
                "pc_url": sheet_url,
                "ios_url": sheet_url,
                "android_url": sheet_url,
            }
        ],
    }


def methodology_panel(summary: dict[str, Any]) -> dict[str, Any]:
    lines = [
        f"- 数据集：`{summary.get('dataset_id')}` / `{summary.get('region')}`",
        f"- 当前窗口：`{summary.get('period', {}).get('current_start')}` ~ `{summary.get('period', {}).get('current_end')}`",
        "- 默认分级粒度：`机审一级标签 × 策略ID × 策略名称`",
        "- `reason`：默认仅用于样本清洗；仅在用户明确要求维度拆解时作为分组字段",
        "- 打标率：`SUM(打标量) / SUM(完审量)`",
        f"- fallback_reason：`{summary.get('fallback_reason')}`",
        f"- source：`{summary.get('source_stage_1_result')}`",
    ]
    return {
        "tag": "collapsible_panel",
        "expanded": False,
        "background_color": "grey-50",
        "padding": "10px",
        "header": {"title": {"tag": "plain_text", "content": "口径与溯源"}},
        "elements": [
            {
                "tag": "markdown",
                "content": "\n".join(lines),
                "text_size": "notation",
            }
        ],
    }


def render_grading_card(
    *,
    summary: dict[str, Any],
    summary_rows: list[dict[str, Any]],
    level_top_rows: dict[str, list[dict[str, Any]]],
    sheet_url: str | None,
    title: str | None = None,
    hash_input: list[dict[str, Any]] | None = None,
    template_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report_title = title or "近7天低效打标策略全等级结果"
    period = summary.get("period", {})
    subtitle = (
        f"默认三维分级 · {period.get('current_start')} ~ {period.get('current_end')}"
    )
    card = card_base(report_title, subtitle)
    elements = card["body"]["elements"]
    elements.extend(
        [
            metrics_block(summary.get("level_counts", {})),
        ]
    )
    elements.append(summary_title_block(len(summary_rows)))
    elements.append(summary_table_block(summary_rows))
    elements.extend(level_table_blocks(level_top_rows))
    button = sheet_button(sheet_url)
    if button:
        elements.append(button)
    elements.append(methodology_panel(summary))

    flattened_rows = list(summary_rows) + [
        row for level in LEVELS for row in level_top_rows.get(level, [])
    ]
    hits_hash = compute_hits_hash(hash_input or flattened_rows)
    return embed_hash_in_card(
        card,
        hits_hash,
        metadata={
            "hash_input": hash_input or flattened_rows,
            "template_name": (template_contract or {}).get("template_name"),
            "template_version": (template_contract or {}).get("template_version"),
            "report_type": "low_efficiency_grading",
            "scenario_key": "efficiency-label-rate",
            "top_rows_count": len(flattened_rows),
            "summary_rows_count": len(summary_rows),
            "level_top_rows_count": {
                level: len(level_top_rows.get(level, [])) for level in LEVELS
            },
            "sheet_url": sheet_url,
        },
    )


def card_design_check(card: dict[str, Any]) -> dict[str, Any]:
    body_elements = card.get("body", {}).get("elements", [])
    tags = [element.get("tag") for element in body_elements if isinstance(element, dict)]
    return {
        "schema_2_0": card.get("schema") == "2.0",
        "has_header": isinstance(card.get("header"), dict),
        "has_metrics": "column_set" in tags,
        "has_table": "table" in tags,
        "table_count": tags.count("table"),
        "has_methodology": "collapsible_panel" in tags,
        "top_level_blocks": len(body_elements),
        "passes_p0_p3_basic_gate": (
            card.get("schema") == "2.0"
            and isinstance(card.get("header"), dict)
            and "column_set" in tags
            and "table" in tags
            and "collapsible_panel" in tags
            and tags.count("table") == 5
            and 9 <= len(body_elements) <= 15
        ),
    }
