# QueryPlan 断言：打标率

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
- `analysis_mode`

## 指标断言

- `metric_id` 必须为 `label_rate`，或属于 `review_in_cnt`、`review_done_cnt`、`label_cnt` 等相关指标。
- 打标率分母必须为完审量。
- 禁止把进审量作为打标率分母。
- 禁止用自动处置准确率、质检准确率或底线事故数替代。

## 来源断言

- `source_priority` 必须以 `semantic_layer` 开头。
- 允许 fallback 到 `governed_dataset` 或 `curated_raw_sql`，但必须记录 `fallback_reason`。
- 普通趋势和高 / 低打标率排序不得过早 fallback。
- 低打标率分级的允许 fallback reason：
  - `complex_grading_rule_not_covered_by_semantic_layer`
- 维度拆解的允许 fallback reason：
  - `dimension_reason_breakdown_requires_curated_sql`
- 未列举维度的允许状态：
  - `dimension_discovery_required`

## 过滤断言

必须包含或等价表达：

- `standard_review_scope`
- A. `project_title` 黑名单：`虚假`、`标注`、`虚假不实`、`封面`、`自动处置`、`演绎`、`模型`、`run`、`质检`、`QA`、`测试`、`大模型`、`离线`。
- B. `scene` 白名单：`community_audit_safe`、`community_audit_style`、`community_audit_moderate`。
- C. `reason` 排除项：`recall_skip_L6`、`fatal_output`。
- D. `mach_root_label_name` 空值保留 + 白名单：空值必须保留，白名单包含 `不良行为或争议价值观`、`侵犯未成年权益`、`偏激社会情绪和涉外言论`、`党和国家形象负面`、`危险行为`、`国家安全`、`引人不适`、`指令舆情相关`、`短期策略迁移`、`色情性化`、`违法违规`、`领导人`。

默认情况下，打标率查询、排序、低打标率分级和维度拆解都必须使用以上 A/B/C/D 基础过滤。若覆盖样本池，必须在 QueryPlan 和 source_footer 中记录覆盖原因并要求人工确认。

## 维度断言

- 支持维度可直接进入 QueryPlan。
- 未列举维度必须先执行 Semantic Layer / 数据集字段发现。
- 未确认字段 Name、业务含义、粒度影响和 Owner 前，不得直接拼接字段查询。

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
