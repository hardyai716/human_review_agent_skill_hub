# 场景：efficiency-label-rate

本文件是 analysis Skill 的运行态单场景文档，由仓库构建流程合并生成。运行态 Skill 只读取本文件，不再拆读四件套。

## 指标口径

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
| 举报打标率 | `report_label_rate` | `SUM(report_label_cnt) / SUM(report_review_done_cnt)` | `day × 举报 × enpool_reason × enpool_reason` |
| 举报进审量 | `report_review_in_cnt` | 数据集指标 `进审量_report_id` | `day × 举报 × enpool_reason × enpool_reason` |
| 举报人审完结量 | `report_review_done_cnt` | 数据集指标 `人审完结量_report_id` | `day × 举报 × enpool_reason × enpool_reason` |
| 举报打标量 | `report_label_cnt` | 数据集指标 `打标量_report_id` | `day × 举报 × enpool_reason × enpool_reason` |
| 举报日均人审完结量 | `avg_daily_report_review_done_cnt` | `SUM(report_review_done_cnt) / COUNT(DISTINCT 进审日期)` | `enpool_reason` |
| 举报日均打标量 | `avg_daily_report_label_cnt` | `SUM(report_label_cnt) / COUNT(DISTINCT 进审日期)` | `enpool_reason` |

## 核心口径

- 打标率分子：打标量。
- 打标率分母：完审量。
- 打标率公式：`打标率 = SUM(打标量) / SUM(完审量)`。
- 日均公式：`SUM(指标) / COUNT(DISTINCT p_date)`。
- 举报方向的分子是 `打标量_report_id`，分母是 `人审完结量_report_id`；时间字段统一使用数据集字段 `进审日期`，底层 expr 为 `` `date` ``。
- 举报方向低效分级使用与常规人工审核明细一致的 `notice/P2/P1/P0` 规则；其字段映射为 `mach_root_label_name='举报'`，`strategy_id=enpool_reason`，`strategy_name=enpool_reason`。
- 环比增长率：`(本期日均进审量 - 上期日均进审量) / NULLIF(上期日均进审量, 0)`。
- 日均增量：`本期日均进审量 - 上期日均进审量`。
- 低打标率分级默认使用三维单策略粒度：`mach_root_label_name × strategy_id × strategy_name`；`reason` 默认只作为样本清洗过滤字段，不参与默认分级分组。
- 风险域维度即 `mach_root_label_name`。风险域爆量类规则必须先在本期和上期分别按三维筛出打标率 `< 10%` 的低效策略；再以当前统计周期开始日期为 cutoff，从两期成员策略中剔除 `+1评估=同意` 且 `更新日期 < cutoff` 的 `strategy_id`；最后按风险域汇总剩余策略的**策略级日均**进审量、完审量、打标量并计算环比，即对每个策略先按自身有数天数计算日均，再求和。风险域行的 `strategy_id` 为空，禁止在汇总后按行级 +1 标记再剔除。
- 若原始 `mach_root_label_name` 为空或空串，必须先按 `dataset_reference.md#空机审一级标签补映射` 使用 `strategy_name` 补齐机审一级标签，再计算三维分级和风险域汇总。非空机审一级标签保持原值。
- 输出等级结果必须按 `strategy_id` 补充 `是否+1同意`、`更新日期`、`+1同意日期是否在本次统计周期前`。单策略维度和 notice 仅使用这些字段做报表层状态标记；风险域维度按前述规则在聚合前应用同一剔除集合。+1 资产由其 `source` 元数据声明的治理飞书表只读刷新，发布资产不得固化真实 token。
- 全等级结果需额外输出剔除口径综合表：从综合结果中移除 `是否+1同意=是` 且 `更新日期` 早于当前统计周期开始日期的策略。
- 全等级结果的汇总统计需同步输出剔除口径版本：`汇总统计_剔除+1同意` 必须基于剔除口径综合表重新聚合。
- 汇总统计的 `低效策略打标率` 按表内展示的 `低效策略日均打标量 / 低效策略日均完审量` 计算，不使用周期总打标量 / 周期总完审量，确保与汇总统计表内展示字段可直接复核。
- 两周期对比必须消费两个周期各自生成的 `汇总统计_剔除+1同意`，每个周期按自身开始日期应用 +1 同意 cutoff；禁止用完整口径、不同周期 cutoff 或过期快照替代。
- 两周期对比粒度固定为 `mach_root_label_name × POC`，取两个周期键的并集；单侧缺失的策略数、日均进审/完审/打标量补 `0`，上期日均完审量为 `0` 时完审增幅展示 `/`。
- 两周期对比的完审增量为 `本期低效策略日均完审量 - 上期低效策略日均完审量`；总计打标率为所有展示桶 `SUM(日均打标量) / SUM(日均完审量)`，严禁平均行级打标率。

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

举报方向低效规则与常规打标率共用：notice 为 `report_label_rate < 10%`，P2/P1/P0 继续使用单策略和风险域爆量规则；其中“单策略”为 `enpool_reason`，“风险域”为固定值 `举报`。涉及 `+1评估=同意` 的剔除时，举报侧使用“保持不变明细表”的 `reason` 字段匹配结果中的 `enpool_reason`，并沿用 `更新日期 < 当前周期开始日` 的 cutoff。

人审明细与举报流转合并展示时，不改变任一数据源的指标公式；必须分别按各自分母/分子计算并分级，再通过标准化字段合并。合并输出必须包含 `数据来源`，取值为 `人审明细` 或 `举报流转`。

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

## 数据源与字段

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
| `governed_dataset` | Aeolus 举报流转任务明细数据集 | 举报场景下的 `enpool_reason` 打标率查询 | 可回退 |

## 方向 1：人工审核明细入口

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

## 方向 2：举报流转入口

- Region：`cn`
- App ID：`555137`
- Dataset ID：`3952594`
- Dataset 名称：`举报流转任务明细数据集`
- 数据集链接：`https://data.bytedance.net/aeolus/pages/dataManage/detail/3952594?appId=555137`
- 查询命令：`bytedcli -j aeolus query -r cn 3952594 "<SQL>" --limit 1000`
- 查字段命令：`bytedcli -j aeolus dataset-fields -r cn 3952594`
- `report_label_rate` 对应风神指标：`打标率_report_id`
- 分子指标：`打标量_report_id`
- 分母指标：`人审完结量_report_id`
- 规模指标：`进审量_report_id`
- 分级维度：`mach_root_label_name='举报'`、`strategy_id=enpool_reason`、`strategy_name=enpool_reason`
- 日期字段：`进审日期`，expr 为 `` `date` ``。
- 直接使用逻辑表名 `Hive-sql-0` 查询会报 unknown table；2026-07-13 通过 `system.query_log` 定位到物理表 `aeolus_data_db_aeolus_sagittarius_mini_202511.aeolus_data_table_22_3373535_migrate_v1_prod`。正式模板优先使用数据集语义字段，必要时可在 provenance 中记录该物理表。

## 风神使用注意事项

- JSON 输出必须使用 `-j`，且 `-j` 是 bytedcli 全局参数，位置必须在 `aeolus` 前：`bytedcli -j aeolus ...`。
- 查数优先使用 `bytedcli -j aeolus query -r cn 3888816 "<SQL>" --limit 1000`。
- 复杂过滤、`NOT LIKE`、`HAVING`、分级规则和多阶段聚合必须走 `aeolus query`，不要用 `viz-query` 兜复杂 SQL。
- `viz-query` 仅适合字段验证、简单聚合或快速探测；若 `expr` 已自带 `sum(`、`count(`、`avg(` 或比率表达式，不要再传 `aggregation`，否则容易触发后端校验错误。
- 查询失败不能解释成“无低打标率 reason”；必须区分权限失败、字段错误、分区缺失、过滤过严和真实空结果。
- 不要误用 `4284992` 等标注准确率数据集替代 `3888816`，否则会把打标率口径查成标签准确率口径。
- 举报方向不要使用 `3888816` 的 `reason`、`完审量_reviewid`、`打标量__reviewid` 字段；必须使用 `3952594` 的 `enpool_reason`、`人审完结量_report_id`、`打标量_report_id`、`打标率_report_id`。
- 举报方向统一使用 `进审日期` 作为时间字段。

## 物理表参考

- 表：`olap_content_security_community.dws_sft_tcs_review_task_detail_di`
- 引擎：ClickHouse
- 分区：`p_date`
- 默认新鲜度：T+1，查询前必须确认 `MAX(p_date)` 和目标分区行数。
- 支持粒度：默认分级使用 `p_date × 机审一级标签 × strategy_id × strategy_name`；维度拆解可扩展到 `p_date × dimensions × reason`。
- 不用于：人员明细、责任人解析、open_id / chat_id、触达对象。

## 字段映射

| 概念 | 逻辑字段 | 默认 Name | 说明 |
| --- | --- | --- | --- |
| 可选 reason 拆解 | `reason` | `reason` | 样本清洗字段；仅在用户明确要求维度拆解时作为分组字段。 |
| 策略 ID | `strategy_id` | `strategy_id` | 规则 ID；2026-07-09 通过 `bytedcli -j aeolus dataset-fields -r cn 3888816` 确认。 |
| 策略名称 | `strategy_name` | `strategy_name` | 策略名称；2026-07-09 通过 `bytedcli -j aeolus dataset-fields -r cn 3888816` 确认。 |
| 日期分区 | `date` | `p_date` | 用于时间窗口和分区就绪检查。 |
| 项目标题 | `project_title` | `project_title` | 用于排除测试、质检、离线等项目。 |
| 审核场景 | `scene` | `scene` | 默认保留社区审核三类场景。 |
| 机审一级标签 / 风险域 | `mach_root_label_name` | `机审一级标签` | 低打标率治理中的风险域即机审一级标签；空值必须保留，维度拆解和风险域汇总使用。 |
| 进审量 | `review_in_cnt` | `进审量_reviewid` | 聚合字段。 |
| 完审量 | `review_done_cnt` | `完审量_reviewid` | 打标率分母。 |
| 打标量 | `label_cnt` | `打标量__reviewid` | 双下划线，打标率分子。 |
| 打标率 | `label_rate` | `打标率__reviewid` | 不直接跨粒度聚合，应重算。 |

## 空机审一级标签补映射

默认分级取数时，若原始 `[机审一级标签]` 为空或空串，必须在 SQL 取数层按 `strategy_name` 补齐 `mach_root_label_key`，再进入聚合、分级和 POC 路由。非空 `[机审一级标签]` 保持原值。

明确策略名映射：

| strategy_name | 补齐后的机审一级标签 |
| --- | --- |
| 高价值-兜底vv进审 | 高热 |
| 短视频-特殊账号-达到VV阈值 | 高热 |
| 非白名单政媒账号投稿vv大于5万vv送审 | 政媒 |
| 商业化付费视频全人审ugc | 商业化 |
| 白名单账号投稿vv大于5万vv送审 | 政媒 |
| 中视频-特殊账号-达到VV阈值 | 高热 |
| 星图预审35wvv强制召回 | 高热 |
| 【ZL推人】麒麟芯片9030 | 指令舆情相关 |
| 【ZL推人】涉日股市负面-词 | 指令舆情相关 |
| 高热虐猫虐狗上升召回-内容现象 | 高热 |
| 【兜底送审】普通视频豁免25W进审 | 高热 |

若空标签策略未命中上表，再按策略名称包含关系兜底：

| 包含关键词 | 补齐后的机审一级标签 |
| --- | --- |
| `ZL` | 指令舆情相关 |
| `商业化` | 商业化 |
| `政媒` | 政媒 |

仍无法命中时输出 `（空/机审一级标签）`，并按低置信度路由处理。

## +1评估同意标记

低打标率全等级结果必须基于 `plus1_agreed_strategy_updates.json` 补充两个治理状态字段：

| 输出字段 | 来源 | 说明 |
| --- | --- | --- |
| `是否+1同意` | 人审按 `strategy_id` 命中 `+1评估=同意` 策略资产；举报按 `reason` 命中同一资产，并映射到结果中的 `enpool_reason` | 命中输出 `是`，未命中输出 `否`。 |
| `更新日期` | 同一策略在原始飞书表中的 `更新日期` | 命中且存在日期时输出 `YYYY-MM-DD`；历史同意清单中无当前日期的策略输出空。 |
| `+1同意日期是否在本次统计周期前` | `是否+1同意`、`更新日期`、当前统计周期开始日期 | `是否+1同意 = 是` 且 `更新日期 < 当前统计周期开始日期` 时输出 `是`，否则输出 `否`。 |

资产来源由 `plus1_agreed_strategy_updates.json.source` 声明的治理飞书表指向，筛选条件为 `+1评估 = 同意`。资产必须同时保存 `entries`（人审 `strategy_id` 索引）与 `report_flow_entries`（举报 `reason` 索引）；`reason` 是“保持不变明细表”中举报对应字段，运行时与举报结果的 `enpool_reason` 对齐。发布资产不得固化真实 token。该清单会持续更新，默认每天第一次使用该策略清单时必须只读刷新飞书表格，并用当前表内容覆盖本地 `plus1_agreed_strategy_updates.json`；日内重复使用可复用当日已刷新的本地资产。

全等级报表除保留完整 `综合` 外，还必须输出 `综合_剔除+1同意`：以当前统计周期开始日期为 cutoff，单策略维度剔除 `是否+1同意 = 是` 且 `更新日期 < cutoff` 的策略；风险域维度在其本期和上期成员策略聚合前应用同一剔除集合。人审风险域剔除 `strategy_id`，举报风险域剔除 `reason/enpool_reason`。示例：周期为 `2026-07-06` 至 `2026-07-12` 时，剔除 `2026-07-06` 之前已同意的策略；`更新日期` 为空或不早于 `2026-07-06` 的行保留。

汇总统计也必须成对输出：`汇总统计` 基于完整 `综合` 聚合，`汇总统计_剔除+1同意` 基于 `综合_剔除+1同意` 聚合，二者字段结构保持一致。合并人审与举报结果时必须输出 `数据来源`，取值为 `人审明细` 或 `举报流转`，汇总统计按 `数据来源 × 机审一级标签 × POC` 分组。汇总统计中的 `低效策略打标率` 必须与表内展示量一致，按 `低效策略日均打标量 / 低效策略日均完审量` 计算。

## 字段映射：举报流转

| 概念 | 逻辑字段 | 默认 Name | Aeolus 字段 ID | expr / 说明 |
| --- | --- | --- | --- | --- |
| 日期分区 | `review_date` | `进审日期` | `10000001218266` | expr 为 `` `date` ``。 |
| 举报入池原因 | `enpool_reason` | `enpool_reason` | `10000010927224` | 等价于举报方向下的 reason。 |
| 进审量 | `report_review_in_cnt` | `进审量_report_id` | `10000001270480` | `count(distinct [report_id])`。 |
| 人审完结量 | `report_review_done_cnt` | `人审完结量_report_id` | `10000001270606` | 打标率分母。 |
| 打标量 | `report_label_cnt` | `打标量_report_id` | `10000001274137` | 打标率分子。 |
| 打标率 | `report_label_rate` | `打标率_report_id` | `10000001274387` | `[打标量_report_id] / [人审完结量_report_id]`。 |
| 终轮队列 | `last_queue_name` | `终轮队列名称` | `10000001218290` | expr 为 `last_tab_roject_name`。 |
| 一轮队列 | `first_queue_name` | `一轮队列名称` | `10000001218268` | expr 为 `first_tab_project_name`。 |
| 任务类型 | `task_type` | `任务类型` | `10000001289385` | 默认取 `关注-【举报专项】任务链路流转`。 |

## 默认过滤：举报流转

举报方向默认基础筛选项：

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

举报方向低效分级默认先按 `进审日期 × enpool_reason` 汇总出进审量、人审完结量、打标量，再映射为 `举报 × enpool_reason × enpool_reason` 并复用常规 `notice/P2/P1/P0` 规则。输出字段结构与常规打标率分级一致。

## 扩展维度发现

当用户指定的维度不在 `metric_contract.md` 支持维度中时：

1. 先查 Semantic Layer 是否存在对应 dimension 或 segment。
2. 若语义层未覆盖，再查 Aeolus / 数据集字段说明。
3. 必须确认字段 Name、业务含义、粒度影响、空值处理和 Owner。
4. 通过确认后才能加入 QueryPlan 的 `dimensions`。
5. 无法确认时输出澄清问题或人工确认请求，不得猜字段。

## 字段发现回填机制

当一次查询使用了原数据集说明中未登记、但已经通过字段发现和真实只读查询验证的字段，必须在本文件和 Skill 快照中回填，避免后续重复探测或误判为未知字段。

回填条件：

1. 字段必须来自受控来源，例如 `bytedcli -j aeolus dataset-fields -r cn 3888816` 或已保存的治理数据集字段说明。
2. 字段必须在小样本查询或真实只读查询中成功使用。
3. 回填内容至少包含：逻辑字段、默认 Name、业务含义、字段来源命令、确认日期。
4. 若字段用于 runner / validator，必须同步更新对应 `DIMENSION_SPECS`、validator 断言和 eval 产物。
5. 若字段属于场景常用维度，必须同步更新本场景文档与 Skill 内 `*.dataset_reference.md` 快照。

本轮已回填字段：

| 逻辑字段 | 默认 Name | Aeolus 字段 ID | 字段说明 | expr | dataType | 确认方式 |
| --- | --- | --- | --- | --- | --- | --- |
| `strategy_id` | `strategy_id` | `1700075931415` | 规则ID | `` `strategy_id` `` | `string` | `dataset-fields` + `2026-06-29~2026-07-05` 多维低打标率查询验证 |
| `strategy_name` | `strategy_name` | `1700075931446` | 策略名称 | `` `strategy_name` `` | `string` | `dataset-fields` + `2026-06-29~2026-07-05` 多维低打标率查询验证 |

## SQL 写法约束

- ClickHouse 语义字段使用反引号包方括号：`` `[Name]` ``。
- 禁止裸 `[Name]`。
- 禁止在最终聚合中 `SUM(rate)`。
- 打标率必须用 `SUM(label_cnt) / SUM(review_done_cnt)` 重算。
- 使用风神语义指标时，可用 `` `[打标率__reviewid]` ``，但必须同时输出 `` `[完审量_reviewid]` `` 和 `` `[打标量__reviewid]` `` 作为 evidence。
- 日均量必须用 `COUNT(DISTINCT p_date)`，不得硬编码 `/7`。
- NULL 机审标签必须用 `field IS NULL OR field IN (...)`，不得写 `IN (NULL, ...)`。
- 可空维度做 `ifNull` / `coalesce` / `case` 归一化后，内部别名不得与底表物理字段或 Aeolus 展示字段同名，统一使用 `*_key`。例如必须写 `ifNull(`[机审一级标签]`, '（空/机审一级标签）') AS mach_root_label_key` 并 `GROUP BY mach_root_label_key`，外层再 `mach_root_label_key AS mach_root_label_name`。禁止写 `AS mach_root_label_name GROUP BY mach_root_label_name`，否则 Aeolus / ClickHouse 可能解析到原始字段，导致 NULL 维度桶丢失。
- 空机审一级标签补映射也必须输出到内部稳定别名 `mach_root_label_key`，不得直接写为展示字段 `mach_root_label_name` 后参与 `GROUP BY`。
- 默认低打标率分级不得按 `reason` 分组；`reason` 只保留为样本过滤字段，即必须继续排除 `recall_skip_L6` 和 `fatal_output`。
- 风险域爆量类查询必须先按 `mach_root_label_key × strategy_id_key × strategy_name_key` 筛出低效策略，再从本期和上期成员集剔除统计周期前已 +1 同意的策略；每个成员策略按自身有数天数计算日均后，再按 `mach_root_label_key` 求和。风险域维度输出时 `strategy_id`、`strategy_name` 置空。

## 查询模板参数化

- `reason` 是可选拆解维度，不是默认分级维度；Agent 必须从用户问题中解析 `dimensions`。
- 已确认维度可直接进入 SQL：`reason`、`p_date`、`scene`、`project_title`、`mach_root_label_name`、`strategy_id`、`strategy_name`。
- 多维度问题按 `dimensions` 生成 `SELECT` 和 `GROUP BY`，例如 `reason, scene`。
- “有哪些 / 排名 / 明细”类问题使用 `query_mode=ranking`，返回维度明细、完审量、打标量和打标率。
- “有多少 / 个数 / 数量”类问题使用 `query_mode=group_count`，先用子查询或 CTE 生成低打标率维度分组，再在外层 `count()` 统计分组数。

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

## 分析模式

## 分析模式

| 模式 | 触发条件 | 主要产出 |
| --- | --- | --- |
| `label_rate_trend` | 用户只问打标率、进审量、完审量趋势 | QueryPlan + 趋势口径说明 + source_footer |
| `label_rate_ranking` | 用户查询高打标率、低打标率、TopN / BottomN 策略或 reason | 排序清单 + evidence |
| `low_label_rate_grading` | 用户明确问低效策略、P0/P1/P2/notice、低打标 reason 清单 | 四级分级清单 + 综合去重清单 |
| `weekly_filtered_summary_comparison` | 用户要求比较两个明确周期的 `汇总统计_剔除+1同意`，通常要求截图式表格或飞书链接 | 两周期周环比表 + 溯源脚注 + 可选飞书表格链接 |
| `dimension_breakdown` | 用户要求按机审一级标签、场景、项目或其他维度拆解 | `dimensions × reason` 明细 + `dimensions` 汇总 |
| `low_label_rate_grading` + `data_direction=report_flow` | 用户询问举报场景、举报流转或 `enpool_reason` 下的低打标率分级 | 固定风险域 `举报` 的 `notice/P2/P1/P0` 全等级清单 |

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
| `notice` | 单策略三维粒度近 7 天打标率 `< 10%`，不限制累计进审量。 |
| `P2` | 单策略日均进审 `> 2000` 且打标率 `< 3%`，或风险域维度低效策略进审上涨。 |
| `P1` | 双周持续低效、单周高量低效，或风险域维度低效策略爆量。 |
| `P0` | 四周持续低效、两周高量低效、单周超高量低效，或风险域维度进审量异常爆量。 |

输出要求：

- 默认输出粒度包含两类 `预警维度`：`单策略维度` 与 `风险域维度`。
- 单策略维度默认按 `机审一级标签 × strategy_id × strategy_name` 三维聚合，`reason` 仅作为样本过滤字段，不参与默认分级分组。
- 分级取数前必须先完成空机审一级标签补映射：原始标签为空时按 `strategy_name` 映射到高热、政媒、商业化或指令舆情相关；仍无法命中时保留 `（空/机审一级标签）`。
- 风险域维度中的“风险域”即 `机审一级标签`；先在本期和上期按三维筛出低效策略（打标率 `< 10%`），再以当前统计周期开始日期为 cutoff 剔除 `+1评估=同意` 且 `更新日期 < cutoff` 的策略，最后按机审一级标签汇总剩余策略的**策略级日均**进审量、完审量、打标量，并计算两期日均进审量环比。策略级日均按各策略自身有数天数计算后再求和。风险域行不能在汇总后按自身空 strategy_id 做 +1 剔除。
- 风险域维度输出时 `strategy_id`、`strategy_name` 置空，POC 仍按机审一级标签映射。
- 四个等级 sheet 保留各自完整命中结果，不跨级去重。
- 综合 sheet 按 `P0 > P1 > P2 > notice` 对同一 `预警维度 × 机审一级标签 × strategy_id × strategy_name` 取最高等级。
- 额外输出 `综合_剔除+1同意` sheet / CSV：单策略维度在综合 sheet 基础上剔除 `是否+1同意=是` 且 `更新日期 < 当前统计周期开始日期` 的策略；风险域维度已在分析聚合前按同一集合剔除成员策略，保留该预聚合结果，不再做行级剔除。
- 额外输出 `汇总统计_剔除+1同意` sheet / CSV：字段结构与 `汇总统计` 一致，但聚合输入必须使用 `综合_剔除+1同意`。
- `汇总统计` 和 `汇总统计_剔除+1同意` 的 `低效策略打标率` 必须按表内展示的 `低效策略日均打标量 / 低效策略日均完审量` 计算，保证用户在表格中直接相除可复核。
- 每条结果必须带 evidence：预警维度、严重等级、机审一级标签、策略ID、策略名称、数据天数、最大有数日期、日均进审、日均完审、日均打标、打标率、命中规则、命中条件、POC、是否+1同意、更新日期、+1同意日期是否在本次统计周期前。
- 某级无命中时写“本期 0 条”，查询失败时写失败原因。

分级条件：

| 等级 | 预警维度 | 命中条件 |
| --- | --- | --- |
| `notice` | 单策略维度 | 近 7 天打标率 `< 10%`。 |
| `P2` | 单策略维度 | 近 7 天日均进审量 `> 2000` 且打标率 `< 3%`。 |
| `P2` | 风险域维度 | 风险域下低效策略汇总日均进审量环比上涨 `> 20%`，日均增量 `> 2000`，上期进审量 `> 0`。 |
| `P1` | 单策略维度 | 双周期日均进审均 `> 2000` 且双周期打标率均 `< 3%`。 |
| `P1` | 单策略维度 | 近 7 天日均进审 `> 5000` 且打标率 `< 3%`。 |
| `P1` | 风险域维度 | 风险域下低效策略汇总日均进审量环比上涨 `> 30%`，日均增量 `> 5000`，上期进审量 `> 0`。 |
| `P0` | 单策略维度 | 近 1 周日均进审 `> 2000` 且连续 4 周打标率均 `< 3%`。 |
| `P0` | 单策略维度 | 近 1 周日均进审 `> 5000` 且连续 2 周打标率均 `< 3%`。 |
| `P0` | 单策略维度 | 近 1 周日均进审 `> 10000` 且打标率 `< 3%`。 |
| `P0` | 风险域维度 | 风险域下低效策略汇总日均进审量环比上涨 `> 50%`，日均增量 `> 10000`，上期进审量 `> 0`。 |

## 模式 C：剔除 +1 同意的两周期汇总对比

适用于用户要求“跑上一周并与本周对比”“按截图格式对比”“对比 `汇总统计_剔除+1同意`”或要求通过飞书发送两周对比表。

输入和执行顺序：

1. 两个周期的 `start_date` / `end_date` 必须显式给出；不得用相对时间模板替代，也不得把当前周期的历史窗口误当作上周期完整结果。
2. 分别执行两个周期的全等级真实只读分级，且每个周期都独立生成 `综合_剔除+1同意` 与 `汇总统计_剔除+1同意`。
3. 每个周期按其自身开始日期应用 `更新日期 < 当前周期开始日` 的 +1 同意剔除；风险域必须沿用成员策略预聚合剔除和策略级日均求和口径。
4. 对比键固定为 `机审一级标签 × POC`，取两个周期键的并集；仅本期或仅上期出现的键另一侧补 `0`，不得静默丢行。

表格字段：

| 分组 | 字段 |
| --- | --- |
| 固定维度 | `机审一级标签`、`POC` |
| 低效策略数 | 上周期、本周期 |
| 低效策略完审量 | 上周期、本周期、增量、本期相对上期增幅 |
| 低效策略打标率 | 上周期、本周期 |

计算与展示约束：

- `低效策略数` 为每个 `机审一级标签 × POC` 桶内去重策略数；总计为所有展示桶之和。
- `日均完审量`、`日均打标量` 总计为各展示桶之和；总计打标率必须为 `SUM(日均打标量) / SUM(日均完审量)`，禁止平均行级打标率。
- `增量 = 本期日均完审量 - 上期日均完审量`；上期日均完审量为 `0` 时，增幅显示 `/`，不伪造百分比。
- 对比工作簿使用双层分组表头、冻结前两行与前两列；分组颜色区分策略数、完审量和打标率；正向完审增量用红色高亮。
- 工作簿必须带溯源脚注，声明两个周期、`汇总统计_剔除+1同意` 输入、+1 cutoff 和加权打标率口径。
- 在线导入飞书表格仅在明确 `--import-sheet` 时执行；真实飞书发送仅在用户确认接收对象、正文和发送身份后由宿主执行。

## 模式 D：维度拆解

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

## 模式 E：举报流转低打标率分级

适用于 `data_direction=report_flow`，即用户明确提到举报、举报场景、举报流转、`enpool_reason`、`report_id`、一轮队列或终轮队列。

字段和口径：

- 时间字段：`进审日期`。
- 风险域：固定填充为 `举报`。
- 策略 ID：填充为 `enpool_reason`。
- 策略名称：填充为 `enpool_reason`。
- 分母：`人审完结量_report_id`。
- 分子：`打标量_report_id`。
- 打标率：`打标率_report_id`。
- 低效条件和 P 级规则：沿用模式 B 的 notice/P2/P1/P0，仅把常规策略三维替换成 `举报 × enpool_reason × enpool_reason`。

默认输出：

- `预警维度`
- `预警等级`
- `数据来源=举报流转`
- `机审一级标签=举报`
- `策略ID=enpool_reason`
- `策略名称=enpool_reason`
- `日均进审量`
- `日均完审量`
- `日均打标量`
- `打标率`
- `命中规则`

SQL 约束：

- 必须使用 Dataset `3952594` / appId `555137`。
- 必须复用 `dataset_reference.md#默认过滤：举报流转` 中的基础筛选。
- `+1评估 = 同意` 剔除逻辑沿用人审链路，但举报侧使用“保持不变明细表”的 `reason` 字段匹配结果中的 `enpool_reason`；风险域爆量分支必须在聚合 `举报` 前剔除 `更新日期 < 当前周期开始日` 的已同意 reason。
- 不得使用人工审核明细 Dataset `3888816` 的 `reason`、`完审量_reviewid`、`打标量__reviewid`。
- 如果直接逻辑表名不可用，可使用 query_log 中确认的物理表作为受控 fallback，并在 provenance 中记录。
- 指标字段已经是聚合表达式时，不要直接 `SUM([打标率_report_id])` 或对已聚合比率二次聚合；应先在 `进审日期 × enpool_reason` 日粒度聚合出进审、完审、打标量，再复用常规分级 SQL 模板。

## 模式 F：人审明细 + 举报流转合并全等级分级

适用于用户要求将举报场景结果与人审数据集下的打标率结果合并展示。

执行规则：

- 不跨数据集拼接单条 SQL；必须分别执行 `manual_review_detail` 与 `report_flow` 两套 QueryPlan，再在标准化结果层合并。
- 合并前两套结果都必须标准化为同一列结构：`数据来源`、`预警维度`、`预警等级`、`机审一级标签`、`策略ID`、`策略名称`、`POC`、日均量、打标率、命中规则、`+1` 治理字段。
- `数据来源` 取值固定为 `人审明细` / `举报流转`，去重与汇总都必须保留该来源边界。
- `综合_剔除+1同意` 的 cutoff 规则不变：`更新日期 < 当前周期开始日`。人审按 `strategy_id` 剔除，举报按 `reason/enpool_reason` 剔除。
- 举报风险域固定为 `举报`，继续参与 P2/P1/P0 的风险域爆量规则；成员粒度为 `enpool_reason`。

### 模式 F 宿主调用

`combined` 是常用正式交付能力，推荐通过仓库宿主 runner 编排：

```bash
python3 human_review_ops/tools/runners/run_label_rate_formal_flow.py \
  --data-direction combined \
  --start-date YYYY-MM-DD \
  --end-date YYYY-MM-DD \
  --run-id <run_id> \
  --no-import-workbook
```

执行完成后，使用 Stage 1 JSONL 生成飞书表格和卡片：

```bash
python3 human_review_ops/tools/runners/run_stage_2_label_rate_notification_draft.py \
  --source human_review_ops/evals/efficiency-label-rate/stage_1_runs/<run_id>_formal_skill_flow_results.jsonl \
  --output-dir human_review_ops/evals/efficiency-label-rate/stage_2_runs/<run_id>_formal_skill_flow \
  --top-n 10 \
  --import-workbook \
  --send-user-id <open_id> \
  --identity bot \
  --title '<标题>'
```

执行注意事项：

- `run_label_rate_formal_flow.py --data-direction combined` 会先跑人审 `manual_review_detail`，再跑举报 `report_flow`；任一数据源失败、超时或截断时必须停止合并。
- 如果人审已成功、举报超时，可单独重跑 `--data-direction report_flow`，再用两份 Stage 1 样本合并；合并后仍必须通过 `validate_label_rate_combined_flow.py` 或 formal-flow 结构校验。
- 如果 `--import-workbook` 已成功但 Card 发送失败，后续重试必须传入既有 `--sheet-url`，避免重复创建飞书表格。
- 飞书卡片使用 Card 2.0；汇总表和 Top 明细表都必须声明并填充 `数据来源` 字段，否则发送会被飞书 schema 拒绝。

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

## 正反例

## 正例

### 查询低打标率 reason

输入：

```text
近 7 天有哪些高完审低打标的 reason？
```

期望：

- 命中 `efficiency-label-rate`。
- `task_type=dimension_breakdown`；`run_mode=query_only` 或 `partial_workflow`。
- 输出 QueryPlan 和 source_footer。
- 若需要低效分级，默认包含 notice/P2/P1/P0。

### 查询高打标率 reason

输入：

```text
近 7 天打标率最高的策略有哪些？
```

期望：

- 命中 `efficiency-label-rate`。
- 命中 `label_rate_ranking` 模式。
- 按打标率降序输出，并带进审量、完审量、打标量和打标率。
- 不套用低效分级。

### 分级分析

输入：

```text
帮我看下近 7 天低打标率策略分 P0/P1/P2/notice 的情况。
```

期望：

- 命中 `low_label_rate_grading` 模式。
- 输出四级分级规则摘要，默认包含 `单策略维度` 和 `风险域维度`。
- 单策略维度按 `机审一级标签 × strategy_id × strategy_name` 聚合；风险域维度按机审一级标签汇总低效策略，策略ID和策略名称为空。
- 说明打标率口径为打标量 / 完审量。

### 两周期剔除口径对比

输入：

```text
先跑 2026-07-06 至 2026-07-12 的全等级低效打标结果，再与 2026-07-13 至 2026-07-19 的汇总统计_剔除+1同意按截图格式对比，生成飞书表格并在确认后推送。
```

期望：

- 先分别执行两个显式周期的全等级只读分级，再读取每个周期的 `汇总统计_剔除+1同意`。
- 对比键为 `机审一级标签 × POC`，保留两个周期键的并集；单侧缺失补 `0`。
- 展示低效策略数、日均完审量、增量、增幅和加权打标率；总计打标率按 `SUM(日均打标量) / SUM(日均完审量)` 计算。
- 对比表冻结双层表头和前两列，正向日均完审增量标红，并写入溯源脚注。
- 未显式授权时只生成本地 XLSX 与发送草稿；在线导入和真实发送必须等待确认。

### 维度拆解

输入：

```text
按机审一级标签拆一下打标率。
```

期望：

- 命中 `dimension_breakdown` 模式。
- 读取 `mach_root_label_name` 维度。
- 输出 `dimensions × reason` 和 `dimensions` 汇总结构。

### 举报场景低打标率

输入：

```text
举报场景近七天打标率小于 10% 的 enpool_reason 有哪些？输出日均人审完结量、日均打标量和打标率。
```

期望：

- 命中 `efficiency-label-rate`。
- `data_direction=report_flow`，`source_profile=report_flow_review`，`task_type=low_label_rate_grading`。
- 使用 Dataset `3952594` / appId `555137`。
- 时间字段使用 `进审日期`。
- 输出字段结构与常规分级一致，其中 `机审一级标签=举报`，`策略ID=enpool_reason`，`策略名称=enpool_reason`。
- 不得走人工审核明细 Dataset `3888816`。

### 合并人审与举报结果

输入：

```text
把举报场景的全等级结果和人审数据集下的打标率结果合并到一起，并剔除 +1评估=同意。
```

期望：

- 设置 `data_direction=combined`，分别执行人审 `3888816` 与举报 `3952594` 的只读分级查询。
- 合并表新增 `数据来源` 列，取值为 `人审明细` / `举报流转`。
- `综合_剔除+1同意` 中，人审按 `strategy_id` 剔除，举报按“保持不变明细表”的 `reason` 匹配 `enpool_reason` 剔除。
- 举报风险域固定为 `举报`，并参与 P2/P1/P0 的风险域爆量规则。

推荐调用：

```bash
python3 human_review_ops/tools/runners/run_label_rate_formal_flow.py \
  --data-direction combined \
  --start-date 2026-07-14 \
  --end-date 2026-07-20 \
  --run-id 20260721_combined_0714_0720_full_levels \
  --no-import-workbook

python3 human_review_ops/tools/runners/run_stage_2_label_rate_notification_draft.py \
  --source human_review_ops/evals/efficiency-label-rate/stage_1_runs/20260721_combined_0714_0720_full_levels_formal_skill_flow_results.jsonl \
  --output-dir human_review_ops/evals/efficiency-label-rate/stage_2_runs/20260721_combined_0714_0720_full_levels_formal_skill_flow \
  --top-n 10 \
  --import-workbook \
  --send-user-id <open_id> \
  --identity bot \
  --title '人审明细+举报流转低效打标全等级结果（2026-07-14~2026-07-20）'
```

若表格已导入但卡片发送失败，第二条命令改用 `--sheet-url <已生成的飞书表格链接>`，不要重复导入 workbook。

### 用户指定未列举维度

输入：

```text
按业务线看打标率。
```

期望：

- 不直接猜字段。
- 先查 Semantic Layer / 数据集字段说明中是否存在业务线维度。
- 字段确认后再加入 QueryPlan。

## 反例

### 自动处置准确率

输入：

```text
分析一下自动处置准确率为什么下降。
```

期望：

- 不命中本场景。
- 提示这是自动处置准确率场景，不可用打标率替代。

### 质量准确率

输入：

```text
质检准确率下降了。
```

期望：

- 不命中本场景。
- 提示需要质量模块场景包。

### 底线事故

输入：

```text
底线事故数上升了。
```

期望：

- 不命中本场景。
- 提示需要底线事故监控场景包。

## 低信息量

输入：

```text
这个策略怎么了？
```

期望：

- 不直接查询。
- 先询问指标、时间窗口和策略 / reason。
- 不生成最终结论。
