# 05 可复用模板

## 1. Knowledge Skill 模板

```markdown
# [Domain] Knowledge Skill

## 目标
把用户问题映射到正确的治理指标、数据源、粒度和过滤条件。

## 强制顺序
1. 识别业务域和运营内容。
2. 识别任务类型：日常分析 / 周期推送 / 撞线预警 / 临时问答。
3. 查询语义层或指标注册表。
4. 加载 `human_review_ops/references/scenarios/{scenario}/metric_contract.md`。
5. 输出 resolved_entities、allowed_sources、forbidden_sources。
6. 如果指标或粒度不明确，必须澄清。

## 禁止行为
- 禁止直接查原始表。
- 禁止从历史 SQL 复制口径。
- 禁止自行创造指标定义。
- 禁止在多个相似字段中猜测。

## 输出
```json
{
  "resolved_entities": [],
  "allowed_sources": [],
  "forbidden_sources": [],
  "required_filters": [],
  "clarification_needed": false
}
```
```

## 2. Runbook Skill 模板

```markdown
# [Domain] Runbook Skill

## 目标
基于 Knowledge Skill 输出执行分析流程，并产出可验证结论。

## 强制步骤
1. 检查 Knowledge Skill 输出。
2. 生成 QueryPlan。
3. 执行只读查询。
4. 执行数据质量检查。
5. 执行趋势、分维度拆解、归因。
6. 对照定级/升级规则。
7. 高风险结论进行复核。
8. 输出来源脚注。

## 禁止行为
- 禁止绕过 QueryPlan 查询。
- 禁止写入或变更业务状态。
- 禁止无来源输出结论。
- 禁止低置信结论自动触发通知。
```

## 3. Reference 文档模板

```markdown
# [场景名称] 数据与指标说明

## Quick Reference
- 业务域：
- 运营内容：
- 核心指标：
- 默认时间窗口：
- 默认粒度：
- 主要 Owner：

## Business Context
用业务语言说明这个场景在运营中解决什么问题。

## Metric Contract
| 指标 | 分子 | 分母 | 过滤条件 | 默认粒度 | Owner |
| --- | --- | --- | --- | --- | --- |

## Entity Grain
说明一行数据代表什么。

## Standard Hygiene Filter
列出每次查询都必须使用的过滤条件。

## Key Tables / Datasets
### [dataset_or_table_name]
- Grain:
- Scope:
- Exclusions:
- Usage:
- Do Not Use When:
- Join Keys:
- Freshness:
- Owner:

## Dimensions
说明风险域、三级标签、策略、队列、治理 BP 等维度如何编码。

## Gotchas
- 容易错用的字段：
- 容易混淆的表：
- 过期口径：
- 禁止数据源：

## Common Query Patterns
- 日常分析：
- 周期推送：
- 撞线预警：

## Cross References
- 相邻场景：
- 关联指标：
```

## 4. QueryPlan 模板

```json
{
  "query_plan_id": "QP-0001",
  "scenario": "string",
  "task_type": "daily_analysis | weekly_push | threshold_alert | ad_hoc",
  "metric_entities": [
    {
      "metric_id": "string",
      "definition_version": "string",
      "source_tier": "semantic_layer | governed_dataset | scenario_reference | readonly_exploration"
    }
  ],
  "dimensions": [],
  "time_range": {
    "start": "datetime",
    "end": "datetime",
    "grain": "day | week"
  },
  "filters": [],
  "required_hygiene_filters": [],
  "allowed_sources": [],
  "forbidden_sources": [],
  "quality_checks": [
    "freshness",
    "completeness",
    "zero_denominator",
    "anomaly"
  ],
  "requires_human_confirmation": false
}
```

## 5. 来源脚注模板

```text
来源：[semantic_layer | governed_dataset | scenario_reference | readonly_exploration]
指标口径：[metric_id]@[definition_version]
数据时间：[time_range]，最新分区：[partition_time]
粒度：[整体/风险域/三级标签/策略/队列]
Owner：[metric_owner/data_owner]
质量检查：[通过/部分通过/失败]
置信度：[高/中/低]
复核状态：[未复核/自动复核/人工复核]
```

## 6. 场景包最小模板

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
