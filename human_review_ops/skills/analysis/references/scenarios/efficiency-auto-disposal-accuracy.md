# 场景：效率模块 / 自动处置准确率

## 场景元信息

| 项 | 内容 |
| --- | --- |
| `scenario_key` | `efficiency-auto-disposal-accuracy` |
| 主指标 | `auto_disposal_accuracy` / 自动处置准确率 |
| 模块 | 效率模块 |
| 运营对象 | 自动处置策略、队列、风险域、三级标签在不同维度下的准确率表现 |
| 当前状态 | 调试态场景，数据源和 Owner 仍需治理确认 |

## 触发与排除

触发：

- 分析自动处置准确率为什么下降。
- 查询自动处置准确率是否达标。
- 按策略、队列、风险域、三级标签拆解自动处置准确率。

排除：

- 打标率、低打标 reason、低效策略分级，使用 `efficiency-label-rate`。
- 质检准确率、底线事故数、人工审核准确率。
- 通知草稿、负责人路由、状态写入。

## 指标口径

| 业务概念 | `metric_id` | 口径 |
| --- | --- | --- |
| 自动处置准确率 | `auto_disposal_accuracy` | 自动处置结果正确样本数 / 自动处置样本总数 |

规则：

- 分子是自动处置结果正确样本数。
- 分母是自动处置样本总数。
- 跨天、跨策略、跨队列、跨风险域聚合时，必须先聚合分子和分母，再重算准确率。
- 不得用质检准确率、底线事故数或人工审核准确率替代本指标。

## 数据源与字段

当前数据源处于待治理状态。生成 QueryPlan 时必须把数据源确认列入 `quality_checks` 和 `review_required`。

推荐字段：

| 逻辑字段 | 含义 |
| --- | --- |
| `strategy_id` | 自动处置策略 ID |
| `queue_id` | 队列 ID |
| `risk_domain` | 风险域 |
| `third_level_label` | 三级标签 |
| `auto_disposal_total_cnt` | 自动处置样本总数 |
| `auto_disposal_correct_cnt` | 自动处置结果正确样本数 |
| `p_date` | 统计日期 |

禁用来源：

- 临时表。
- 无 Owner 历史 SQL。
- 已废弃策略效果表。
- 未标记治理口径的数据集。
- 敏感个人明细。

## 默认过滤

当前无已固化 SQL 过滤片段。生成 QueryPlan 时必须显式列出用户指定过滤和待确认样本池；样本池未确认前不得输出高置信业务结论。

## 支持维度

- `strategy_id`
- `queue_id`
- `risk_domain`
- `third_level_label`
- `p_date`
- `time_window`

用户指定新维度时，先确认字段含义、粒度、权限和 Owner；无法确认时停止。

## 分析模式

| 模式 | `task_type` | 触发条件 | 主要产出 |
| --- | --- | --- | --- |
| 准确率趋势 | `accuracy_trend` | 用户询问整体趋势、是否达标、近期变化 | QueryPlan、趋势结果、source_footer |
| 准确率排序 | `accuracy_ranking` | 用户查询高/低准确率策略或队列 | 排序清单、分子、分母、准确率 |
| 维度拆解 | `dimension_breakdown` | 用户按策略、队列、风险域或三级标签拆解 | `dimensions` 明细和汇总 |

通用顺序：

1. 确认指标口径和时间窗口。
2. 确认数据源、字段和 Owner。
3. 检查数据新鲜度和分母是否为 0。
4. 输出整体趋势。
5. 按策略、队列、风险域、三级标签拆分。
6. 输出候选根因和 source_footer。

## QueryPlan 要求

必填字段：

- `metric_id`
- `time_range`
- `dimensions`
- `filters`
- `allowed_sources`
- `forbidden_sources`
- `quality_checks`
- `review_required`

当前场景默认 `review_required=true`，直到数据源、字段和样本池被治理确认。

## 输出要求

- 展示自动处置样本总数、正确样本数和准确率。
- 百分比保留两位小数。
- 样本池、数据源或字段未确认时，置信度不得标为 high。
- source_footer 必须说明当前数据源治理状态。

source_footer ref 示例：

```json
{
  "metric_contract_ref": "references/scenarios/efficiency-auto-disposal-accuracy.md#指标口径",
  "dataset_reference_ref": "references/scenarios/efficiency-auto-disposal-accuracy.md#数据源与字段",
  "analysis_ref": "references/scenarios/efficiency-auto-disposal-accuracy.md#分析模式"
}
```

## 失败处理

- 指标口径不明确：停止，要求确认分子和分母。
- 数据源未确认：停止，输出待确认数据源和 Owner。
- 字段映射失败：停止，列出缺失字段。
- 分母为 0：输出质量风险，不给强结论。
- 查询失败：输出错误、QueryPlan、source_footer 和下一步修复建议。

## 正反例

正例：

- 分析一下自动处置准确率为什么下降。
- 按策略维度看自动处置准确率。

反例：

- 近 7 天低打标率 reason 有哪些？
- 质检准确率下降了。
- 底线事故数上升了。

低信息量：

- 这个策略怎么了？

处理：先询问指标、时间窗口和策略 / 队列范围，不直接查询。
