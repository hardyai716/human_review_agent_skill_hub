# Source Footer 方法

## 适用范围

所有分析输出都必须包含 source_footer。source_footer 用于说明口径、来源、过滤、质量检查和限制，不能只给业务结论。

## 必填字段

| 字段 | 要求 |
| --- | --- |
| `metric_contract_ref` | 指向命中场景文档的指标口径章节。 |
| `dataset_reference_ref` | 指向命中场景文档的数据源与字段章节。 |
| `analysis_ref` | 指向命中场景文档的分析模式章节。 |
| `query_plan_id` | 与 QueryPlan 一致。 |
| `time_window` | 本次实际分析窗口。 |
| `data_lag` | 数据延迟或最新分区说明。 |
| `source_priority` | QueryPlan 中的来源优先级。 |
| `actual_source` | 实际使用的数据源。未执行时写待执行来源。 |
| `filters` | 默认过滤和用户覆盖过滤。 |
| `dimensions` | 实际输出维度。 |
| `quality_checks` | 新鲜度、分母、字段、权限、样本池等检查结果。 |
| `limitations` | 样本偏差、字段缺失、fallback、权限限制、未执行原因。 |
| `run_mode` | `debug_only`、`readonly` 或宿主 Agent 定义的只读模式。 |

## 单场景文档引用格式

单场景文档结构下，三个 ref 可以指向同一个文件的不同章节：

```json
{
  "metric_contract_ref": "references/scenarios/efficiency-label-rate.md#指标口径",
  "dataset_reference_ref": "references/scenarios/efficiency-label-rate.md#数据源与字段",
  "analysis_ref": "references/scenarios/efficiency-label-rate.md#分析模式"
}
```

## 禁止事项

- 不得指向 Skill 外部的场景包作为运行态来源。
- 不得隐藏 fallback 原因。
- 不得把查询失败写成“无异常”。
- 不得省略用户覆盖样本池、新增维度或权限不足的限制说明。
