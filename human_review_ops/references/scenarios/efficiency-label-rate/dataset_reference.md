# 数据集说明：打标率

## 查询路径优先级

1. Semantic Layer：强制第一优先级，先查 canonical metric、dimension、segment 和 freshness。
2. Governed Dataset / Aeolus Dataset：语义层暂不覆盖但存在治理数据集时使用。
3. Curated Raw SQL：仅在复杂分级或维度拆解无法由语义层表达时使用。
4. Raw Exploration：只允许字段探测，不得作为最终结论。
5. 不可查询：无权限、无口径、无 Owner、数据未就绪时停止。

## 推荐来源

| source_tier | 来源 | 用途 | 状态 |
| --- | --- | --- | --- |
| `semantic_layer` | 公司内部语义层 / 风神语义数据集 | 普通打标率、完审量、趋势查询 | 优先 |
| `governed_dataset` | Aeolus 治理数据集 | 语义层未覆盖但数据集已治理时使用 | 可回退 |
| `curated_raw_sql` | `olap_content_security_community.dws_sft_tcs_review_task_detail_di` | 低打标率分级、维度拆解 | 受控回退 |

## 真实风神入口

- Region：`cn`
- App ID：`1128`
- Dataset ID：`3888816`
- Dataset 名称：`[重点模型]-社区_人工审核明细数据`
- 查询命令：`bytedcli -j aeolus query -r cn 3888816 "<SQL>" --limit 1000`
- 查字段命令：`bytedcli -j aeolus dataset-fields -r cn 3888816`
- `label_rate` 对应风神指标：`打标率__reviewid`
- Aeolus metric ID：`10000036292379`
- 分子指标：`打标量__reviewid`
- 分母指标：`完审量_reviewid`

## 风神使用注意事项

- JSON 输出必须使用 `-j`，且 `-j` 是 bytedcli 全局参数，位置必须在 `aeolus` 前：`bytedcli -j aeolus ...`。
- 查数优先使用 `bytedcli -j aeolus query -r cn 3888816 "<SQL>" --limit 1000`。
- 复杂过滤、`NOT LIKE`、`HAVING`、分级规则和多阶段聚合必须走 `aeolus query`，不要用 `viz-query` 兜复杂 SQL。
- `viz-query` 仅适合字段验证、简单聚合或快速探测；若 `expr` 已自带 `sum(`、`count(`、`avg(` 或比率表达式，不要再传 `aggregation`，否则容易触发后端校验错误。
- 查询失败不能解释成“无低打标率 reason”；必须区分权限失败、字段错误、分区缺失、过滤过严和真实空结果。
- 不要误用 `4284992` 等标注准确率数据集替代 `3888816`，否则会把打标率口径查成标签准确率口径。

## 物理表参考

- 表：`olap_content_security_community.dws_sft_tcs_review_task_detail_di`
- 引擎：ClickHouse
- 分区：`p_date`
- 默认新鲜度：T+1，查询前必须确认 `MAX(p_date)` 和目标分区行数。
- 支持粒度：`p_date × reason`；维度拆解支持 `p_date × dimensions × reason`。
- 不用于：人员明细、责任人解析、open_id / chat_id、触达对象。

## 字段映射

| 概念 | 逻辑字段 | 默认 Name | 说明 |
| --- | --- | --- | --- |
| 送审 reason / 策略 | `reason` | `reason` | 打标率分析主实体。 |
| 日期分区 | `date` | `p_date` | 用于时间窗口和分区就绪检查。 |
| 项目标题 | `project_title` | `project_title` | 用于排除测试、质检、离线等项目。 |
| 审核场景 | `scene` | `scene` | 默认保留社区审核三类场景。 |
| 机审一级标签 | `mach_root_label_name` | `机审一级标签` | 空值必须保留，维度拆解使用。 |
| 进审量 | `review_in_cnt` | `进审量_reviewid` | 聚合字段。 |
| 完审量 | `review_done_cnt` | `完审量_reviewid` | 打标率分母。 |
| 打标量 | `label_cnt` | `打标量__reviewid` | 双下划线，打标率分子。 |
| 打标率 | `label_rate` | `打标率__reviewid` | 不直接跨粒度聚合，应重算。 |

## 扩展维度发现

当用户指定的维度不在 `metric_contract.md` 支持维度中时：

1. 先查 Semantic Layer 是否存在对应 dimension 或 segment。
2. 若语义层未覆盖，再查 Aeolus / 数据集字段说明。
3. 必须确认字段 Name、业务含义、粒度影响、空值处理和 Owner。
4. 通过确认后才能加入 QueryPlan 的 `dimensions`。
5. 无法确认时输出澄清问题或人工确认请求，不得猜字段。

## SQL 写法约束

- ClickHouse 语义字段使用反引号包方括号：`` `[Name]` ``。
- 禁止裸 `[Name]`。
- 禁止在最终聚合中 `SUM(rate)`。
- 打标率必须用 `SUM(label_cnt) / SUM(review_done_cnt)` 重算。
- 使用风神语义指标时，可用 `` `[打标率__reviewid]` ``，但必须同时输出 `` `[完审量_reviewid]` `` 和 `` `[打标量__reviewid]` `` 作为 evidence。
- 日均量必须用 `COUNT(DISTINCT p_date)`，不得硬编码 `/7`。
- NULL 机审标签必须用 `field IS NULL OR field IN (...)`，不得写 `IN (NULL, ...)`。

## 数据质量检查

- 目标分区是否就绪。
- 分母 `review_done_cnt` 是否为 0。
- 目标时间窗口是否与已就绪分区一致。
- 维度粒度是否与用户问题一致。
- 查询结果为空时，是否已排除权限失败、字段错误、分区缺失和过滤过严。
- 是否误用了单下划线字段，如 `打标量_reviewid`。

## 禁止来源

- 临时表。
- 无 Owner 的历史 SQL。
- 已废弃策略效果表。
- 未标记治理口径的数据集。
- 未经脱敏的人员明细表。

## Provenance 要求

最终输出必须带：

```markdown
> Source: semantic_layer | governed_dataset | curated_raw_sql | raw_exploration
> Confidence: high | medium | low
> Freshness: max_partition=YYYY-MM-DD / checked_at=YYYY-MM-DD HH:mm
> Owner: 人审效率域数据 Owner
> Reviewed: semantic_compile_passed | sql_review_passed | needs_human_review
```
