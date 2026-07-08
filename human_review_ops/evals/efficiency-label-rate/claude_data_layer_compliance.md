# Claude 数据层设计合规评估：打标率

## 结论

当前 `efficiency-label-rate` 场景的数据层设计与 Claude 自助数据分析框架的核心逻辑基本一致，可以进入阶段 1 的感知 + 分析最小链路验证。

但在接入真实查询前仍有两个非阻断缺口：

- 真实 Semantic Layer / Aeolus 指标 ID 尚未接入，只能以 `semantic_layer` 作为强制优先路径和 QueryPlan 约束。
- Owner 目前是角色级 Owner，尚未替换为具体负责人、群或值班机制。

## 对照检查

| Claude 要求 | 当前设计 | 结论 |
| --- | --- | --- |
| Data Foundations：核心指标必须有唯一治理口径 | `metric_contract.md` 明确 `label_rate = SUM(label_cnt) / SUM(review_done_cnt)`，并禁止用进审量作分母。 | 通过 |
| Sources of Truth：语义层优先 | `dataset_reference.md` 要求 Semantic Layer 为第一优先级，普通趋势和排序不得过早 fallback。 | 通过 |
| Reference 面向 Agent 检索 | 场景包拆分为 `metric_contract.md`、`dataset_reference.md`、`analysis.md`、`examples.md` 等一级文件。 | 通过 |
| 禁止猜字段 | 未列举维度必须先做 Semantic Layer / 数据集字段发现，确认字段名、含义、粒度、权限和 Owner。 | 通过 |
| QueryPlan 先于查询 | `analysis.md` 和 `query_plan_assertions.md` 都要求先生成 QueryPlan。 | 通过 |
| 来源脚注 | `dataset_reference.md` 定义 source_footer / provenance 字段。 | 通过 |
| Validation | `eval_samples.jsonl` 覆盖趋势、高打标率、低打标率、分级、已知维度、未列举维度、反例和低信息量。 | 通过 |
| Maintenance | 角色级 Owner 已存在，但尚未落到具体负责人。 | 部分通过 |
| 真实 source 接入 | 物理表和字段映射来自已验证 Skill，但真实语义层指标 ID 尚未接入。 | 部分通过 |

## 已避免的失败模式

- 概念到实体歧义：自动处置准确率、质检准确率、底线事故数均被列为反例或禁用替代口径。
- 数据 / 口径过期：字段、Owner、分区新鲜度和禁止来源被显式记录，后续变更必须回测。
- 检索失败：场景包通过一级 `scenario-index.md` 暴露给四类 Skill，避免深层链式检索。

## 阶段 1 约束

- 只做感知 + 分析最小链路。
- 只输出 `scenario_key`、`task_type`、QueryPlan、source_footer。
- 不连接真实 Aeolus / Hive / ClickHouse。
- 不发送真实通知。
- 不写线上状态。
- 未列举维度只输出 `dimension_discovery_required`，不拼接字段查询。

## 后续接真实数据前必须补齐

- 接入真实 Semantic Layer / Aeolus 指标 ID。
- 将角色级 Owner 替换为具体治理 Owner、群或值班机制。
- 为字段发现增加真实字段元数据查询工具或只读 mock。
- 为 QueryPlan 增加 source tier 与字段命中率回测。
