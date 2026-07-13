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
| `是否+1同意` | `strategy_id` 命中 `+1评估=同意` 策略资产 | 命中输出 `是`，未命中输出 `否`；风险域维度因策略 ID 为空默认 `否`。 |
| `更新日期` | 同一策略在原始飞书表中的 `更新日期` | 命中且存在日期时输出 `YYYY-MM-DD`；历史同意清单中无当前日期的策略输出空。 |
| `+1同意日期是否在本次统计周期前` | `是否+1同意`、`更新日期`、当前统计周期开始日期 | `是否+1同意 = 是` 且 `更新日期 < 当前统计周期开始日期` 时输出 `是`，否则输出 `否`。 |

资产来源为飞书表格 `GzpCwP516imDB8kQ3g1cLr5bnPc`，筛选条件为 `+1评估 = 同意`。该清单会持续更新，默认每天第一次使用该策略清单时必须只读刷新飞书表格，并用当前表内容覆盖本地 `plus1_agreed_strategy_updates.json`；日内重复使用可复用当日已刷新的本地资产。

全等级报表除保留完整 `综合` 外，还必须输出 `综合_剔除+1同意`：以当前统计周期开始日期为 cutoff，剔除 `是否+1同意 = 是` 且 `更新日期 < cutoff` 的策略。示例：周期为 `2026-07-06` 至 `2026-07-12` 时，剔除 `2026-07-06` 之前已同意的策略；`更新日期` 为空或不早于 `2026-07-06` 的行保留。

汇总统计也必须成对输出：`汇总统计` 基于完整 `综合` 聚合，`汇总统计_剔除+1同意` 基于 `综合_剔除+1同意` 聚合，二者字段结构保持一致。汇总统计中的 `低效策略打标率` 必须与表内展示量一致，按 `低效策略日均打标量 / 低效策略日均完审量` 计算。

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
- 空机审一级标签补映射也必须输出到内部稳定别名 `mach_root_label_key`，不得直接写为展示字段 `mach_root_label_name` 后参与 `GROUP BY`。
- 默认低打标率分级不得按 `reason` 分组；`reason` 只保留为样本过滤字段，即必须继续排除 `recall_skip_L6` 和 `fatal_output`。
- 风险域爆量类查询必须先按 `mach_root_label_key × strategy_id_key × strategy_name_key` 筛出低效策略，再按 `mach_root_label_key` 汇总。风险域维度输出时 `strategy_id`、`strategy_name` 置空。

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
