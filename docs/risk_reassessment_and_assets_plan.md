# 风险重估与样例 Assets 建设计划

## 1. 结论

基于最新业务补充，之前“最没把握”的四个点需要重估。

新的判断是：

- 指标口径本身不是最大风险，因为业务核心指标有唯一口径，公式、排除项和标准过滤是固定逻辑。
- Aeolus/Hive 元数据不是空白，平台本身提供字段描述、粒度、血缘等能力。
- 最大风险转为：Agent 是否能稳定命中唯一口径、正确字段、正确粒度、正确时间窗口，并避免在相似字段和相近数据集之间偏移。
- 解决路径应参考 Claude 官方自助数据分析框架：数据基础 + 事实来源 + Knowledge/Runbook Skill + 评估/纠错闭环。

## 2. 四个问题的重估

### 2.1 指标口径

原担忧：

- 核心指标是否存在多个口径。

最新判断：

- 核心指标有唯一口径。
- 公式计算、排除项和标准过滤是固定逻辑。
- 泛化部分主要是维度层和时间窗口，但它们可以被抽象为规则。

架构调整：

- `metric_contract.md` 不应只记录指标定义，还应显式记录维度规则和时间窗口规则。
- QueryPlan 必须校验维度和时间窗口，而不是只校验指标 ID。

需要沉淀：

```text
metric_contract.md
  - metric_id
  - formula
  - numerator
  - denominator
  - exclusion_rules
  - standard_filters
  - supported_dimensions
  - supported_time_windows
  - aggregation_rules
```

### 2.2 Aeolus/Hive 数据基础

原担忧：

- 数据源是否缺少字段描述、粒度和血缘。

最新判断：

- Aeolus/Hive 已具备详细字段描述、粒度、血缘等信息。
- 主要风险发生在字段多、相近字段多、类似数据集多时，Agent 可能选错字段。

架构调整：

- 不需要从零建设字段元数据。
- 需要为人审运营实际使用的数据集/Hive 表补充 LLM 友好的字段选择 reference。
- 对相近字段、禁用字段、推荐字段、默认 join key、标准过滤进行显式说明。

需要沉淀：

```text
dataset_reference.md
  - dataset_name
  - business_context
  - grain
  - allowed_metrics
  - key_fields
  - confusing_fields
  - forbidden_fields
  - required_filters
  - lineage_summary
  - owner
  - freshness
```

### 2.3 指标契约和 reference 结构

原担忧：

- `metric_contract.md` 是否能写得足够细。

最新判断：

- 可以参考 Claude 官方框架，将指标契约和 reference 文档面向 LLM 检索设计。
- 文档重点不是堆 SQL，而是写清业务上下文、实体粒度、适用/禁用场景、字段差异和常见坑。

架构调整：

- 场景流程包必须包含 `metric_contract.md`。
- Aeolus/Hive 数据集必须有对应 `dataset_reference.md` 或等价知识输入。
- Knowledge Skill 先读取这些 reference，再输出治理实体和 allowed_sources。

### 2.4 样例 / Assets

原担忧：

- 是否有足够历史样例做验收。

最新判断：

- 可以主动搭建样例/assets 资产，不必等待完备历史沉淀。
- 样例应同时覆盖正例、反例、边界例和纠错例。

架构调整：

- 每个场景流程包必须有 `examples.md`。
- 建议单独建设 `assets/eval_samples/` 和 `assets/reference_cases/`。

## 3. 样例 Assets 目录建议

```text
assets/
  eval_samples/
    machine_review_effectiveness/
      daily_low_accuracy_analysis.jsonl
      weekly_push.jsonl
      label_rate_threshold_alert.jsonl
      auto_disposal_accuracy_threshold_alert.jsonl
    quality_monitoring/
      daily_quality_analysis.jsonl
      quality_threshold_alert.jsonl
    baseline_incident_monitoring/
      incident_threshold_alert.jsonl

  reference_cases/
    machine_review_effectiveness.md
    quality_monitoring.md
    baseline_incident_monitoring.md

  query_plans/
    machine_review_effectiveness_examples.md
    quality_monitoring_examples.md
    baseline_incident_examples.md

  expected_outputs/
    ai_summary_cards.md
    root_cause_reports.md
    source_footer_examples.md
```

## 4. 样例字段标准

每条评估样例建议包含：

```json
{
  "sample_id": "string",
  "scenario": "machine_review_effectiveness | quality_monitoring | baseline_incident_monitoring",
  "task_type": "daily_analysis | weekly_push | threshold_alert | ad_hoc",
  "user_input": "string",
  "expected_metric_ids": [],
  "expected_dimensions": [],
  "expected_time_window": {},
  "expected_filters": [],
  "expected_dataset_or_table": "string",
  "forbidden_fields": [],
  "expected_query_plan_assertions": [],
  "expected_rule_hit": "P1 | P2 | none",
  "expected_output_type": "summary | detail | root_cause_report | ai_summary_card",
  "reviewer": "string",
  "notes": "string"
}
```

## 5. 第一批建议建设的 Assets

### 5.1 机审策略有效性

至少建设：

- 日常低准分析样例 3 条。
- 周度推送样例 2 条。
- 打标率撞线预警样例 3 条。
- 自动处置准确率撞线预警样例 3 条。
- 错字段反例 3 条。

### 5.2 质量监控

至少建设：

- 日常质量分析样例 3 条。
- 质量撞线预警样例 3 条。
- 风险域/整体粒度混淆反例 2 条。

### 5.3 底线事故监控

至少建设：

- 底线事故撞线预警样例 3 条。
- S23/S01/N1/LS 分层反例 3 条。
- P1/P2 定级边界样例 2 条。

## 6. 当前最大风险重排

| 优先级 | 风险 | 说明 | 应对 |
| --- | --- | --- | --- |
| P0 | 字段选择偏移 | 数据集/Hive 字段多且含义接近，Agent 选错字段 | 建 dataset_reference、confusing_fields、forbidden_fields |
| P0 | 维度/时间窗口误选 | 指标口径唯一，但粒度和窗口泛化 | 在 metric_contract 中沉淀 supported_dimensions 和 supported_time_windows |
| P1 | QueryPlan 不可验证 | Agent 输出结论但无法确认查询是否正确 | 强制 QueryPlan + query_plan_assertions |
| P1 | 样例覆盖不足 | 没有正例/反例/边界样例，难以评估 | 建 eval_samples 和 reference_cases |
| P2 | 场景包维护滞后 | 策略、队列、字段变化后 reference 未同步 | 建版本管理和变更评审 |

## 7. 下一步建议

优先做一个最小闭环：

1. 选定场景：机审策略有效性。
2. 固定指标：打标率、自动处置准确率。
3. 补 `metric_contract.md`。
4. 补对应 Aeolus/Hive 数据集 `dataset_reference.md`。
5. 建 8-10 条 eval samples。
6. 让 Agent 只做感知 + QueryPlan + 分析输出。
7. 对比人工标准答案，修正 reference。
