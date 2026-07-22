# 分析规则：打标率

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
