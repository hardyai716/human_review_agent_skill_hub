# 分析规则：自动处置准确率

## 分析顺序

1. 确认指标口径和时间窗口。
2. 检查数据新鲜度和分母是否为 0。
3. 输出整体趋势。
4. 按策略维度拆分。
5. 按队列维度拆分。
6. 按风险域和三级标签拆分。
7. 输出候选根因，不做单点断言。

## QueryPlan 要求

必须包含：

- `metric_id`
- `time_range`
- `dimensions`
- `filters`
- `allowed_sources`
- `forbidden_sources`
- `quality_checks`

## 输出要求

- 输出归因摘要。
- 输出证据引用。
- 输出 source_footer。
- 低置信度时要求人工确认。
