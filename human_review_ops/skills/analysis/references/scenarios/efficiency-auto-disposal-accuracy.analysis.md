# 调试快照：自动处置准确率分析规则

来源：`human_review_ops/references/scenarios/efficiency-auto-disposal-accuracy/analysis.md`

## 分析顺序

1. 确认指标口径和时间窗口。
2. 检查数据新鲜度和分母是否为 0。
3. 输出整体趋势。
4. 按策略、队列、风险域、三级标签拆分。
5. 输出候选根因和 source_footer。

## QueryPlan 必填

- `metric_id`
- `time_range`
- `dimensions`
- `filters`
- `allowed_sources`
- `forbidden_sources`
- `quality_checks`
