#!/usr/bin/env python3
"""Build Skill runtime snapshots and scenario bundle packages."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT.parent

LEGACY_TARGET = "legacy-capability-skills"
SCENARIO_BUNDLE_TARGET = "scenario-bundle"

SCENARIO_SOURCE_FILES = [
    "scenario_manifest.md",
    "metric_contract.md",
    "dataset_reference.md",
    "analysis.md",
    "notification_templates.md",
    "owner_routing.md",
    "state_machine.md",
    "sla.md",
    "examples.md",
]

# Structured scenario assets that must be synced verbatim (not merged into
# Markdown) from the root scenario package into a Skill's assets directory.
SKILL_ASSET_SYNC = {
    "notification": ["mach_root_label_poc_mapping.json"],
}

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
        "- 必须消费 analysis Skill 或外部执行环境产出的结构化分析结果、QueryPlan、source_footer 和证据引用。",
        "- 默认 `send_mode=preview_only`、`requires_confirmation=true`、`group_send_blocked=true`、`sent=false`、`real_group_send_executed=false`。",
        "- 真实通知前必须由 calling_agent 或 external_executor 在通知 Skill 外完成目标群、接收人、open_id、正文、附件和权限确认。",
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

SCENARIO_BUNDLE_SCRIPT_SOURCES = [
    ("skills/perception/scripts/label_rate_perception.py", "scripts/label_rate_perception.py"),
    ("skills/analysis/scripts/label_rate_analysis.py", "scripts/label_rate_analysis.py"),
    (
        "skills/notification/scripts/label_rate_notification_artifacts.py",
        "scripts/label_rate_notification_artifacts.py",
    ),
    (
        "skills/notification/scripts/render_label_rate_grading_card.py",
        "scripts/render_label_rate_grading_card.py",
    ),
    (
        "skills/notification/scripts/resolve_label_rate_poc_routing.py",
        "scripts/resolve_label_rate_poc_routing.py",
    ),
    ("skills/notification/scripts/card_hash.py", "scripts/card_hash.py"),
    ("skills/notification/scripts/sheet_importer.py", "scripts/sheet_importer.py"),
    (
        "skills/resolution/scripts/build_label_rate_manual_tracking.py",
        "scripts/build_label_rate_manual_tracking.py",
    ),
]

SCENARIO_BUNDLE_ASSET_SOURCES = [
    (
        "references/scenarios/{scenario_key}/mach_root_label_poc_mapping.json",
        "assets/{scenario_key}/mach_root_label_poc_mapping.json",
    ),
    (
        "skills/notification/assets/efficiency-label-rate/card_schema_notes.md",
        "assets/{scenario_key}/card_schema_notes.md",
    ),
    (
        "skills/notification/assets/efficiency-label-rate/low_efficiency_grading_card_template.json",
        "assets/{scenario_key}/low_efficiency_grading_card_template.json",
    ),
]


PackageRecord = dict[str, Any]
TextTransform = Callable[[str], str]


def repo_rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def root_rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def strip_top_heading(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        return "\n".join(lines[1:]).strip()
    return text.strip()


def scenario_bundle_name(scenario_key: str) -> str:
    return f"{scenario_key}-ops"


def scenario_dir_for(scenario_key: str) -> Path:
    scenario_dir = ROOT / "references" / "scenarios" / scenario_key
    if not scenario_dir.exists():
        raise FileNotFoundError(f"Scenario package not found: {scenario_dir}")
    return scenario_dir


def build_skill_scenario_doc(skill: str, scenario_dir: Path, scenario_key: str) -> str:
    sections = [f"# {SKILL_TITLES[skill]}：{scenario_key}", ""]
    sections.extend(SKILL_PREAMBLES[skill])
    for heading, source_name in SKILL_COMBINED_SOURCES[skill]:
        source = scenario_dir / source_name
        if not source.exists():
            raise FileNotFoundError(f"Missing source file: {source}")
        sections.extend(
            [
                "",
                f"## {heading}",
                "",
                strip_top_heading(source.read_text(encoding="utf-8")),
            ]
        )
    return "\n".join(sections).rstrip() + "\n"


def build_combined_scenario_reference(
    scenario_dir: Path,
    scenario_key: str,
) -> str:
    sections = [
        f"# 场景流程包合并快照：{scenario_key}",
        "",
        "本文件由根目录场景包生成，用于发布包运行态读取。",
        "业务事实以根目录 `human_review_ops/references/scenarios/` 中的源文件为准。",
    ]
    for filename in SCENARIO_SOURCE_FILES:
        source = scenario_dir / filename
        if not source.exists():
            raise FileNotFoundError(f"Missing source file: {source}")
        sections.extend(
            [
                "",
                f"## {filename}",
                "",
                strip_top_heading(source.read_text(encoding="utf-8")),
            ]
        )
    return "\n".join(sections).rstrip() + "\n"


def scenario_bundle_skill_md(scenario_key: str, bundle_name: str) -> str:
    return f"""---
name: {bundle_name}
description: "当用户需要围绕 efficiency-label-rate 打标率场景执行只读分析、低效分级、通知草稿、POC 路由、报表生成或本地人工跟踪时使用；这是由四个通用能力 Skill 和根场景包生成的自包含发布包，默认不真实发送通知、不写线上状态。"
allowed-tools:
  - Read
  - Bash
---

# 打标率场景发布包

## 触发条件

- 用户明确询问打标率、低打标率、低效打标策略、进审量、完审量、打标量、reason、机审一级标签拆解。
- 用户要求对 `notice/P2/P1/P0` 低效打标策略分级。
- 用户要求基于既有分析结果生成通知草稿、飞书 Card、XLSX 报表、`sheet_url` 或 `send_plan`。
- 用户要求记录本地人工跟踪、继续观察或闭环检查。

## 禁止使用

- 不用于自动处置准确率、质检准确率、底线事故等其他场景。
- 不默认真实群发、不拉群、不解析敏感身份、不写线上状态。
- 不替代 calling_agent 的权限判断、人工确认和真实外部执行。
- 不把本发布包作为业务事实来源；业务事实以根目录场景包为准。

## 输入

- `raw_user_request` 或上游感知结果。
- 可选 `analysis_result.jsonl`、`sheet_url`、通知草稿、`send_plan`。
- 可选时间窗口、维度和运行模式；默认 `debug_only`。

## 输出

- 感知结果：`scenario_key`、`task_type`、`readiness`、`workflow_plan`。
- 分析结果：`QueryPlan`、SQL、`analysis_result`、`source_footer`、`provenance`。
- 通知产物：`notification_draft.json`、`send_plan.json`、`poc_routing_plan.json`、Card JSON、CSV/XLSX 报表、可选 `sheet_url`。
- 解决记录：`manual_tracking.json`。

## 工作流

1. 使用 `scripts/label_rate_perception.py` 识别场景、任务类型和运行模式。
2. 使用 `references/scenario-index.md` 定位指标契约、数据集说明、分析规则、通知模板和状态机。
3. 使用 `scripts/label_rate_analysis.py` 生成 QueryPlan、SQL、分级规则和 source_footer；真实只读查询由 external_executor 执行。
4. 使用 `scripts/label_rate_notification_artifacts.py` 生成通知草稿、报表、Card 和 send_plan；未提供 `sheet_url` 时可尝试导入 XLSX。
5. 使用 `scripts/build_label_rate_manual_tracking.py` 记录本地人工处理状态；不写线上状态。

## 参考资料加载

- `references/scenario-index.md`
- `references/scenarios/{scenario_key}.md`
- `references/metric_contract.md`
- `references/dataset_reference.md`
- `references/analysis.md`
- `references/notification_templates.md`
- `references/owner_routing.md`
- `references/state_machine.md`
- `references/sla.md`
- `references/examples.md`

## 脚本

```bash
python3 scripts/selfcheck.py
python3 scripts/label_rate_perception.py --dry-run --request "帮我看近7天低打标率策略，按P0/P1/P2/notice分级。"
python3 scripts/label_rate_analysis.py --dry-run --levels notice,P2,P1,P0
python3 scripts/label_rate_notification_artifacts.py --source <analysis_result.jsonl> --output-dir <output>
python3 scripts/build_label_rate_manual_tracking.py --notification-draft <draft.json> --send-plan <send_plan.json> --output <tracking.json>
```

## 失败处理

- 场景不唯一：停止并要求 calling_agent 补充场景。
- 时间窗口或维度缺失：只输出 readiness，不进入查询。
- 缺少分析结果：不生成通知草稿，要求先补齐分析产物。
- 缺少人工确认：保持 `group_send_blocked=true` 和 `sent=false`。
- 缺少证据三件套：不关闭事件，只记录继续跟进。

## 验证

发布包内至少运行：

```bash
python3 scripts/selfcheck.py
```

源文件同步检查由仓库侧执行，命令记录在 `package_manifest.json` 的 `check_command` 字段。
"""


def scenario_bundle_common_md(scenario_key: str) -> str:
    return f"""# 通用约束

本发布包面向 `{scenario_key}` 场景，只用于打标率低效治理的调试态和发布态运行。

## 唯一事实来源

- 根目录场景包是业务事实来源。
- 本发布包由打包脚本生成，不手工维护业务口径。
- `package_manifest.json` 记录每个文件的来源路径和 sha256。

## 安全边界

- 默认 `debug_only`。
- 只读优先。
- 不真实通知、不拉群、不写线上状态。
- 真实外部动作必须由 calling_agent 或 external_executor 完成人工确认。
"""


def scenario_bundle_index_md(scenario_key: str) -> str:
    return f"""# 场景索引

## {scenario_key}

- 合并运行态文档：`references/scenarios/{scenario_key}.md`
- 场景清单：`references/scenario_manifest.md`
- 指标契约：`references/metric_contract.md`
- 数据集说明：`references/dataset_reference.md`
- 分析规则：`references/analysis.md`
- 通知模板：`references/notification_templates.md`
- Owner / POC 路由：`references/owner_routing.md`
- 状态机：`references/state_machine.md`
- SLA：`references/sla.md`
- 样例：`references/examples.md`
- 资产：`assets/{scenario_key}/`
- 同步清单：`package_manifest.json`
"""


def scenario_bundle_assets_readme(scenario_key: str) -> str:
    return f"""# Assets

本目录存放 `{scenario_key}` 发布包运行所需的结构化资产。

- `test-prompts.json`：触发和反触发样例。
- `{scenario_key}/mach_root_label_poc_mapping.json`：机审一级标签到 POC 的姓名级映射。
- `{scenario_key}/low_efficiency_grading_card_template.json`：飞书 Card 模板。
- `{scenario_key}/card_schema_notes.md`：Card schema 说明。

这些文件由打包脚本从根场景包和通用 Skill assets 同步。
"""


def scenario_bundle_test_prompts(scenario_key: str, bundle_name: str) -> str:
    data = {
        "schema_version": "v1",
        "skill": bundle_name,
        "cases": [
            {
                "id": "label-rate-full-flow",
                "category": "should-trigger",
                "prompt": "帮我看近7天低打标率策略，按机审一级标签、策略ID、策略名称、送审原因拆解，并分P0/P1/P2/notice。",
                "expected": {
                    "scenario_key": scenario_key,
                    "task_type": "low_label_rate_grading",
                    "run_mode": "debug_only",
                },
            },
            {
                "id": "label-rate-notification-draft",
                "category": "should-trigger",
                "prompt": "基于已有低打标率分级结果，生成飞书Card草稿、POC路由和send_plan，不要真实发送。",
                "expected": {
                    "scenario_key": scenario_key,
                    "task_type": "notification_only",
                    "must_block_real_send": True,
                },
            },
            {
                "id": "auto-disposal-adjacent-scenario",
                "category": "should-not-trigger",
                "prompt": "帮我看自动处置准确率下降的原因。",
                "expected": {
                    "reason": "相邻场景，不应由打标率发布包承接。",
                },
            },
            {
                "id": "unauthorized-real-send",
                "category": "should-not-trigger",
                "prompt": "直接把低打标率P0/P1结果群发给所有POC并写线上状态。",
                "expected": {
                    "must_block_real_send": True,
                    "must_block_online_write": True,
                },
            },
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def scenario_bundle_selfcheck_py() -> str:
    return '''#!/usr/bin/env python3
"""Self-check for the efficiency-label-rate scenario bundle."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import label_rate_analysis as analysis  # noqa: E402
from build_label_rate_manual_tracking import build_manual_tracking, load_json  # noqa: E402
from label_rate_notification_artifacts import build_label_rate_notification_artifacts  # noqa: E402
from label_rate_perception import detect_label_rate_perception  # noqa: E402


def run_perception_check() -> None:
    payload = detect_label_rate_perception(
        raw_user_request="帮我看近7天低打标率策略，按P0/P1/P2/notice分级。"
    )
    assert payload["scenario_key"] == "efficiency-label-rate"
    assert payload["task_type"] == "low_label_rate_grading"
    assert payload["readiness"]["status"] == "ready"


def build_analysis_records() -> list[dict]:
    levels = analysis.parse_levels(",".join(analysis.DEFAULT_LEVELS))
    sql_map = analysis.sql_by_level()
    payloads = analysis.build_smoke_payloads(levels)
    return analysis.build_records(payloads, levels, sql_map)


def run_notification_and_resolution_check(records: list[dict]) -> None:
    with tempfile.TemporaryDirectory(prefix="label-rate-bundle-selfcheck-") as tmp:
        tmp_path = Path(tmp)
        source_path = tmp_path / "analysis_result.jsonl"
        output_dir = tmp_path / "notification"
        source_path.write_text(
            "\\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\\n",
            encoding="utf-8",
        )
        build_label_rate_notification_artifacts(
            source_path=source_path,
            output_dir=output_dir,
            top_n=2,
            sheet_url="https://example.com/sheets/smoke",
            identity="bot",
            title="近7天低效打标策略全等级结果",
            self_send_requested=False,
            sent_payload=None,
            target_user_id=None,
            target_chat_id=None,
            auto_import_sheet=False,
        )
        notification_draft = load_json(output_dir / "notification_draft.json")
        send_plan = load_json(output_dir / "send_plan.json")
        tracking = build_manual_tracking(
            notification_draft=notification_draft,
            send_plan=send_plan,
            state_machine_ref="references/scenarios/efficiency-label-rate.md#状态机",
        )
        assert send_plan["sent"] is False
        assert send_plan["group_send_blocked"] is True
        assert tracking["tracking_mode"] == "local_debug_only"
        assert tracking["safety"]["online_write_executed"] is False


def main() -> None:
    run_perception_check()
    records = build_analysis_records()
    sample = records[1]
    for key in ("QueryPlan", "source_footer", "readonly_execution", "analysis_result"):
        assert key in sample, f"analysis sample missing {key}"
    run_notification_and_resolution_check(records)
    print("efficiency-label-rate scenario bundle selfcheck OK")


if __name__ == "__main__":
    main()
'''


def rewrite_for_scenario_bundle(source_rel: str, text: str, scenario_key: str) -> str:
    if source_rel.endswith("label_rate_analysis.py"):
        text = text.replace(
            f"human_review_ops/skills/analysis/references/scenarios/{scenario_key}.md",
            f"references/scenarios/{scenario_key}.md",
        )
    if source_rel.endswith("label_rate_perception.py"):
        text = text.replace(
            "human_review_ops/skills/perception/references",
            "references",
        )
    return text


def copy_or_transform_file(
    *,
    source: Path,
    target: Path,
    dry_run: bool,
    records: list[PackageRecord],
    transform: TextTransform | None = None,
    record_kind: str = "copy",
) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Missing source file: {source}")

    source_bytes = source.read_bytes()
    if transform is None:
        target_bytes = source_bytes
    else:
        target_bytes = transform(source.read_text(encoding="utf-8")).encode("utf-8")

    print(f"{repo_rel(source)} -> {repo_rel(target)}")
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(target_bytes)

    records.append(
        {
            "kind": record_kind,
            "source": repo_rel(source),
            "target": repo_rel(target),
            "source_sha256": sha256_bytes(source_bytes),
            "target_sha256": sha256_bytes(target_bytes),
        }
    )


def write_generated_file(
    *,
    target: Path,
    content: str,
    dry_run: bool,
    records: list[PackageRecord],
    kind: str,
    sources: list[Path] | None = None,
) -> None:
    target_bytes = content.encode("utf-8")
    print(f"<generated:{kind}> -> {repo_rel(target)}")
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(target_bytes)
    record: PackageRecord = {
        "kind": kind,
        "target": repo_rel(target),
        "target_sha256": sha256_bytes(target_bytes),
    }
    if sources:
        record["sources"] = [
            {
                "path": repo_rel(source),
                "sha256": file_sha256(source),
            }
            for source in sources
        ]
    records.append(record)


def sync_skill_assets(scenario_dir: Path, scenario_key: str, dry_run: bool) -> None:
    """Copy structured scenario assets verbatim into each Skill's assets dir."""
    for skill, asset_names in SKILL_ASSET_SYNC.items():
        for asset_name in asset_names:
            source = scenario_dir / asset_name
            if not source.exists():
                continue
            target_dir = ROOT / "skills" / skill / "assets" / scenario_key
            target = target_dir / asset_name
            print(f"{root_rel(source)} -> {root_rel(target)}")
            if not dry_run:
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)


def build_legacy_snapshots(
    scenario_key: str,
    dry_run: bool,
    assets_only: bool = False,
) -> None:
    scenario_dir = scenario_dir_for(scenario_key)

    if not assets_only:
        for skill, combined_sources in SKILL_COMBINED_SOURCES.items():
            target_dir = ROOT / "skills" / skill / "references" / "scenarios"
            if not dry_run:
                target_dir.mkdir(parents=True, exist_ok=True)

            target = target_dir / f"{scenario_key}.md"
            source_summary = " + ".join(name for _, name in combined_sources)
            print(
                f"{root_rel(scenario_dir)}/[{source_summary}] -> {root_rel(target)}"
            )
            if not dry_run:
                target.write_text(
                    build_skill_scenario_doc(skill, scenario_dir, scenario_key),
                    encoding="utf-8",
                )

    sync_skill_assets(scenario_dir, scenario_key, dry_run)


def build_scenario_bundle(scenario_key: str, dry_run: bool) -> None:
    scenario_dir = scenario_dir_for(scenario_key)
    bundle_name = scenario_bundle_name(scenario_key)
    bundle_dir = ROOT / "skills" / bundle_name
    records: list[PackageRecord] = []

    scenario_sources = [scenario_dir / filename for filename in SCENARIO_SOURCE_FILES]
    for source in scenario_sources:
        target = bundle_dir / "references" / source.name
        copy_or_transform_file(
            source=source,
            target=target,
            dry_run=dry_run,
            records=records,
        )

    write_generated_file(
        target=bundle_dir / "SKILL.md",
        content=scenario_bundle_skill_md(scenario_key, bundle_name),
        dry_run=dry_run,
        records=records,
        kind="generated_skill_md",
    )
    write_generated_file(
        target=bundle_dir / "references" / "common.md",
        content=scenario_bundle_common_md(scenario_key),
        dry_run=dry_run,
        records=records,
        kind="generated_common",
    )
    write_generated_file(
        target=bundle_dir / "references" / "scenario-index.md",
        content=scenario_bundle_index_md(scenario_key),
        dry_run=dry_run,
        records=records,
        kind="generated_scenario_index",
    )
    write_generated_file(
        target=bundle_dir / "references" / "scenarios" / f"{scenario_key}.md",
        content=build_combined_scenario_reference(scenario_dir, scenario_key),
        dry_run=dry_run,
        records=records,
        kind="generated_combined_scenario_reference",
        sources=scenario_sources,
    )
    write_generated_file(
        target=bundle_dir / "assets" / "README.md",
        content=scenario_bundle_assets_readme(scenario_key),
        dry_run=dry_run,
        records=records,
        kind="generated_assets_readme",
    )
    write_generated_file(
        target=bundle_dir / "assets" / "test-prompts.json",
        content=scenario_bundle_test_prompts(scenario_key, bundle_name),
        dry_run=dry_run,
        records=records,
        kind="generated_test_prompts",
    )
    write_generated_file(
        target=bundle_dir / "scripts" / "selfcheck.py",
        content=scenario_bundle_selfcheck_py(),
        dry_run=dry_run,
        records=records,
        kind="generated_selfcheck",
    )

    for source_pattern, target_pattern in SCENARIO_BUNDLE_ASSET_SOURCES:
        source = ROOT / source_pattern.format(scenario_key=scenario_key)
        target = bundle_dir / target_pattern.format(scenario_key=scenario_key)
        copy_or_transform_file(
            source=source,
            target=target,
            dry_run=dry_run,
            records=records,
        )

    for source_rel, target_rel in SCENARIO_BUNDLE_SCRIPT_SOURCES:
        source = ROOT / source_rel
        target = bundle_dir / target_rel
        copy_or_transform_file(
            source=source,
            target=target,
            dry_run=dry_run,
            records=records,
            transform=lambda text, source_rel=source_rel: rewrite_for_scenario_bundle(
                source_rel,
                text,
                scenario_key,
            ),
        )

    package_manifest = {
        "schema_version": "human_review_ops_scenario_bundle_manifest.v1",
        "bundle_name": bundle_name,
        "scenario_key": scenario_key,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_of_truth": repo_rel(scenario_dir),
        "sync_command": (
            "python3 human_review_ops/tools/packagers/build_skill_package.py "
            f"{scenario_key} --target {SCENARIO_BUNDLE_TARGET} --write"
        ),
        "check_command": (
            "python3 human_review_ops/tools/packagers/build_skill_package.py "
            f"{scenario_key} --target {SCENARIO_BUNDLE_TARGET} --check-sync"
        ),
        "files": records,
    }
    manifest_target = bundle_dir / "package_manifest.json"
    print(f"<generated:package_manifest> -> {repo_rel(manifest_target)}")
    if not dry_run:
        manifest_target.write_text(
            json.dumps(package_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def check_scenario_bundle_sync(scenario_key: str) -> None:
    bundle_name = scenario_bundle_name(scenario_key)
    bundle_dir = ROOT / "skills" / bundle_name
    manifest_path = bundle_dir / "package_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing package manifest: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    issues: list[str] = []
    for record in manifest.get("files", []):
        target = REPO_ROOT / record["target"]
        if not target.exists():
            issues.append(f"Missing target: {record['target']}")
            continue
        target_hash = file_sha256(target)
        if target_hash != record.get("target_sha256"):
            issues.append(
                f"Target changed: {record['target']} "
                f"expected={record.get('target_sha256')} actual={target_hash}"
            )
        source = record.get("source")
        if source:
            source_path = REPO_ROOT / source
            if not source_path.exists():
                issues.append(f"Missing source: {source}")
                continue
            source_hash = file_sha256(source_path)
            if source_hash != record.get("source_sha256"):
                issues.append(
                    f"Source changed: {source} "
                    f"expected={record.get('source_sha256')} actual={source_hash}"
                )
        for source_entry in record.get("sources", []):
            source_path = REPO_ROOT / source_entry["path"]
            if not source_path.exists():
                issues.append(f"Missing source: {source_entry['path']}")
                continue
            source_hash = file_sha256(source_path)
            if source_hash != source_entry.get("sha256"):
                issues.append(
                    f"Source changed: {source_entry['path']} "
                    f"expected={source_entry.get('sha256')} actual={source_hash}"
                )

    if issues:
        raise SystemExit("Scenario bundle is out of sync:\n" + "\n".join(issues))
    print(f"Scenario bundle sync OK: {repo_rel(bundle_dir)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_key")
    parser.add_argument(
        "--target",
        choices=(LEGACY_TARGET, SCENARIO_BUNDLE_TARGET),
        default=LEGACY_TARGET,
        help=(
            "Build legacy four-Skill snapshots or a self-contained scenario "
            "bundle under human_review_ops/skills/{scenario_key}-ops."
        ),
    )
    parser.add_argument("--write", action="store_true", help="Write files instead of dry-run.")
    parser.add_argument(
        "--assets-only",
        action="store_true",
        help="Only sync structured scenario assets for legacy capability Skills.",
    )
    parser.add_argument(
        "--check-sync",
        action="store_true",
        help="Check whether an existing scenario bundle matches its recorded sources.",
    )
    args = parser.parse_args()

    if args.check_sync:
        if args.target != SCENARIO_BUNDLE_TARGET:
            raise SystemExit("--check-sync is only supported with --target scenario-bundle.")
        check_scenario_bundle_sync(args.scenario_key)
        return

    if args.target == LEGACY_TARGET:
        build_legacy_snapshots(
            args.scenario_key,
            dry_run=not args.write,
            assets_only=args.assets_only,
        )
        return

    if args.assets_only:
        raise SystemExit("--assets-only is only supported for legacy capability snapshots.")
    build_scenario_bundle(args.scenario_key, dry_run=not args.write)


if __name__ == "__main__":
    main()
