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

## tool_call_record 断言

阶段 1 P1 接入 mock / 只读 Tool 后，当前预检阶段：

- 正例 QueryPlan 必须包含 `tool_calls`，值为 `tool_call_record.tool_call_id` 列表。
- 顶层输出必须包含 `tool_call_records`。
- 每条 `tool_call_record` 必须为 `permission_level=readonly`。
- 每条 `tool_call_record` 必须为 `execution_mode=mock_readonly_no_real_query`。
- 每条 `tool_call_record` 必须为 `real_query_executed=false`。
- 每条 `tool_call_record` 的 `scenario_key`、`metric_id`、`review_required`、`fallback_reason` 必须与 QueryPlan 一致。
- 未列举维度必须生成字段发现类 mock 记录，但不得把未确认字段直接用于真实查询。
- 低打标率分级和维度拆解若需要 `curated_raw_sql` fallback，必须生成受控 SQL guard 记录，且真实 SQL 执行状态必须是 blocked。
- 反例和低信息量样例不得生成工具调用记录。

后续接入真实只读执行时，应新增执行结果断言，校验数据来源、指标口径、过滤条件、质量检查、source_footer 和 provenance，不再把 mock 预检断言作为真实查询结论断言。

## 只读执行结果断言

阶段 1 P1 只读执行链路必须：

- QueryPlan 通过后才生成 `readonly_execution`。
- `readonly_execution` 必须记录 `execution_id`、`execution_mode`、`status`、`source_tier`、`data_freshness`、`row_count`、`rows`、`evidence_fields`、`metric_formula` 和 `quality_checks`。
- `analysis_result.query_plan.tool_calls` 必须与顶层 QueryPlan 的 `tool_calls` 一致。
- `analysis_result.source_footer` 必须与顶层 `source_footer` 一致。
- `analysis_result.provenance` 必须与顶层 `provenance` 一致。
- `provenance.tool_call_ids` 必须与 QueryPlan 的 `tool_calls` 一致。
- `provenance.references` 必须包含 `metric_contract`、`dataset_reference` 和 `analysis_rule`。
- 当前 mock 阶段必须标明 `mock_fixture_not_real_data`，不得声称真实分区新鲜度。
- 反例和低信息量样例不得生成 `readonly_execution`、`analysis_result` 或 `provenance`。

## 真实只读查询断言

真实只读打标率查询必须：

- `QueryPlan.execution_mode=real_readonly_query`。
- `tool_call_record.tool_name=bytedcli_aeolus_query`。
- `tool_call_record.permission_level=readonly`。
- `tool_call_record.real_query_executed=true`。
- QueryPlan 必须绑定 `aeolus_dataset_id=3888816` 和 `aeolus_metric_id=10000036292379`。
- `QueryPlan.dimensions` 必须来自用户问题解析后的已治理维度，默认 `reason`。
- `QueryPlan.dimension_mappings` 必须记录每个维度对应的 Aeolus 字段。
- 明细型问题使用 `query_mode=ranking`，SQL 必须按 `dimensions` 生成 `SELECT` 和 `GROUP BY`。
- “有多少”一类分组计数问题使用 `query_mode=group_count`，SQL 必须先生成低打标率分组子查询或 CTE，再统计分组数。
- SQL 必须包含 A/B/C/D 基础过滤。
- `readonly_execution.truncated=false`。
- `query_mode=ranking` 时，`readonly_execution.rows[*].label_rate < 0.1`。
- `query_mode=group_count` 时，`readonly_execution.rows[0].low_label_rate_group_cnt >= 0`。
- 不生成 `notification_draft`、`owner_recommendation` 或 `manual_tracking`。

## 真实只读分级断言

真实只读低打标率分级必须：

- `QueryPlan.analysis_mode=low_label_rate_grading`。
- `QueryPlan.fallback_reason=complex_grading_rule_not_covered_by_semantic_layer`。
- `QueryPlan.levels=["notice","P2","P1","P0"]`。
- `QueryPlan.level_priority` 必须表达 `P0 > P1 > P2 > notice`。
- `QueryPlan.sql_by_level` 必须包含四级 SQL，且每级 SQL 都包含 A/B/C/D 基础过滤。
- `readonly_execution.level_results` 必须包含四级结果。
- `readonly_execution.comprehensive_results` 必须按最高等级对 reason 去重。
- 每条分级 evidence 必须包含 `avg_review_in_cnt`、`avg_review_done_cnt`、`avg_label_cnt`、`label_rate`、`hit_rule_ids`、`hit_conditions`。
- 所有分级结果必须 `truncated=false`。
- 不生成 `notification_draft`、`owner_recommendation` 或 `manual_tracking`。
