# 期望输出：打标率

## 正例

正例必须：

- 命中 `scenario_key=efficiency-label-rate`。
- 输出 `task_type=query_only` 或 `partial_workflow`。
- 输出 QueryPlan。
- 输出 source_footer。
- 阶段 1 P1 开始，输出 mock / 只读 `tool_call_record`。
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

阶段 1 必须保持：

- 不调用真实数据查询。
- mock / 只读 Tool 只生成 `tool_call_record`，不得返回真实数据行。
- 不发送真实通知。
- 不写线上状态。
- 如需真实查询，必须输出人工确认提示。

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
