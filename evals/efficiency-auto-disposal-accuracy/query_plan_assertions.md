# QueryPlan 断言：自动处置准确率

## 必填字段

- `metric_id`
- `time_range`
- `dimensions`
- `filters`
- `allowed_sources`
- `forbidden_sources`
- `quality_checks`

## 必须命中

- `metric_id = auto_disposal_accuracy`
- 不得使用质检准确率字段。
- 不得使用底线事故数字段。
- 不得使用临时表或废弃表。

## 阻断条件

- 缺少时间窗口且无法默认。
- 缺少指标对象。
- 命中混淆字段。
- 来源脚注缺失。
