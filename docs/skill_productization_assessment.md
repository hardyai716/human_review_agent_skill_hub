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

当前 Agent + Skill + Tool/MCP/CLI 三层架构方向仍然合理。相对初次评估，`efficiency-label-rate` 已从“开发态可跑通”推进到“可发布、可独立 dry-run、可回退”的产品化状态。

本次复核后的决策是：

1. 保留 `perception`、`analysis`、`notification`、`resolution` 四能力 Skill 作为 legacy compatibility path。
2. 将 `efficiency-label-rate-ops` 作为打标率场景 canonical path，承载完整打标率闭环发布包。
3. 用 `skill_path_registry.json` 和 `skill_path_resolver.py` 管理 `auto/canonical/legacy` 路径，避免 runner / validator 继续硬编码旧目录。
4. 真实群发、在线表格导入、线上状态写入继续留在 calling_agent / external_executor 的显式确认链路，不由 Skill 默认执行。

### 1.2 判断

| 维度 | 当前状态 | 判断 | 说明 |
| --- | --- | --- | --- |
| Agent 编排 | 已成型 | 通过 | `run_label_rate_formal_flow.py` 能串联感知、分析、通知和 external_executor，并已接入 resolver。 |
| 场景包资产 | 已成型 | 通过 | `references/scenarios/efficiency-label-rate/` 承载口径、字段、路由、模板和样例。 |
| 四能力 Skill 独立性 | 已达基线 | 通过 | perception、analysis、notification、resolution 均具备 `SKILL.md`、assets/test-prompts、scripts、release manifest 和 standalone smoke。 |
| 场景级 Skill | 已建立 | 通过 | `efficiency-label-rate-ops` 已具备完整 references/assets/scripts、`package_manifest.json` 和 selfcheck。 |
| 路径治理 | 已起步 | 需继续 | 已新增 registry/resolver，并切换正式入口；历史 runner / validator 仍需逐步迁移。 |
| 真实闭环 | 未完成 | 需增强 | open_id 安全解析、群推送确认链路、状态表 schema、幂等写入和回滚策略仍是后续重点。 |

## 2. 外部规范对齐

参考资料：

- Claude 官方 Skill 创建指南：`https://claude.com/blog/how-to-create-skills-key-steps-limitations-and-examples`
- Agent Skills 规范：`https://agentskills.io/specification`
- Agent Skills 最佳实践：`https://agentskills.io/skill-creation/best-practices`
- Skill description 优化：`https://agentskills.io/skill-creation/optimizing-descriptions`

### 2.1 规范要点

| 规范项 | 要求 | 当前差距 |
| --- | --- | --- |
| `SKILL.md` frontmatter | `name`、`description` 是触发 Skill 的核心入口，description 要说明何时使用。 | 四能力 Skill 与 `efficiency-label-rate-ops` 已具备。 |
| 渐进披露 (Progressive_Disclosure) | `SKILL.md` 只放核心流程，细节放 `references/`、`assets/`、`scripts/`。 | 已具备；场景级 Skill 还通过 `package_manifest.json` 记录源文件同步关系。 |
| 可执行脚本 (scripts) | 重复、易错、需要一致性的逻辑应沉淀为脚本。 | 已具备；剩余工作是让历史 runner/validator 统一通过 resolver 选择脚本路径。 |
| 资源资产 (assets) | 模板、schema、映射表应放入 Skill 包。 | 已具备；POC 映射、Card 模板、test-prompts 已进入场景级 Skill。 |
| 失败模式 | 应明确“如果 X 失败，执行 Y”。 | 已具备基线；后续需增加真实通知和状态写入失败样例。 |
| 禁止事项 | 应列出不要做什么，避免误触发和越权。 | 已具备；继续保留 `adjacent-misfire` 和 `unauthorized-action` 负向样例。 |
| 触发评估 | 应有 should-trigger / should-not-trigger 测试。 | 已具备，并已纳入 productization profile。 |

## 3. 当前架构现状

### 3.1 目录现状

```text
human_review_ops/
  skills/
    perception/
      SKILL.md
      references/
      assets/
      scripts/
        label_rate_perception.py
    analysis/
      SKILL.md
      references/
      assets/
      scripts/
        label_rate_analysis.py
        quality_inspection_accuracy_query.py
    notification/
      SKILL.md
      references/
      assets/
      scripts/
        card_hash.py
        label_rate_notification_artifacts.py
        render_label_rate_grading_card.py
        resolve_label_rate_poc_routing.py
        sheet_importer.py
    resolution/
      SKILL.md
      references/
      assets/
      scripts/
        build_label_rate_manual_tracking.py
    efficiency-label-rate-ops/
      SKILL.md
      package_manifest.json
      references/
      assets/
      scripts/
        label_rate_perception.py
        label_rate_analysis.py
        label_rate_notification_artifacts.py
        render_label_rate_grading_card.py
        resolve_label_rate_poc_routing.py
        card_hash.py
        sheet_importer.py
        build_label_rate_manual_tracking.py
  configs/
    skill_path_registry.json
  tools/
    compat/
      skill_path_resolver.py
    runners/
      run_label_rate_formal_flow.py
      run_stage_1_real_readonly_label_rate_grading.py
      run_stage_2_label_rate_notification_draft.py
      run_custom_label_rate_breakdown_e2e.py
      ...
    validators/
      validate_stage_1_real_readonly_label_rate_grading.py
      validate_stage_2_label_rate_notification_draft.py
      validate_custom_label_rate_breakdown_e2e.py
      validate_skill_path_registry.py
      ...
```

### 3.2 已经做得好的部分

| 部分 | 价值 |
| --- | --- |
| 根场景包 | 已经形成长期业务事实来源，避免规则散落在脚本里。 |
| Skill 快照 | 支持单 Skill 发布态的自包含方向。 |
| perception / analysis scripts | 已把场景识别、readiness、QueryPlan、SQL、分级规则和 source_footer 下沉。 |
| notification scripts | 已把通知草稿、send_plan、CSV/XLSX、Card、POC 路由、hash 校验和 sheet_importer 下沉。 |
| resolution scripts | 已把 manual_tracking 构造下沉。 |
| 场景级 Skill | `efficiency-label-rate-ops` 已成为打标率 canonical path，旧四能力路径保留兼容。 |
| 路径治理 | `skill_path_registry.json` 与 `skill_path_resolver.py` 已提供 `auto/canonical/legacy` 模式。 |
| validators | 已有较强的产物结构校验和发布校验。 |
| AgentBuddy 发布 | 已具备平台发布配置和基础门禁。 |

### 3.3 主要事实

| 位置 | 现状 |
| --- | --- |
| `human_review_ops/skills/perception/` | 已有场景识别脚本和 selfcheck。 |
| `human_review_ops/skills/analysis/` | 已有打标率分析脚本、质检准确率 SQL 生成脚本和 selfcheck。 |
| `human_review_ops/skills/notification/scripts/` | 已有通知产物、Card、POC 路由、hash、sheet_importer 和 selfcheck。 |
| `human_review_ops/skills/resolution/scripts/` | 已有 manual_tracking 和 selfcheck。 |
| `human_review_ops/skills/efficiency-label-rate-ops/` | 已有完整场景级发布包，包含四段脚本、场景 references/assets 和 package manifest。 |
| `human_review_ops/tools/runners/run_label_rate_formal_flow.py` | 已通过 resolver 加载脚本，默认 `auto` 优先场景级 canonical path。 |
| 历史阶段 runner / validator | 仍有部分硬编码旧四能力路径，后续按优先级迁移到 resolver。 |

## 4. 主要问题

### 4.1 历史 runner / validator 路径治理未完全收敛

当前正式入口已通过 registry/resolver 选择 canonical 或 legacy 路径，但部分历史阶段 runner 和 validator 仍直接拼接旧四能力 Skill 目录。

典型表现：

- `run_stage_1_real_readonly_label_rate_grading.py` 等历史 runner 仍可继续作为 legacy 回归入口，但不应再作为新开发模板。
- `validate_label_rate_*` 部分脚本级 validator 仍需要改为通过 resolver 定位 canonical / legacy 脚本。
- 新增 runner / validator 必须先登记 `skill_path_registry.json`，再调用 `skill_path_resolver.py`。

### 4.2 真实闭环能力仍在人工确认前

当前 Skill 已能生成通知和本地跟踪产物，但真实 POC 通知和状态闭环仍未产品化上线：

- 姓名级 POC 已可审计，但 open_id 安全存储和权限边界仍待确认。
- `send_plan` 已默认阻断群发，但真实群推送确认记录、发送前 validator 和目标收件人确认链路仍待补齐。
- `manual_tracking.json` 仍是本地记录；线上状态表 schema、幂等写入和回滚策略尚未完成。

### 4.3 tools 与 skills 边界仍需持续执行

`tools/runners/` 应继续只承担项目级编排、eval 写入和真实外部发送门禁；稳定领域逻辑必须留在 Skill scripts 或场景级 Skill 中。

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
python3 human_review_ops/tools/validators/validate_skill_path_registry.py
python3 human_review_ops/tools/validators/validate_efficiency_label_rate_ops_skill.py
python3 human_review_ops/tools/validators/validate_skill_productization.py --strict --profile all_releaseable
python3 human_review_ops/tools/validators/validate_skill_standalone_smoke.py --profile all_releaseable
python3 human_review_ops/tools/validators/validate_agentbuddy_publish.py
python3 human_review_ops/tools/validators/validate_label_rate_poc_mapping.py
python3 human_review_ops/tools/validators/validate_stage_1_real_readonly_label_rate_grading.py
python3 human_review_ops/tools/validators/validate_stage_2_label_rate_notification_draft.py
python3 human_review_ops/tools/validators/validate_custom_label_rate_breakdown_e2e.py
```

## 10. 结论

当前项目的架构方向是正确的：Agent 负责编排，Skill 负责可复用业务能力，Tool/MCP/CLI 负责原子动作。打标率场景已经完成四能力 Skill 产品化和场景级 Skill 自包含发布包建设；`efficiency-label-rate-ops` 是当前 canonical path，旧四能力路径是 legacy compatibility path。

最合理的下一步不是推翻结构，而是在现有产品化基线上继续收敛运行治理：

1. 将仍硬编码旧四能力路径的历史 runner / validator 分批改用 resolver。
2. 补齐 POC open_id 安全解析、真实群推送确认链路和发送前校验。
3. 设计状态表 schema、幂等写入、回滚策略和回收闭环。
4. 复制当前模式到质检准确率等新场景，保持根场景包、场景级 Skill、registry 和评估样例同步。
