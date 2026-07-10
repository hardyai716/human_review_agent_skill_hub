# QueryPlan 方法

## 适用范围

所有分析场景在生成 SQL、只读执行请求或业务结论前必须先生成 QueryPlan。

## 必填字段

| 字段 | 要求 |
| --- | --- |
| `query_plan_id` | 本次分析唯一 ID。 |
| `scenario_key` | 必须来自 `references/scenario-index.md`。 |
| `metric_id` | 必须来自命中场景文档。 |
| `task_type` | 必须与场景文档的分析模式一致。 |
| `time_range` | 写明日期范围、相对窗口和数据延迟。 |
| `dimensions` | 只允许已治理字段；新增维度必须先确认字段含义、粒度和权限。 |
| `filters` | 写明默认样本池和用户覆盖项。 |
| `source_priority` | 从语义层、治理数据集、受控 SQL 中按场景规则选择。 |
| `allowed_sources` | 只列当前允许读取的来源。 |
| `forbidden_sources` | 必须包含临时表、无 Owner 历史 SQL、废弃表、敏感明细。 |
| `fallback_reason` | 未 fallback 时写 `none`；fallback 时写具体原因。 |
| `quality_checks` | 至少包含新鲜度、分母、字段映射、权限和样本池检查。 |
| `review_required` | 样本池覆盖、新维度、权限不明或真实执行时为 `true`。 |

## 来源优先级

1. `semantic_layer`：普通趋势、排序、口径确认优先。
2. `governed_dataset`：语义层缺维度或复杂过滤时使用。
3. `curated_raw_sql`：仅用于场景文档声明的复杂分级、拆解或 SQL 模板。
4. `raw_exploration`：只允许字段探测，不得作为最终结论来源。

## SQL 生成约束

- 按维度聚合时，必须先把可空维度转换为稳定 key，例如 `ifNull(`[机审一级标签]`, '（空/机审一级标签）') AS mach_root_label_key`。
- `GROUP BY` 必须使用转换后的 key 字段，不得使用与底表物理字段同名的别名，例如不要在内层写 `AS mach_root_label_name GROUP BY mach_root_label_name`。
- 对外输出时再把内部 key 映射回标准字段名，例如 `mach_root_label_key AS mach_root_label_name`。
- 该规则适用于所有维度字段，尤其是 `mach_root_label_name`、`strategy_id`、`strategy_name`、`reason`。否则 Aeolus / ClickHouse 可能在别名与物理字段重名时解析到原始字段，导致 NULL 维度记录在聚合阶段丢失。

## 失败分支

- 场景不明确：停止，交回感知 Skill。
- 时间窗口不明确：停止，要求用户补时间。
- 字段未确认：停止，列出待确认字段。
- 权限不足：停止，保留权限错误和所需授权对象。
- 分区未就绪：停止，输出最新分区和目标窗口差距。
- 命中禁用来源：停止，要求改用治理来源。
