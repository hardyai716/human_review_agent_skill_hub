# 感知场景：效率模块 / 自动处置准确率

## 场景标识

- `scenario_key`: `efficiency-auto-disposal-accuracy`
- 模块: 效率模块
- 指标对象: 自动处置准确率
- 主指标: `auto_disposal_accuracy`
- 运营对象: 自动处置策略、队列、风险域和标签下的准确率表现

## 触发与排除

应触发:

- 用户询问自动处置准确率下降、波动、撞线或预警。
- 用户要求按策略、队列、风险域、三级标签或时间窗口拆解自动处置准确率。
- 用户询问自动处置准确率预警应由谁处理，且仍处于场景识别或 readiness 判断阶段。

应排除:

- 打标率、低打标 reason、P0/P1/P2/notice 低效策略分级。
- 质检准确率、底线事故数、人工审核准确率。
- 只要求生成通知、触达 POC、闭环记录或线上写状态。
- 用户要求直接执行 SQL、真实群发、拉群或导出敏感明细。

## 用户意图别名

| 意图 | 常见表达 |
| --- | --- |
| 准确率分析 | 自动处置准确率、自动处置准、自动处置是否准确 |
| 波动预警 | 下降、波动、撞线、预警、异常 |
| 维度拆解 | 按策略、按队列、按风险域、按三级标签、按时间 |
| 负责人确认 | 应该找谁、谁处理、责任人 |

## 指标与维度别名

| `metric_id` | 别名 | 感知说明 |
| --- | --- | --- |
| `auto_disposal_accuracy` | 自动处置准确率、自动处置准 | 主指标；不得与质检准确率、底线事故数或人工审核准确率混用。 |

| 维度 | 别名 | 感知说明 |
| --- | --- | --- |
| `strategy` | 策略、策略 ID、规则 | 常用拆解实体。 |
| `queue` | 队列、审核队列 | 常用拆解实体。 |
| `risk_domain` | 风险域、风险类型 | 常用拆解实体。 |
| `third_level_label` | 三级标签、标签 | 常用拆解实体。 |
| `time_window` | 时间窗口、统计日期、近 N 天 | 分析型任务必需。 |

未列举维度不得猜字段；需澄清或要求字段发现。

## `task_type` 判定规则

- `auto_disposal_accuracy_trend`: 命中下降、波动、趋势、撞线、预警。
- `dimension_breakdown`: 用户要求按策略、队列、风险域、三级标签或时间拆解。
- `notification_request`: 用户要求通知、卡片、触达、群发或 POC 路由。
- `resolution_tracking`: 用户要求闭环、跟进、状态、关闭或 tracking。
- `unknown`: 无法唯一识别任务类型。

## Readiness 检查

必须检查:

- 场景是否唯一命中 `efficiency-auto-disposal-accuracy`。
- 是否与打标率、质检准确率、底线事故数或人工审核准确率混淆。
- 分析型任务是否有明确 `time_window`。
- 用户指定维度是否在本场景列举范围内。
- 是否要求 SQL 执行、真实通知、自动拉群、线上写状态或敏感明细导出。
- 通知 / 闭环请求是否已有前置分析或 tracking 产物。

状态规则:

- `ready`: 场景、任务、必要时间窗口和维度均明确，且无越权动作。
- `needs_clarification`: 缺少时间窗口、任务类型或维度确认。
- `blocked`: 命中相邻指标、要求越权动作或存在敏感数据风险。

## Handoff 规则

- 分析型任务且 `readiness.status=ready`: `next_skill=analysis`。
- 通知请求且已有分析产物: `next_skill=notification`。
- 闭环请求且已有通知或 tracking 产物: `next_skill=resolution`。
- 其他情况不交接，先输出澄清字段或阻断原因。

感知阶段交接 reference 只指向本单场景文档:

- `references/scenarios/efficiency-auto-disposal-accuracy.md`

## 阻断条件

- `scenario_not_recognized`
- `excluded_adjacent_metric:<scenario_key>`
- `task_type_not_clear`
- `missing_time_window`
- `unsupported_dimension_requires_field_discovery`
- `missing_analysis_artifact`
- `missing_notification_or_tracking_source`
- `sql_execution_requested`
- `real_group_send_requested`
- `auto_group_invite_requested`
- `online_write_requested`
- `sensitive_detail_export_requested`

## 正反例

正例:

- `分析一下自动处置准确率为什么下降。` -> `scenario_key=efficiency-auto-disposal-accuracy`
- `按策略维度看自动处置准确率。` -> `task_type=dimension_breakdown`
- `自动处置准确率预警应该找谁？` -> 命中本场景；若缺少分析产物，不直接进入通知

反例:

- `近 7 天有哪些低打标 reason？` -> 不命中本场景，候选为 `efficiency-label-rate`
- `质检准确率下降了。` -> 不命中本场景
- `底线事故数上升了。` -> 不命中本场景
- `直接群发自动处置预警并把状态写成已处理。` -> `blocked`
