# 场景：efficiency-label-rate

本文件是 analysis Skill 的运行态单场景文档，由根场景包合并生成。运行态 Skill 只读取本文件，不再拆读四件套。

## 指标口径

## 主指标

- `metric_id`：`label_rate`
- 中文名：打标率
- 模块：效率模块
- 场景：送审原因 / reason 在不同维度下的打标率查询、对比、趋势和分级分析
- 状态：active

## 相关指标

### 方向 1：人工审核明细

| 业务概念 | `metric_id` | 口径 | 默认粒度 |
| --- | --- | --- | --- |
| 打标率 | `label_rate` | `SUM(label_cnt) / SUM(review_done_cnt)` | `day × reason` |
| 进审量 | `review_in_cnt` | 进入人审的审核量 | `day × reason` |
| 完审量 | `review_done_cnt` | 完成人审的审核量 | `day × reason` |
| 打标量 | `label_cnt` | 被打标的审核量 | `day × reason` |
| 日均进审量 | `avg_daily_review_in_cnt` | `SUM(review_in_cnt) / COUNT(DISTINCT p_date)` | `reason` |
| 日均完审量 | `avg_daily_review_done_cnt` | `SUM(review_done_cnt) / COUNT(DISTINCT p_date)` | `reason` |
| 日均打标量 | `avg_daily_label_cnt` | `SUM(label_cnt) / COUNT(DISTINCT p_date)` | `reason` |

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

- `reason`：送审原因。
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
- 主维度：`enpool_reason`
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
- 支持粒度：`p_date × reason`；维度拆解支持 `p_date × dimensions × reason`。
- 不用于：人员明细、责任人解析、open_id / chat_id、触达对象。

## 字段映射

| 概念 | 逻辑字段 | 默认 Name | 说明 |
| --- | --- | --- | --- |
| 送审原因 / reason | `reason` | `reason` | 打标率分析主实体。 |
| 策略 ID | `strategy_id` | `strategy_id` | 规则 ID；2026-07-09 通过 `bytedcli -j aeolus dataset-fields -r cn 3888816` 确认。 |
| 策略名称 | `strategy_name` | `strategy_name` | 策略名称；2026-07-09 通过 `bytedcli -j aeolus dataset-fields -r cn 3888816` 确认。 |
| 日期分区 | `date` | `p_date` | 用于时间窗口和分区就绪检查。 |
| 项目标题 | `project_title` | `project_title` | 用于排除测试、质检、离线等项目。 |
| 审核场景 | `scene` | `scene` | 默认保留社区审核三类场景。 |
| 机审一级标签 | `mach_root_label_name` | `机审一级标签` | 空值必须保留，维度拆解使用。 |
| 进审量 | `review_in_cnt` | `进审量_reviewid` | 聚合字段。 |
| 完审量 | `review_done_cnt` | `完审量_reviewid` | 打标率分母。 |
| 打标量 | `label_cnt` | `打标量__reviewid` | 双下划线，打标率分子。 |
| 打标率 | `label_rate` | `打标率__reviewid` | 不直接跨粒度聚合，应重算。 |

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

举报方向低效查询默认 `HAVING [人审完结量_report_id] > 0 AND [打标率_report_id] < 0.1`，输出 `enpool_reason`、日均人审完结量、日均打标量和打标率。

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
5. 若字段属于场景常用维度，必须同步更新根场景包与 Skill 内 `*.dataset_reference.md` 快照。

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

## 查询模板参数化

- `reason` 是默认维度，不是固定唯一维度；Agent 必须从用户问题中解析 `dimensions`。
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
| `dimension_breakdown` | 用户要求按机审一级标签、场景、项目或其他维度拆解 | `dimensions × reason` 明细 + `dimensions` 汇总 |
| `report_flow_low_label_rate` | 用户询问举报场景、举报流转或 `enpool_reason` 下的低打标率 | `enpool_reason` 低效清单 + evidence |

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
| `notice` | 近 7 天打标率 `< 10%` 且当前周期进审量 `> 100`。 |
| `P2` | 单策略低效，或低效策略环比增长。 |
| `P1` | 双周持续低效、单周高量低效，或低效策略爆量。 |
| `P0` | 四周持续低效、两周高量低效、单周超高量低效，或进审量异常爆量。 |

输出要求：

- 四个等级默认均要求当前周期进审量 `> 100`，用于降低小样本下比率型指标的波动影响。
- 四个等级 sheet 保留各自完整命中结果，不跨级去重。
- 综合 sheet 按 `P0 > P1 > P2 > notice` 对同一 reason 取最高等级。
- 每条 reason 必须带 evidence：日均进审、日均完审、日均打标、打标率、命中条件。
- 某级无命中时写“本期 0 条”，查询失败时写失败原因。

## 模式 C：维度拆解

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

## 模式 D：举报流转低打标率

适用于 `data_direction=report_flow`，即用户明确提到举报、举报场景、举报流转、`enpool_reason`、`report_id`、一轮队列或终轮队列。

字段和口径：

- 时间字段：`进审日期`。
- 主维度：`enpool_reason`。
- 分母：`人审完结量_report_id`。
- 分子：`打标量_report_id`。
- 打标率：`打标率_report_id`。
- 低效条件：`打标率_report_id < 10%` 且 `人审完结量_report_id > 0`。

默认输出：

- `enpool_reason`
- `日均人审完结量`
- `日均打标量`
- `打标率`

SQL 约束：

- 必须使用 Dataset `3952594` / appId `555137`。
- 必须复用 `dataset_reference.md#默认过滤：举报流转` 中的基础筛选。
- 不得使用人工审核明细 Dataset `3888816` 的 `reason`、`完审量_reviewid`、`打标量__reviewid`。
- 如果直接逻辑表名不可用，可使用 query_log 中确认的物理表作为受控 fallback，并在 provenance 中记录。
- 指标字段已经是聚合表达式时，不要放入未按维度聚合的子查询中二次聚合；应在同一层按 `enpool_reason` 聚合，或改写成底层 raw formula。

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
- `task_type` 为 `query_only` 或 `partial_workflow`。
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
- 输出四级分级规则摘要。
- 说明打标率口径为打标量 / 完审量。

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
- `data_direction=report_flow`，`source_profile=report_flow_review`。
- 使用 Dataset `3952594` / appId `555137`。
- 时间字段使用 `进审日期`。
- 输出字段为 `enpool_reason`、`日均人审完结量`、`日均打标量`、`打标率`。
- 不得走人工审核明细 Dataset `3888816`。

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
