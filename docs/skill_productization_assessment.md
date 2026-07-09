# 效率-打标率 Skill 产品化与复用性评估

## 目录

- [1. 评估结论](#1-评估结论)
- [2. 外部规范对齐](#2-外部规范对齐)
- [3. 当前架构现状](#3-当前架构现状)
- [4. 主要问题](#4-主要问题)
- [5. 目标边界](#5-目标边界)
- [6. 脚本下沉建议](#6-脚本下沉建议)
- [7. SKILL.md 增强标准](#7-skillmd-增强标准)
- [8. 分阶段改造路线](#8-分阶段改造路线)
- [9. 验收门禁](#9-验收门禁)

## 1. 评估结论

### 1.1 决策

当前 Agent + Skill + Tool/MCP/CLI 三层架构方向是合理的，但 `efficiency-label-rate` 场景还停留在“开发态可跑通”，尚未完全达到“Skill 可独立复用”的产品化标准。

下一阶段应采用以下方向：

1. 保留 `tools/runners/` 作为项目级端到端编排入口。
2. 将已经跑通、可复用、可被单个 Skill 独立调用的领域逻辑下沉到各 Skill 的 `scripts/`。
3. 将 `SKILL.md` 从“简要说明卡”升级为“可执行操作手册”，包含触发条件、决策树、输入输出、脚本调用、失败分支、禁止事项和验证步骤。
4. 强化发布包校验，确保单个 Skill 脱离当前 Agent 后仍具备最小可用能力。

### 1.2 判断

| 维度 | 当前状态 | 判断 | 说明 |
| --- | --- | --- | --- |
| Agent 编排 | 已基本成型 | 通过 | 能串联感知、分析、通知、解决，并支持 E2E 验证。 |
| 场景包资产 | 已基本成型 | 通过 | `references/scenarios/efficiency-label-rate/` 已承载口径、字段、路由、模板和样例。 |
| Skill 独立性 | 部分通过 | 需增强 | notification/resolution 有脚本；perception/analysis 缺少 `scripts/`。 |
| SKILL.md 可操作性 | 不足 | 需重写 | 当前多为字段清单，缺少流程、失败分支和脚本用法。 |
| 脚本职责边界 | 部分混杂 | 需拆分 | E2E runner 中混入了查询、转换、发布、发送等多类职责。 |
| 发布自包含 | 部分通过 | 需增强 | 快照和脚本编译有校验，但缺少“独立运行能力”校验。 |

## 2. 外部规范对齐

参考资料：

- Claude 官方 Skill 创建指南：`https://claude.com/blog/how-to-create-skills-key-steps-limitations-and-examples`
- Agent Skills 规范：`https://agentskills.io/specification`
- Agent Skills 最佳实践：`https://agentskills.io/skill-creation/best-practices`
- Skill description 优化：`https://agentskills.io/skill-creation/optimizing-descriptions`

### 2.1 规范要点

| 规范项 | 要求 | 当前差距 |
| --- | --- | --- |
| `SKILL.md` frontmatter | `name`、`description` 是触发 Skill 的核心入口，description 要说明何时使用。 | 当前 description 可触发，但边界和负例不足。 |
| 渐进披露 (Progressive_Disclosure) | `SKILL.md` 只放核心流程，细节放 `references/`、`assets/`、`scripts/`。 | references 已有，但 `SKILL.md` 没有明确“何时读取哪个文件”。 |
| 可执行脚本 (scripts) | 重复、易错、需要一致性的逻辑应沉淀为脚本。 | 关键逻辑多数仍在 `tools/runners/`。 |
| 资源资产 (assets) | 模板、schema、映射表应放入 Skill 包。 | notification 已较好，analysis/perception 仍偏文档化。 |
| 失败模式 | 应明确“如果 X 失败，执行 Y”。 | 当前 `SKILL.md` 基本缺失失败分支。 |
| 禁止事项 | 应列出不要做什么，避免误触发和越权。 | 当前只有简单调试约束，缺少反例清单。 |
| 触发评估 | 应有 should-trigger / should-not-trigger 测试。 | 当前没有针对四个 Skill 的触发测试集。 |

## 3. 当前架构现状

### 3.1 目录现状

```text
human_review_ops/
  skills/
    perception/
      SKILL.md
      references/
    analysis/
      SKILL.md
      references/
    notification/
      SKILL.md
      references/
      assets/
      scripts/
        card_hash.py
        render_label_rate_grading_card.py
        resolve_label_rate_poc_routing.py
    resolution/
      SKILL.md
      references/
      scripts/
        build_label_rate_manual_tracking.py
  tools/
    runners/
      run_stage_1_real_readonly_label_rate_grading.py
      run_stage_2_label_rate_notification_draft.py
      run_custom_label_rate_breakdown_e2e.py
      ...
    validators/
      validate_stage_1_real_readonly_label_rate_grading.py
      validate_stage_2_label_rate_notification_draft.py
      validate_custom_label_rate_breakdown_e2e.py
      ...
```

### 3.2 已经做得好的部分

| 部分 | 价值 |
| --- | --- |
| 根场景包 | 已经形成长期业务事实来源，避免规则散落在脚本里。 |
| Skill 快照 | 支持单 Skill 发布态的自包含方向。 |
| notification scripts | 已把卡片渲染、POC 路由、hash 校验下沉。 |
| resolution scripts | 已把 manual_tracking 构造下沉。 |
| validators | 已有较强的产物结构校验和发布校验。 |
| AgentBuddy 发布 | 已具备平台发布配置和基础门禁。 |

### 3.3 主要事实

| 位置 | 现状 |
| --- | --- |
| `human_review_ops/skills/perception/` | 只有 `SKILL.md` 和 references，无 scripts。 |
| `human_review_ops/skills/analysis/` | 只有 `SKILL.md` 和 references，无 scripts。 |
| `human_review_ops/skills/notification/scripts/` | 已有 3 个可复用脚本。 |
| `human_review_ops/skills/resolution/scripts/` | 已有 1 个可复用脚本。 |
| `human_review_ops/tools/runners/run_stage_1_real_readonly_label_rate_grading.py` | 约 930 行，包含 SQL 构造、查询执行、分级、POC 解析、结果包装。 |
| `human_review_ops/tools/runners/run_stage_2_label_rate_notification_draft.py` | 约 853 行，包含 CSV/XLSX、卡片、发送、草稿、send_plan。 |
| `human_review_ops/tools/runners/run_custom_label_rate_breakdown_e2e.py` | 约 1162 行，包含查询、表格、飞书导入、卡片、消息发送、POC 路由。 |

## 4. 主要问题

### 4.1 Skill 的独立性不足

当前很多可复用逻辑仍只能通过 `tools/runners/` 使用。对于外部 Agent 或只安装单个 Skill 的 runtime 来说，Skill 包本身缺少直接可调用的能力入口。

典型表现：

- 分析 Skill 不包含 QueryPlan、SQL 构造、分级规则执行脚本。
- 感知 Skill 不包含场景识别或 readiness 结构化生成脚本。
- 通知 Skill 已有核心脚本，但发送草稿、send_plan、CSV/XLSX 构造仍主要在 runner。
- 部分 runner 通过 `sys.path.insert` 临时引用 Skill 脚本，说明复用方向正确，但封装边界还没有稳定下来。

### 4.2 SKILL.md 过短，无法指导真实执行

当前四个 `SKILL.md` 都是简要说明，缺少以下内容：

- 输入对象示例。
- 输出 JSON 模板。
- 工作流决策树。
- 对应场景文件读取规则。
- 脚本调用方式。
- 失败模式。
- 禁止事项。
- 验收命令。
- should-trigger / should-not-trigger 示例。

这会导致 Agent 在真实使用时只能“猜”怎么执行，无法稳定复现已经跑通的最佳路径。

### 4.3 tools 与 skills 边界不够清晰

`tools/runners/` 当前同时承担了两类职责：

| 职责类型 | 是否应长期留在 tools | 说明 |
| --- | --- | --- |
| 端到端串联多个 Skill | 是 | 例如从查询到通知再到 manual tracking 的一键演练。 |
| 写 eval 产物和回归样例 | 是 | 属于项目级验证资产。 |
| 真实外部发送验证 | 是 | 需要 Agent/项目权限门禁。 |
| 构造打标率 SQL | 否 | 属于 analysis Skill 可复用能力。 |
| 执行低打标率分级规则 | 否 | 属于 analysis Skill 可复用能力。 |
| 构造通知草稿和 send_plan | 部分否 | 草稿结构应在 notification Skill；真实发送仍在 runner/Agent。 |
| 构造 manual_tracking | 否 | 已下沉到 resolution Skill，应继续保持。 |

## 5. 目标边界

### 5.1 三层职责

| 层级 | 应承担 | 不应承担 |
| --- | --- | --- |
| Agent | 意图识别、流程编排、权限卡点、人工确认、跨 Skill 调度、真实发送/写入审批。 | 不内置业务口径细节，不手写 SQL，不替代 Skill 的领域逻辑。 |
| Skill | 可复用领域能力、场景文件读取、输入输出契约、可执行脚本、局部验证。 | 不直接越权发送群消息，不写线上状态，不决定全局状态机。 |
| tools | 项目级 runner、validator、packager、E2E 回归、发布门禁。 | 不长期承载已稳定的领域逻辑。 |

### 5.2 单 Skill 独立可用标准

单个 Skill 脱离当前 Agent 后，至少应做到：

1. 能被 description 正确触发。
2. 能通过 `SKILL.md` 知道要读哪些 reference。
3. 能用 `scripts/` 完成本 Skill 的核心可复用动作。
4. 能输出稳定结构化结果。
5. 能在失败时给出明确阻断原因。
6. 能通过自身 smoke test 或项目级 validator 验证。

## 6. 脚本下沉建议

### 6.1 推荐目标结构

```text
human_review_ops/
  skills/
    perception/
      scripts/
        detect_label_rate_scenario.py
        build_label_rate_readiness.py
    analysis/
      scripts/
        build_label_rate_query_plan.py
        build_label_rate_sql.py
        run_label_rate_readonly_query.py
        grade_label_rate_results.py
        build_label_rate_analysis_outputs.py
    notification/
      scripts/
        build_label_rate_notification_draft.py
        build_label_rate_report_workbook.py
        build_label_rate_send_plan.py
        render_label_rate_grading_card.py
        resolve_label_rate_poc_routing.py
        card_hash.py
    resolution/
      scripts/
        build_label_rate_manual_tracking.py
  tools/
    runners/
      run_label_rate_full_workflow.py
      run_custom_label_rate_breakdown_e2e.py
    validators/
      validate_label_rate_skill_scripts.py
      validate_label_rate_full_workflow.py
```

### 6.2 迁移优先级

| 优先级 | 迁移对象 | 目标 Skill | 理由 |
| --- | --- | --- | --- |
| P0 | 打标率 SQL 构造、标准过滤片段、分级规则 | analysis | 当前最核心、最容易被复用，也最容易因 Agent 自由发挥而出错。 |
| P0 | QueryPlan 构造和 source_footer 构造 | analysis | 是分析链路的治理入口。 |
| P1 | 通知草稿、send_plan、CSV/XLSX 构造 | notification | 已经稳定，适合从 runner 拆为 reusable builder。 |
| P1 | readiness 生成、场景识别结构化输出 | perception | 能提升 Skill 独立使用时的可解释性。 |
| P2 | 自定义日期窗口低打标率 breakdown | analysis + notification | 先拆查询和展示，再保留 E2E runner。 |
| P2 | validator 中的 Skill 级断言 | 各 Skill 或 tools/validators | 先保留项目级 validator，再补 Skill smoke test。 |

### 6.3 不建议直接搬迁的内容

| 内容 | 保留位置 | 原因 |
| --- | --- | --- |
| E2E 总控流程 | `tools/runners/` | 涉及多个 Skill，属于 Agent/项目级编排。 |
| 真实飞书发送 | `tools/runners/` 或 Agent Tool | 有权限和人工确认风险，不应由 Skill 默认执行。 |
| eval 目录写入策略 | `tools/runners/` | 属于项目回归资产，不是 Skill 核心能力。 |
| AgentBuddy 发布和打包 | `tools/packagers/`、`tools/validators/` | 属于工程治理。 |

## 7. SKILL.md 增强标准

### 7.1 每个 Skill 必须包含的章节

```text
SKILL.md
  Frontmatter
    name
    description
    compatibility
    metadata.version
  1. Use When
  2. Do Not Use When
  3. Inputs
  4. Outputs
  5. Workflow
  6. Scenario Reference Loading
  7. Scripts
  8. Failure Modes
  9. Validation
  10. Examples
```

### 7.2 description 标准

description 应覆盖：

- 使用场景。
- 用户可能的自然语言表达。
- 核心输出。
- 边界。

示例方向：

```yaml
description: Use this skill when a human-review operations request needs to identify the efficiency-label-rate scenario, task type, metric intent, required scenario references, and data-readiness gate before analysis. It outputs scenario_key, task_type, run_mode, metric_ids, retrieval_policy, and blocking reasons. Not for executing SQL, sending notifications, or writing resolution status.
```

### 7.3 Workflow 标准

每个工作流步骤必须写清：

| 字段 | 说明 |
| --- | --- |
| Step | 执行动作。 |
| Input | 需要的输入。 |
| Read | 需要读取的 reference 或 asset。 |
| Script | 可选脚本。 |
| Output | 产物。 |
| Gate | 阻断条件。 |

### 7.4 Failure Modes 标准

必须显式写出：

| 失败模式 | 处理方式 |
| --- | --- |
| 场景无法唯一识别 | 输出候选场景和澄清问题，不进入分析。 |
| 必要字段缺失 | 输出 `readiness=blocked` 和缺失字段列表。 |
| QueryPlan 未通过断言 | 不执行查询，返回修复建议。 |
| bytedcli 查询失败 | 保留 SQL、错误码、stderr 摘要，禁止伪造结果。 |
| POC 映射缺失 | 使用占位 POC 并标注 `poc_confidence=low`，禁止自动 @未知对象。 |
| 发送目标未确认 | 只生成 `send_plan.json`，不发送。 |

## 8. 分阶段改造路线

### 8.1 Phase A：Skill 质量基线评估

目标：不改行为，先补齐评分和测试资产。

任务：

1. 为四个 Skill 建立 `test-prompts.json`。
2. 增加 should-trigger / should-not-trigger 查询集。
3. 使用 9 维 rubric 记录当前分数。
4. 更新 `validate_agentbuddy_publish.py`，检查 `SKILL.md` 必备章节。

验收：

- 四个 Skill 都有触发测试集。
- validator 能识别过短或缺章节的 `SKILL.md`。

### 8.2 Phase B：analysis Skill 脚本下沉

目标：让分析 Skill 独立具备打标率查询计划和分级能力。

任务：

1. 从 `run_stage_1_real_readonly_label_rate_grading.py` 抽出 SQL 构造、等级规则、结果标准化函数。
2. 放入 `human_review_ops/skills/analysis/scripts/`。
3. runner 改为调用 analysis scripts。
4. 保持现有 stage 1 validator 全部通过。

验收：

- analysis Skill 安装后可独立生成 QueryPlan 和 SQL。
- runner 行数明显下降，只保留编排和产物写入。

### 8.3 Phase C：notification Skill 脚本补全

目标：让通知 Skill 独立生成通知草稿、表格和发送计划。

任务：

1. 从 `run_stage_2_label_rate_notification_draft.py` 抽出 `build_notification_draft`、`build_send_plan`、CSV/XLSX builder。
2. 放入 `human_review_ops/skills/notification/scripts/`。
3. 真实发送仍保留在 runner 或 Agent Tool。

验收：

- notification Skill 可独立从分析结果生成 `notification_draft.json`、`send_plan.json`、Card JSON。
- 群发仍默认 blocked。

### 8.4 Phase D：perception Skill 可执行化

目标：让感知 Skill 不只描述场景，还能结构化输出路由结果。

任务：

1. 增加 `detect_label_rate_scenario.py`。
2. 增加 `build_label_rate_readiness.py`。
3. 将场景识别、任务类型、run_mode、readiness 输出模板固化。

验收：

- 输入自然语言后可输出 `scenario_key=efficiency-label-rate`、`task_type`、`metric_ids`、`retrieval_policy`。
- 无法识别时有明确阻断原因。

### 8.5 Phase E：发布包独立运行门禁

目标：证明 Skill 脱离当前 Agent 后仍可用。

任务：

1. 增加 `validate_skill_standalone_smoke.py`。
2. 对每个 Skill 执行最小脚本 smoke test。
3. 检查 scripts 是否只依赖包内 references/assets 或显式 CLI。
4. 生成 `skill_release_manifest.json`。

验收：

- 单 Skill 包含 `SKILL.md`、`references/`、`assets/`、`scripts/`。
- 无本机绝对路径。
- 脚本可编译、可 dry-run。
- 所有外部依赖写入 compatibility 或 metadata。

## 9. 验收门禁

### 9.1 架构门禁

| 门禁 | 通过标准 |
| --- | --- |
| Skill 自包含 | 单 Skill 发布包内包含执行所需的 references/assets/scripts。 |
| 职责清晰 | runner 只编排，Skill scripts 负责领域逻辑。 |
| 风险动作隔离 | 真实发送、写状态、更新配置不由 Skill 默认自动执行。 |
| 口径一致 | SQL 过滤片段来自 `metric_contract.md` 或 analysis scripts 的同源实现。 |
| POC 一致 | POC 映射来自 `mach_root_label_poc_mapping.json`，输出可 @mention 但不自动拉人。 |

### 9.2 Skill 文档门禁

| 门禁 | 通过标准 |
| --- | --- |
| description | 说明何时使用、输出什么、不适用什么，长度不超过 1024 字符。 |
| Workflow | 至少包含输入、读取、脚本、输出和 gate。 |
| Failure Modes | 至少覆盖场景识别失败、字段缺失、查询失败、发送未确认。 |
| Do Not Use | 明确禁止跨场景误用、越权发送、伪造查询结果。 |
| Examples | 至少 2 个正例、2 个反例。 |

### 9.3 回归命令

```bash
python3 human_review_ops/tools/validators/validate_scenario_package.py efficiency-label-rate
python3 human_review_ops/tools/validators/validate_agentbuddy_publish.py
python3 human_review_ops/tools/validators/validate_label_rate_poc_mapping.py
python3 human_review_ops/tools/validators/validate_stage_1_real_readonly_label_rate_grading.py
python3 human_review_ops/tools/validators/validate_stage_2_label_rate_notification_draft.py
python3 human_review_ops/tools/validators/validate_custom_label_rate_breakdown_e2e.py
```

## 10. 结论

当前项目的架构方向是正确的：Agent 负责编排，Skill 负责可复用业务能力，Tool/MCP/CLI 负责原子动作。但目前打标率场景的实现更偏“Agent 项目工程化可跑通”，还没有完全完成“Skill 产品化可独立复用”。

最合理的下一步不是推翻结构，而是做一次可控的产品化重构：

1. 先增强 `SKILL.md`，让 Agent 知道怎么用。
2. 再下沉稳定脚本，让 Skill 自己能做事。
3. 最后用 standalone smoke test 证明 Skill 脱离当前 Agent 也可用。

