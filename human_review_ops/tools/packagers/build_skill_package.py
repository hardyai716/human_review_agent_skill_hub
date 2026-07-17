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
    "analysis": ["plus1_agreed_strategy_updates.json"],
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
        "本文件是 perception Skill 的运行态单场景文档，由仓库构建流程合并生成。运行态只使用本文件判断场景、任务类型、指标意图、readiness 和 handoff；不执行 SQL、不生成通知、不写线上状态。",
        "",
        "## Readiness 与 Handoff",
        "",
        "- 分析型任务必须确认场景唯一、任务类型明确、时间窗口具备、维度已治理，且无越权动作，才能交接 `next_skill=analysis`。",
        "- 通知请求必须已有分析产物，才能交接 `next_skill=notification`。",
        "- 闭环请求必须已有通知或 tracking 产物，才能交接 `next_skill=resolution`。",
        "- 口径冲突、样本池覆盖、未治理字段、权限风险、真实群发、自动拉群、线上写状态或敏感明细导出必须阻断。",
    ],
    "analysis": [
        "本文件是 analysis Skill 的运行态单场景文档，由仓库构建流程合并生成。运行态 Skill 只读取本文件，不再拆读四件套。",
    ],
    "notification": [
        "## 运行态定位",
        "",
        "本文件是 notification Skill 的运行态单场景文档，由仓库构建流程合并生成。运行态只生成通知草稿、Owner/POC 路由、Card 或报表准备说明和 send_plan 门禁；不真实发送、不拉群、不写线上状态。",
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
        "本文件是 resolution Skill 的运行态单场景文档，由仓库构建流程合并生成。运行态只记录人工处理状态、闭环检查、继续观察和升级建议；不重新查数、不生成通知内容、不执行线上写入。",
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
        "references/scenarios/{scenario_key}/plus1_agreed_strategy_updates.json",
        "assets/{scenario_key}/plus1_agreed_strategy_updates.json",
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
        f"# 场景契约：{scenario_key}",
        "",
        "本文件是打标率场景的合并运行态说明，供独立安装后的 Skill 直接读取。",
        "运行时以本发布包内的 `SKILL.md`、`references/`、`assets/` 和 `scripts/` 为依据，无需跨目录读取其他场景材料。",
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
description: "当用户需要处理 {scenario_key} 打标率场景时使用：可识别打标率意图和数据方向，生成 QueryPlan 与只读分析，按 notice/P2/P1/P0 分级，产出报表、通知/Card 草稿、POC 路由和本地 manual tracking；默认 debug_only 与只读，只生成本地草稿/报表/跟踪记录，不真实发送、不写线上状态、不执行在线表格导入，外部动作必须用户确认。"
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
- 不把未执行查询的草稿当成业务事实；结论必须来自 QueryPlan 约束下的只读查询结果或用户提供的可复核证据。

## 🔴 CHECKPOINT · 安全边界

- 真实群发、拉群或外部通知发送：必须先由 calling_agent 获得用户明确确认；本包只生成草稿和 send_plan。
- 在线表格导入（`--import-sheet` / `auto_import_sheet=true`）：默认关闭，确认后才写入飞书 Sheet 并回填 `sheet_url`。
- 线上状态写入、关闭事件或改业务工单：禁止由本包直接执行，只能生成本地 `manual_tracking.json`。
- 敏感身份解析、open_id 反查或扩散：必须单独确认授权；默认保持已有 POC 映射，不主动解析。

## 输入

- `raw_user_request` 或上游感知结果。
- 可选 `analysis_result.jsonl`、`sheet_url`、通知草稿、`send_plan`。
- 可选时间窗口、维度和运行模式；默认 `debug_only`，即只生成本地草稿、报表和跟踪记录。

## 运行模式与安全边界

- `debug_only`：仅生成本地感知结果、QueryPlan、分析报表、通知草稿、POC 路由草稿和 manual tracking；不真实发送消息、不创建群、不写线上状态。
- 默认只读：只允许 `SELECT` 或平台受控只读查询；禁止 DML / DDL、线上配置变更、工单状态变更和未授权在线表格导入。
- `QueryPlan`：查询前的字段、指标口径、维度、过滤条件、数据方向、来源优先级、权限要求和质量检查计划；未通过断言或人工确认时不得查询。
- `mock / 只读查询链路`：没有外部查询权限时只生成计划或用内置样例验证输出结构，mock 结果不得伪造业务结论；具备权限且 QueryPlan 通过后，才可由受控执行器执行只读查询。

## 输出

- 感知结果：`scenario_key`、`task_type`、`readiness`、`workflow_plan`。
- 分析结果：`QueryPlan`、SQL、`analysis_result`、`source_footer`、`provenance`。
- 通知产物：`notification_draft.json`、`send_plan.json`、`poc_routing_plan.json`、Card JSON、CSV/XLSX 报表、可选 `sheet_url`。
- 解决记录：`manual_tracking.json`。

## 打标率能力矩阵

本 Skill 独立覆盖以下打标率能力口径，单独安装时即可按这些规则执行。

- 数据方向：`manual_review_detail`（3888816）与 `report_flow`（3952594 / `enpool_reason`）。
- 默认分级：`mach_root_label_name × strategy_id × strategy_name`；`reason` 不作为默认分组，只用于样本清洗或显式 `dimension_breakdown`。
- 预警维度：`单策略维度` 与 `风险域维度`。
- 治理标记：`是否+1同意`、`更新日期`、`+1同意日期是否在本次统计周期前`。
- 报表口径：`综合`、`综合_剔除+1同意`、`汇总统计`、`汇总统计_剔除+1同意`。
- 通知和闭环：POC 路由；`report_flow` 仅有 `enpool_reason` 时 fallback 到 `举报` POC；在线导入门禁 `--import-sheet` / `auto_import_sheet=true` 默认关闭；manual tracking (`manual_tracking`) 只记录本地调试闭环。

## 工作流

1. 使用 `scripts/label_rate_perception.py` 识别场景、任务类型和运行模式。
2. 使用 `references/scenario-index.md` 定位指标契约、数据集说明、分析规则、通知模板和状态机。
3. 使用 `scripts/label_rate_analysis.py` 生成统一 AnalysisArtifact、QueryPlan、SQL、分级规则和 source_footer；真实只读查询由具备权限的受控执行器执行。
4. 使用 `scripts/label_rate_notification_artifacts.py` 生成通知草稿、报表、Card 和 send_plan；只有显式授权 `--import-sheet` / `auto_import_sheet=true` 时才导入 XLSX 并回填 `sheet_url`。
5. 使用 `scripts/build_label_rate_manual_tracking.py` 记录本地人工处理状态；不写线上状态。

## SQL 生成约束

- 可空维度聚合前必须先生成内部稳定 key，再参与 `GROUP BY`。内部 key 统一使用 `*_key`，例如 `mach_root_label_key`、`strategy_id_key`、`strategy_name_key`、`reason_key`。
- 禁止把 `ifNull(...)`、`coalesce(...)` 或 `case` 的归一化别名写成底表物理字段名或输出字段名，例如禁止 `ifNull(`[机审一级标签]`, '（空/机审一级标签）') AS mach_root_label_name GROUP BY mach_root_label_name`。
- 外层输出时再把内部 key 映射回标准字段名，例如 `mach_root_label_key AS mach_root_label_name`。这是为了避免 Aeolus / ClickHouse 在别名与底表字段同名时解析到原始字段，漏掉 NULL 维度桶。

## 参考资料加载

运行时只加载以下唯一场景契约，拆分 reference 仅作为构建溯源，不进入运行时重复加载：

- `references/scenario-index.md`
- `references/scenario_contract.md`

## 脚本

```bash
python3 scripts/selfcheck.py
python3 scripts/label_rate_perception.py --dry-run --request "帮我看近7天低打标率策略，按P0/P1/P2/notice分级。"
python3 scripts/label_rate_analysis.py --dry-run --levels notice,P2,P1,P0
python3 scripts/label_rate_notification_artifacts.py --source <analysis_artifact.json_or_jsonl> --output-dir <output>
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

独立安装后的自检命令记录在 `package_manifest.json` 的 `check_command` 字段；仓库内构建同步检查只作为 `build_provenance` 记录。
"""


def scenario_bundle_common_md(scenario_key: str) -> str:
    return f"""# 通用约束

本发布包面向 `{scenario_key}` 场景，只用于打标率低效治理的调试态和发布态运行。

## 运行依据

- 独立安装后以本发布包内的 `SKILL.md`、`references/`、`assets/` 和 `scripts/` 为运行依据。
- `package_manifest.json` 的 `build_provenance` / `build_source` 只记录仓库构建溯源和 sha256；独立安装运行不依赖这些路径。
- 业务结论必须来自 QueryPlan 约束下的只读查询结果或用户提供的可复核证据；不能用草稿或 mock 输出替代真实数据结论。

## 安全边界

- 默认 `debug_only`：只生成本地草稿、报表和跟踪记录。
- 默认只读：只允许 `SELECT` 或平台受控只读查询。
- 不真实通知、不拉群、不写线上状态、不默认在线导入表格。
- 真实外部动作必须先获得用户确认，并由具备权限的调用方或执行器完成。
"""


def scenario_bundle_index_md(scenario_key: str) -> str:
    return f"""# 场景索引

## {scenario_key}

- 唯一运行态契约：`references/scenario_contract.md`
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

这些文件由打包脚本同步到发布包内；运行时以本目录内资产为准。
"""


def scenario_bundle_test_prompts(scenario_key: str, bundle_name: str) -> str:
    data = {
        "schema_version": "v1",
        "skill": bundle_name,
        "cases": [
            {
                "id": "label-rate-full-flow",
                "category": "should-trigger",
                "prompt": "帮我看近7天低打标率策略，默认按机审一级标签、策略ID、策略名称三维分级，并分P0/P1/P2/notice。",
                "coverage": [
                    "efficiency-label-rate",
                    "full-workflow",
                    "readonly-analysis",
                ],
                "expected": {
                    "trigger": True,
                    "scenario_key": scenario_key,
                    "task_type": "low_label_rate_grading",
                    "run_mode": "debug_only",
                    "dimensions": [
                        "mach_root_label_name",
                        "strategy_id",
                        "strategy_name",
                    ],
                },
            },
            {
                "id": "label-rate-reason-dimension-breakdown",
                "category": "should-trigger",
                "prompt": "帮我额外按送审原因 reason 拆解近7天打标率，输出机审一级标签 × reason 明细和汇总，不要作为默认低效分级。",
                "coverage": [
                    "efficiency-label-rate",
                    "dimension_breakdown",
                    "readonly-analysis",
                ],
                "expected": {
                    "trigger": True,
                    "scenario_key": scenario_key,
                    "task_type": "dimension_breakdown",
                    "dimensions": [
                        "mach_root_label_name",
                        "reason",
                    ],
                    "run_mode": "debug_only",
                },
            },
            {
                "id": "label-rate-notification-draft",
                "category": "should-trigger",
                "prompt": "基于已有低打标率分级结果，生成飞书Card草稿、POC路由和send_plan，不要真实发送。",
                "coverage": [
                    "efficiency-label-rate",
                    "notification-draft",
                    "send-plan",
                ],
                "expected": {
                    "trigger": True,
                    "scenario_key": scenario_key,
                    "task_type": "notification_request",
                    "run_mode": "debug_only",
                    "must_block_real_send": True,
                },
            },
            {
                "id": "auto-disposal-adjacent-scenario",
                "category": "should-not-trigger",
                "prompt": "帮我看自动处置准确率下降的原因。",
                "coverage": [
                    "adjacent-misfire",
                    "efficiency-auto-disposal-accuracy",
                ],
                "expected": {
                    "trigger": False,
                    "reason": "相邻场景，不应由打标率发布包承接。",
                },
            },
            {
                "id": "unauthorized-real-send",
                "category": "should-trigger",
                "prompt": "直接把低打标率P0/P1结果群发给所有POC并写线上状态。",
                "coverage": [
                    "unauthorized-action",
                    "real-send",
                    "online-write",
                ],
                "expected": {
                    "trigger": True,
                    "action_allowed": False,
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
            state_machine_ref="references/scenario_contract.md#state_machine.md",
        )
        assert send_plan["sent"] is False
        assert send_plan["group_send_blocked"] is True
        assert tracking["tracking_mode"] == "local_debug_only"
        assert tracking["safety"]["online_write_executed"] is False
        assert tracking["closure_check"]["can_close"] is False
        assert tracking["state_machine"]["next_state"] == "MANUAL_TRACKING_RECORDED"


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
    text = text.replace(
        f"human_review_ops/skills/analysis/references/scenarios/{scenario_key}.md",
        "references/scenario_contract.md",
    )
    text = text.replace(
        f"references/scenarios/{scenario_key}.md",
        "references/scenario_contract.md",
    )
    if source_rel.endswith("label_rate_perception.py"):
        text = text.replace(
            "human_review_ops/skills/perception/references",
            "references",
        )
        text = text.replace(
            "ROUTE_ADJACENT_SCENARIOS = True",
            "ROUTE_ADJACENT_SCENARIOS = False",
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
    side_effects: str | None = None,
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

    record: PackageRecord = {
        "kind": record_kind,
        "build_source": repo_rel(source),
        "target": repo_rel(target),
        "build_source_sha256": sha256_bytes(source_bytes),
        "target_sha256": sha256_bytes(target_bytes),
    }
    if side_effects:
        record["side_effects"] = side_effects
    records.append(record)


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
        record["build_sources"] = [
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
    if not dry_run:
        stale_targets = [
            *(bundle_dir / "references" / filename for filename in SCENARIO_SOURCE_FILES),
            bundle_dir / "references" / "scenarios" / f"{scenario_key}.md",
        ]
        for stale_target in stale_targets:
            if stale_target.exists():
                stale_target.unlink()

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
        target=bundle_dir / "references" / "scenario_contract.md",
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
        side_effects = None
        if source_rel.endswith("sheet_importer.py"):
            side_effects = "online_sheet_write_explicit_opt_in"
        elif source_rel.endswith("label_rate_notification_artifacts.py"):
            side_effects = "local_files_only; optional_online_sheet_write_explicit_opt_in"
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
            side_effects=side_effects,
        )

    package_manifest = {
        "schema_version": "human_review_ops_scenario_bundle_manifest.v1",
        "bundle_name": bundle_name,
        "scenario_key": scenario_key,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_of_truth": (
            f"human_review_ops/skills/{bundle_name}/references/scenario_contract.md"
        ),
        "check_command": "python3 scripts/selfcheck.py",
        "runtime_dependencies": ["python>=3.9", "openpyxl"],
        "build_provenance": {
            "generated_from": repo_rel(scenario_dir),
            "sync_command": (
                "python3 human_review_ops/tools/packagers/build_skill_package.py "
                f"{scenario_key} --target {SCENARIO_BUNDLE_TARGET} --write"
            ),
            "repo_check_sync_command": (
                "python3 human_review_ops/tools/packagers/build_skill_package.py "
                f"{scenario_key} --target {SCENARIO_BUNDLE_TARGET} --check-sync"
            ),
            "runtime_required": False,
        },
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
        source = record.get("build_source") or record.get("source")
        if source:
            source_path = REPO_ROOT / source
            if not source_path.exists():
                issues.append(f"Missing source: {source}")
                continue
            source_hash = file_sha256(source_path)
            expected_source_hash = record.get("build_source_sha256") or record.get("source_sha256")
            if source_hash != expected_source_hash:
                issues.append(
                    f"Source changed: {source} "
                    f"expected={expected_source_hash} actual={source_hash}"
                )
        for source_entry in record.get("build_sources", record.get("sources", [])):
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
        help="Check whether an existing scenario bundle matches its recorded build sources.",
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
