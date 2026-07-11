# 场景：效率模块 / 自动处置准确率

## 场景元信息

| 项 | 内容 |
| --- | --- |
| `scenario_key` | `efficiency-auto-disposal-accuracy` |
| 逻辑主指标 | `auto_disposal_accuracy` / 自动处置准确率；这是 Skill 内部 `metric_id`，不是数据集物理字段。 |
| 数据集主指标字段 | `label_acc_weight_rate` / 三级标签准确率 |
| 相关指标 | `root_label_accuracy` / 一级标签准确率 |
| 模块 | 效率模块 |
| 运营对象 | 一级风险标签、三级风险标签、是否安全治理域、权重类型和日期分区下的准确率表现 |
| 当前状态 | 数据源和一级风险标签维度查询已完成只读验证，其他查询类型待补充验证 |
| 默认运行模式 | `debug_only` / readonly |

## 触发与排除

触发：

- 分析自动处置准确率为什么下降。
- 查询自动处置准确率是否达标。
- 查询三级标签准确率或机审自动处置准确率。
- 按一级风险标签、三级标签、是否安全治理域、权重类型或时间拆解自动处置准确率。

排除：

- 打标率、低打标 reason、低效策略分级，使用 `efficiency-label-rate`。
- 质检准确率、底线事故数、人工审核准确率。
- 通知草稿、负责人路由、状态写入。

## 指标口径

本节只维护 Aeolus 数据集标准字段及其 `` `[数据集字段名]` `` 查询写法；`metric_id`、内部 alias 和脚本变量不进入字段表。

支持维度字段：

| 概念 | aeolus query 使用字段 | 说明 |
| --- | --- | --- |
| 日期分区 | `[date]` | 数据集字段为 `date`，分区字段。 |
| 一级风险标签 | `[一级风险标签]` | 默认主拆解维度；输出前按“一级风险标签统一归一规则”归一。 |
| 三级风险标签 | `[三级风险标签]` | 三级标签准确率主实体。 |
| 一级标签 ID | `[root_label_id]` | 一级标签稳定 ID。 |
| 三级标签 ID | `[label_id]` | 三级标签稳定 ID。 |
| 是否安全治理域 | `[是否安全治理域]` | 可用于安全治理域筛选或拆解。 |

默认筛选字段：

| 概念 | aeolus query 使用字段 | 说明 |
| --- | --- | --- |
| 标签等级 | `[标签等级]` | 一级标签查询固定 `1`；三级标签查询固定 `3`。 |
| 权重类型 | `[权重类型]` | 默认 `0=整体（安全、画风、大模型）`；`1=大盘（安全、画风）`；`2=大模型`。 |
| 一级风险标签 | `[一级风险标签]` | 默认排除空值、`-`、`平台秩序`、`指令临时管控`、`指令舆情相关`。 |

指标字段与口径：

| 概念 | aeolus query 使用字段 | 口径 | 说明 |
| --- | --- | --- | --- |
| 自动处置准确率 / 三级标签准确率 | `[三级标签准确率]` | `[三级标签准确量] / ([mach_label_injury_cnt_1d] + [三级标签准确量])` | 当前主指标字段；默认粒度为日期 × 标签等级 × 权重类型 × 三级标签。 |
| 一级标签准确率 | `[一级标签准确率]` | `[一级标签准确量] / ([mach_rlabel_injury_cnt_1d] + [一级标签准确量])` | 一级风险标签维度表现使用字段。 |
| 三级标签准确量 | `[三级标签准确量]` | 数据集标准指标 | 三级标签准确率分子。 |
| 三级标签误伤量 | `[mach_label_injury_cnt_1d]` | 数据集标准字段 | 三级标签准确率分母组成部分。 |
| 一级标签准确量 | `[一级标签准确量]` | 数据集标准指标 | 一级标签准确率分子。 |
| 一级标签误伤量 | `[mach_rlabel_injury_cnt_1d]` | 数据集标准字段 | 一级标签准确率分母组成部分。 |
| 标注量 | `[标注量(周期总量)]` | 数据集标准指标 | 人审标注对象数。 |

规则：

- 自动处置准确率在本数据集中对应 `[三级标签准确率]`。
- 一级风险标签维度表现使用 `[一级标签准确率]`。
- 物理表已经提供加权准确率字段；单日、单标签、单 `weight_type` 查询可直接展示对应 rate 字段。
- 周维度准确率使用 `sum([一级标签准确率]) / count(distinct [date])`；不得只输出 `SUM(rate)`。
- 跨标签、跨 `weight_type` 汇总时，应先确认权重口径，不得把不同口径的 rate 直接相加。
- 环比以百分点差值展示：`cur_rate - prev_rate`，回答时乘 100 后展示为 `pp`。
- 不得用质检准确率、底线事故数或人工审核准确率替代本指标。

## 数据源与字段

查询路径优先级：

1. `governed_dataset`：已验证 Aeolus 数据集 `3945965`，用于当前一级风险标签查询。
2. `curated_raw_sql`：当需要受控 SQL 模板、环比或复杂过滤时，查询物理 ClickHouse 表。
3. `semantic_layer`：后续若补齐公司语义层指标，可前置为第一优先级。
4. `raw_exploration`：只允许字段探测，不得作为最终结论。

推荐来源：

| 项 | 内容 |
| --- | --- |
| Region | `cn` |
| App ID | `1128` |
| Dataset ID | `3945965` |
| Dataset 链接 | `https://data.bytedance.net/aeolus/pages/dataManage/detail/3945965?appId=1128` |
| Dataset 白皮书 | `https://data.bytedance.net/aeolus/pages/dataManage/larkDoc?activeFieldTableMode=struct&appId=1128&dataSetId=3945965&demoUrl=https%3A%2F%2Fbytedance.larkoffice.com%2Fdocx%2FCU61dumoBoyPDtxqS9vcUQi6ndd` |
| Dataset 名称 | `[核心指标]-机审标签误伤准确聚合数据集` |
| 物理表 | `olap_content_security_community.dm_sft_eft_mach_label_injury_aggr_1d` |
| 引擎 | ClickHouse |
| 分区 | `date` |
| 新鲜度 | 默认 T+1，一级风险标签查询默认取 T-1 |
| 数据集 Owner | `tangshuo.0819` |

字段清单基于 `bytedcli -j aeolus dataset-fields -r cn 3945965` 的真实返回。运行态可用字段、指标口径、默认维度和默认筛选项统一维护在上方“指标口径”章节；本节不重复维护字段表，未出现在该数据集中的字段不得写入默认查询口径。

字段写法：

- 遵循 `references/common.md#Aeolus 字段引用快速参考`：通过 `aeolus query` 按数据集 ID 编译 `` `[数据集字段名]` ``，非必要时不手写底层字段逻辑。
- 物理表字段使用 ClickHouse 裸列或反引号：`` `date` ``、`` `root_label_name` ``。
- Aeolus 展示维度名如 `一级风险标签`、`三级风险标签` 来自数据集字段定义；当前 SQL 模板仅在需要一级标签归一或避免中文别名解析失败时使用物理列 + 明确 `case`。
- 中文输出列名在最终回答层转换；SQL 内部 alias 使用 ASCII，例如 `root_label`、`rlabel_acc_rate`、`wow_diff`。
- 维度归一先生成内部 `*_key` 字段，再 join 或 group；不要用中文别名参与 join。

一级风险标签统一归一规则：

```sql
case
  when `root_label_name` in ('公序良俗', '不良行为或争议价值观') then '不良行为或争议价值观'
  when `root_label_name` = '色情低俗' then '色情性化'
  when `root_label_name` = '未成年人' then '侵犯未成年权益'
  else `root_label_name`
end
```

禁用来源：

- 临时表。
- 无 Owner 历史 SQL。
- 已废弃策略效果表。
- 未标记治理口径的数据集。
- 敏感个人明细。

## 默认过滤

一级风险标签维度查询默认过滤已前置在“指标口径”的默认筛选字段表中：

```sql
WHERE `date` = today() - 1
  AND label_level = 1
  AND weight_type = 0
  AND root_label_name NOT IN ('', '-', '平台秩序', '指令临时管控', '指令舆情相关')
```

说明：

- 日期默认 T-1；环比默认对比 T-2。
- `label_level` 是必筛项；当前一级标签查询固定 `label_level=1`，三级标签查询应显式使用 `label_level=3`。
- `weight_type=0` 按“整体（安全、画风、大模型）”口径使用；如用户要求大盘或大模型分口径，分别使用 `1` 或 `2`，并在输出中增加 `weight_type` 列。
- 排除空标签、占位标签和用户指定不纳入当前查询口径的标签。

## 预警目标与等级

目标线：

- 自动处置准确率目标为 `80%`。
- 当前数据集没有独立的策略、队列或风险域字段；预警条件 1 使用一级风险标签 `root_label_key` 承接风险域类运营视角。

等级规则：

| 等级 | 已具备查询口径的条件 1 | 暂保留描述的条件 2 |
| --- | --- | --- |
| `P2` | 一级标签日维度准确率环比下降 `>= 3pp`，即 `cur_rate - prev_rate <= -0.03`。 | 一级标签维度，近 7 天日均处置量 `> 50` 且准确率 `< 30%`；处置量字段和统计口径待补充。 |
| `P1` | 一级标签周维度自动处置准确率 `< 80%`。 | 上周期低效策略在本周期仍未提升至 `80%` 或未下线；该条件不属于当前数据集字段清单，待外部策略状态表补充。 |
| `P0` | 连续三周一级标签自动处置准确率 `< 80%`。 | 上上周期低效策略在上周期和本周期均未提升至 `80%` 或未下线；该条件不属于当前数据集字段清单，待外部策略状态表补充。 |

条件 1 输出要求：

- `P2`: 输出一级风险标签、当前日期、当前准确率、上一日准确率、环比变化 pp。
- `P1`: 输出一级风险标签、当前周窗口、周准确率、目标线、低于目标差距 pp。
- `P0`: 输出一级风险标签、三周窗口、三周准确率、目标线、连续低于目标说明。
- 同一一级风险标签同时命中多个等级时，综合视图按 `P0 > P1 > P2` 取最高等级；分等级视图保留各自命中明细。

## 支持维度

默认支持维度和筛选字段已前置在“指标口径”章节。用户指定新维度时，先确认字段含义、粒度、权限和 Owner；无法确认时停止。

## 分析模式

| 模式 | `task_type` | 触发条件 | 主要产出 |
| --- | --- | --- | --- |
| 准确率趋势 | `accuracy_trend` | 用户询问整体趋势、是否达标、近期变化 | QueryPlan、趋势结果、source_footer |
| 预警分级 | `auto_disposal_alert_grading` | 用户查询 P0/P1/P2 或低于目标的预警清单 | P0/P1/P2 条件 1 命中清单和待补条件说明 |
| 一级风险标签拆解 | `auto_disposal_root_label_accuracy_breakdown` | 用户查询一级风险标签维度表现 | 一级风险标签、一级标签准确率、环比 pp |
| 准确率排序 | `accuracy_ranking` | 用户查询高/低准确率标签 | 排序清单、分子、分母、准确率 |
| 维度拆解 | `dimension_breakdown` | 用户按一级标签、三级标签、是否安全治理域、权重类型或日期拆解 | `dimensions` 明细和汇总 |

通用顺序：

1. 确认指标口径和时间窗口。
2. 确认数据源、字段和 Owner。
3. 检查数据新鲜度、字段映射和 `weight_type` 口径。
4. 按任务类型选择指标字段：一级标签表现用 `rlabel_acc_weight_rate`，三级标签准确率用 `label_acc_weight_rate`。
5. 输出整体趋势或按一级标签、三级标签、是否安全治理域、权重类型、日期拆分。
6. 输出候选根因和 source_footer。

## 模式 A：一级风险标签拆解

适用于用户要求看一级风险标签维度表现，或默认查询“自动处置准确率 / 三级标签准确率”的一级标签表现。

默认输出列：

- 一级风险标签。
- 一级标签准确率，来自 `rlabel_acc_weight_rate`。
- 环比，来自 `cur_rate - prev_rate`，展示为 `pp`。

已验证 SQL：

```sql
WITH cur AS (
  SELECT
    case
      when root_label_name in ('公序良俗', '不良行为或争议价值观') then '不良行为或争议价值观'
      when root_label_name = '色情低俗' then '色情性化'
      when root_label_name = '未成年人' then '侵犯未成年权益'
      else root_label_name
    end AS root_label_key,
    rlabel_acc_weight_rate AS cur_rate
  FROM olap_content_security_community.dm_sft_eft_mach_label_injury_aggr_1d
  WHERE `date` = today() - 1
    AND label_level = 1
    AND weight_type = 0
    AND root_label_name NOT IN ('', '-', '平台秩序', '指令临时管控', '指令舆情相关')
),
prev AS (
  SELECT
    case
      when root_label_name in ('公序良俗', '不良行为或争议价值观') then '不良行为或争议价值观'
      when root_label_name = '色情低俗' then '色情性化'
      when root_label_name = '未成年人' then '侵犯未成年权益'
      else root_label_name
    end AS root_label_key,
    rlabel_acc_weight_rate AS prev_rate
  FROM olap_content_security_community.dm_sft_eft_mach_label_injury_aggr_1d
  WHERE `date` = today() - 2
    AND label_level = 1
    AND weight_type = 0
    AND root_label_name NOT IN ('', '-', '平台秩序', '指令临时管控', '指令舆情相关')
)
SELECT
  cur.root_label_key AS root_label,
  cur.cur_rate AS rlabel_acc_rate,
  (cur.cur_rate - prev.prev_rate) AS wow_diff,
  prev.prev_rate AS prev_rlabel_acc_rate
FROM cur
LEFT JOIN prev
  ON cur.root_label_key = prev.root_label_key
ORDER BY cur.cur_rate ASC
```

执行命令：

```bash
bytedcli -j aeolus query -r cn 3945965 "<SQL>" --limit 200
```

已验证结果特征：

- T-1 为 `2026-07-10`，返回 11 个一级风险标签。
- `短期策略迁移` 最低，一级标签准确率约 `29.11%`，环比约 `-22.12pp`。
- `侵犯未成年权益` 最高，一级标签准确率约 `91.55%`。
- SQL 内中文别名可能触发 Aeolus 解析失败，必须使用 ASCII alias，最终输出时再翻译列名。

## 模式 B：预警分级

当前先执行 P2/P1/P0 的条件 1；条件 2 只输出规则占位，不生成命中结论。

### P2 条件 1：日维度环比下降

```sql
WITH cur AS (
  SELECT
    case
      when root_label_name in ('公序良俗', '不良行为或争议价值观') then '不良行为或争议价值观'
      when root_label_name = '色情低俗' then '色情性化'
      when root_label_name = '未成年人' then '侵犯未成年权益'
      else root_label_name
    end AS root_label_key,
    rlabel_acc_weight_rate AS cur_rate
  FROM olap_content_security_community.dm_sft_eft_mach_label_injury_aggr_1d
  WHERE `date` = today() - 1
    AND label_level = 1
    AND weight_type = 0
    AND root_label_name NOT IN ('', '-', '平台秩序', '指令临时管控', '指令舆情相关')
),
prev AS (
  SELECT
    case
      when root_label_name in ('公序良俗', '不良行为或争议价值观') then '不良行为或争议价值观'
      when root_label_name = '色情低俗' then '色情性化'
      when root_label_name = '未成年人' then '侵犯未成年权益'
      else root_label_name
    end AS root_label_key,
    rlabel_acc_weight_rate AS prev_rate
  FROM olap_content_security_community.dm_sft_eft_mach_label_injury_aggr_1d
  WHERE `date` = today() - 2
    AND label_level = 1
    AND weight_type = 0
    AND root_label_name NOT IN ('', '-', '平台秩序', '指令临时管控', '指令舆情相关')
)
SELECT
  cur.root_label_key AS root_label,
  cur.cur_rate AS cur_rate,
  prev.prev_rate AS prev_rate,
  (cur.cur_rate - prev.prev_rate) AS delta_rate,
  'P2_daily_drop_ge_3pp' AS hit_rule_id
FROM cur
LEFT JOIN prev
  ON cur.root_label_key = prev.root_label_key
WHERE (cur.cur_rate - prev.prev_rate) <= -0.03
ORDER BY delta_rate ASC
```

### P1 条件 1：周维度低于目标

周维度准确率使用日级 `rlabel_acc_weight_rate` 跨日期求和后除以日期数。

```sql
SELECT
  case
    when root_label_name in ('公序良俗', '不良行为或争议价值观') then '不良行为或争议价值观'
    when root_label_name = '色情低俗' then '色情性化'
    when root_label_name = '未成年人' then '侵犯未成年权益'
    else root_label_name
  end AS root_label,
  sum(rlabel_acc_weight_rate) / count(distinct `date`) AS week_rate,
  (sum(rlabel_acc_weight_rate) / count(distinct `date`) - 0.8) AS gap_to_target,
  min(`date`) AS window_start,
  max(`date`) AS window_end,
  'P1_week_rate_lt_80pct' AS hit_rule_id
FROM olap_content_security_community.dm_sft_eft_mach_label_injury_aggr_1d
WHERE `date` >= today() - 7
  AND `date` < today()
  AND label_level = 1
  AND weight_type = 0
  AND root_label_name NOT IN ('', '-', '平台秩序', '指令临时管控', '指令舆情相关')
GROUP BY root_label
HAVING week_rate < 0.8
ORDER BY week_rate ASC
```

### P0 条件 1：连续三周低于目标

```sql
WITH weekly AS (
  SELECT
    case
      when root_label_name in ('公序良俗', '不良行为或争议价值观') then '不良行为或争议价值观'
      when root_label_name = '色情低俗' then '色情性化'
      when root_label_name = '未成年人' then '侵犯未成年权益'
      else root_label_name
    end AS root_label,
    multiIf(`date` >= today() - 7 AND `date` < today(), 'week_0',
            `date` >= today() - 14 AND `date` < today() - 7, 'week_1',
            `date` >= today() - 21 AND `date` < today() - 14, 'week_2',
            'other') AS week_bucket,
    sum(rlabel_acc_weight_rate) / count(distinct `date`) AS week_rate
  FROM olap_content_security_community.dm_sft_eft_mach_label_injury_aggr_1d
  WHERE `date` >= today() - 21
    AND `date` < today()
    AND label_level = 1
    AND weight_type = 0
    AND root_label_name NOT IN ('', '-', '平台秩序', '指令临时管控', '指令舆情相关')
  GROUP BY root_label, week_bucket
)
SELECT
  root_label,
  maxIf(week_rate, week_bucket = 'week_0') AS week_0_rate,
  maxIf(week_rate, week_bucket = 'week_1') AS week_1_rate,
  maxIf(week_rate, week_bucket = 'week_2') AS week_2_rate,
  'P0_three_week_rate_lt_80pct' AS hit_rule_id
FROM weekly
GROUP BY root_label
HAVING week_0_rate < 0.8
   AND week_1_rate < 0.8
   AND week_2_rate < 0.8
ORDER BY week_0_rate ASC
```

## QueryPlan 要求

必填字段：

- `metric_id`
- `time_range`
- `dimensions`
- `filters`
- `allowed_sources`
- `forbidden_sources`
- `quality_checks`
- `review_required`

一级风险标签拆解已完成只读验证，可将 `review_required=false` 用于同口径复用；新增维度或跨周期汇总仍需 `review_required=true`。

## 输出要求

- 一级风险标签拆解展示一级风险标签、一级标签准确率和环比 pp。
- 三级标签准确率查询展示自动处置评估量、三级标签处置准确量和自动处置准确率。
- 百分比保留两位小数。
- 样本池、聚合口径或字段未确认时，置信度不得标为 high。
- source_footer 必须说明数据集、表、分区、新鲜度、`label_level`、`weight_type` 和过滤条件。

source_footer ref 示例：

```json
{
  "metric_contract_ref": "references/scenarios/efficiency-auto-disposal-accuracy.md#指标口径",
  "dataset_reference_ref": "references/scenarios/efficiency-auto-disposal-accuracy.md#数据源与字段",
  "analysis_ref": "references/scenarios/efficiency-auto-disposal-accuracy.md#分析模式"
}
```

## 失败处理

- 指标口径不明确：停止，要求确认分子和分母。
- 数据源未确认：停止，输出待确认数据源和 Owner。
- 字段映射失败：停止，列出缺失字段。
- 分母为 0：输出质量风险，不给强结论。
- 周聚合口径异常：必须使用 `sum(rlabel_acc_weight_rate) / count(distinct date)`；不得只输出 `SUM(rate)` 或跨 `weight_type` 混算。
- 查询失败：输出错误、QueryPlan、source_footer 和下一步修复建议。

## 正反例

正例：

- 分析一下自动处置准确率为什么下降。
- 看一下昨天一级风险标签维度的自动处置准确率。
- 三级标签准确率按一级风险标签拆一下。
- 按三级标签维度看自动处置准确率。

反例：

- 近 7 天低打标率 reason 有哪些？
- 质检准确率下降了。
- 底线事故数上升了。

低信息量：

- 这个标签怎么了？

处理：先询问指标、时间窗口和标签范围，不直接查询。
