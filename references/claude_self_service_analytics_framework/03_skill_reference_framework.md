# 03 Skill 与 Reference 组织框架

## 1. Pairwise Skills

Claude 官方实践建议将数据分析能力拆成两类配对 Skill：

| Skill 类型 | 职责 |
| --- | --- |
| Knowledge Skill | 负责路由知识、限定检索空间、找到正确治理实体 |
| Runbook Skill | 负责执行分析流程、生成查询计划、运行查询、验证结果 |

## 2. Knowledge Skill

Knowledge Skill 是薄路由层。

它应该回答：

- 这个问题属于哪个业务域？
- 应该查哪个场景流程包？
- 是否能命中语义层或指标注册表？
- 如果语义层未覆盖，应该读哪些 reference？
- 哪些表、字段、维度、过滤条件允许使用？
- 哪些数据源明确禁止使用？

在人审运营中的职责：

```text
用户问题
  -> 识别运营内容
  -> 识别任务类型
  -> 识别指标概念
  -> 读取 metric_contract.md
  -> 输出治理实体和允许数据源
```

## 3. Runbook Skill

Runbook Skill 是执行流程层。

它应该回答：

- 是否需要澄清问题？
- 如何基于 Knowledge Skill 输出生成 QueryPlan？
- 如何执行只读查询？
- 如何做质量检查？
- 如何做归因、趋势、分维度拆解？
- 如何输出可验证结论？
- 是否需要对抗性复核？

在人审运营中的职责：

```text
治理实体
  -> QueryPlan
  -> 只读查询
  -> 数据质量检查
  -> 规则命中
  -> 波动归因
  -> 来源脚注
  -> 测试通知或归档
```

## 4. Reference Docs 编写原则

Reference 文档必须面向 LLM 检索和使用，而不是只面向人读。

好的 reference 应该包含：

- 业务上下文。
- 表或指标的 grain。
- 适用范围和排除项。
- 何时使用、何时禁止使用。
- Join key。
- 必须使用的过滤条件。
- 相似字段之间的差异。
- 常见错误。
- 跨领域引用。

不建议：

- 只贴历史 SQL。
- 只写业务口号。
- 不写粒度和排除项。
- 不写禁用场景。
- 让 Agent 在大量相似字段中自己猜。

## 5. 人审运营场景包中的 reference 文件

每个运营内容建议有以下文件：

```text
human_review_ops/references/scenarios/{scenario}/
  metric_contract.md
  perception.md
  analysis.md
  notification.md
  resolution.md
  state_machine.md
  sla.md
  owner_routing.md
  notification_templates.md
  tool_policy.md
  examples.md
```

其中当前 MVP 最关键的是：

- `metric_contract.md`
- `perception.md`
- `analysis.md`
- `tool_policy.md`
- `examples.md`

通知、解决、Owner 路由可以先写轻量版本，后续基建成熟后再深化。

## 6. Reference 文档质量标准

| 检查项 | 要求 |
| --- | --- |
| 业务上下文 | 能让 Agent 知道问题真实含义 |
| 指标定义 | 分子、分母、过滤条件、时间窗口明确 |
| 数据源 | 允许/禁止数据源明确 |
| 粒度 | 支持整体、风险域、三级标签、策略、队列等粒度 |
| 字段差异 | 相似字段必须解释差异 |
| Owner | 数据 Owner 和业务解释 Owner 明确 |
| 常见坑 | 写清容易查错的表、字段、口径 |
| 样例 | 至少包含正例、反例、边界样例 |
