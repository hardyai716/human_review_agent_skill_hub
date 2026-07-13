# 指标契约：打标率

## 主指标

- `metric_id`：`label_rate`
- 中文名：打标率
- 模块：效率模块
- 场景：策略、风险域、可选 `reason` 拆解维度下的打标率查询、对比、趋势和分级分析
- 状态：active

## 相关指标

### 方向 1：人工审核明细

| 业务概念 | `metric_id` | 口径 | 默认粒度 |
| --- | --- | --- | --- |
| 打标率 | `label_rate` | `SUM(label_cnt) / SUM(review_done_cnt)` | `day × mach_root_label_name × strategy_id × strategy_name` |
| 进审量 | `review_in_cnt` | 进入人审的审核量 | `day × mach_root_label_name × strategy_id × strategy_name` |
| 完审量 | `review_done_cnt` | 完成人审的审核量 | `day × mach_root_label_name × strategy_id × strategy_name` |
| 打标量 | `label_cnt` | 被打标的审核量 | `day × mach_root_label_name × strategy_id × strategy_name` |
| 日均进审量 | `avg_daily_review_in_cnt` | `SUM(review_in_cnt) / COUNT(DISTINCT p_date)` | `mach_root_label_name × strategy_id × strategy_name` |
| 日均完审量 | `avg_daily_review_done_cnt` | `SUM(review_done_cnt) / COUNT(DISTINCT p_date)` | `mach_root_label_name × strategy_id × strategy_name` |
| 日均打标量 | `avg_daily_label_cnt` | `SUM(label_cnt) / COUNT(DISTINCT p_date)` | `mach_root_label_name × strategy_id × strategy_name` |

### 方向 2：举报流转

| 业务概念 | `metric_id` | 口径 | 默认粒度 |
| --- | --- | --- | --- |
| 举报打标率 | `report_label_rate` | `SUM(report_label_cnt) / SUM(report_review_done_cnt)` | `day × enpool_reason` |
| 举报进审量 | `report_review_in_cnt` | 数据集指标 `进审量_report_id` | `day × enpool_reason` |
| 举报人审完结量 | `report_review_done_cnt` | 数据集指标 `人审完结量_report_id` | `day × enpool_reason` |
| 举报打标量 | `report_label_cnt` | 数据集指标 `打标量_report_id` | `day × enpool_reason` |
| 举报日均人审完结量 | `avg_daily_report_review_done_cnt` | `SUM(report_review_done_cnt) / COUNT(DISTINCT 进审日期)` | `enpool_reason` |
| 举报日均打标量 | `avg_daily_report_label_cnt` | `SUM(report_label_cnt) / COUNT(DISTINCT 进审日期)` | `enpool_reason` |

## 核心口径

- 打标率分子：打标量。
- 打标率分母：完审量。
- 打标率公式：`打标率 = SUM(打标量) / SUM(完审量)`。
- 日均公式：`SUM(指标) / COUNT(DISTINCT p_date)`。
- 举报方向的分子是 `打标量_report_id`，分母是 `人审完结量_report_id`；时间字段统一使用数据集字段 `进审日期`，底层 expr 为 `` `date` ``。
- 举报方向默认输出字段为 `enpool_reason`、`日均人审完结量`、`日均打标量`、`打标率`。
- 环比增长率：`(本期日均进审量 - 上期日均进审量) / NULLIF(上期日均进审量, 0)`。
- 日均增量：`本期日均进审量 - 上期日均进审量`。
- 低打标率分级默认使用三维单策略粒度：`mach_root_label_name × strategy_id × strategy_name`；`reason` 默认只作为样本清洗过滤字段，不参与默认分级分组。
- 风险域维度即 `mach_root_label_name`。风险域爆量类规则必须先在本期和上期分别按三维筛出打标率 `< 10%` 的低效策略，再按风险域汇总这些低效策略的进审量、完审量、打标量并计算环比。
- 若原始 `mach_root_label_name` 为空或空串，必须先按 `dataset_reference.md#空机审一级标签补映射` 使用 `strategy_name` 补齐机审一级标签，再计算三维分级和风险域汇总。非空机审一级标签保持原值。
- 输出等级结果必须按 `strategy_id` 补充 `是否+1同意`、`更新日期`、`+1同意日期是否在本次统计周期前`。这些字段来自 `+1评估=同意` 治理资产及当前统计周期，只做状态标记，不改变分级命中逻辑；该资产默认每天首次使用时从飞书表 `GzpCwP516imDB8kQ3g1cLr5bnPc` 只读刷新。
- 全等级结果需额外输出剔除口径综合表：从综合结果中移除 `是否+1同意=是` 且 `更新日期` 早于当前统计周期开始日期的策略。
- 全等级结果的汇总统计需同步输出剔除口径版本：`汇总统计_剔除+1同意` 必须基于剔除口径综合表重新聚合。
- 汇总统计的 `低效策略打标率` 按表内展示的 `低效策略日均打标量 / 低效策略日均完审量` 计算，不使用周期总打标量 / 周期总完审量，确保与汇总统计表内展示字段可直接复核。

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

## 举报方向默认样本池

当 `data_direction=report_flow` 时，默认使用举报流转任务明细数据集 `3952594`，并复用以下基础筛选项。该样本池与人工审核明细默认样本池互斥，不得混用。

```sql
AND `[终轮队列名称]` IN (
  '【视频专项_举报】D-J-不良行为和争议价值观-B',
  '【视频专项_举报】D-J-人工分流-B',
  '【视频专项_举报】D-J-危险行为-B',
  '【视频专项_举报】D-J-引人不适-B',
  '【视频专项_举报】D-J-未成年-B',
  '【视频专项_举报】D-J-色情低俗-B',
  '【视频专项_举报】D-J-违法犯罪-B',
  '【视频专项_举报】【众包-PC端】短视频-安全-举报-时政',
  '【视频专项_举报】短视频-安全-举报-兜底',
  '【视频专项_举报】短视频-安全-举报-时政',
  '短视频-安全-疑难研判专审队列-涉政-举报'
)
AND `[一轮队列名称]` IN (
  '【众包-PC端】【视频专项_举报】短视频-安全-举报-兜底',
  '【视频专项_举报】D-J-不良行为和争议价值观-B',
  '【视频专项_举报】D-J-人工分流-B',
  '【视频专项_举报】D-J-危险行为-B',
  '【视频专项_举报】D-J-引人不适-B',
  '【视频专项_举报】D-J-未成年-B',
  '【视频专项_举报】D-J-短视频-兜底-2.0',
  '【视频专项_举报】D-J-短视频特殊2.0',
  '【视频专项_举报】D-J-色情低俗-B',
  '【视频专项_举报】D-J-违法犯罪-B',
  '【视频专项_举报】D-J-长视频特殊2.0',
  '【视频专项_举报】D-J-音频-B',
  '【视频专项_举报】D-J-高审',
  '【视频专项_举报】D-J-高频',
  '【视频专项_举报】【众包-PC端】短视频-安全-举报-时政',
  '【视频专项_举报】短视频-安全-举报-兜底',
  '【视频专项_举报】短视频-安全-举报-时政'
)
AND `[任务类型]` IN ('关注-【举报专项】任务链路流转')
AND `[一轮队列名称]` NOT LIKE '%兜底%'
AND `[一轮队列名称]` NOT LIKE '%海外%'
AND `[一轮队列名称]` NOT LIKE '%特殊%'
```

举报方向低效规则默认是 `打标率_report_id < 10%` 且 `人审完结量_report_id > 0`。

## 支持维度

- `reason`：样本清洗字段；仅在用户明确要求维度拆解时作为分组字段，不参与默认分级。
- `p_date`：日期分区。
- `enpool_reason`：举报方向的入池原因，等价于举报场景下的 reason。
- `进审日期`：举报方向日期分区字段，底层 expr 为 `` `date` ``。
- `mach_root_label_name`：机审一级标签。
- `strategy_id`：策略 / 规则 ID，2026-07-09 经 `dataset-fields` 与真实只读查询确认。
- `strategy_name`：策略名称，2026-07-09 经 `dataset-fields` 与真实只读查询确认。
- `scene`：审核场景。
- `project_title`：项目标题。
- `time_window`：时间窗口。

未列举维度处理规则：

- 用户指定的新维度不在上表时，先走 Semantic Layer / 数据集字段发现，确认字段名、字段含义、粒度、权限和 Owner。
- 只有字段通过数据集说明或字段探测确认后，才能加入 QueryPlan。
- 无法确认字段或粒度时，必须澄清或转人工，不得猜测字段。

## 分级与排序

| 等级 | 判定方向 | 说明 |
| --- | --- | --- |
| `P0` | 最严重 | 四周持续低效、高量低效、单周超高量低效或风险域低效策略进审量异常爆量。 |
| `P1` | 高 | 双周持续低效、单周高量低效或风险域低效策略爆量。 |
| `P2` | 中 | 单策略低效或风险域低效策略环比增长。 |
| `notice` | 观察 | 单周期打标率偏低，需要观察，不限制累计进审量。 |

低打标率分级阈值由 `analysis.md` 维护，默认来源于已验证的低效策略分级规则。高打标率或普通打标率查询不套用低效分级，按用户指定的排序、TopN、维度和时间窗口输出。

## 禁止事项

- 不得把打标率分母写成进审量。
- 不得直接跨天、跨 reason、跨标签累加 `打标率` 字段。
- 不得在默认分级中重新引入 `reason` 分组；如用户显式要求 reason 拆解，必须在 QueryPlan 中标注为维度拆解而非默认分级。
- 不得在分区缺失或数据未就绪时输出“无低效策略”。
- 不得把查询失败、权限失败解释成业务无异常。
- 不得使用自动处置准确率、质检准确率或底线事故数字段替代打标率。
- 不得使用无 Owner、已废弃或未治理字段作为最终结论来源。

## Owner

- 指标 Owner：人审效率域指标治理 Owner，负责确认打标率、进审量、完审量、打标量、分级阈值和口径变更。
- 数据 Owner：人审效率域数据 Owner，负责确认语义层指标、Aeolus 数据集、Hive / ClickHouse 表、字段含义、分区新鲜度和血缘。
- 业务解释 Owner：人审运营效率治理 Owner，负责解释打标率波动、高低打标策略表现、治理动作和升级路径。

> 当前先使用角色级 Owner，不编造具体个人。接入真实治理资产后再替换为具体负责人、群或值班机制。
