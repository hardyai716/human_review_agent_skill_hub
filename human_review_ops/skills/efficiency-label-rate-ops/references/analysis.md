# 分析规则：打标率

## 分析模式

| 模式 | 触发条件 | 主要产出 |
| --- | --- | --- |
| `label_rate_trend` | 用户只问打标率、进审量、完审量趋势 | QueryPlan + 趋势口径说明 + source_footer |
| `label_rate_ranking` | 用户查询高打标率、低打标率、TopN / BottomN 策略或 reason | 排序清单 + evidence |
| `low_label_rate_grading` | 用户明确问低效策略、P0/P1/P2/notice、低打标 reason 清单 | 四级分级清单 + 综合去重清单 |
| `dimension_breakdown` | 用户要求按机审一级标签、场景、项目或其他维度拆解 | `dimensions × reason` 明细 + `dimensions` 汇总 |
| `report_flow_low_label_rate` | 用户询问举报场景、举报流转或 `enpool_reason` 下的低打标率 | `enpool_reason` 低效清单 + evidence |

## 通用分析顺序

1. 识别指标是否为打标率或相关效率指标。
2. 解析时间窗口；缺失时先澄清。
3. 优先进行 Semantic Layer 发现，搜索 metric、dimension、segment 和 freshness。
4. 判断是否需要 fallback：
   - 普通趋势查询不应过早 fallback。
   - 高 / 低打标率排序优先走语义层或治理数据集。
   - 低打标率分级可 fallback 到受控 SQL 模板。
   - 维度拆解可 fallback 到受控维度拆解 SQL。
5. 生成 QueryPlan。
6. 做数据就绪 gate：权限、分区、行数、分母、字段映射。
7. 输出结论时区分数据事实、解释判断和业务建议。
8. 附 source_footer。

## QueryPlan 要求

必须包含：

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
- `data_direction`
- `source_profile`

示例：

```json
{
  "metric_id": "label_rate",
  "data_direction": "manual_review_detail",
  "source_profile": "community_manual_review",
  "time_range": {"type": "trailing_days", "days": 7, "data_lag_days": 1},
  "dimensions": ["reason"],
  "filters": ["standard_review_scope"],
  "source_priority": ["semantic_layer", "governed_dataset", "curated_raw_sql"],
  "allowed_sources": ["semantic_layer", "olap_content_security_community.dws_sft_tcs_review_task_detail_di"],
  "forbidden_sources": ["temporary_table", "ownerless_legacy_sql", "deprecated_strategy_effect_table"],
  "fallback_reason": "none",
  "quality_checks": ["freshness_gate", "denominator_not_zero", "field_mapping_check"],
  "review_required": true
}
```

举报方向 QueryPlan 示例：

```json
{
  "metric_id": "report_label_rate",
  "data_direction": "report_flow",
  "source_profile": "report_flow_review",
  "time_range": {"type": "trailing_days", "days": 7, "date_field": "进审日期"},
  "dimensions": ["enpool_reason"],
  "filters": ["report_flow_queue_scope", "task_type_report_flow", "first_queue_exclusion"],
  "source_priority": ["governed_dataset", "curated_raw_sql"],
  "allowed_sources": ["aeolus_dataset:3952594"],
  "forbidden_sources": ["aeolus_dataset:3888816", "temporary_table", "ownerless_legacy_sql"],
  "fallback_reason": "report_flow_source_profile",
  "quality_checks": ["field_mapping_check", "freshness_gate", "denominator_not_zero"],
  "review_required": false
}
```

## 模式 A：打标率排序

适用于用户查询高打标率、低打标率、TopN、BottomN 或普通策略表现。

输出要求：

- 按用户要求升序或降序排序。
- 用户未指定时，先澄清是看高打标率、低打标率，还是整体分布。
- 每条策略 / reason 必须带 evidence：进审量、完审量、打标量、打标率、时间窗口。
- 不套用 P0/P1/P2/notice，除非用户明确要求低效分级。

## 模式 B：低打标率分级

默认跑全等级：`notice`、`P2`、`P1`、`P0`。

| 等级 | 默认条件摘要 |
| --- | --- |
| `notice` | 近 7 天打标率 `< 10%` 且当前周期进审量 `> 100`。 |
| `P2` | 单策略低效，或低效策略环比增长。 |
| `P1` | 双周持续低效、单周高量低效，或低效策略爆量。 |
| `P0` | 四周持续低效、两周高量低效、单周超高量低效，或进审量异常爆量。 |

输出要求：

- 四个等级默认均要求当前周期进审量 `> 100`，用于降低小样本下比率型指标的波动影响。
- 四个等级 sheet 保留各自完整命中结果，不跨级去重。
- 综合 sheet 按 `P0 > P1 > P2 > notice` 对同一 reason 取最高等级。
- 每条 reason 必须带 evidence：日均进审、日均完审、日均打标、打标率、命中条件。
- 某级无命中时写“本期 0 条”，查询失败时写失败原因。

## 模式 C：维度拆解

先拉 `day × dimensions × reason` 日粒度明细，再跨日聚合：

- `dimensions × reason` 分组跨日 SUM。
- `dimensions` 分组跨日 SUM。
- 打标率重算：`SUM(label_cnt) / SUM(review_done_cnt)`。
- 日均量使用该组合实际有数据天数。
- NULL 维度值输出为 `（空/<维度名>）`。
- 可空维度必须先生成内部稳定 key，再参与 `GROUP BY`。内部 key 统一使用 `*_key`，不得与底表物理字段同名；例如 `ifNull(`[机审一级标签]`, '（空/机审一级标签）') AS mach_root_label_key`，后续 `GROUP BY mach_root_label_key`，外层再映射为 `mach_root_label_name`。禁止把归一化别名写成 `mach_root_label_name` 后再 `GROUP BY mach_root_label_name`，否则可能漏掉 NULL 机审标签记录。

输出：

- `dimensions × reason` 明细。
- `dimensions` 全量汇总。

如果用户指定的维度不在 `metric_contract.md` 支持维度中，必须先通过 Semantic Layer / 数据集字段发现确认字段，不能直接拼字段名。

## 模式 D：举报流转低打标率

适用于 `data_direction=report_flow`，即用户明确提到举报、举报场景、举报流转、`enpool_reason`、`report_id`、一轮队列或终轮队列。

字段和口径：

- 时间字段：`进审日期`。
- 主维度：`enpool_reason`。
- 分母：`人审完结量_report_id`。
- 分子：`打标量_report_id`。
- 打标率：`打标率_report_id`。
- 低效条件：`打标率_report_id < 10%` 且 `人审完结量_report_id > 0`。

默认输出：

- `enpool_reason`
- `日均人审完结量`
- `日均打标量`
- `打标率`

SQL 约束：

- 必须使用 Dataset `3952594` / appId `555137`。
- 必须复用 `dataset_reference.md#默认过滤：举报流转` 中的基础筛选。
- 不得使用人工审核明细 Dataset `3888816` 的 `reason`、`完审量_reviewid`、`打标量__reviewid`。
- 如果直接逻辑表名不可用，可使用 query_log 中确认的物理表作为受控 fallback，并在 provenance 中记录。
- 指标字段已经是聚合表达式时，不要放入未按维度聚合的子查询中二次聚合；应在同一层按 `enpool_reason` 聚合，或改写成底层 raw formula。

## 停止条件

遇到以下情况必须停止，不得输出业务结论：

- 无法确认打标率口径。
- 无法确认时间窗口。
- 数据分区未就绪。
- 权限不足。
- 字段映射失败。
- 查询失败。
- 命中禁用来源。

## 输出要求

- 结论摘要。
- 口径方法：分子、分母、过滤条件、grain。
- 数据证据：趋势、分级或维度拆解。
- 限制说明：新鲜度、缺失、样本偏差、未覆盖范围。
- source_footer。
