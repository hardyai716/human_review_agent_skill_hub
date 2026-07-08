# QueryPlan 断言：打标率低效 reason 分析

## 必填字段

- `metric_id`
- `time_range`
- `dimensions`
- `filters`
- `source_priority`
- `allowed_sources`
- `forbidden_sources`
- `fallback_reason`
- `quality_checks`
- `review_required`

## 指标断言

- `metric_id` 必须为 `label_rate`，或属于 `review_in_cnt`、`review_done_cnt`、`label_cnt` 等相关指标。
- 打标率分母必须为完审量。
- 禁止把进审量作为打标率分母。
- 禁止用自动处置准确率、质检准确率或底线事故数替代。

## 来源断言

- `source_priority` 必须以 `semantic_layer` 开头。
- 允许 fallback 到 `governed_dataset` 或 `curated_raw_sql`，但必须记录 `fallback_reason`。
- 低效分级的允许 fallback reason：
  - `complex_grading_rule_not_covered_by_semantic_layer`
- 维度拆解的允许 fallback reason：
  - `dimension_reason_breakdown_requires_curated_sql`

## 过滤断言

必须包含或等价表达：

- `standard_review_scope`
- 非常规审核项目排除。
- 社区审核场景白名单。
- 特殊 reason 排除。
- NULL 机审标签保留。

## 质量断言

必须包含：

- `freshness_gate`
- `denominator_not_zero`
- `field_mapping_check`
- `grain_check`
- `forbidden_source_check`

## 输出断言

最终输出必须包含 source_footer：

- `source_tier`
- `confidence`
- `freshness`
- `owner`
- `reviewed`
