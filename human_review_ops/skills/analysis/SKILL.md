---
name: analyzing-ops-metrics
description: "当用户需要对已识别的人审运营指标或场景做只读分析时使用；生成 QueryPlan、受控 SQL、分析结果、source_footer 和 provenance；不识别未知场景、不通知、不写状态。"
allowed-tools:
  - Read
  - Bash
---

# 分析 Skill

本 Skill 是运行态自包含分析包。所有分析口径、数据源、分析模式和正反例必须从本目录 `references/` 读取，不依赖 `human_review_ops/references/` 外部场景包。

## 触发条件

当用户需要对已识别的人审运营指标或场景做查询计划 (QueryPlan)、只读查询、字段选择、趋势、排序、低效分级或结论输出时使用本技能 (Skill)。

- 上游感知技能 (perception Skill) 已输出 `scenario_key`、`metric_ids`、`task_type` 和 `readiness.status=ready`。
- 用户直接要求分析打标率、进审量、完审量、打标量、自动处置准确率、高/低打标 reason、低效策略分级或维度拆解。
- 用户要求输出可复核口径、受控 SQL、数据证据、分级结果或来源页脚 (source_footer)。
- 用户要求先生成查询计划 (QueryPlan)，再由具备只读权限的外部执行环境执行查询。

## 禁止使用

- 不用于识别未知场景或补全路由；场景不明确时先交给感知技能。
- 不用于生成通知草稿、飞书卡片 (Card)、负责人 (POC) 路由或发送计划 (send_plan)；这些交给通知技能。
- 不用于记录人工跟踪 (manual tracking)、状态流转、关闭事件或写线上状态；这些交给解决技能。
- 不执行 DDL、DML、INSERT、UPDATE、DELETE、MERGE、DROP、CREATE、ALTER、TRUNCATE、写临时线上表或任何有副作用操作。
- 不使用未授权数据源、无 Owner 字段、已废弃表、临时表、敏感个人明细或用户未确认的样本池覆盖。
- 不把查询失败、权限失败、分区未就绪解释为业务“无异常”。
- 不读取 `human_review_ops/references/`、旧 Skill、历史 SQL 或未确认记忆来补运行态口径。

## 输入

必需输入：

- `scenario_key`：例如 `efficiency-label-rate`。
- `metric_ids`：例如 `label_rate`。
- `task_type`：例如 `label_rate_trend`、`label_rate_ranking`、`low_label_rate_grading`、`dimension_breakdown`。
- `time_window`：开始日期、结束日期、相对天数或数据延迟说明。

可选输入：

- `dimensions`：拆解维度，如 `mach_root_label_name`、`strategy_id`、`strategy_name`、`reason`。
- `filters`：用户指定过滤条件，必须与指标契约兼容。
- `run_mode`：默认调试模式 (`debug_only`)。
- `source_preference`：语义层、治理数据集或受控原始 SQL。
- `perception_readiness`：感知阶段的就绪结果。
- `user_override`：用户要求覆盖默认样本池或新增字段时，必须进入人工确认。

## 输出

输出必须包含：

- 查询计划 (QueryPlan)：指标、时间、维度、过滤、来源优先级、禁用来源、质量检查和人工确认要求。
- 只读 SQL 或只读执行请求 (`readonly_execution_request`)：仅在 QueryPlan 通过后生成。
- 只读执行结果 (`readonly_execution`)：由具备只读权限的外部执行环境执行后回填；无权限时输出待执行请求。
- 分析摘要：区分数据事实、解释判断和业务建议。
- 分级结果：仅低打标率分级任务输出 `notice`、`P2`、`P1`、`P0`。
- 来源页脚 (source_footer)：说明指标契约、数据源、时间窗口、过滤、质量检查和限制。
- 溯源信息 (`provenance`)：引用的 reference、数据集、字段映射和工具调用记录。
- 质量检查结果 (`quality_checks`)：新鲜度、分母、字段映射、权限、样本池。
- 停止原因 (`stop_reason`)：查询失败、权限不足或信息不足时必须输出。

## 工作流

1. 确认 `scenario_key` 和 `metric_ids` 已就绪；不明确时停止并交回感知技能。
2. 按固定加载顺序读取 `references/common.md`、`references/scenario-index.md`、一个场景文档和必要的 `references/methods/*.md`。
3. 从场景文档读取指标口径、数据源字段、过滤、分析模式、失败条件和正反例。
4. 生成 QueryPlan，并在执行前完成字段、权限、分区、新鲜度和样本池检查。
5. 构造 SQL 或只读执行请求。比率类指标必须用分子和分母重新计算，不直接聚合已有比率字段。
6. 执行只读门禁：只有外部执行环境具备只读工具权限，且 QueryPlan 未命中禁用来源，才能执行查询。
7. 做质量检查：分区是否就绪、分母是否为 0、字段映射是否确认、结果行数是否合理、是否有 NULL 维度。
8. 按 `task_type` 输出趋势、排序、低效分级或维度拆解。低效分级只在场景文档声明的模式中启用。
9. 生成 source_footer，把口径、过滤、数据源、限制和人工确认项写清楚。
10. 遇到失败或阻断时停止，不输出业务结论，只输出 `stop_reason` 和下一步澄清/修复建议。

每次只加载一个场景文档。不要为同一场景继续拆读 `metric_contract`、`dataset_reference`、`analysis`、`examples` 四类文件；这些内容已经合并到 `references/scenarios/<scenario_key>.md`。

## 参考资料加载

加载顺序固定如下：

1. `references/common.md`
2. `references/scenario-index.md`
3. `references/scenarios/<scenario_key>.md`
4. 仅当场景文档要求时，读取 `references/methods/query_plan.md`、`references/methods/source_footer.md` 或 `references/methods/weighted_attribution.md`

当前场景文档：

| `scenario_key` | 场景文档 | 适用指标 |
| --- | --- | --- |
| `efficiency-label-rate` | `references/scenarios/efficiency-label-rate.md` | `label_rate`、`review_in_cnt`、`review_done_cnt`、`label_cnt` |
| `efficiency-auto-disposal-accuracy` | `references/scenarios/efficiency-auto-disposal-accuracy.md` | `auto_disposal_accuracy` |

场景文档必须自包含以下章节：

- 场景元信息
- 触发与排除
- 指标口径
- 数据源与字段
- 默认过滤
- 支持维度
- 分析模式
- QueryPlan 要求
- 输出要求
- 失败处理
- 正反例

## QueryPlan 与 SQL

查询计划 (QueryPlan) 必填字段：

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

打标率 SQL 规则：

- 默认样本池必须复用 `references/scenarios/efficiency-label-rate.md#默认过滤` 中的过滤片段，不在 `SKILL.md` 重复维护。
- 默认治理数据源和字段映射以 `references/scenarios/efficiency-label-rate.md#数据源与字段` 为准。
- 标准分析粒度为 `mach_root_label_name × strategy_id × strategy_name × reason`，除非用户要求更粗或更细粒度且字段已治理。
- 按维度字段聚合前，必须先用 `ifNull(...)` 把可空维度转换为稳定 key；内部 key 不得与底表物理字段同名，统一使用 `mach_root_label_key`、`strategy_id_key`、`strategy_name_key`、`reason_key` 这类 `*_key` 别名，并在 `GROUP BY` 中使用这些转换后的 key。外层再映射回标准输出字段名，避免 ClickHouse / Aeolus 把 `GROUP BY mach_root_label_name` 解析到同名物理字段，漏掉 NULL 维度记录。
- 跨天、跨 reason、跨标签聚合时，必须分别 `SUM(label_cnt)` 和 `SUM(review_done_cnt)` 后重算 `label_rate`。
- 用户指定新维度时，先通过语义层或数据集字段发现确认字段含义、粒度和权限；未确认前不得拼接字段名。
- SQL 只能是只读 `SELECT` 或公共表达式 (CTE)，不得包含写入、建表或状态更新语句。

## 分级

低打标率分级仅在 `task_type=low_label_rate_grading` 时启用。

- 默认输出等级：`notice`、`P2`、`P1`、`P0`。
- 综合清单按 `P0 > P1 > P2 > notice` 对同一 reason 取最高等级。
- 每条命中必须带证据：日均进审量、日均完审量、日均打标量、打标率、命中条件、时间窗口。
- 某等级无命中时写“本期 0 条”；查询失败时写失败原因，不写“0 条”。
- 高打标率、普通趋势或普通排序不套用低效分级。

分级阈值和细节以 `references/scenarios/efficiency-label-rate.md#模式-b低打标率分级` 为准。

## 归因

打标率下降归因默认使用“策略加权影响”作为主排序口径；Rate / Mix Effect 作为二级解释字段。

- 主排序字段：`weighted_impact = cur_share * cur_rate - prev_share * prev_rate`
- 维度主键：`mach_root_label_name × strategy_id × strategy_name`
- `strategy_id` 是稳定主键，`strategy_name` 只用于展示。
- 需要具体公式、输出字段和边界时读取 `references/methods/weighted_attribution.md`。

## Source Footer

来源页脚 (source_footer) 必须包含：

- `metric_contract_ref`
- `dataset_reference_ref`
- `analysis_ref`
- `query_plan_id`
- `time_window`
- `data_lag`
- `source_priority`
- `actual_source`
- `filters`
- `dimensions`
- `quality_checks`
- `limitations`
- `run_mode`

在单文档场景结构下，`metric_contract_ref`、`dataset_reference_ref`、`analysis_ref` 可以都指向同一个 `references/scenarios/<scenario_key>.md` 的不同章节锚点。不得指向 Skill 外部场景包。

如果用户覆盖样本池、使用新增维度或 fallback 到受控原始 SQL，必须在 `source_footer.limitations` 和 `QueryPlan.fallback_reason` 中说明原因。

## 只读查询边界

- 本技能文档不声明外部工具；真实查询只能由具备只读权限的外部执行环境执行。
- 查询前必须先生成 QueryPlan，并确认未命中 `forbidden_sources`。
- 允许读取语义层、治理数据集或受控原始表；禁止读取无治理、无 Owner、临时、废弃或敏感明细来源。
- 只读执行失败时，保留工具错误、QueryPlan 和 source_footer，不输出业务结论。
- 不把只读查询结果写入线上状态、工单、飞书消息或持久化业务表。

## 脚本

`human_review_ops/skills/analysis/scripts/label_rate_analysis.py` 是打标率低效分级的可复用分析入口。该脚本无副作用，不执行 SQL、不发送通知、不写线上状态；它负责生成和标准化分析资产：

- `parse_levels()`：解析 `notice`、`P2`、`P1`、`P0` 等级参数。
- `sql_by_level()`：生成各等级只读 SQL，复用指标契约中的样本池过滤、四维粒度和低打标率分级规则。
- `build_query_plan(levels, sql_map)`：生成 QueryPlan，包含来源优先级、允许/禁止来源、质量检查和 `sql_by_level`。
- `build_records(payloads, levels, sql_map, row_enricher=None)`：把只读查询返回 payload 标准化为 `environment`/`sample` 记录，包含 `readonly_execution`、`analysis_result`、`source_footer` 和 `provenance`。
- `build_source_footer(...)`、`build_readonly_execution(...)`、`build_analysis_result(...)`：生成来源页脚、只读执行摘要和标准化分析结果。

可用 dry-run 验证脚本输出结构：

```bash
python3 human_review_ops/skills/analysis/scripts/label_rate_analysis.py --dry-run --levels notice,P2,P1,P0
```

脚本与外部执行环境的分工：

- `label_rate_analysis.py` 负责 QueryPlan、source_footer、打标率 SQL 构造、分级规则、结果标准化和 smoke 样例。
- 外部执行环境负责调用只读数据工具、回填查询结果、补充 POC 名称和保存分析产物；它通过 `label_rate_analysis.parse_levels()`、`label_rate_analysis.sql_by_level()` 和 `label_rate_analysis.build_records(...)` 复用本 Skill 脚本。
- 调用方 Agent 无只读执行权限时，只输出 QueryPlan 或只读执行请求，不绕过工具权限门禁执行真实查询。

## 失败处理

- `scenario_key`、指标、时间窗口或口径不明确：停止，输出澄清字段。
- 分区未就绪或新鲜度不足：停止，输出数据延迟说明。
- 权限不足：停止，输出权限阻断，不输出低效结论。
- 字段映射失败：停止，列出缺失字段和需要确认的字段。
- 命中禁用来源：停止，要求改用治理来源。
- 查询失败：输出错误、QueryPlan、source_footer 和重试建议，不把失败解释成无异常。
- 分母为 0 或样本过小：输出质量风险，不给强结论。

## 验证

运行 Skill 内自包含 smoke 校验：

```bash
python3 scripts/selfcheck.py
```

该脚本只调用本 Skill 内 `label_rate_analysis.py`，不引用 Skill 外部路径、不执行 SQL、不发送通知、不写线上状态。

人工验证点：

- `label_rate_analysis.py --dry-run` 输出 JSON，且包含 `QueryPlan`、`source_footer`、`readonly_execution`、`analysis_result` 和 `provenance`。
- 低打标率只读执行方复用 `label_rate_analysis.parse_levels()`、`label_rate_analysis.sql_by_level()` 和 `label_rate_analysis.build_records(...)`。
- 每次查询前都有查询计划 (QueryPlan)。
- SQL 只读，且未出现写入、建表、删表或线上状态更新。
- 打标率按 `SUM(label_cnt) / SUM(review_done_cnt)` 重算。
- 打标率归因排序默认使用 `weighted_impact`。
- 低效分级只在 `low_label_rate_grading` 模式启用。
- 输出包含来源页脚 (source_footer) 和质量检查结果。
- Skill 内部不再存在同场景四件套文件；每个场景只有一个 `references/scenarios/<scenario_key>.md`。

## 示例

用户输入：

```text
已确认场景为 efficiency-label-rate，请看近 7 天低打标率策略，按机审一级标签、策略 ID、策略名称、送审原因拆分，并给 P0/P1/P2/notice。
```

期望输出要点：

```json
{
  "QueryPlan": {
    "scenario_key": "efficiency-label-rate",
    "metric_id": "label_rate",
    "task_type": "low_label_rate_grading",
    "dimensions": ["mach_root_label_name", "strategy_id", "strategy_name", "reason"],
    "review_required": true
  },
  "readonly_execution_request": {
    "mode": "select_only",
    "requires_external_readonly_executor": true
  },
  "source_footer": {
    "metric_contract_ref": "references/scenarios/efficiency-label-rate.md#指标口径",
    "dataset_reference_ref": "references/scenarios/efficiency-label-rate.md#数据源与字段",
    "analysis_ref": "references/scenarios/efficiency-label-rate.md#分析模式"
  }
}
```
