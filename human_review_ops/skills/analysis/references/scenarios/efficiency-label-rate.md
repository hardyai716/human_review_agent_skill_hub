# 场景：效率模块 / 打标率

## 场景元信息

| 项 | 内容 |
| --- | --- |
| `scenario_key` | `efficiency-label-rate` |
| 主指标 | `label_rate` / 打标率 |
| 相关指标字段 | `[进审量_reviewid]`、`[完审量_reviewid]`、`[打标量__reviewid]` |
| 模块 | 效率模块 |
| 运营对象 | 送审原因 / reason、策略、机审一级标签在不同维度下的打标率表现 |
| 默认运行模式 | `debug_only` / readonly |

## 触发与排除

触发：

- 查询打标率、进审量、完审量、打标量趋势。
- 查询高打标率或低打标率策略 / reason。
- 按机审一级标签、策略 ID、策略名称、送审原因拆解打标率。
- 查询低效策略、低打标 reason、P0/P1/P2/notice 清单。
- 解释一级标签或策略维度的打标率下降原因。

排除：

- 自动处置准确率分析，使用 `efficiency-auto-disposal-accuracy`。
- 质检准确率、人工审核准确率、底线事故数分析。
- 责任人触达、建群、工单推进或线上状态写入。
- 审核员个人明细、手机号、open_id 等敏感明细导出。

## 指标口径

本节只维护 Aeolus 数据集标准字段及其 `` `[数据集字段名]` `` 查询写法；`metric_id`、内部 alias 和脚本变量不进入字段表。

支持维度字段：

| 概念 | aeolus query 使用字段 | 说明 |
| --- | --- | --- |
| 日期分区 | `[p_date]` | 时间窗口和分区字段。 |
| 送审原因 | `[reason]` | 打标率分析主实体。 |
| 机审一级标签 | `[机审一级标签]` | 默认支持拆解维度；空值必须保留。 |
| 策略 ID | `[strategy_id]` | 稳定主键；策略维度分析优先使用。 |
| 策略名称 | `[strategy_name]` | 展示字段；历史改名时不得替代策略 ID。 |
| 审核场景 | `[scene]` | 默认样本池筛选字段。 |
| 项目标题 | `[project_title]` | 默认样本池排除测试、质检、离线等项目。 |

指标字段与口径：

| 概念 | aeolus query 使用字段 | 口径 | 说明 |
| --- | --- | --- | --- |
| 打标率 | `[打标率__reviewid]` | `[打标量__reviewid] / [完审量_reviewid]` | 可展示或校验；跨粒度聚合时必须用量级字段重算。 |
| 进审量 | `[进审量_reviewid]` | 数据集标准指标 | 规模判断、排序和治理优先级字段。 |
| 完审量 | `[完审量_reviewid]` | 数据集标准指标 | 打标率分母字段；日均完审量由该字段按查询窗口派生。 |
| 打标量 | `[打标量__reviewid]` | 数据集标准指标 | 打标率分子字段；日均打标量由该字段按查询窗口派生。 |

规则：

- 打标率分子是打标量，分母是完审量。
- 进审量只用于规模判断、排序和治理优先级，不作为打标率分母。
- 跨天、跨 reason、跨标签或跨策略聚合时，必须先聚合 `[打标量__reviewid]` 和 `[完审量_reviewid]`，再重算打标率。
- 日均量必须用 `COUNT(DISTINCT [p_date])`，不得硬编码 `/7`；日均量不写入字段清单。
- 分母为 0 时输出质量风险，不给强结论。

## 数据源与字段

查询路径优先级：

1. `semantic_layer`：普通趋势、排序、口径确认优先。
2. `governed_dataset`：语义层暂不覆盖或缺维度时使用。
3. `curated_raw_sql`：仅用于低打标率分级、维度拆解和受控 SQL 模板。
4. `raw_exploration`：只允许字段探测，不得作为最终结论。

推荐来源：

| 项 | 内容 |
| --- | --- |
| Region | `cn` |
| App ID | `1128` |
| Dataset ID | `3888816` |
| Dataset 白皮书 | `https://data.bytedance.net/aeolus/pages/dataManage/larkDoc?appId=1128&dataSetId=3888816&demoUrl=https%3A%2F%2Fbytedance.larkoffice.com%2Fdocx%2FCynjdVMrPoAI5cxvnjXc0ndanFe` |
| Dataset 名称 | `[重点模型]-社区_人工审核明细数据` |
| 物理表 | `olap_content_security_community.dws_sft_tcs_review_task_detail_di` |
| 引擎 | ClickHouse |
| 分区 | `p_date` |
| 新鲜度 | 默认 T+1，查询前必须确认最新完整分区 |

字段清单基于 `bytedcli -j aeolus dataset-fields -r cn 3888816` 的真实返回。运行态可用字段、指标口径、默认维度和默认筛选项统一维护在上方“指标口径”章节；本节不重复维护字段表，未出现在该数据集中的字段不得写入默认查询口径。

字段写法：

- 遵循 `references/common.md#Aeolus 字段引用快速参考`：通过 `aeolus query` 按数据集 ID 编译 `` `[数据集字段名]` ``，非必要时不手写底层字段逻辑。
- 例如 `` `[进审量_reviewid]` ``、`` `[完审量_reviewid]` ``、`` `[打标量__reviewid]` `` 均由 Aeolus 按数据集字段定义编译。
- 禁止裸 `[Name]`。
- 禁止在最终聚合中 `SUM(rate)`。
- 使用风神语义指标时，可用 `` `[打标率__reviewid]` `` 展示，但 evidence 必须同时包含 `` `[完审量_reviewid]` `` 和 `` `[打标量__reviewid]` ``。
- 维度聚合必须先处理空值：对 `mach_root_label_name`、`strategy_id`、`strategy_name`、`reason` 等维度使用 `ifNull(...)` 生成内部 `*_key` 字段，再用这些 key 做 `GROUP BY`。不要把 `ifNull(...)` 的别名直接命名成底表同名字段，例如不要写 `ifNull(`[机审一级标签]`, '（空/机审一级标签）') AS mach_root_label_name GROUP BY mach_root_label_name`；应写成 `AS mach_root_label_key GROUP BY mach_root_label_key`，外层再 `mach_root_label_key AS mach_root_label_name`。这是为了避免 Aeolus / ClickHouse 在同名字段解析时漏掉 NULL 维度记录。

## 默认过滤

默认样本池圈定“社区人工审核”有效样本。所有打标率 SQL 默认复用以下过滤片段：

```sql
AND `[project_title]` NOT LIKE '%虚假%'
AND `[project_title]` NOT LIKE '%标注%'
AND `[project_title]` NOT LIKE '%虚假不实%'
AND `[project_title]` NOT LIKE '%封面%'
AND `[project_title]` NOT LIKE '%自动处置%'
AND `[project_title]` NOT LIKE '%演绎%'
AND `[project_title]` NOT LIKE '%模型%'
AND `[project_title]` NOT LIKE '%run%'
AND `[project_title]` NOT LIKE '%质检%'
AND `[project_title]` NOT LIKE '%QA%'
AND `[project_title]` NOT LIKE '%测试%'
AND `[project_title]` NOT LIKE '%大模型%'
AND `[project_title]` NOT LIKE '%离线%'
AND `[scene]` IN (
  'community_audit_safe',
  'community_audit_style',
  'community_audit_moderate'
)
AND `[reason]` NOT IN ('recall_skip_L6', 'fatal_output')
AND (
  `[机审一级标签]` IS NULL
  OR `[机审一级标签]` IN (
    '不良行为或争议价值观',
    '侵犯未成年权益',
    '偏激社会情绪和涉外言论',
    '党和国家形象负面',
    '危险行为',
    '国家安全',
    '引人不适',
    '指令舆情相关',
    '短期策略迁移',
    '色情性化',
    '违法违规',
    '领导人'
  )
)
```

用户覆盖样本池时，QueryPlan 的 `filters` 和 source_footer 的 `limitations` 必须写明覆盖原因，并要求人工确认。

## 支持维度

默认支持维度和筛选字段已前置在“指标口径”章节。

未列举维度处理规则：

1. 先查语义层或数据集字段说明。
2. 确认字段 Name、业务含义、粒度影响、空值处理和 Owner。
3. 字段确认后才能加入 QueryPlan。
4. 无法确认时停止，不得猜字段。

## 分析模式

| 模式 | `task_type` | 触发条件 | 主要产出 |
| --- | --- | --- | --- |
| 打标率趋势 | `label_rate_trend` | 用户只问打标率、进审量、完审量趋势 | QueryPlan、趋势结果、source_footer |
| 打标率排序 | `label_rate_ranking` | 查询高/低打标率、TopN / BottomN 策略或 reason | 排序清单、进审量、完审量、打标量、打标率 |
| 低打标率分级 | `low_label_rate_grading` | 查询低效策略、P0/P1/P2/notice | 四级分级清单和综合清单 |
| 维度拆解 | `dimension_breakdown` | 按机审一级标签、策略、场景、项目拆分 | `dimensions × reason` 明细和 `dimensions` 汇总 |
| 加权归因 | `weighted_attribution` | 解释一级标签或策略导致的打标率下降 | `weighted_impact` 排序和 Rate / Mix 二级解释 |

通用顺序：

1. 解析时间窗口；缺失时停止澄清。
2. 确认指标是打标率或相关效率指标。
3. 生成 QueryPlan。
4. 做权限、分区、字段、分母、样本池检查。
5. 按模式生成只读 SQL 或只读执行请求。
6. 输出数据事实、解释判断和业务建议，并附 source_footer。

## 模式 B：低打标率分级

默认跑全等级：`notice`、`P2`、`P1`、`P0`。

| 等级 | 默认条件摘要 |
| --- | --- |
| `notice` | 近 7 天打标率 `< 10%` 且当前周期进审量 `> 100`。 |
| `P2` | 单策略低效，或低效策略环比增长。 |
| `P1` | 双周持续低效、单周高量低效，或低效策略爆量。 |
| `P0` | 四周持续低效、两周高量低效、单周超高量低效，或进审量异常爆量。 |

输出要求：

- 四个等级默认均要求当前周期进审量 `> 100`。
- 四个等级 sheet 保留各自完整命中结果，不跨级去重。
- 综合 sheet 按 `P0 > P1 > P2 > notice` 对同一 reason 取最高等级。
- 每条 reason 必须带 evidence：日均进审、日均完审、日均打标、打标率、命中条件。
- 某级无命中时写“本期 0 条”；查询失败时写失败原因。

## 模式 E：加权归因

主排序字段：

```text
weighted_impact = cur_share * cur_rate - prev_share * prev_rate
```

要求：

- 默认周期为近 7 天 vs 前 7 天，必须使用相同窗口长度。
- 默认维度为 `mach_root_label_name × strategy_id × strategy_name`。
- 排序按 `weighted_impact` 升序，负值越大代表对整体打标率下降拖累越大。
- 输出 Rate / Mix Effect 作为二级解释，具体公式读取 `references/methods/weighted_attribution.md`。

## QueryPlan 要求

QueryPlan 必须包含：

- `query_plan_id`
- `scenario_key`
- `metric_id`
- `task_type`
- `time_range`
- `dimensions`
- `filters`
- `source_priority`
- `allowed_sources`
- `forbidden_sources`
- `fallback_reason`
- `quality_checks`
- `review_required`

禁用来源：

- 临时表。
- 无 Owner 的历史 SQL。
- 已废弃策略效果表。
- 未标记治理口径的数据集。
- 未经脱敏的人员明细表。

## 输出要求

- 结论摘要。
- 口径方法：分子、分母、过滤条件、grain。
- 数据证据：趋势、分级、排序、维度拆解或加权归因表。
- 限制说明：新鲜度、缺失、样本偏差、未覆盖范围。
- source_footer。

source_footer ref 示例：

```json
{
  "metric_contract_ref": "references/scenarios/efficiency-label-rate.md#指标口径",
  "dataset_reference_ref": "references/scenarios/efficiency-label-rate.md#数据源与字段",
  "analysis_ref": "references/scenarios/efficiency-label-rate.md#分析模式"
}
```

## 失败处理

- 无法确认打标率口径：停止，输出待确认口径。
- 无法确认时间窗口：停止，要求用户补时间。
- 数据分区未就绪：停止，输出最新分区和目标分区。
- 权限不足：停止，输出权限阻断。
- 字段映射失败：停止，列出缺失字段。
- 查询失败：输出错误、QueryPlan、source_footer 和重试建议。
- 分母为 0 或样本过小：输出质量风险，不给强结论。

## 正反例

正例：

- 近 7 天有哪些高完审低打标的 reason？
- 近 7 天打标率最高的策略有哪些？
- 帮我看下近 7 天低打标率策略分 P0/P1/P2/notice 的情况。
- 按机审一级标签拆一下打标率。
- 看危险行为打标率下降主要是哪些策略拖累。

反例：

- 分析一下自动处置准确率为什么下降。
- 质检准确率下降了。
- 底线事故数上升了。

低信息量：

- 这个策略怎么了？

处理：先询问指标、时间窗口和策略 / reason，不直接查询。
