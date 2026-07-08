# 期望输出：自动处置准确率

## 正例

必须输出：

- `scenario_key`
- `task_type`
- `run_mode`
- QueryPlan
- source_footer

## 反例

必须满足：

- 不命中 `efficiency-auto-disposal-accuracy`。
- 或者进入澄清，不执行查询。

## 低信息量样例

必须满足：

- 不直接查询。
- 要求补充指标、时间窗口、策略或队列对象。
