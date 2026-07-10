# 场景流程包合并快照：efficiency-label-rate

本文件由根目录场景包生成，用于发布包运行态读取。
业务事实以根目录 `human_review_ops/references/scenarios/` 中的源文件为准。

## scenario_manifest.md

## 场景标识

- `scenario_key`：`efficiency-label-rate`
- 模块：效率模块
- 指标对象：打标率
- 运营对象：送审原因 / reason 在不同维度下的打标率表现
- 当前状态：阶段 1 主线样板场景

## 参考来源

本场景只吸收以下已验证 Skill 中与打标率流程直接相关的内容：

- `.trae/skills/warehouse-skill/`：数据治理、Semantic Layer first、provenance、字段映射和数据质量 gate。
- `.trae/skills/low-efficiency-strategy-analysis/`：低打标率分级、维度拆解和输出结构。

不直接迁移旧 Skill 的完整实现、历史目录结构或在线工具权限。

## 触发意图

- 查询打标率、进审量、完审量、打标量趋势，并要求可复核口径。
- 查询高打标率或低打标率的策略 / reason。
- 按机审一级标签、场景、项目等维度拆解打标率。
- 近 N 天有哪些高完审、低打标 reason。
- 打标率低的策略 / reason 是否需要分级。
- notice、P2、P1、P0 低效策略清单。

## 排除意图

- 自动处置准确率分析。
- 质检准确率分析。
- 底线事故数分析。
- 审核员个人明细、手机号、open_id 等敏感明细导出。
- 责任人触达、建群、工单推进等后续运营流转。

## 默认运行约束

- 第一阶段默认 `debug_only`。
- 默认只读。
- 默认先生成 QueryPlan；QueryPlan 通过断言后，可执行符合权限策略的 mock / 只读查询链路。
- 覆盖样本池、未治理字段、权限不足、真实飞书触达、状态写入或高风险动作必须人工确认。
- 数据未就绪、权限不足、口径不清时停止，不输出“无异常”结论。

## metric_contract.md

## 主指标

- `metric_id`：`label_rate`
- 中文名：打标率
- 模块：效率模块
- 场景：送审原因 / reason 在不同维度下的打标率查询、对比、趋势和分级分析
- 状态：active

## 相关指标

| 业务概念 | `metric_id` | 口径 | 默认粒度 |
| --- | --- | --- | --- |
| 打标率 | `label_rate` | `SUM(label_cnt) / SUM(review_done_cnt)` | `day × reason` |
| 进审量 | `review_in_cnt` | 进入人审的审核量 | `day × reason` |
| 完审量 | `review_done_cnt` | 完成人审的审核量 | `day × reason` |
| 打标量 | `label_cnt` | 被打标的审核量 | `day × reason` |
| 日均进审量 | `avg_daily_review_in_cnt` | `SUM(review_in_cnt) / COUNT(DISTINCT p_date)` | `reason` |
| 日均完审量 | `avg_daily_review_done_cnt` | `SUM(review_done_cnt) / COUNT(DISTINCT p_date)` | `reason` |
| 日均打标量 | `avg_daily_label_cnt` | `SUM(label_cnt) / COUNT(DISTINCT p_date)` | `reason` |

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

- `reason`：送审原因。
- `p_date`：日期分区。
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

## dataset_reference.md

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

## analysis.md

## 分析模式

| 模式 | 触发条件 | 主要产出 |
| --- | --- | --- |
| `label_rate_trend` | 用户只问打标率、进审量、完审量趋势 | QueryPlan + 趋势口径说明 + source_footer |
| `label_rate_ranking` | 用户查询高打标率、低打标率、TopN / BottomN 策略或 reason | 排序清单 + evidence |
| `low_label_rate_grading` | 用户明确问低效策略、P0/P1/P2/notice、低打标 reason 清单 | 四级分级清单 + 综合去重清单 |
| `dimension_breakdown` | 用户要求按机审一级标签、场景、项目或其他维度拆解 | `dimensions × reason` 明细 + `dimensions` 汇总 |

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

示例：

```json
{
  "metric_id": "label_rate",
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

输出：

- `dimensions × reason` 明细。
- `dimensions` 全量汇总。

如果用户指定的维度不在 `metric_contract.md` 支持维度中，必须先通过 Semantic Layer / 数据集字段发现确认字段，不能直接拼字段名。

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

## notification_templates.md

## 调试阶段原则

- 只生成通知草稿。
- 不发送真实飞书消息。
- 不创建群。
- 不写入状态。

## 低打标率策略预警草稿

```text
【人审效率预警｜低打标率 reason】

场景：{scenario_key}
等级：{severity}
周期：{time_window}

摘要：
{summary}

证据：
- reason：{reason}
- 日均进审量：{avg_review_in_cnt}
- 日均完审量：{avg_review_done_cnt}
- 日均打标量：{avg_label_cnt}
- 打标率：{label_rate}
- 命中条件：{hit_condition}

建议 Owner：{owner}
Owner 依据：{routing_evidence}
置信度：{confidence}

说明：
- 本通知为 debug_only 草稿，未真实发送。
- 打标率口径：打标量 / 完审量。
- source_footer：{source_footer}
```

## 打标率维度拆解摘要草稿

```text
【人审效率分析｜打标率维度拆解】

维度：{dimensions}
周期：{time_window}

核心发现：
{summary}

TOP 低效组合：
{top_dimension_reason_rows}

限制说明：
{limitations}

本结果仅为调试草稿，真实触达前需要人工确认。
```

## 升级草稿

```text
【需人工确认｜打标率分析】

触发原因：{review_reason}
待确认事项：
1. 指标口径是否确认。
2. 数据分区是否就绪。
3. Owner 是否准确。
4. 是否允许真实触达或线上状态写入。

当前不会发送真实通知或写入线上状态。
```

## owner_routing.md

## 路由原则

本场景用于基于低打标率数据生成 POC / 触达对象路由计划。当前 POC 找人逻辑按 `mach_root_label_name`（机审一级标签）映射到 POC 姓名；真实触达前必须再完成飞书 open_id 解析、目标确认和发送门禁校验。

## 当前开发阶段决策

- POC 路由粒度：优先按 `mach_root_label_name` 映射 POC；`reason`、`strategy_id`、`strategy_name` 作为证据字段保留。
- 映射来源：飞书表格 `https://bytedance.larkoffice.com/sheets/TpxwsA8zohUZkVtJ4J9cDcXUnbg?sheet=HKdm9w`。
- 当前身份粒度：仅完成 POC 姓名映射，`poc_open_id` 尚未解析。
- 默认收件人：当输入数据缺少 `mach_root_label_name` 或标签未映射时，开发验证阶段 fallback 到用户本人，即 `default_recipient=self`。
- 群推送：当前不自动群发，真实触达前必须人工确认目标群 / POC 收件人。
- 回收闭环：暂不做联系人回复收集、卡片按钮回调或结果回收。

## 机审一级标签 POC 映射

| 机审一级标签 | POC |
| --- | --- |
| 国家安全 | 杜衡 |
| 领导人 | 宋诗慧 |
| 指令舆情相关 | 张发奇 |
| 偏激社会情绪和涉外言论 | 张发奇 |
| 党和国家形象负面 | 李中涛 |
| 举报 | 韩晶晶 |
| 不良行为或争议价值观 | 陈雅静 |
| 色情性化 | 刘小楷 |
| 高热 | 闫秦河 |
| 侵犯未成年权益 | 张宇轩 |
| 引人不适 | 陈思乔 |
| 短期策略迁移 | 陈思乔 |
| 危险行为 | 陈雅静 |
| 政媒 | 杜衡 |
| 违法违规 | 叶健 |

## 等级触达规则

| 等级 | 触达范围 | 动作要求 | 当前占位 |
| --- | --- | --- | --- |
| `notice` | 群内同步策略明细和数据链接。 | 周知明细，纳入观察。 | `default_recipient=self`，默认发给用户本人预览。 |
| `P2` | 治理 BP、审核 VOC 的 POC 角色、人审运营。 | 请相关 POC 说明低打标原因和后续处理计划。 | `default_recipient=self`，默认发给用户本人预览。 |
| `P1` | P2 范围 + 治理 BP 的 +1、VOC 负责人、人审运营负责人。 | 要求负责人关注，并推动原因说明和处理计划。 | `default_recipient=self`，默认发给用户本人预览。 |
| `P0` | P1 范围 + 治理负责人。 | 高优先级周知，要求重点关注和处理。 | `default_recipient=self`，默认发给用户本人预览。 |

## 输出要求

- POC / 触达对象路由计划。
- 等级触达范围。
- 动作要求。
- 命中依据。
- POC 姓名、命中的机审一级标签、未映射标签和缺失路由维度计数。
- 置信度：`high` / `medium` / `low`。
- 是否需要人工确认。

## 低置信度条件

- 输入数据只有 reason 名称，没有 `mach_root_label_name`。
- `mach_root_label_name` 未命中 POC 映射。
- POC 只有姓名，尚未解析飞书 open_id。
- 触达角色仍为角色级占位。
- 数据来源 fallback 到 curated raw SQL。
- 用户问题涉及正式汇报、处罚、资源调整或高风险决策。

## 调试阶段约束

- 不在未确认 open_id 和目标群前真实触达 POC。
- 不创建飞书群。
- 不自动群发消息。
- 不写状态存储。

## state_machine.md

## 调试状态

```text
INTAKE
  -> SCENARIO_RESOLVED
  -> PERCEPTION_READY
  -> QUERY_PLAN_READY
  -> ANALYSIS_READY
  -> OWNER_SUGGESTED
  -> NOTIFICATION_DRAFTED
  -> MANUAL_TRACKING_RECORDED
  -> DEBUG_CLOSED
```

## 异常状态

```text
NEED_MORE_INFO
DATA_NOT_READY
PERMISSION_BLOCKED
HUMAN_REVIEW_REQUIRED
STOPPED_NO_CONCLUSION
```

## 状态说明

| 状态 | 含义 | 输出 |
| --- | --- | --- |
| `INTAKE` | 接收用户问题 | 原始输入 |
| `SCENARIO_RESOLVED` | 命中打标率场景 | `scenario_key` |
| `PERCEPTION_READY` | 识别任务类型、指标、时间窗口和维度 | `task_type`、`metric_id`、`dimensions` |
| `QUERY_PLAN_READY` | 生成 QueryPlan | QueryPlan |
| `ANALYSIS_READY` | 完成趋势、分级或维度拆解分析 | 分析摘要、evidence |
| `OWNER_SUGGESTED` | 生成 Owner 建议 | Owner 依据、置信度 |
| `NOTIFICATION_DRAFTED` | 生成通知草稿 | 草稿文本 |
| `MANUAL_TRACKING_RECORDED` | 记录人工处理状态 | manual tracking |
| `DEBUG_CLOSED` | 调试闭环 | 调试结论 |

## 流转规则

- 用户只问趋势：`QUERY_PLAN_READY -> ANALYSIS_READY -> DEBUG_CLOSED`。
- 用户问低打标率 reason 分级：`QUERY_PLAN_READY -> ANALYSIS_READY -> OWNER_SUGGESTED`。
- 用户问高打标率或普通趋势：`QUERY_PLAN_READY -> ANALYSIS_READY -> DEBUG_CLOSED`。
- 用户要求通知：必须先 `OWNER_SUGGESTED`，再 `NOTIFICATION_DRAFTED`。
- 口径、时间窗口或指标不明确：进入 `NEED_MORE_INFO`。
- 数据未就绪：进入 `DATA_NOT_READY`，不得输出低效结论。
- 权限不足：进入 `PERMISSION_BLOCKED`。
- QueryPlan 通过且工具权限为只读时，可以进入只读查询执行。
- 真实通知、线上写状态、覆盖样本池、未治理字段、禁用来源或高风险动作：进入 `HUMAN_REVIEW_REQUIRED`。

## sla.md

## 分级响应

| 等级 | 响应建议 | 处理建议 | 升级条件 |
| --- | --- | --- | --- |
| `P0` | 当日确认 | 当日完成 Owner 定位和治理方案确认 | 超过 1 个工作日未确认 |
| `P1` | 1 个工作日内确认 | 2 个工作日内给出治理动作 | 连续两轮仍未改善 |
| `P2` | 2 个工作日内确认 | 3 个工作日内完成复盘 | 进审量继续增长或打标率继续下降 |
| `notice` | 周期性观察 | 纳入周报或观察清单 | 连续命中或升级到 P2+ |

## 调试阶段

- 不启动真实 SLA 计时。
- 只输出建议等级、建议响应时间和升级条件。
- 真实触达、状态流转和升级必须人工确认。

## 停止条件

以下情况不进入 SLA：

- 数据未就绪。
- 查询失败。
- 口径未确认。
- Owner 置信度为 low 且无人确认。
- 当前只做普通趋势或高打标率查询，不做低打标率治理。

## examples.md

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
