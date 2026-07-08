# 期望输出：打标率低效 reason 分析

## 正例

正例必须：

- 命中 `scenario_key=efficiency-label-rate-low-efficiency`。
- 输出 `task_type=query_only` 或 `partial_workflow`。
- 输出 QueryPlan。
- 输出 source_footer。
- 明确打标率口径：打标量 / 完审量。
- 明确 source priority：Semantic Layer first，必要时受控 fallback。

## 低效分级

当 `analysis_mode=low_efficiency_grading` 时必须：

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

阶段 1 之前必须保持：

- 不调用真实数据查询。
- 不发送真实通知。
- 不写线上状态。
- 如需真实查询，必须输出人工确认提示。
