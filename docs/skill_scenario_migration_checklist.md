# Skill 场景化迁移操作清单

## Table of Contents

- [结论](#结论)
- [迁移目标](#迁移目标)
- [目标目录结构](#目标目录结构)
- [需要新建的文件](#需要新建的文件)
- [需要迁移或复制的文件](#需要迁移或复制的文件)
- [需要修改的配置文件](#需要修改的配置文件)
- [Runner 兼容性修改方案](#runner-兼容性修改方案)
- [Validator 兼容性修改方案](#validator-兼容性修改方案)
- [AgentBuddy 发布配置修改](#agentbuddy-发布配置修改)
- [建议执行顺序](#建议执行顺序)
- [验收命令](#验收命令)
- [回滚方案](#回滚方案)

## 结论

当前 `perception`、`analysis`、`notification`、`resolution` 四个 Skill 的能力命名是横向的，但打标率 (`efficiency-label-rate`) 的脚本、参考资料、测试样例和发布资产已经深度嵌在四个能力 Skill 中。

已采用的迁移方案是：

1. 已新建场景 Skill：`efficiency-label-rate-ops`。
2. 已将打标率强绑定 references、assets、scripts 复制到新场景 Skill，作为新 canonical path。
3. 已保留旧四能力 Skill 路径，作为 legacy compatibility path。
4. 已新增路径注册表和 resolver；正式入口已接入，历史 runner / validator 后续分批迁移。
5. 默认采用 `auto` 模式：优先新路径，缺失时回退旧路径。

注意：第一阶段不要直接删除旧四能力 Skill 下的打标率文件；先复制、注册、验证、发布，再逐步把旧路径改成 wrapper 或标记 deprecated。

当前执行状态：

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| 场景 Skill 目录与发布包 | 已完成 | `human_review_ops/skills/efficiency-label-rate-ops/` 已生成，并有 `package_manifest.json`。 |
| 路径注册表与 resolver | 已完成 | `skill_path_registry.json`、`skill_path_resolver.py`、`validate_skill_path_registry.py` 已落地。 |
| 正式 Skill-first runner | 已完成 | `run_label_rate_formal_flow.py` 已默认通过 `auto` 模式优先 canonical。 |
| 产品化 / standalone profile | 已完成 | `validate_skill_productization.py` 和 `validate_skill_standalone_smoke.py` 已支持 `scenario_label_rate` 与 `all_releaseable`。 |
| 历史 runner / validator 全量切换 | 待开始 | 阶段性 runner 和部分脚本级 validator 仍需分批改用 resolver。 |
| AgentBuddy 场景 Skill 发布 | 已完成 | 20260710 首次发布 `efficiency-label-rate-ops:1.0.0`；20260713 收敛基线发布成功到 `efficiency-label-rate-ops:1.0.2`，见 `human_review_ops/evals/agentbuddy_publish/20260710_agentbuddy_efficiency_label_rate_ops_publish_summary.json` 与 `human_review_ops/evals/agentbuddy_publish/20260713_agentbuddy_label_rate_convergence_baseline_summary.json`。 |
| AgentBuddy 安装后路由观察 | 观察中 | 发布已完成；真实安装后的 skill 检索、路由命中和跨 Agent 调用表现仍需在下一轮安装环境中观察。 |

## 迁移目标

目标形态：

```text
human_review_ops/
├── skills/
│   ├── efficiency-label-rate-ops/        # 当前 canonical：打标率场景 Skill
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   ├── references/
│   │   └── assets/
│   ├── perception/                       # 旧：能力 Skill，保留兼容
│   ├── analysis/
│   ├── notification/
│   ├── resolution/
│   └── skill_release_manifest.json
├── configs/
│   └── skill_path_registry.json          # 新旧路径注册表
└── tools/
    ├── compat/
│   └── skill_path_resolver.py        # 路径解析器
    ├── runners/
    └── validators/
```

迁移后的职责：

| 层级 | 新职责 | 兼容策略 |
| --- | --- | --- |
| `efficiency-label-rate-ops` | 打标率场景的完整闭环 Skill | 新 canonical path |
| `perception/analysis/notification/resolution` | 横向能力 Skill 或旧入口 | 暂时保留 legacy path |
| `runner` | 项目级编排入口 | 通过 resolver 找脚本 |
| `validator` | 同时校验新旧路径 | 通过 registry 选择 profile |
| `skill_release_manifest.json` | 声明可发布 Skill | 新旧 Skill entries 共存 |
| `.agentbuddy/publish.yaml` | AgentBuddy 发布入口 | 新旧 Skill items 共存 |

## 目标目录结构

新增场景 Skill 建议结构：

```text
human_review_ops/skills/efficiency-label-rate-ops/
├── SKILL.md
├── scripts/
│   ├── label_rate_perception.py
│   ├── label_rate_analysis.py
│   ├── label_rate_notification_artifacts.py
│   ├── render_label_rate_grading_card.py
│   ├── resolve_label_rate_poc_routing.py
│   ├── card_hash.py
│   └── build_label_rate_manual_tracking.py
├── references/
│   ├── common.md
│   ├── scenario_manifest.md
│   ├── metric_contract.md
│   ├── dataset_reference.md
│   ├── analysis.md
│   ├── notification_templates.md
│   ├── owner_routing.md
│   ├── state_machine.md
│   ├── sla.md
│   └── examples.md
└── assets/
    ├── README.md
    ├── test-prompts.json
    ├── card_schema_notes.md
    ├── low_efficiency_grading_card_template.json
    └── mach_root_label_poc_mapping.json
```

## 需要新建的文件

### 场景 Skill 文件

- `human_review_ops/skills/efficiency-label-rate-ops/SKILL.md`
  - 场景级 description：明确“打标率场景完整闭环”，不要再拆成四个能力入口。
  - 正文包含：触发条件、禁止使用、输入、输出、工作流、脚本、参考资料、失败分支、验证命令。
- `human_review_ops/skills/efficiency-label-rate-ops/assets/README.md`
  - 说明本 Skill 的资产用途和安全边界。
- `human_review_ops/skills/efficiency-label-rate-ops/assets/test-prompts.json`
  - 覆盖完整场景链路，而不是单个能力。
  - 至少包含：
    - `should-trigger`: 打标率低效分级闭环。
    - `should-trigger`: 只做 owner routing / notification draft。
    - `should-trigger`: 只做 manual tracking。
    - `should-not-trigger`: 自动处置准确率等相邻场景。
    - `should-not-trigger`: 未授权真实群发或线上写状态。
- `human_review_ops/skills/efficiency-label-rate-ops/references/common.md`
  - 场景通用约束：只读、debug_only、禁止真实群发、禁止线上写入。

### 路径兼容配置

- `human_review_ops/configs/skill_path_registry.json`
  - 新旧路径共存的唯一配置源。
- `human_review_ops/tools/compat/skill_path_resolver.py`
  - Runner 和 validator 都调用这个 resolver，避免继续硬编码 `skills/analysis/scripts` 等路径。
- `human_review_ops/tools/compat/README.md`
  - 说明 `auto`、`canonical`、`legacy` 三种路径模式。

### 场景级验证器

- `human_review_ops/tools/validators/validate_efficiency_label_rate_ops_skill.py`
  - 新场景 Skill 的 standalone smoke。
  - 串联 perception、analysis、notification、resolution 四段脚本，但不执行 SQL、不发消息、不写状态。
- `human_review_ops/tools/validators/validate_skill_path_registry.py`
  - 校验 registry 中声明的新旧路径都存在，且 canonical / legacy fallback 可解析。

### 可选 wrapper 文件

如果后续要真正把旧脚本改成兼容 wrapper，而不是长期双份复制，需要新增或改造旧路径脚本：

- `human_review_ops/skills/perception/scripts/label_rate_perception.py`
- `human_review_ops/skills/analysis/scripts/label_rate_analysis.py`
- `human_review_ops/skills/notification/scripts/label_rate_notification_artifacts.py`
- `human_review_ops/skills/notification/scripts/render_label_rate_grading_card.py`
- `human_review_ops/skills/notification/scripts/resolve_label_rate_poc_routing.py`
- `human_review_ops/skills/notification/scripts/card_hash.py`
- `human_review_ops/skills/resolution/scripts/build_label_rate_manual_tracking.py`

wrapper 的目标是保持旧 import 和 CLI 不变，但内部转发到新 canonical 脚本或共享模块。

## 需要迁移或复制的文件

第一阶段建议使用“复制到新 Skill，旧路径保留”的方式。不要直接 `git mv`，否则现有 runner、validator、AgentBuddy 已发布 Skill 都会被打断。

### References

从全局场景包复制到新场景 Skill：

| 来源 | 目标 |
| --- | --- |
| `human_review_ops/references/scenarios/efficiency-label-rate/scenario_manifest.md` | `human_review_ops/skills/efficiency-label-rate-ops/references/scenario_manifest.md` |
| `human_review_ops/references/scenarios/efficiency-label-rate/metric_contract.md` | `human_review_ops/skills/efficiency-label-rate-ops/references/metric_contract.md` |
| `human_review_ops/references/scenarios/efficiency-label-rate/dataset_reference.md` | `human_review_ops/skills/efficiency-label-rate-ops/references/dataset_reference.md` |
| `human_review_ops/references/scenarios/efficiency-label-rate/analysis.md` | `human_review_ops/skills/efficiency-label-rate-ops/references/analysis.md` |
| `human_review_ops/references/scenarios/efficiency-label-rate/notification_templates.md` | `human_review_ops/skills/efficiency-label-rate-ops/references/notification_templates.md` |
| `human_review_ops/references/scenarios/efficiency-label-rate/owner_routing.md` | `human_review_ops/skills/efficiency-label-rate-ops/references/owner_routing.md` |
| `human_review_ops/references/scenarios/efficiency-label-rate/state_machine.md` | `human_review_ops/skills/efficiency-label-rate-ops/references/state_machine.md` |
| `human_review_ops/references/scenarios/efficiency-label-rate/sla.md` | `human_review_ops/skills/efficiency-label-rate-ops/references/sla.md` |
| `human_review_ops/references/scenarios/efficiency-label-rate/examples.md` | `human_review_ops/skills/efficiency-label-rate-ops/references/examples.md` |

旧能力 Skill 下这些快照暂时保留：

- `human_review_ops/skills/perception/references/scenarios/efficiency-label-rate.*.md`
- `human_review_ops/skills/analysis/references/scenarios/efficiency-label-rate.*.md`
- `human_review_ops/skills/notification/references/scenarios/efficiency-label-rate.*.md`
- `human_review_ops/skills/resolution/references/scenarios/efficiency-label-rate.*.md`

### Assets

复制到新场景 Skill：

| 来源 | 目标 |
| --- | --- |
| `human_review_ops/references/scenarios/efficiency-label-rate/mach_root_label_poc_mapping.json` | `human_review_ops/skills/efficiency-label-rate-ops/assets/mach_root_label_poc_mapping.json` |
| `human_review_ops/skills/notification/assets/efficiency-label-rate/card_schema_notes.md` | `human_review_ops/skills/efficiency-label-rate-ops/assets/card_schema_notes.md` |
| `human_review_ops/skills/notification/assets/efficiency-label-rate/low_efficiency_grading_card_template.json` | `human_review_ops/skills/efficiency-label-rate-ops/assets/low_efficiency_grading_card_template.json` |

旧路径暂时保留：

- `human_review_ops/skills/notification/assets/efficiency-label-rate/mach_root_label_poc_mapping.json`
- `human_review_ops/skills/notification/assets/efficiency-label-rate/card_schema_notes.md`
- `human_review_ops/skills/notification/assets/efficiency-label-rate/low_efficiency_grading_card_template.json`

### Scripts

复制到新场景 Skill：

| 来源 | 目标 |
| --- | --- |
| `human_review_ops/skills/perception/scripts/label_rate_perception.py` | `human_review_ops/skills/efficiency-label-rate-ops/scripts/label_rate_perception.py` |
| `human_review_ops/skills/analysis/scripts/label_rate_analysis.py` | `human_review_ops/skills/efficiency-label-rate-ops/scripts/label_rate_analysis.py` |
| `human_review_ops/skills/notification/scripts/label_rate_notification_artifacts.py` | `human_review_ops/skills/efficiency-label-rate-ops/scripts/label_rate_notification_artifacts.py` |
| `human_review_ops/skills/notification/scripts/render_label_rate_grading_card.py` | `human_review_ops/skills/efficiency-label-rate-ops/scripts/render_label_rate_grading_card.py` |
| `human_review_ops/skills/notification/scripts/resolve_label_rate_poc_routing.py` | `human_review_ops/skills/efficiency-label-rate-ops/scripts/resolve_label_rate_poc_routing.py` |
| `human_review_ops/skills/notification/scripts/card_hash.py` | `human_review_ops/skills/efficiency-label-rate-ops/scripts/card_hash.py` |
| `human_review_ops/skills/resolution/scripts/build_label_rate_manual_tracking.py` | `human_review_ops/skills/efficiency-label-rate-ops/scripts/build_label_rate_manual_tracking.py` |

旧路径暂时保留。等新路径稳定后，再决定是否把旧脚本改成 wrapper。

## 需要修改的配置文件

### `human_review_ops/skills/skill_release_manifest.json`

需要保留现有四个 entry：

- `perception`
- `analysis`
- `notification`
- `resolution`

新增一个 entry：

- `efficiency-label-rate-ops`

建议新增片段：

```json
{
  "skills": {
    "efficiency-label-rate-ops": {
      "skill_md": "efficiency-label-rate-ops/SKILL.md",
      "test_prompts": "efficiency-label-rate-ops/assets/test-prompts.json",
      "references": [
        "efficiency-label-rate-ops/references/common.md",
        "efficiency-label-rate-ops/references/scenario_manifest.md",
        "efficiency-label-rate-ops/references/metric_contract.md",
        "efficiency-label-rate-ops/references/dataset_reference.md",
        "efficiency-label-rate-ops/references/analysis.md",
        "efficiency-label-rate-ops/references/notification_templates.md",
        "efficiency-label-rate-ops/references/owner_routing.md",
        "efficiency-label-rate-ops/references/state_machine.md",
        "efficiency-label-rate-ops/references/sla.md",
        "efficiency-label-rate-ops/references/examples.md"
      ],
      "assets": [
        "efficiency-label-rate-ops/assets/README.md",
        "efficiency-label-rate-ops/assets/test-prompts.json",
        "efficiency-label-rate-ops/assets/card_schema_notes.md",
        "efficiency-label-rate-ops/assets/low_efficiency_grading_card_template.json",
        "efficiency-label-rate-ops/assets/mach_root_label_poc_mapping.json"
      ],
      "scripts": [
        {
          "path": "efficiency-label-rate-ops/scripts/label_rate_perception.py",
          "entrypoint": "python3 scripts/label_rate_perception.py --dry-run --request <request>",
          "smoke_command": "python3 human_review_ops/tools/validators/validate_efficiency_label_rate_ops_skill.py",
          "side_effects": ["none"],
          "outputs": ["scenario_key", "task_type", "readiness"]
        }
      ],
      "external_dependencies": ["openpyxl"],
      "release_assets": [
        "efficiency-label-rate-ops/SKILL.md",
        "efficiency-label-rate-ops/assets/test-prompts.json",
        "efficiency-label-rate-ops/references/common.md",
        "efficiency-label-rate-ops/references/scenario_manifest.md",
        "efficiency-label-rate-ops/references/metric_contract.md",
        "efficiency-label-rate-ops/references/dataset_reference.md",
        "efficiency-label-rate-ops/references/analysis.md",
        "efficiency-label-rate-ops/references/notification_templates.md",
        "efficiency-label-rate-ops/references/owner_routing.md",
        "efficiency-label-rate-ops/references/state_machine.md",
        "efficiency-label-rate-ops/references/sla.md",
        "efficiency-label-rate-ops/references/examples.md",
        "efficiency-label-rate-ops/assets/README.md",
        "efficiency-label-rate-ops/assets/card_schema_notes.md",
        "efficiency-label-rate-ops/assets/low_efficiency_grading_card_template.json",
        "efficiency-label-rate-ops/assets/mach_root_label_poc_mapping.json",
        "efficiency-label-rate-ops/scripts/label_rate_perception.py",
        "efficiency-label-rate-ops/scripts/label_rate_analysis.py",
        "efficiency-label-rate-ops/scripts/label_rate_notification_artifacts.py",
        "efficiency-label-rate-ops/scripts/render_label_rate_grading_card.py",
        "efficiency-label-rate-ops/scripts/resolve_label_rate_poc_routing.py",
        "efficiency-label-rate-ops/scripts/card_hash.py",
        "efficiency-label-rate-ops/scripts/build_label_rate_manual_tracking.py"
      ]
    }
  }
}
```

### `human_review_ops/configs/skill_path_registry.json`

新增配置示例：

```json
{
  "schema_version": "human_review_ops_skill_path_registry.v1",
  "default_path_mode": "auto",
  "validation_profiles": {
    "legacy_core": ["perception", "analysis", "notification", "resolution"],
    "scenario_label_rate": ["efficiency-label-rate-ops"],
    "all_releaseable": [
      "perception",
      "analysis",
      "notification",
      "resolution",
      "efficiency-label-rate-ops"
    ]
  },
  "scenario_skills": {
    "efficiency-label-rate": {
      "canonical_skill": "efficiency-label-rate-ops",
      "canonical_root": "human_review_ops/skills/efficiency-label-rate-ops",
      "legacy_capability_roots": {
        "perception": "human_review_ops/skills/perception",
        "analysis": "human_review_ops/skills/analysis",
        "notification": "human_review_ops/skills/notification",
        "resolution": "human_review_ops/skills/resolution"
      },
      "scripts": {
        "perception": {
          "canonical": "human_review_ops/skills/efficiency-label-rate-ops/scripts/label_rate_perception.py",
          "legacy": ["human_review_ops/skills/perception/scripts/label_rate_perception.py"]
        },
        "analysis": {
          "canonical": "human_review_ops/skills/efficiency-label-rate-ops/scripts/label_rate_analysis.py",
          "legacy": ["human_review_ops/skills/analysis/scripts/label_rate_analysis.py"]
        },
        "notification_artifacts": {
          "canonical": "human_review_ops/skills/efficiency-label-rate-ops/scripts/label_rate_notification_artifacts.py",
          "legacy": ["human_review_ops/skills/notification/scripts/label_rate_notification_artifacts.py"]
        },
        "poc_routing": {
          "canonical": "human_review_ops/skills/efficiency-label-rate-ops/scripts/resolve_label_rate_poc_routing.py",
          "legacy": ["human_review_ops/skills/notification/scripts/resolve_label_rate_poc_routing.py"]
        },
        "card_render": {
          "canonical": "human_review_ops/skills/efficiency-label-rate-ops/scripts/render_label_rate_grading_card.py",
          "legacy": ["human_review_ops/skills/notification/scripts/render_label_rate_grading_card.py"]
        },
        "card_hash": {
          "canonical": "human_review_ops/skills/efficiency-label-rate-ops/scripts/card_hash.py",
          "legacy": ["human_review_ops/skills/notification/scripts/card_hash.py"]
        },
        "manual_tracking": {
          "canonical": "human_review_ops/skills/efficiency-label-rate-ops/scripts/build_label_rate_manual_tracking.py",
          "legacy": ["human_review_ops/skills/resolution/scripts/build_label_rate_manual_tracking.py"]
        }
      },
      "assets": {
        "poc_mapping": {
          "canonical": "human_review_ops/skills/efficiency-label-rate-ops/assets/mach_root_label_poc_mapping.json",
          "legacy": [
            "human_review_ops/skills/notification/assets/efficiency-label-rate/mach_root_label_poc_mapping.json",
            "human_review_ops/references/scenarios/efficiency-label-rate/mach_root_label_poc_mapping.json"
          ]
        },
        "card_template": {
          "canonical": "human_review_ops/skills/efficiency-label-rate-ops/assets/low_efficiency_grading_card_template.json",
          "legacy": ["human_review_ops/skills/notification/assets/efficiency-label-rate/low_efficiency_grading_card_template.json"]
        }
      },
      "references": {
        "state_machine": {
          "canonical": "human_review_ops/skills/efficiency-label-rate-ops/references/state_machine.md",
          "legacy": [
            "human_review_ops/skills/resolution/references/scenarios/efficiency-label-rate.state_machine.md",
            "human_review_ops/references/scenarios/efficiency-label-rate/state_machine.md"
          ]
        },
        "analysis": {
          "canonical": "human_review_ops/skills/efficiency-label-rate-ops/references/analysis.md",
          "legacy": [
            "human_review_ops/skills/analysis/references/scenarios/efficiency-label-rate.analysis.md",
            "human_review_ops/references/scenarios/efficiency-label-rate/analysis.md"
          ]
        }
      }
    }
  }
}
```

### `human_review_ops/tools/packagers/build_skill_package.py`

当前 `SKILL_FILE_MAP` 只支持把一个场景包拆成四个能力 Skill 快照。需要新增场景 Skill 复制模式：

```python
SCENARIO_SKILL_FILE_MAP = {
    "scenario_manifest.md": "scenario_manifest.md",
    "metric_contract.md": "metric_contract.md",
    "dataset_reference.md": "dataset_reference.md",
    "analysis.md": "analysis.md",
    "notification_templates.md": "notification_templates.md",
    "owner_routing.md": "owner_routing.md",
    "state_machine.md": "state_machine.md",
    "sla.md": "sla.md",
    "examples.md": "examples.md",
}
```

新增参数：

```text
python3 human_review_ops/tools/packagers/build_skill_package.py efficiency-label-rate --target scenario-skill --write
python3 human_review_ops/tools/packagers/build_skill_package.py efficiency-label-rate --target legacy-capability-skills --write
```

兼容策略：

- `--target scenario-skill` 写入 `skills/efficiency-label-rate-ops/references/`。
- `--target legacy-capability-skills` 保留现有行为，写入四个能力 Skill 的 `references/scenarios/`。
- 默认第一阶段可以继续使用现有行为，避免影响旧发布链路。

## Runner 兼容性修改方案

### 需要修改的 runner 文件

这些 runner 当前硬编码了旧能力 Skill 脚本路径，需要改成 resolver：

- `human_review_ops/tools/runners/run_stage_1_real_readonly_label_rate_grading.py`
  - 当前硬编码：`skills/analysis/scripts`、`skills/notification/scripts`
- `human_review_ops/tools/runners/run_stage_2_label_rate_notification_draft.py`
  - 当前硬编码：`skills/notification/scripts`
- `human_review_ops/tools/runners/run_stage_2_label_rate_poc_routing.py`
  - 当前硬编码：`skills/notification/scripts`
- `human_review_ops/tools/runners/run_stage_2_label_rate_manual_tracking.py`
  - 当前硬编码：`skills/resolution/scripts`
- `human_review_ops/tools/runners/run_custom_label_rate_breakdown_e2e.py`
  - 当前硬编码：`skills/notification/scripts`

### Resolver 接口建议

新增 `human_review_ops/tools/compat/skill_path_resolver.py`：

```python
from __future__ import annotations

import json
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "human_review_ops" / "configs" / "skill_path_registry.json"


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def resolve_registered_path(
    scenario_key: str,
    section: str,
    key: str,
    mode: str | None = None,
) -> Path:
    registry = load_registry()
    mode = mode or os.environ.get("HRO_SKILL_PATH_MODE") or registry.get("default_path_mode", "auto")
    entry = registry["scenario_skills"][scenario_key][section][key]

    candidates: list[str]
    if mode == "canonical":
        candidates = [entry["canonical"]]
    elif mode == "legacy":
        candidates = entry.get("legacy", [])
    elif mode == "auto":
        candidates = [entry["canonical"], *entry.get("legacy", [])]
    else:
        raise ValueError(f"Unknown HRO_SKILL_PATH_MODE: {mode}")

    for raw_path in candidates:
        path = REPO_ROOT / raw_path
        if path.exists():
            return path

    raise FileNotFoundError(
        f"No path found for scenario={scenario_key}, section={section}, key={key}, mode={mode}"
    )


def resolve_script_dir(scenario_key: str, script_key: str, mode: str | None = None) -> Path:
    return resolve_registered_path(scenario_key, "scripts", script_key, mode).parent


def resolve_script_path(scenario_key: str, script_key: str, mode: str | None = None) -> Path:
    return resolve_registered_path(scenario_key, "scripts", script_key, mode)
```

### Runner 修改示例

把旧代码：

```python
NOTIFICATION_SCRIPTS = ROOT / "skills" / "notification" / "scripts"
sys.path.insert(0, str(NOTIFICATION_SCRIPTS))
```

改为：

```python
from human_review_ops.tools.compat.skill_path_resolver import resolve_script_dir

NOTIFICATION_SCRIPTS = resolve_script_dir(
    "efficiency-label-rate",
    "notification_artifacts",
)
sys.path.insert(0, str(NOTIFICATION_SCRIPTS))
```

需要注意：

- `auto` 模式下，新路径存在就用新路径。
- 如果新场景 Skill 尚未复制对应脚本，自动回退旧路径。
- 本地调试可以显式指定：

```bash
HRO_SKILL_PATH_MODE=legacy python3 human_review_ops/tools/runners/run_stage_2_label_rate_notification_draft.py
HRO_SKILL_PATH_MODE=canonical python3 human_review_ops/tools/runners/run_stage_2_label_rate_notification_draft.py
```

## Validator 兼容性修改方案

### 需要修改的 validator 文件

基础产品化 validator：

- `human_review_ops/tools/validators/validate_skill_productization.py`
  - 当前问题：`SKILLS = ("perception", "analysis", "notification", "resolution")` 写死。
  - 修改方向：从 `skill_release_manifest.json` 或 `skill_path_registry.json` 读取 skill choices。
  - 增加 `--profile legacy_core|scenario_label_rate|all_releaseable`。
- `human_review_ops/tools/validators/validate_skill_standalone_smoke.py`
  - 当前问题：`SKILLS` 和 `SCRIPT_LEVEL_VALIDATORS` 写死，resolution smoke 硬编码旧路径。
  - 修改方向：优先读取 manifest entry 的 `smoke_command`，没有再 fallback 到旧逻辑。
- `human_review_ops/tools/validators/validate_skill_package.py`
  - 当前问题：`SKILLS = ["perception", "analysis", "notification", "resolution"]` 写死。
  - 修改方向：从 manifest 读取可发布 Skill。
- `human_review_ops/tools/validators/validate_trae_stage_0_5.py`
  - 当前问题：四能力 Skill 集合写死。
  - 修改方向：区分 `legacy_core` 和 `scenario_label_rate` profile。

打标率脚本 validator：

- `human_review_ops/tools/validators/validate_label_rate_perception_scripts.py`
- `human_review_ops/tools/validators/validate_label_rate_analysis_scripts.py`
- `human_review_ops/tools/validators/validate_label_rate_notification_scripts.py`
- `human_review_ops/tools/validators/validate_label_rate_poc_mapping.py`
- `human_review_ops/tools/validators/validate_stage_2_label_rate_notification_draft.py`
- `human_review_ops/tools/validators/validate_custom_label_rate_breakdown_e2e.py`

这些文件里涉及 `skills/perception`、`skills/analysis`、`skills/notification`、`skills/resolution` 的常量，都需要改为 resolver。

### `validate_skill_productization.py` 具体修改方案

现状：

```python
SKILLS = ("perception", "analysis", "notification", "resolution")
```

建议改为：

```python
def load_registry() -> dict:
    path = HUMAN_REVIEW_OPS_ROOT / "configs" / "skill_path_registry.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def load_manifest_skill_names() -> tuple[str, ...]:
    if not MANIFEST_PATH.exists():
        return ("perception", "analysis", "notification", "resolution")
    manifest = load_json_object(MANIFEST_PATH)
    skills = manifest.get("skills", {})
    return tuple(sorted(skills))


def profile_skills(profile: str) -> tuple[str, ...]:
    registry = load_registry()
    profiles = registry.get("validation_profiles", {})
    if profile in profiles:
        return tuple(profiles[profile])
    return load_manifest_skill_names()
```

CLI 改为：

```python
parser.add_argument(
    "--profile",
    choices=("legacy_core", "scenario_label_rate", "all_releaseable"),
    default="legacy_core",
)
parser.add_argument("--skills", nargs="+", default=None)
args = parser.parse_args()
selected = tuple(args.skills) if args.skills else profile_skills(args.profile)
```

这样第一阶段默认仍校验旧四能力 Skill；需要验证新场景 Skill 时显式运行：

```bash
python3 human_review_ops/tools/validators/validate_skill_productization.py --strict --profile scenario_label_rate
python3 human_review_ops/tools/validators/validate_skill_productization.py --strict --profile all_releaseable
```

### `validate_skill_standalone_smoke.py` 具体修改方案

现状：

```python
SCRIPT_LEVEL_VALIDATORS = {
    "perception": "...validate_label_rate_perception_scripts.py",
    "analysis": "...validate_label_rate_analysis_scripts.py",
    "notification": "...validate_label_rate_notification_scripts.py",
}
```

建议改为：

```python
def smoke_commands_for_skill(skill: str, manifest: dict[str, Any]) -> list[str]:
    entry = manifest.get("skills", {}).get(skill, {})
    commands = []
    for script in entry.get("scripts", []):
        command = script.get("smoke_command")
        if command and command not in commands:
            commands.append(command)
    return commands
```

`run_skill_smoke` 改为：

```python
def run_skill_smoke(skill: str, manifest: dict[str, Any], issues: list[str]) -> None:
    commands = smoke_commands_for_skill(skill, manifest)
    if commands:
        for command in commands:
            run_shell_smoke(command, f"{skill} smoke: {command}", issues)
        return

    # Legacy fallback for old resolution entry before manifest smoke is normalized.
    if skill == "resolution":
        run_resolution_smoke(issues)
        return

    issues.append(f"No standalone smoke configured for Skill: {skill}")
```

同时将 resolution 旧路径：

```python
script_path = SKILLS_ROOT / "resolution" / "scripts" / "build_label_rate_manual_tracking.py"
```

改为：

```python
from human_review_ops.tools.compat.skill_path_resolver import resolve_script_path

script_path = resolve_script_path("efficiency-label-rate", "manual_tracking")
```

### 打标率 validator 路径修改示例

把旧代码：

```python
SCRIPT_DIR = HUMAN_REVIEW_OPS_ROOT / "skills" / "analysis" / "scripts"
SCRIPT_PATH = SCRIPT_DIR / "label_rate_analysis.py"
sys.path.insert(0, str(SCRIPT_DIR))
```

改为：

```python
from human_review_ops.tools.compat.skill_path_resolver import resolve_script_path

SCRIPT_PATH = resolve_script_path("efficiency-label-rate", "analysis")
SCRIPT_DIR = SCRIPT_PATH.parent
sys.path.insert(0, str(SCRIPT_DIR))
```

### `validate_label_rate_poc_mapping.py` 修改方案

当前 validator 比对全局 mapping 和旧 notification Skill asset mapping。迁移后需要三方一致：

1. 全局场景包：
   - `human_review_ops/references/scenarios/efficiency-label-rate/mach_root_label_poc_mapping.json`
2. 新场景 Skill：
   - `human_review_ops/skills/efficiency-label-rate-ops/assets/mach_root_label_poc_mapping.json`
3. 旧 notification Skill：
   - `human_review_ops/skills/notification/assets/efficiency-label-rate/mach_root_label_poc_mapping.json`

校验逻辑：

```text
global mapping == canonical scenario skill mapping == legacy notification skill mapping
```

第一阶段如果新场景 Skill 还没建立，可以允许 canonical path 缺失但发 warning；一旦进入发布阶段，必须改为 hard fail。

## AgentBuddy 发布配置修改

### `.agentbuddy/publish.yaml`

当前 items：

```yaml
registry:
  skills:
    - path: human_review_ops/skills
      items:
        - perception
        - analysis
        - notification
        - resolution
```

新增新场景 Skill，保留旧四能力 Skill：

```yaml
registry:
  skills:
    - path: human_review_ops/skills
      items:
        - perception
        - analysis
        - notification
        - resolution
        - efficiency-label-rate-ops
```

发布命令：

```bash
NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y agentbuddy@latest skill publish ./human_review_ops/skills/efficiency-label-rate-ops --group skills.byted.org/lizhongtao/hunman_review_ops --access restricted --region cn -y
```

检索命令：

```bash
NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y agentbuddy@latest skill find efficiency-label-rate
NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y agentbuddy@latest skill find label-rate
```

## 建议执行顺序

### Phase 0：冻结旧路径基线

- [x] 确认当前 main 分支 clean。
- [x] 跑旧链路 validator，记录基线：
  - `validate_skill_productization.py --strict`
  - `validate_skill_standalone_smoke.py`
  - `validate_label_rate_perception_scripts.py`
  - `validate_label_rate_analysis_scripts.py`
  - `validate_label_rate_notification_scripts.py`
- [x] 记录当前四能力 Skill AgentBuddy 版本。

### Phase 1：新增注册表和 resolver

- [x] 新建 `human_review_ops/configs/skill_path_registry.json`。
- [x] 新建 `human_review_ops/tools/compat/skill_path_resolver.py`。
- [x] 新建 `human_review_ops/tools/validators/validate_skill_path_registry.py`。
- [x] 正式入口 `run_label_rate_formal_flow.py` 已接入 resolver；历史 runner 后续分批迁移。

### Phase 2：新建场景 Skill

- [x] 新建 `human_review_ops/skills/efficiency-label-rate-ops/`。
- [x] 复制 references、assets、scripts。
- [x] 编写场景级 `SKILL.md`。
- [x] 编写场景级 `assets/test-prompts.json`。
- [x] 更新 `skill_release_manifest.json`。
- [x] 更新 `.agentbuddy/publish.yaml`。

### Phase 3：Runner 切换到 auto 模式

- [x] 修改正式打标率 runner `run_label_rate_formal_flow.py` 的脚本路径解析。
- [x] 默认 `HRO_SKILL_PATH_MODE=auto`。
- [ ] 分别验证历史 runner：
  - `HRO_SKILL_PATH_MODE=legacy`
  - `HRO_SKILL_PATH_MODE=canonical`
  - `HRO_SKILL_PATH_MODE=auto`

### Phase 4：Validator 支持新旧共存

- [x] `validate_skill_productization.py` 支持 `--profile`。
- [x] `validate_skill_standalone_smoke.py` 从 manifest 读取 smoke command。
- [ ] 打标率脚本 validator 改用 resolver。
- [ ] `validate_label_rate_poc_mapping.py` 改为三方一致校验。
- [x] 新增 `validate_efficiency_label_rate_ops_skill.py`。

### Phase 5：发布和观察

- [x] 发布 `efficiency-label-rate-ops` 到 AgentBuddy restricted 空间。
- [ ] 保留旧四能力 Skill，不立刻下线。
- [x] 正式本地入口将 `efficiency-label-rate` 优先指向新场景 Skill。
- [ ] 观察真实安装后的 AgentBuddy 路由和跨 Agent 调用命中情况。
- [ ] 观察至少一轮完整验证后，再评估旧四能力 Skill 是否降级为公共能力模板。

## 验收命令

旧路径兼容：

```bash
HRO_SKILL_PATH_MODE=legacy python3 human_review_ops/tools/validators/validate_skill_standalone_smoke.py --profile legacy_core
HRO_SKILL_PATH_MODE=legacy python3 human_review_ops/tools/validators/validate_label_rate_analysis_scripts.py
HRO_SKILL_PATH_MODE=legacy python3 human_review_ops/tools/validators/validate_label_rate_notification_scripts.py
```

新路径验证：

```bash
HRO_SKILL_PATH_MODE=canonical python3 human_review_ops/tools/validators/validate_skill_productization.py --strict --profile scenario_label_rate
HRO_SKILL_PATH_MODE=canonical python3 human_review_ops/tools/validators/validate_efficiency_label_rate_ops_skill.py
```

新旧全量：

```bash
HRO_SKILL_PATH_MODE=auto python3 human_review_ops/tools/validators/validate_skill_productization.py --strict --profile all_releaseable
HRO_SKILL_PATH_MODE=auto python3 human_review_ops/tools/validators/validate_skill_standalone_smoke.py --profile all_releaseable
python3 human_review_ops/tools/validators/validate_skill_path_registry.py
python3 human_review_ops/tools/validators/validate_agentbuddy_publish.py
git diff --check
```

Runner 验证：

```bash
HRO_SKILL_PATH_MODE=legacy python3 human_review_ops/tools/runners/run_stage_2_label_rate_notification_draft.py --output-dir /tmp/hro_legacy_notification
HRO_SKILL_PATH_MODE=canonical python3 human_review_ops/tools/runners/run_stage_2_label_rate_notification_draft.py --output-dir /tmp/hro_canonical_notification
HRO_SKILL_PATH_MODE=auto python3 human_review_ops/tools/runners/run_stage_2_label_rate_notification_draft.py --output-dir /tmp/hro_auto_notification
```

AgentBuddy 发布：

```bash
NPM_CONFIG_REGISTRY=http://bnpm.byted.org npx -y agentbuddy@latest skill publish ./human_review_ops/skills/efficiency-label-rate-ops --group skills.byted.org/lizhongtao/hunman_review_ops --access restricted --region cn -y
```

## 回滚方案

如果新场景 Skill 出现问题，不需要回滚旧四能力 Skill：

1. 将环境变量设为旧路径：

```bash
export HRO_SKILL_PATH_MODE=legacy
```

2. Agent 路由恢复为旧四能力 Skill：

```text
efficiency-label-rate -> perception -> analysis -> notification -> resolution
```

3. 暂停发布或安装 `efficiency-label-rate-ops`。

4. 保留 `skill_path_registry.json`，但将默认模式改为：

```json
{
  "default_path_mode": "legacy"
}
```

5. 继续运行旧 validator：

```bash
python3 human_review_ops/tools/validators/validate_skill_productization.py --strict --profile legacy_core
python3 human_review_ops/tools/validators/validate_skill_standalone_smoke.py --profile legacy_core
```

这个回滚不需要删除新场景 Skill 目录，只需要切换路径模式即可。
