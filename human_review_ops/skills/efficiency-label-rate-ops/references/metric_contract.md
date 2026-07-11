# 指标契约：打标率

## 主指标

- `metric_id`：`label_rate`
- 中文名：打标率
- 模块：效率模块
- 场景：送审原因 / reason 在不同维度下的打标率查询、对比、趋势和分级分析
- 状态：active

## 相关指标

指标字段与口径：

| 概念 | aeolus query 使用字段 | 口径 | 说明 |
| --- | --- | --- | --- |
| 打标率 | `[打标率__reviewid]` | `[打标量__reviewid] / [完审量_reviewid]` | 可展示或校验；跨粒度聚合时必须用量级字段重算。 |
| 进审量 | `[进审量_reviewid]` | 数据集标准指标 | 规模判断、排序和治理优先级字段。 |
| 完审量 | `[完审量_reviewid]` | 数据集标准指标 | 打标率分母字段；日均完审量由该字段按查询窗口派生。 |
| 打标量 | `[打标量__reviewid]` | 数据集标准指标 | 打标率分子字段；日均打标量由该字段按查询窗口派生。 |

## 核心口径

- 打标率分子：打标量。
- 打标率分母：完审量。
- 打标率公式：`打标率 = SUM(打标量) / SUM(完审量)`。
- 日均公式：`SUM(指标) / COUNT(DISTINCT p_date)`。
- 环比增长率：`(本期日均进审量 - 上期日均进审量) / NULLIF(上期日均进审量, 0)`。
- 日均增量：`本期日均进审量 - 上期日均进审量`。

## 默认样本池

默认样本池圈定“社区人工审核”有效样本，所有打标率 SQL 必须直接复用以下过滤片段：

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

默认情况下，打标率查询、排序、低打标率分级和维度拆解都必须使用以上默认样本池 SQL 片段。若用户明确要求覆盖样本池，必须在 QueryPlan 的 `filters` 和 source_footer 中标明覆盖原因，并要求人工确认。

## 支持维度

| 概念 | aeolus query 使用字段 | 说明 |
| --- | --- | --- |
| 日期分区 | `[p_date]` | 时间窗口和分区字段。 |
| 送审原因 | `[reason]` | 打标率分析主实体。 |
| 机审一级标签 | `[机审一级标签]` | 常用拆解维度；空值必须保留。 |
| 策略 ID | `[strategy_id]` | 策略 / 规则 ID，2026-07-09 经 `dataset-fields` 与真实只读查询确认。 |
| 策略名称 | `[strategy_name]` | 策略名称，2026-07-09 经 `dataset-fields` 与真实只读查询确认。 |
| 审核场景 | `[scene]` | 默认样本池筛选字段。 |
| 项目标题 | `[project_title]` | 默认样本池排除字段。 |

未列举维度处理规则：

- 用户指定的新维度不在上表时，先走 Semantic Layer / 数据集字段发现，确认字段名、字段含义、粒度、权限和 Owner。
- 只有字段通过数据集说明或字段探测确认后，才能加入 QueryPlan。
- 无法确认字段或粒度时，必须澄清或转人工，不得猜测字段。

## 分级与排序

| 等级 | 判定方向 | 说明 |
| --- | --- | --- |
| `P0` | 最严重 | 四周持续低效、高量低效或进审量异常爆量。 |
| `P1` | 高 | 双周持续低效、单周高量低效或低效爆量。 |
| `P2` | 中 | 单策略低效或低效策略环比增长。 |
| `notice` | 观察 | 单周期打标率偏低，需要观察。 |

低打标率分级阈值由 `analysis.md` 维护，默认来源于已验证的 `low-efficiency-strategy-analysis/references/grading_rules.md`。高打标率或普通打标率查询不套用低效分级，按用户指定的排序、TopN、维度和时间窗口输出。

## 禁止事项

- 不得把打标率分母写成进审量。
- 不得直接跨天、跨 reason、跨标签累加 `打标率` 字段。
- 不得在分区缺失或数据未就绪时输出“无低效策略”。
- 不得把查询失败、权限失败解释成业务无异常。
- 不得使用自动处置准确率、质检准确率或底线事故数字段替代打标率。
- 不得使用无 Owner、已废弃或未治理字段作为最终结论来源。

## Owner

- 指标 Owner：人审效率域指标治理 Owner，负责确认打标率、进审量、完审量、打标量、分级阈值和口径变更。
- 数据 Owner：人审效率域数据 Owner，负责确认语义层指标、Aeolus 数据集、Hive / ClickHouse 表、字段含义、分区新鲜度和血缘。
- 业务解释 Owner：人审运营效率治理 Owner，负责解释打标率波动、高低打标策略表现、治理动作和升级路径。

> 当前先使用角色级 Owner，不编造具体个人。接入真实治理资产后再替换为具体负责人、群或值班机制。
