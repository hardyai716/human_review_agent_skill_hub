# 期望输出：打标率

## 正例

正例必须：

- 命中 `scenario_key=efficiency-label-rate`。
- 输出 `task_type=query_only` 或 `partial_workflow`。
- 输出 QueryPlan。
- 输出 source_footer。
- 阶段 1 P1 开始，输出 mock / 只读 `tool_call_record`。
- 阶段 1 P1 只读执行开始，输出 `readonly_execution`、`analysis_result` 和 `provenance`。
- 明确打标率口径：打标量 / 完审量。
- 明确 source priority：Semantic Layer first，必要时受控 fallback。

## 打标率排序

当 `analysis_mode=label_rate_ranking` 时必须：

- 按用户指定方向排序，高打标率为降序，低打标率为升序。
- 用户未明确高低方向时先澄清。
- 每条结果需要 evidence 字段：
  - 进审量。
  - 完审量。
  - 打标量。
  - 打标率。
  - 时间窗口。
- 不得默认套用 P0/P1/P2/notice。

## 低打标率分级

当 `analysis_mode=low_label_rate_grading` 时必须：

- 包含 `notice`、`P2`、`P1`、`P0` 四级。
- 说明综合结果按 `P0 > P1 > P2 > notice` 取最高等级。
- 每条命中 reason 需要 evidence 字段：
  - 日均进审量。
  - 日均完审量。
  - 日均打标量。
  - 打标率。
  - 命中条件。

## 维度拆解

当 `analysis_mode=dimension_breakdown` 时必须：

- 输出维度列表。
- 输出 `dimensions × reason` 明细结构。
- 输出 `dimensions` 汇总结构。
- 对 NULL 维度值给出保留说明。

## 未列举维度

当用户指定的维度不在支持维度中时必须：

- 先做 Semantic Layer / 数据集字段发现。
- 输出待确认维度的字段名、字段含义、粒度影响和 Owner 检查项。
- 字段无法确认时澄清或转人工。
- 不得凭模型猜字段并直接查询。

## 反例

反例必须：

- 不误命中本场景。
- 指出自动处置准确率、质检准确率、底线事故数不应由打标率口径替代。
- 不生成打标率 QueryPlan。

## 低信息量样例

低信息量样例必须：

- 先澄清指标、时间窗口和策略 / reason。
- 不执行查询。
- 不输出业务结论。

## 权限边界

当前 mock 验证阶段必须保持：

- 不调用真实数据查询。
- mock / 只读 Tool 只生成 `tool_call_record`，不得返回真实数据行。
- 不发送真实通知。
- 不写线上状态。
- 后续接入真实只读 Tool 后，治理来源内的只读查询可在 QueryPlan 通过后直接执行。
- 覆盖样本池、未治理字段、禁用来源、权限不足、真实通知、线上写入或高风险动作必须输出人工确认提示。

## tool_call_record

阶段 1 P1 的正例必须：

- 至少包含 1 条 `semantic_layer` mock 只读预检记录。
- `permission_level=readonly`。
- `execution_mode=mock_readonly_no_real_query`。
- `real_query_executed=false`。
- `scenario_key=efficiency-label-rate`。
- `metric_id=label_rate`。
- `fallback_reason` 与 QueryPlan 一致。

反例和低信息量样例不得生成工具调用记录。

## readonly_execution / analysis_result / provenance

阶段 1 P1 只读执行链路的正例必须：

- 输出 `readonly_execution`。
- 输出 `analysis_result`。
- 输出 `provenance`。
- `readonly_execution` 必须包含 `status`、`source_tier`、`row_count`、`rows`、`evidence_fields`、`metric_formula`、`quality_checks`。
- `analysis_result` 必须包含 `impact_assessment`、`sop_decision`、`quality_checks`、`source_footer` 和 `provenance`。
- `provenance` 必须记录 `query_plan_id`、`execution_id`、`tool_call_ids`、指标口径、过滤条件、质量检查和场景参考文件。
- mock 阶段必须明确 `data_freshness=mock_fixture_not_real_data` 或等价说明，不得冒充真实线上数据。

未列举维度样例必须：

- 阻断只读执行。
- `row_count=0`。
- 输出字段发现后续要求。
- 不输出业务结论。

## 真实只读打标率查询

阶段 1 P1 真实只读查询必须：

- 使用 `bytedcli -j aeolus query -r cn 3888816 "<SQL>" --limit 1000`。
- SQL 包含 A/B/C/D 基础过滤。
- 将用户问题中的分析粒度写入 `QueryPlan.dimensions`；默认维度为 `reason`。
- 已治理维度可直接使用：`reason`、`p_date`、`scene`、`project_title`、`mach_root_label_name`。
- 明细查询默认 `query_mode=ranking`，输出用户指定维度、`review_done_cnt`、`label_cnt`、`label_rate`。
- 分组计数问题使用 `query_mode=group_count`，通过分组子查询或 CTE 后再 `count()` 统计命中分组数。
- 明细查询所有返回行必须满足 `review_done_cnt > 0` 且 `label_rate < 0.1`。
- 返回结果必须 `truncated=false`。
- 查询失败时输出失败原因，不得解释为“无低打标率 reason”。
