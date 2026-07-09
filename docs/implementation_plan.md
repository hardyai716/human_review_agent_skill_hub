# 人审运营 Agent + Skill 开发落地实施方案

## 1. 目标与定位

本文是后续开发落地的唯一实施方案。它承接 `demo/architecture-preview.html` 中的目标架构，用于指导后续真实代码、配置、Skill、Agent 文件、场景包、评估样例和工具治理的建设。

本方案不再把“架构展示页优化计划”或“早期路线图”作为开发依据。后续执行时，以本文作为开发主计划，其他文档只作为背景资料或专项规范引用。

## 2. 开发成功标准

第一阶段成功不以“页面展示完整”为标准，而以一个可运行样板场景通过评估为标准。

必须证明：

- Agent 能根据任务识别场景、任务类型和运行模式。
- Agent 能安装并调用感知、分析、触达、解决四类 Skill。
- TRAE 自定义调试智能体「人审运营智能体」能作为前期开发入口，完成 Agent 路由、Skill 调用、场景包读取和工具边界验证。
- Skill 能通过一级索引加载正确场景包，而不是深层链式查找。
- 打标率主线场景能完成查询计划、字段选择、趋势 / 排序 / 分级 / 维度拆解计划、来源脚注和结果输出。
- 混淆字段、禁止字段、跨场景冲突、低置信度场景能被阻断或转人工确认。
- 场景包变更必须通过结构校验、评估样例、查询计划断言和人工验收后才能启用。

开发过程必须遵循 YAGNI 原则：每一步只开发当前阶段明确需要的能力，不预先设计或开发未来“可能用到”的逻辑、抽象、框架或泛化适配层。若下一步能力缺少真实输入、工具绑定或验收依据，应先生成准备度检查和阻断原因，而不是提前写空泛实现。

## 3. 开发范围

### 3.1 第一阶段纳入范围

- Agent 自身文件。
- TRAE 自定义调试智能体配置与调试检查清单。
- 四个通用 Skill 的最小可用模板。
- 一个阶段 1 主线样板场景：打标率。
- 一个阶段 0.5 架构占位场景：自动处置准确率分析/预警。
- 场景包一级索引和场景文件。
- `retrieval_policy`、`run_mode`、`task_type` 等核心调度契约。
- QueryPlan、source_footer、tool_call_record 等输出契约。
- 评估样例、查询计划断言、结构校验脚本。
- MVP 测试通知和人工跟进记录。

### 3.2 第一阶段不纳入范围

- 全量运营模块覆盖。
- 动态 Owner 路由线上自动触达。
- 自动催办、自动升级和完整 SLA 闭环。
- 自动修改业务配置或替代审批。
- 全量 Lark Base 或数据库工程化建设。
- 复杂前端产品化界面。

## 4. 目标目录结构

后续开发应收敛到以下结构：

```text
human_review_ops/
  references/
    scenarios/
      efficiency-auto-disposal-accuracy/
        scenario_manifest.md
        state_machine.md
        sla.md
        metric_contract.md
        dataset_reference.md
        owner_routing.md
        notification_templates.md
        analysis.md
        examples.md
      efficiency-label-rate/
        scenario_manifest.md
        state_machine.md
        sla.md
        metric_contract.md
        dataset_reference.md
        owner_routing.md
        notification_templates.md
        analysis.md
        examples.md
  agents/
    human_review_ops_agent/
      agent.md
      identity.md
      capability_manifest.md
      install_plan.md
      routing_policy.md
      permission_policy.md
      memory_policy.md
      evaluation_policy.md
      trae_debug_profile.md
      trae_debug_checklist.md
  skills/
    perception/
      SKILL.md
      references/
        common.md
        scenario-index.md
        scenarios/
          efficiency-auto-disposal-accuracy.manifest.md
          efficiency-auto-disposal-accuracy.metric_contract.md
          efficiency-auto-disposal-accuracy.dataset_reference.md
          efficiency-auto-disposal-accuracy.examples.md
          efficiency-label-rate.manifest.md
          efficiency-label-rate.metric_contract.md
          efficiency-label-rate.dataset_reference.md
          efficiency-label-rate.examples.md
    analysis/
      SKILL.md
      references/
        common.md
        scenario-index.md
        scenarios/
          efficiency-auto-disposal-accuracy.metric_contract.md
          efficiency-auto-disposal-accuracy.dataset_reference.md
          efficiency-auto-disposal-accuracy.analysis.md
          efficiency-auto-disposal-accuracy.examples.md
          efficiency-label-rate.metric_contract.md
          efficiency-label-rate.dataset_reference.md
          efficiency-label-rate.analysis.md
          efficiency-label-rate.examples.md
    notification/
      SKILL.md
      references/
        common.md
        scenario-index.md
        scenarios/
          efficiency-auto-disposal-accuracy.owner_routing.md
          efficiency-auto-disposal-accuracy.notification_templates.md
          efficiency-auto-disposal-accuracy.sla.md
          efficiency-label-rate.owner_routing.md
          efficiency-label-rate.notification_templates.md
          efficiency-label-rate.sla.md
    resolution/
      SKILL.md
      references/
        common.md
        scenario-index.md
        scenarios/
          efficiency-auto-disposal-accuracy.state_machine.md
          efficiency-auto-disposal-accuracy.sla.md
          efficiency-auto-disposal-accuracy.owner_routing.md
          efficiency-auto-disposal-accuracy.examples.md
          efficiency-label-rate.state_machine.md
          efficiency-label-rate.sla.md
          efficiency-label-rate.owner_routing.md
          efficiency-label-rate.examples.md
  evals/
    efficiency-auto-disposal-accuracy/
      eval_samples.jsonl
      expected_outputs.md
      query_plan_assertions.md
    efficiency-label-rate/
      eval_samples.jsonl
      expected_outputs.md
      query_plan_assertions.md
  schemas/
    event.schema.json
    analysis_result.schema.json
    resolution_result.schema.json
    retrieval_policy.schema.json
    tool_call_record.schema.json
  tools/
    packagers/
      build_skill_package.py
    policies/
      efficiency-auto-disposal.tool-policy.md
      efficiency-label-rate.tool-policy.md
    validators/
      validate_scenario_package.py
      validate_skill_package.py
      validate_query_plan.py
      validate_source_footer.py
```

说明：

- 目标态采用 Skill 兄弟目录下的 `human_review_ops/references/scenarios/` 维护完整场景流程包，这是长期唯一业务事实来源。
- 前期使用 TRAE 调试时，如果跨目录读取不稳定，可以把必要场景文件同步到 `human_review_ops/skills/*/references/scenarios/`，作为本地调试快照，先把 Skill 流程跑通。
- 本地调试快照不是长期主数据；后续若 TRAE/MCP 能稳定读取兄弟目录，Skill 应优先通过 `scenario-index.md` 指向根目录 `human_review_ops/references/scenarios/`。
- 如果未来要单 Skill 独立发布，再由打包脚本把 `human_review_ops/references/scenarios/` 中该 Skill 需要的文件复制进发布包，保证发布包自包含。
- 发布门禁必须校验根目录场景包与 Skill 内调试/发布快照的版本、摘要或 hash，避免多份文件发生口径漂移。

## 5. Claude Skill 规范落地要求

### 5.1 SKILL.md 基本要求

每个 `SKILL.md` 必须包含：

- YAML frontmatter。
- `name`：小写、数字、连字符，不使用泛化名称。
- `description`：第三人称描述能力和触发条件。
- `allowed-tools` / `disallowed-tools`：声明工具权限。
- 能力边界。
- 输入输出。
- 禁止事项。
- 一级参考索引。
- 验证要求。

建议命名：

| 目录 | Skill 名称 | 说明 |
| --- | --- | --- |
| `human_review_ops/skills/perception/` | `perceiving-ops-events` | 识别运营模块、指标、任务类型和数据就绪。 |
| `human_review_ops/skills/analysis/` | `analyzing-ops-metrics` | 生成查询计划、执行只读分析、输出归因和来源脚注。 |
| `human_review_ops/skills/notification/` | `routing-ops-notifications` | 生成通知卡片、建议责任人和升级对象。 |
| `human_review_ops/skills/resolution/` | `tracking-ops-resolution` | 记录人工处理状态、结论、证据和复查标记。 |

### 5.2 支持文件不要深层嵌套

允许物理目录分层，但不允许阅读路径分层。

要求：

- `SKILL.md` 只做轻入口。
- 每个 Skill 的 `references/scenario-index.md` 必须一级列出可读取场景文件的直接链接。
- 不允许 `common.md -> scenario.md -> dataset_reference.md` 这种链式阅读。
- 所有场景关键文件必须能从 `SKILL.md` 或 `scenario-index.md` 直接定位。
- 目标态场景流程包放在根目录 `human_review_ops/references/scenarios/{scenario_key}/`。
- 前期 TRAE 调试态允许在 `human_review_ops/skills/{skill_name}/references/scenarios/` 放置快照文件，但必须标明来源并可由脚本重新生成。
- 单 Skill 独立发布时，支持文件必须位于该 Skill 自己的 `references/` 目录内，由打包脚本从根目录场景包生成。
- 超过 100 行的参考文件顶部必须有目录。

### 5.3 场景流程包的两阶段引用策略

场景包属于 Skill 体系内的业务资产。它不直接执行任务，执行任务的仍然是感知、分析、通知、解决四个 Skill。

为兼顾前期 TRAE 调试和后期治理，场景文件采用两阶段引用策略：

| 阶段 | 场景文件位置 | 用途 | 约束 |
| --- | --- | --- | --- |
| 前期 TRAE 调试态 | `human_review_ops/skills/{skill_name}/references/scenarios/` | 保证单个 Skill 在 TRAE 中可直接跑通，减少跨目录读取风险。 | 只能作为根目录场景包的快照，不能手工漂移。 |
| 目标治理态 | `human_review_ops/references/scenarios/{scenario_key}/` | 长期维护完整场景流程包，供 Agent 和 Skill 按 `scenario_key` 检索。 | 作为唯一业务事实来源，变更必须走评审和回测。 |
| 单 Skill 发布态 | 发布包内 `references/scenarios/` | 独立发布时随 Skill 打包，保证包自包含。 | 由打包脚本从目标治理态生成。 |

| Skill | 一级索引文件 | 挂载的场景文件 | 用途 |
| --- | --- | --- | --- |
| 感知 Skill | `human_review_ops/skills/perception/references/scenario-index.md` | `references/scenarios/*.manifest.md`、`*.metric_contract.md`、`*.dataset_reference.md`、`*.examples.md` | 识别场景、指标、任务类型、数据就绪。 |
| 分析 Skill | `human_review_ops/skills/analysis/references/scenario-index.md` | `references/scenarios/*.metric_contract.md`、`*.dataset_reference.md`、`*.analysis.md`、`*.examples.md` | 生成 QueryPlan、选择字段、归因分析。 |
| 通知 Skill | `human_review_ops/skills/notification/references/scenario-index.md` | `references/scenarios/*.owner_routing.md`、`*.notification_templates.md`、`*.sla.md` | 生成通知、POC / 触达对象路由、判断升级。 |
| 解决 Skill | `human_review_ops/skills/resolution/references/scenario-index.md` | `references/scenarios/*.state_machine.md`、`*.sla.md`、`*.owner_routing.md`、`*.examples.md` | 推进状态、回收结论、关闭或复查。 |

示例索引：

```markdown
# human_review_ops/skills/analysis/references/scenario-index.md

## efficiency-label-rate

- 调试态指标契约：scenarios/efficiency-label-rate.metric_contract.md
- 调试态数据集说明：scenarios/efficiency-label-rate.dataset_reference.md
- 调试态分析规则：scenarios/efficiency-label-rate.analysis.md
- 调试态样例与边界：scenarios/efficiency-label-rate.examples.md
- 目标态场景包：../../../references/scenarios/efficiency-label-rate/
```

## 6. Agent 自身文件开发任务

### 6.1 `agent.md`

定义：

- Agent 目标。
- 服务对象。
- 默认运行模式。
- 可调用能力。
- 不做事项。
- 审计要求。

验收：

- 能明确说明该 Agent 是人审运营调度器，而不是数据查询脚本或自动审批系统。

### 6.2 `identity.md`

定义：

- Agent 身份。
- 对运营用户的交互原则。
- 什么时候建议转人工。
- 什么时候必须拒绝。

验收：

- 能覆盖低置信度、权限不足、高风险动作、数据缺失等情况。

### 6.3 `capability_manifest.md`

定义：

- 已安装 Skill。
- Skill 版本。
- 可用状态。
- 依赖的场景包。

验收：

- Agent 能知道当前可调度哪些 Skill，哪些 Skill 只是草稿或灰度状态。

### 6.4 `routing_policy.md`

定义：

- `run_mode`。
- `task_type`。
- `scenario_key`。
- 场景候选。
- 人工确认阈值。

必须支持：

```text
debug_only
full_workflow
query_only
owner_lookup_only
notification_only
resolution_only
partial_workflow
```

### 6.5 `permission_policy.md`

定义：

- 只读工具。
- 可写工具。
- 需人工确认工具。
- 禁止动作。
- Tool/MCP/CLI 白名单。

验收：

- 写状态、发通知、更新配置等动作不能绕过权限策略。

### 6.6 `trae_debug_profile.md`

定义 TRAE 自定义调试智能体「人审运营智能体」的使用方式。该文件不是线上 Agent 身份文件，而是前期开发调试入口说明。

必须定义：

- 调试智能体名称：`人审运营智能体`。
- 调试目标：验证 Agent 路由、Skill 调用、场景包读取、Tool/MCP/CLI 权限边界。
- 启用能力：感知、分析、通知、解决四个 Skill。
- 默认运行模式：`debug_only`，优先只读，不执行真实写入。
- 场景读取策略：优先验证 `human_review_ops/references/scenarios/` 跨目录读取；如 TRAE 不稳定，则使用 `human_review_ops/skills/*/references/scenarios/` 调试快照。
- 工具策略：先使用 mock 或只读 Tool；真实通知、写状态、更新配置必须人工确认。
- 调试样例：打标率、P0/P1/P2/notice 分级、机审一级标签维度拆解、跨场景拒绝、低信息量澄清。

验收：

- 能从自然语言问题识别 `scenario_key`、`task_type` 和 `run_mode`。
- 能按 `scenario-index.md` 加载正确场景文件，不误读无关场景。
- 能分别调通感知、分析、通知、解决 Skill。
- 能输出 QueryPlan、source_footer、routing evidence、manual tracking 等关键结构。
- 能证明跨目录 `human_review_ops/references/scenarios/` 可读；若不可读，能切换到 Skill 内调试快照。
- 不能发送真实通知、写入线上状态或更新业务配置，除非经过人工确认。

### 6.7 `trae_debug_checklist.md`

定义每次使用「人审运营智能体」调试时必须记录的检查项。

必须记录：

- 输入问题。
- 识别出的 `scenario_key`、`task_type`、`run_mode`。
- 调用的 Skill。
- 读取的场景文件路径。
- 是否使用根目录 `human_review_ops/references/scenarios/`。
- 是否使用 Skill 内调试快照。
- Tool/MCP/CLI 调用记录。
- 是否触发人工确认。
- 输出是否包含 QueryPlan、source_footer、Owner 依据或 manual tracking。
- 失败原因和下一步修复动作。

验收：

- 每个样板调试用例都有可复盘记录。
- 每次失败都能归因到路由、检索、Skill 输出、工具权限或场景包内容之一。
- 调试检查清单可以作为后续评估样例和回归测试的输入。

## 7. 四个 Skill 开发任务

### 7.1 感知 Skill

文件：

- `human_review_ops/skills/perception/SKILL.md`
- `human_review_ops/skills/perception/references/common.md`
- `human_review_ops/skills/perception/references/scenario-index.md`

职责：

- 识别运营模块。
- 识别指标/对象。
- 识别任务类型。
- 判断数据就绪等级。
- 生成场景候选和置信度。

必须输出：

- `scenario_key`
- `related_scenarios`
- `metric_ids`
- `readiness`
- `retrieval_policy` 前置材料

### 7.2 分析 Skill

文件：

- `human_review_ops/skills/analysis/SKILL.md`
- `human_review_ops/skills/analysis/references/common.md`
- `human_review_ops/skills/analysis/references/scenario-index.md`

职责：

- 生成 QueryPlan。
- 执行只读分析。
- 校验字段和过滤条件。
- 输出归因、影响评估、规则命中和来源脚注。

禁止：

- 未通过 QueryPlan 断言时执行查询。
- 使用 `dataset_reference.md` 标记的禁止字段。
- 绕过 `metric_contract.md` 自行解释口径。

### 7.3 通知 Skill

文件：

- `human_review_ops/skills/notification/SKILL.md`
- `human_review_ops/skills/notification/references/common.md`
- `human_review_ops/skills/notification/references/scenario-index.md`

职责：

- 基于分析结果生成 AI Summary 卡片。
- MVP 阶段只发送固定人/群。
- 输出 POC / 触达对象路由计划和升级对象。

禁止：

- 未经确认扩大通知范围。
- 未带来源脚注进入自动触达。

### 7.4 解决 Skill

文件：

- `human_review_ops/skills/resolution/SKILL.md`
- `human_review_ops/skills/resolution/references/common.md`
- `human_review_ops/skills/resolution/references/scenario-index.md`

职责：

- 记录人工状态。
- 记录人工结论。
- 归档证据。
- 标记是否继续观察。
- 标记是否进入迭代候选。

禁止：

- 未完成动作、证据、结论三件套时自动关闭。

## 8. 阶段 1 主线样板场景：效率模块 / 打标率

### 8.1 场景目标

验证 Agent 能在效率模块下识别打标率低效 reason 相关任务，并完成：

- 场景识别。
- 指标口径加载。
- 数据集字段选择。
- QueryPlan 生成。
- 低效分级或维度拆解计划。
- 只读查询前校验。
- 分析结果结构化输出。
- 责任人建议。
- 来源脚注输出。

### 8.2 场景包文件

目标态根目录路径：

```text
human_review_ops/references/scenarios/efficiency-label-rate/
```

TRAE 调试快照 / 未来发布包内路径示例：

```text
human_review_ops/skills/analysis/references/scenarios/efficiency-label-rate.metric_contract.md
human_review_ops/skills/analysis/references/scenarios/efficiency-label-rate.dataset_reference.md
human_review_ops/skills/analysis/references/scenarios/efficiency-label-rate.analysis.md
human_review_ops/skills/analysis/references/scenarios/efficiency-label-rate.examples.md
```

`human_review_ops/references/scenarios/` 是长期维护的完整场景流程包。前期 TRAE 调试时，可以把其中必要文件同步到 Skill 内部 `human_review_ops/skills/{skill_name}/references/scenarios/` 快照目录；实际运行时，Agent 先选择 Skill，再由该 Skill 的 `references/scenario-index.md` 决定读取本地快照还是目标态场景包。

文件：

- `scenario_manifest.md`
- `state_machine.md`
- `sla.md`
- `metric_contract.md`
- `dataset_reference.md`
- `owner_routing.md`
- `notification_templates.md`
- `analysis.md`
- `examples.md`

### 8.3 `metric_contract.md`

必须定义：

- 指标 ID。
- 中文指标名。
- 分子。
- 分母。
- 排除项。
- 标准过滤条件。
- 支持维度。
- 支持时间窗口。
- 口径 Owner。
- 版本。

### 8.4 `dataset_reference.md`

必须定义：

- 推荐数据集。
- 推荐字段。
- 混淆字段。
- 禁止字段。
- 字段粒度。
- 数据刷新。
- 血缘说明。
- 字段选择示例。

### 8.5 `analysis.md`

必须定义：

- 整体趋势分析。
- 策略维度归因。
- 队列维度归因。
- 风险域维度归因。
- 撞线预警规则。
- 低置信度降级规则。

## 9. 检索与调度契约

### 9.1 `retrieval_policy.schema.json`

新增文件：

- `human_review_ops/schemas/retrieval_policy.schema.json`

字段：

- `scenario_key`
- `related_scenarios`
- `allowed_paths`
- `denied_paths`
- `metric_ids`
- `confidence_threshold`
- `tie_break_rules`
- `fallback_to_human`

### 9.2 `tool_call_record.schema.json`

新增文件：

- `human_review_ops/schemas/tool_call_record.schema.json`

字段：

- `tool_call_id`
- `caller`
- `tool_name`
- `command_name`
- `permission_level`
- `source_tier`
- `scenario_key`
- `metric_id`
- `review_required`
- `fallback_reason`
- `execution_mode`
- `real_query_executed`
- `input_summary`
- `output_summary`
- `status`
- `latency_ms`
- `error_reason`

## 10. 评估与发布门禁

### 10.1 评估样例

路径：

```text
human_review_ops/evals/efficiency-label-rate/eval_samples.jsonl
```

至少包含：

- 正例：近 7 天高完审低打标 reason 分析。
- 正例：低打标率策略分 P0/P1/P2/notice。
- 正例：按机审一级标签拆解低打标 reason。
- 正例：打标率和完审量趋势。
- 反例：自动处置准确率下降，不应命中打标率场景。
- 反例：质检准确率下降，不应命中打标率场景。
- 混淆字段：字段名相似但口径不同。
- 低置信度：缺少指标或时间窗口。

### 10.2 发布门禁

场景包进入可用状态前必须通过：

- 文件结构校验。
- 指标契约完整性校验。
- 数据集说明完整性校验。
- QueryPlan 断言。
- 反例拒绝。
- 来源脚注完整性检查。
- 人工验收。

失败处理：

- P0/P1 样例失败：阻断发布。
- 混淆字段未拒绝：阻断发布。
- 来源脚注缺失：阻断发布。
- 低置信度未转人工：阻断发布。

## 11. 开发阶段

### 阶段 0：目录和模板初始化

交付：

- `human_review_ops/agents/human_review_ops_agent/`
- `human_review_ops/skills/perception/`
- `human_review_ops/skills/analysis/`
- `human_review_ops/skills/notification/`
- `human_review_ops/skills/resolution/`
- `human_review_ops/references/scenarios/efficiency-auto-disposal-accuracy/`
- `human_review_ops/references/scenarios/efficiency-label-rate/`
- `human_review_ops/skills/*/references/scenarios/` 中的样板场景发布文件
- `human_review_ops/evals/efficiency-auto-disposal-accuracy/`
- `human_review_ops/evals/efficiency-label-rate/`
- `human_review_ops/tools/policies/`

验收：

- 目录结构符合本文。
- 每个 `SKILL.md` 有合法 frontmatter。
- 每个 Skill 有一级 `scenario-index.md`。

### 阶段 0.5：TRAE 调试智能体跑通

交付：

- TRAE 自定义智能体：`人审运营智能体`。
- `human_review_ops/agents/human_review_ops_agent/trae_debug_profile.md`。
- `human_review_ops/agents/human_review_ops_agent/trae_debug_checklist.md`。
- 打标率样板调试用例。
- Skill 内调试快照与根目录场景包读取验证记录。

调试顺序：

1. 创建 TRAE 自定义智能体「人审运营智能体」。
2. 绑定或安装感知、分析、通知、解决四个 Skill。
3. 使用 Skill 内 `human_review_ops/skills/{skill}/references/scenarios/` 调试快照跑通最小流程。
4. 验证是否能稳定读取根目录 `human_review_ops/references/scenarios/`。
5. 逐步接入只读 Tool/MCP/CLI。
6. 查询类任务优先跑通 QueryPlan 后的只读执行与依据记录；通知草稿、POC / 触达对象路由和人工处理记录只在用户明确要求，或分析结果触发治理/升级条件时生成，不发送真实通知、不写线上状态。

验收：

- 查询类任务能进入 `query_only` 或 `partial_workflow`。
- 找人类任务能进入 `owner_lookup_only`，并输出 POC / 触达对象路由依据和置信度。
- 通知类任务只能生成草稿或测试卡片，不能绕过人工确认。
- 解决类任务只能记录人工状态、结论、证据和是否继续观察。
- 若根目录 `human_review_ops/references/scenarios/` 跨目录读取失败，必须明确记录失败原因，并继续使用 Skill 内调试快照。
- 若根目录跨目录读取稳定，则后续优先让 `scenario-index.md` 指向根目录场景包。

### 阶段 1：样板场景跑通

交付：

- 打标率场景包。
- QueryPlan 断言。
- 来源脚注模板。
- 只读查询 Tool 策略。
- 只读执行结果、证据字段和 provenance 记录。

验收：

- 正例命中率达到标准。
- 反例拒绝率达到标准。
- 混淆字段拒绝率达到标准。
- QueryPlan 校验通过后，Agent 应按用户问题执行可用的 mock / 只读查询链路。
- 输出包含 QueryPlan、tool_call_record、source_footer、数据来源、指标口径和分析依据。
- 不把通知草稿、POC / 触达对象路由或人工处理状态作为查询类任务的默认产出。
- 只有覆盖样本池、未治理字段、权限不足、真实通知、线上写入或高风险动作才要求人工确认。

执行原则：

- Agent 不应把每一步都转成人工确认。
- 当用户问题明确、场景命中、QueryPlan 通过断言、数据源属于允许来源、工具权限为只读时，Agent 应直接执行可用的只读查询或 mock 查询链路。
- 执行后必须记录依据，包括数据来源、指标口径、时间窗口、过滤条件、质量检查、tool_call_record、source_footer 和 provenance。
- 只有信息不足、字段无法确认、用户要求覆盖标准样本池、命中禁止来源、权限不足、真实通知、线上写入或高风险动作时，才进入澄清或人工确认。
- POC / 触达对象路由不是查询类任务的前置步骤；只有结果需要治理跟进、通知、升级或用户明确询问“找谁”时才生成。

### 阶段 2：局部调度能力

交付：

- `query_only`
- `owner_lookup_only`
- `notification_only`
- `resolution_only`
- `partial_workflow`

验收：

- 局部任务不绕过 `metric_contract`、`dataset_reference` 和 `retrieval_policy`。
- 单独责任人定位能输出依据和置信度。

### 阶段 3：发布治理

交付：

- 场景包状态：draft、reviewing、enabled、disabled、rollback。
- 发布校验脚本。
- 回滚记录。

验收：

- 任一阻断条件失败时不能启用场景包。
- 可回滚到上一版场景包。

### 阶段 4：扩展到更多模块

交付：

- 效率模块更多指标。
- 质量模块样板场景。
- 成本模块样板场景。

验收：

- 新模块复用同一套 Skill，不复制 Skill。
- 新场景只新增场景包和评估样例。

## 12. 架构合规评估与开发进展看板

### 12.1 当前架构合规结论

当前架构与本实施方案的核心要求一致，阶段 0.5 TRAE 调试验证已完成，阶段 1 感知 + 分析链路已围绕打标率场景跑通。阶段 2 已完成低打标率分级结果的通知卡片草稿、POC / 触达对象路由占位、群推送门禁、本地人工处理状态记录和局部调度回归。

| 检查项 | 当前状态 | 结论 |
| --- | --- | --- |
| 运行态开发目录 | 已统一收敛到 `human_review_ops/`。 | 通过 |
| Agent 元文件 | 已具备身份、能力、安装、路由、权限、记忆、评估和 TRAE 调试文件。 | 通过 |
| 四类 Skill 模板 | 感知、分析、通知、解决 Skill 已有最小 `SKILL.md`、`common.md`、`scenario-index.md`。 | 通过 |
| 场景流程包 | 已具备自动处置准确率占位场景包；阶段 1 主线已切换为打标率场景包。 | 通过 |
| TRAE 调试快照 | 四类 Skill 已具备样板场景调试快照。 | 通过 |
| 评估样例 | 已具备 `eval_samples.jsonl`、`expected_outputs.md`、`query_plan_assertions.md`。 | 通过 |
| Schema 契约 | 已具备 event、analysis_result、resolution_result、retrieval_policy、tool_call_record。 | 通过 |
| Tool 策略 | 已具备自动处置准确率和打标率的只读工具策略。 | 通过 |
| 打包和校验脚本 | 已具备最小 packager 和 validator 脚本。 | 通过 |
| TRAE 调试验证 | 已在 TRAE 中确认「人审运营智能体 / human-review-operator」存在，阶段 0.5 样例记录与校验通过；用户已手动复核并保存提示词和调用条件。 | 通过 |
| 阶段 1 最小链路 | 打标率场景已生成 `scenario_key`、`task_type`、QueryPlan、source_footer，并通过只读校验。 | 通过 |
| 阶段 1 P1 mock Tool | 已生成 mock / 只读 `tool_call_record`，并校验不会执行真实查询、通知或写状态。 | 通过 |
| 阶段 1 P1 只读执行 | 已生成 mock `readonly_execution`、`analysis_result` 和 `provenance`，并校验不会发送通知或写状态。 | 通过 |
| 阶段 1 P1 真实只读查询 | 已通过 Aeolus 数据集 `3888816` 执行打标率只读查询，支持 `--days`、`--dimensions` 和 `--query-mode`。 | 通过 |
| 阶段 1 P1 低打标率分级 | 已通过真实只读 SQL 输出 notice/P2/P1/P0 分级结果、综合去重结果、evidence 和 provenance。 | 通过 |

### 12.2 已完成任务看板

| 阶段 | 优先级 / 类型 | 已完成内容 | 验收标准 / 产物 | 状态 |
| --- | --- | --- | --- | --- |
| 基础建设 | 基础 | 初始化 GitHub 仓库并推送主分支。 | 仓库地址：`https://github.com/hardyai716/human_review_agent_skill_hub.git`。 | 已完成 |
| 基础建设 | 基础 | 将运行态开发产物统一收敛到 `human_review_ops/`。 | 运行态 Agent、Skill、场景包、eval、schema、tool 均位于 `human_review_ops/`。 | 已完成 |
| 基础建设 | 基础 | 创建人审运营 Agent 最小元文件。 | 具备身份、能力、安装、路由、权限、记忆、评估和 TRAE 调试文件。 | 已完成 |
| 基础建设 | 基础 | 创建四类通用 Skill 最小模板。 | 感知、分析、通知、解决 Skill 均具备 `SKILL.md`、`common.md`、`scenario-index.md`。 | 已完成 |
| 基础建设 | 基础 | 创建样板场景包。 | 已具备自动处置准确率占位场景包和打标率主线场景包。 | 已完成 |
| 基础建设 | 基础 | 创建 Skill 内调试快照。 | 四类 Skill 已具备样板场景调试快照。 | 已完成 |
| 基础建设 | 基础 | 创建评估样例和 QueryPlan 断言。 | `eval_samples.jsonl`、`expected_outputs.md`、`query_plan_assertions.md` 已具备。 | 已完成 |
| 基础建设 | 基础 | 创建 schema、工具策略、打包和校验脚本最小实现。 | 已具备 retrieval_policy、tool_call_record schema、工具权限策略、packager 和 validator。 | 已完成 |
| 基础建设 | 文档 | 更新 HTML 架构演示和核心文档路径。 | 架构演示与核心文档路径已同步到 `human_review_ops/`。 | 已完成 |
| 阶段 0.5 | P0 | 在 TRAE 创建自定义智能体「人审运营智能体」。 | 能加载 Agent 调试配置和四类 Skill；UI 已确认，配置已人工复核。 | 已完成 |
| 阶段 0.5 | P0 | 使用 5 条样例跑调试闭环。 | 每条样例都有 `trae_debug_checklist.md` 格式记录；本轮覆盖 6 条样例。 | 已完成 |
| 阶段 0.5 | P0 | 验证 `human_review_ops/references/scenarios/` 跨目录读取。 | 根目录读取通过；Skill 快照可作为回退。 | 已完成 |
| 阶段 0.5 | 校验 | 新增阶段 0.5 校验脚本。 | `validate_trae_stage_0_5.py` 校验通过。 | 已完成 |
| 阶段 1 | P0 | 以打标率为主线，跑通感知 + 分析最小链路。 | 输出 `scenario_key`、`task_type`、QueryPlan、source_footer；运行记录：`20260708_minimal_chain.md`。 | 已完成 |
| 阶段 1 | P0 | 新增阶段 1 最小链路 runner 和校验脚本。 | `run_stage_1_minimal_chain.py`、`validate_stage_1_minimal_chain.py`。 | 已完成 |
| 阶段 1 | P1 | 接入 mock / 只读 Tool。 | 只读工具调用有 `tool_call_record`，且不会写状态；运行记录：`20260708_mock_tool_chain.md`。 | 已完成 |
| 阶段 1 | P1 | 新增 mock / 只读 Tool runner 和校验脚本。 | `run_stage_1_mock_tool_chain.py`、`validate_stage_1_mock_tool_chain.py`。 | 已完成 |
| 阶段 1 | P1 | 基于 QueryPlan 执行只读查询并输出分析结果与依据。 | 输出数据来源、指标口径、证据字段、source_footer 和 provenance；运行记录：`20260708_readonly_execution.md`。 | 已完成 |
| 阶段 1 | P1 | 新增只读执行 runner 和校验脚本。 | `run_stage_1_readonly_execution_chain.py`、`validate_stage_1_readonly_execution_chain.py`。 | 已完成 |
| 阶段 1 | P1 | 完成真实只读 Tool 接入准备度检查。 | `20260708_real_readonly_readiness.json` 校验通过。 | 已完成 |
| 阶段 1 | P1 | 新增真实只读 Tool 准备度 runner 和校验脚本。 | `run_stage_1_real_readonly_readiness.py`、`validate_stage_1_real_readonly_readiness.py`。 | 已完成 |
| 阶段 1 | P1 | 接入真实只读 Tool。 | 替换 mock fixture，保留 QueryPlan、tool_call_record、analysis_result 和 provenance 契约；已支持时间窗口、维度与计数模式。 | 已完成 |
| 阶段 1 | P1 | 新增真实只读打标率 runner 和校验脚本。 | `run_stage_1_real_readonly_label_rate.py`、`validate_stage_1_real_readonly_label_rate.py`。 | 已完成 |
| 阶段 1 | P1 | 完成真实只读打标率查询参数化。 | 支持 `--days`、`--dimensions`、`--query-mode=ranking/group_count`；生成 7 天、14 天、多维度和计数回归产物。 | 已完成 |
| 阶段 1 | P1 | 接入低打标率分级注册 SQL。 | 基于真实只读入口输出 notice/P2/P1/P0 分级结果，保留 evidence 与 provenance；结果文件：`20260708_real_readonly_label_rate_grading_results.jsonl`。 | 已完成 |
| 阶段 1 | P1 | 新增真实只读低打标率分级 runner 和校验脚本。 | `run_stage_1_real_readonly_label_rate_grading.py`、`validate_stage_1_real_readonly_label_rate_grading.py`。 | 已完成 |
| 阶段 2 | P2 | 生成低打标率分级通知卡片草稿。 | 生成 summary、notice/P2/P1/P0/综合 CSV、xlsx、Card 2.0、hash 校验和 publish summary。 | 已完成 |
| 阶段 2 | P2 | 新增通知卡片草稿 runner 和校验脚本。 | `run_stage_2_label_rate_notification_draft.py`、`validate_stage_2_label_rate_notification_draft.py`。 | 已完成 |
| 阶段 2 | P2 | 完成单人飞书卡片预览推送。 | 以用户明确要求为前提，导入飞书表格并单独推送给用户本人；发送前剥离 `_meta`。 | 已完成 |
| 阶段 2 | P2 | 实现 POC / 触达对象路由占位。 | 生成 `poc_routing_plan.json`，固定 `routing_mode=placeholder`、`fallback_to_default_user=true`、`default_recipient=self`，不编造真实 POC。 | 已完成 |
| 阶段 2 | P2 | 新增 POC 路由占位 runner 和校验脚本。 | `run_stage_2_label_rate_poc_routing.py`、`validate_stage_2_label_rate_poc_routing.py`。 | 已完成 |
| 阶段 2 | P2 | 增强通知草稿并生成群推送门禁计划。 | 生成 `notification_draft.json` 和 `send_plan.json`；默认 `requires_confirmation=true`、`group_send_blocked=true`、`sent=false`。 | 已完成 |
| 阶段 2 | P2 | 新增本地人工处理状态记录。 | 生成 `manual_tracking.json`；包含 `evidence_refs`、`operator_note`、`next_action`、`continue_observation`，且 `online_write_executed=false`。 | 已完成 |
| 阶段 2 | P2 | 新增局部调度回归。 | 生成 `owner_lookup_only_results.jsonl`、`notification_only_results.jsonl`、`resolution_only_results.jsonl` 和 `partial_dispatch_results.jsonl`。 | 已完成 |
| 阶段 2 | P2 | 完成阶段 2 全量安全验收。 | `validate_stage_2_label_rate_poc_routing.py`、`validate_stage_2_label_rate_notification_draft.py`、`validate_stage_2_label_rate_manual_tracking.py`、`validate_stage_2_label_rate_partial_dispatch.py` 均通过。 | 已完成 |
| 阶段 2 | P2 | 完成私有验证群群发验证。 | 用户明确授权后，新建私有验证群 `人审阶段2群发验证-20260709`，仅包含用户本人和机器人，发送今日数据版 Card 2.0 通知，并记录 `group_send_validation.json`。 | 已完成 |
| 阶段 2 | P2 | 完成自定义多维低打标率泛化验证。 | 查询 `2026-06-29` 至 `2026-07-05` 期间 `机审一级标签 × strategy_id × strategy_name × reason` 维度下打标率 `<0.1` 的明细；默认输出汇总、TopN、CSV/XLSX 和飞书电子表格，不默认发送卡片；显式传入群聊时才进入发送验证。 | 已完成 |
| 发布准备 | P2 | 完成 AgentBuddy Git 仓库上传准备。 | 新增 `.agentbuddy/publish.yaml`，按 AgentBuddy `path + items` 白名单协议声明四个 Skill；新增 `validate_agentbuddy_publish.py` 校验发布清单、Skill frontmatter、调试快照、脚本编译和本机绝对路径。 | 已完成 |
| 发布验证 | P2 | 完成 AgentBuddy restricted 空间发布。 | 将 `perceiving-ops-events`、`analyzing-ops-metrics`、`routing-ops-notifications`、`tracking-ops-resolution` 发布到 `skills.byted.org/lizhongtao/hunman_review_ops`；四个 Skill 均可通过 AgentBuddy 搜索命中，发布摘要记录在 `human_review_ops/evals/agentbuddy_publish/20260709_agentbuddy_publish_summary.json`。 | 已完成 |
| 发布验证 | P2 | 同步 AgentBuddy 指标契约 SQL 片段版本。 | 将打标率默认样本池由自然语言枚举改为可直接复用的 SQL 片段后，重新发布 `perceiving-ops-events` 与 `analyzing-ops-metrics` 到 AgentBuddy restricted 空间，版本升至 `1.0.1`。 | 已完成 |
| 阶段 2 | P1 | 接入打标率场景 POC 姓名级映射。 | 按 `mach_root_label_name` 映射 POC 姓名，映射来源为飞书表格 `HKdm9w`；自定义多维低打标率查询默认生成 `poc_routing_plan.json`，10293 行历史明细均命中 POC，真实触达前仍需 open_id 解析和人工确认。 | 已完成 |

### 12.3 阶段 3 / 后续实施计划

#### 12.3.1 阶段 2 收尾结论

| 事项 | 当前结论 | 后续解锁条件 |
| --- | --- | --- |
| POC 映射 | 已接入 `mach_root_label_name -> POC 姓名` 映射；当前是姓名级，不含 open_id。 | 完成飞书联系人解析、歧义消解、open_id 存储策略和真实触达确认链路。 |
| 分析粒度 | 当前按 `reason` 粒度完成端到端验证。 | 业务确认是否切换或补充 `strategy_name` 粒度。 |
| 触达身份 | 开发验证阶段默认本人预览。 | 真实 POC 身份字段、open_id 解析方式和权限边界确认。 |
| 群推送 | 已生成 `send_plan.json` 门禁，默认阻断群发；用户明确授权下已完成一次私有验证群发送。 | 真实 POC 群推送仍需人工确认目标群 / POC 收件人、发送身份和卡片内容。 |
| 回收闭环 | 当前仅记录本地 `manual_tracking.json`。 | 明确联系人回复收集、卡片按钮回调或 Lark Base 状态表设计。 |
| 状态存储 | 开发阶段仅本地存储，不写线上状态。 | 状态表 schema、权限、写入幂等和回滚策略确认。 |
| 发送身份 | 当前默认 bot，未确认时不做真实群推送。 | 若 bot 权限不足，再评估 user identity 或应用权限补齐。 |

#### 12.3.2 后续任务表

| 优先级 | 任务 | 要做什么 | 预期产物 | 验收标准 | 状态 |
| --- | --- | --- | --- | --- | --- |
| P1 | 接入 POC 联系人身份解析 | 基于当前 `mach_root_label_name -> POC 姓名` 映射，解析飞书 open_id，处理重名歧义，并保留姓名级 fallback。 | POC open_id 映射配置、联系人解析 runner、validator、脱敏样例。 | 能输出可触达 POC 或明确 fallback 原因；不泄露敏感身份；映射缺失可解释。 | 待开始 |
| P1 | 固化触达对象解析 | 将角色范围、POC 身份、open_id 解析和置信度写入路由计划。 | 增强版 `poc_routing_plan.json`。 | notice/P2/P1/P0 均有可审计收件人来源、置信度和升级关系。 | 待开始 |
| P1 | 建立群推送确认链路 | 在 `send_plan.json` 基础上增加人工确认状态和真实发送前检查。 | 确认记录、发送前 validator、群推送 dry-run 结果。 | 未确认不发送；确认后仅向指定群 / POC 发送；发送结果可追踪。 | 待开始 |
| P2 | 设计回收闭环 | 设计联系人说明、处理计划、继续观察和关闭条件。 | 状态表 schema、卡片交互方案或本地回收样例。 | 可记录回复、处理结论、下一次观察时间；支持不写线上表的回退模式。 | 待开始 |
| P2 | 发布治理与 Skill 打包 | 将阶段 2 新增 Notification / Resolution 能力纳入 Skill 自包含资产和发布校验。 | Skill 包、打包校验、发布前检查清单。 | Skill 独立可发布；根场景包与 Skill 快照一致；回归脚本通过。 | 待开始 |
| P2 | 线上观测与异常处理 | 增加发送失败、权限不足、映射缺失、数据过期等异常样例。 | 异常样例、validator、调试记录模板。 | 失败可归因到数据、权限、路由、通知或状态写入，不产生不可控副作用。 | 待开始 |

### 12.4 进度更新规则

- 每完成一项开发任务，必须把 `12.2 已完成任务看板` 或 `12.3 后续实施计划` 中对应状态同步更新。
- 每次 TRAE 调试失败，必须补充调试检查记录，并把失败归因到路由、检索、Skill 输出、工具权限或场景包内容之一。
- 每次修改场景包，必须重新运行场景包结构校验和相关评估样例。

## 13. 仓库与开发流程规范

GitHub 仓库：

```text
https://github.com/hardyai716/human_review_agent_skill_hub.git
```

本项目后续更新、调整、调试记录和模板变更都必须进入 Git 仓库管理。

要求：

- `main` 分支只保留可回溯的稳定版本。
- 日常开发使用功能分支，例如 `feat/trae-debug-agent`、`feat/efficiency-scenario-template`。
- 每次提交前必须运行结构检查或至少完成手工检查：目录结构、关键文件、调试记录、场景包引用路径。
- 涉及场景包、Skill、Agent 路由、权限策略的变更，必须同步更新对应评估样例或调试检查清单。
- 不提交敏感信息、真实 Token、个人账号密钥、线上数据明细。
- TRAE 调试失败记录可以提交，但必须脱敏，只保留问题类型、命中文件、失败原因和修复动作。

首次接入仓库步骤：

```text
git init
git remote add origin https://github.com/hardyai716/human_review_agent_skill_hub.git
git add .
git commit -m "chore: initialize human review agent skill hub"
git branch -M main
git push -u origin main
```

若本地推送因 GitHub 权限或网络失败，先保留本地提交；待认证完成后再执行 push。

## 14. 旧文档处理原则

以下文件属于过程性方案或旧路线图，不再作为开发依据：

- `.trae/documents/html_architecture_final_optimization_plan.md`
- `.trae/documents/human_review_ops_workflow_rearchitecture_plan.md`
- `.trae/documents/architecture_demo_prd.md`
- `.trae/documents/architecture_demo_technical.md`
- `docs/roadmap.md`

处理方式：

- 删除上述过程性方案。
- 本文成为后续开发唯一实施方案。
- `docs/architecture.md`、`docs/data_query_governance.md`、`docs/skill_interface_and_tool_mcp_spec.md` 继续作为架构依据和接口规范保留。
