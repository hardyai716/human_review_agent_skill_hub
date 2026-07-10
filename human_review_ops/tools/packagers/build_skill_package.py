#!/usr/bin/env python3
"""Build runtime Skill scenario documents from root scenario packages."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

SKILL_COMBINED_SOURCES = {
    "perception": [
        ("场景标识、触发与排除", "scenario_manifest.md"),
        ("指标与维度识别", "metric_contract.md"),
        ("数据就绪与字段风险提示", "dataset_reference.md"),
        ("正反例", "examples.md"),
    ],
    "analysis": [
        ("指标口径", "metric_contract.md"),
        ("数据源与字段", "dataset_reference.md"),
        ("分析模式", "analysis.md"),
        ("正反例", "examples.md"),
    ],
    "notification": [
        ("场景定位", "scenario_manifest.md"),
        ("通知模板", "notification_templates.md"),
        ("Owner / POC 路由", "owner_routing.md"),
        ("SLA 与升级", "sla.md"),
    ],
    "resolution": [
        ("场景定位", "scenario_manifest.md"),
        ("状态机", "state_machine.md"),
        ("Owner / POC 路由", "owner_routing.md"),
        ("SLA、继续观察与升级", "sla.md"),
        ("正反例", "examples.md"),
    ],
}

SKILL_TITLES = {
    "perception": "感知场景",
    "analysis": "场景",
    "notification": "通知场景",
    "resolution": "解决闭环场景",
}

SKILL_PREAMBLES = {
    "perception": [
        "## 运行态定位",
        "",
        "本文件是 perception Skill 的运行态单场景文档，由根场景包合并生成。运行态只使用本文件判断场景、任务类型、指标意图、readiness 和 handoff；不执行 SQL、不生成通知、不写线上状态。",
        "",
        "## Readiness 与 Handoff",
        "",
        "- 分析型任务必须确认场景唯一、任务类型明确、时间窗口具备、维度已治理，且无越权动作，才能交接 `next_skill=analysis`。",
        "- 通知请求必须已有分析产物，才能交接 `next_skill=notification`。",
        "- 闭环请求必须已有通知或 tracking 产物，才能交接 `next_skill=resolution`。",
        "- 口径冲突、样本池覆盖、未治理字段、权限风险、真实群发、自动拉群、线上写状态或敏感明细导出必须阻断。",
    ],
    "analysis": [
        "本文件是 analysis Skill 的运行态单场景文档，由根场景包合并生成。运行态 Skill 只读取本文件，不再拆读四件套。",
    ],
    "notification": [
        "## 运行态定位",
        "",
        "本文件是 notification Skill 的运行态单场景文档，由根场景包合并生成。运行态只生成通知草稿、Owner/POC 路由、Card 或报表准备说明和 send_plan 门禁；不真实发送、不拉群、不写线上状态。",
        "",
        "## 输入与输出门禁",
        "",
        "- 必须消费 analysis Skill 或上游 runner 产出的结构化分析结果、QueryPlan、source_footer 和证据引用。",
        "- 默认 `send_mode=preview_only`、`requires_confirmation=true`、`group_send_blocked=true`、`sent=false`、`real_group_send_executed=false`。",
        "- 真实触达前必须由宿主 Agent 或 runner 在通知 Skill 外完成目标群、接收人、open_id、正文、附件和权限确认。",
        "- 结构化 Card 模板、schema notes、POC mapping 等资产存在时保留在 `assets/<scenario_key>/`，不要合并进 Markdown。",
    ],
    "resolution": [
        "## 运行态定位",
        "",
        "本文件是 resolution Skill 的运行态单场景文档，由根场景包合并生成。运行态只记录人工处理状态、闭环检查、继续观察和升级建议；不重新查数、不生成通知内容、不执行线上写入。",
        "",
        "## 闭环门禁",
        "",
        "- 必须消费前置分析、通知草稿、send_plan、人工动作和证据引用。",
        "- 关闭前必须具备动作、证据、结论三件套。",
        "- `send_plan.sent=false` 或 `group_send_blocked=true` 时不得写成已通知完成。",
        "- 真实通知、线上写状态、自动关闭、处罚或资源调整进入 `HUMAN_REVIEW_REQUIRED`，只记录阻断原因。",
    ],
}


def strip_top_heading(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        return "\n".join(lines[1:]).strip()
    return text.strip()


def build_skill_scenario_doc(skill: str, scenario_dir: Path, scenario_key: str) -> str:
    sections = [f"# {SKILL_TITLES[skill]}：{scenario_key}", ""]
    sections.extend(SKILL_PREAMBLES[skill])
    for heading, source_name in SKILL_COMBINED_SOURCES[skill]:
        source = scenario_dir / source_name
        if not source.exists():
            raise FileNotFoundError(f"Missing source file: {source}")
        sections.extend(["", f"## {heading}", "", strip_top_heading(source.read_text(encoding="utf-8"))])
    return "\n".join(sections).rstrip() + "\n"


def build_snapshots(scenario_key: str, dry_run: bool) -> None:
    scenario_dir = ROOT / "references" / "scenarios" / scenario_key
    if not scenario_dir.exists():
        raise FileNotFoundError(f"Scenario package not found: {scenario_dir}")

    for skill, combined_sources in SKILL_COMBINED_SOURCES.items():
        target_dir = ROOT / "skills" / skill / "references" / "scenarios"
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)

        target = target_dir / f"{scenario_key}.md"
        source_summary = " + ".join(name for _, name in combined_sources)
        print(f"{scenario_dir.relative_to(ROOT)}/[{source_summary}] -> {target.relative_to(ROOT)}")
        if not dry_run:
            target.write_text(
                build_skill_scenario_doc(skill, scenario_dir, scenario_key),
                encoding="utf-8",
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_key")
    parser.add_argument("--write", action="store_true", help="Write files instead of dry-run.")
    args = parser.parse_args()
    build_snapshots(args.scenario_key, dry_run=not args.write)


if __name__ == "__main__":
    main()
