# 感知场景：效率模块 / 自动处置准确率

## 场景标识

- `scenario_key`: `efficiency-auto-disposal-accuracy`
- 模块: 效率模块
- 指标对象: 自动处置准确率 / 一级标签准确率 / 三级标签准确率 / 机审自动处置准确率
- 逻辑主指标: `auto_disposal_accuracy`，这是 Skill 内部 `metric_id`，不是数据集物理字段。
- 数据集主指标字段: `label_acc_weight_rate` / 三级标签准确率
- 相关证据指标: `third_label_accuracy`, `root_label_accuracy`
- 运营对象: 一级风险标签、三级风险标签、是否安全治理域、权重类型和日期分区下的准确率表现

## 触发与排除

应触发:

- 用户询问自动处置准确率下降、波动、撞线或预警。
- 用户询问三级标签准确率、机审自动处置准确率或自动处置准。
- 用户要求按一级风险标签、三级标签、是否安全治理域、权重类型或时间窗口拆解自动处置准确率。
- 用户询问自动处置准确率预警应由谁处理，且仍处于场景识别或 readiness 判断阶段。

应排除:

- 打标率、低打标 reason、P0/P1/P2/notice 低效策略分级。
- 质检准确率、底线事故数、人工审核准确率。
- 只要求生成通知、触达 POC、闭环记录或线上写状态。
- 用户要求直接执行 SQL、真实群发、拉群或导出敏感明细。

## 用户意图别名

| 意图 | 常见表达 |
| --- | --- |
| 准确率分析 | 自动处置准确率、三级标签准确率、机审自动处置准确率、自动处置准、自动处置是否准确 |
| 波动预警 | 下降、波动、撞线、预警、异常 |
| 预警分级 | P0、P1、P2、预警等级、低于目标、低效一级标签、连续低于 80% |
| 一级标签拆解 | 一级风险标签、一级标签准确率、按一级风险标签、root label |
| 维度拆解 | 按一级标签、按三级标签、按是否安全治理域、按权重类型、按时间 |
| 负责人确认 | 应该找谁、谁处理、责任人 |

## 指标与维度别名

| `metric_id` | 别名 | 感知说明 |
| --- | --- | --- |
| `auto_disposal_accuracy` | 自动处置准确率、三级标签准确率、机审自动处置准确率、自动处置准 | Skill 内部逻辑指标 ID；数据集真实字段为 `label_acc_weight_rate` / 三级标签准确率；口径为三级标签处置准确量 / 总自动处置评估量。 |
| `root_label_accuracy` | 一级标签准确率、一级风险标签准确率 | 相关分析指标，用于一级风险标签维度表现拆解。 |

| 维度 | 别名 | 感知说明 |
| --- | --- | --- |
| `root_label_name` | 一级风险标签、一级标签、root label | 当前已验证的默认拆解维度。 |
| `root_label_id` | 一级标签 ID | 数据集支持维度。 |
| `label_id` | 三级标签 ID | 数据集支持维度。 |
| `third_level_label` | 三级标签、三级风险标签、标签 | 数据集支持维度；底层字段为 `label_name`。 |
| `is_safety_governance_domain` | 是否安全治理域、安全治理域 | 数据集支持计算维度。 |
| `label_level` | 标签等级 | 必筛项；`1` 表示一级标签，`3` 表示三级标签；一级风险标签查询默认 `label_level=1`。 |
| `weight_type` | 权重类型、整体、大盘、大模型、安全、画风 | 数值枚举：`0=整体（安全、画风、大模型）`、`1=大盘（安全、画风）`、`2=大模型`；默认使用 `0`。 |
| `date` / `time_window` | 日期分区、统计日期、T-1、昨天、近 N 天 | 一级风险标签查询可默认取 T-1，趋势或自定义窗口仍需明确时间。 |

未列举维度不得猜字段；需澄清或要求字段发现。

## `task_type` 判定规则

- `auto_disposal_alert_grading`: 命中 P0、P1、P2、预警等级、低于目标、连续低于 80% 等表达。
- `auto_disposal_root_label_accuracy_breakdown`: 命中一级风险标签、一级标签准确率、按一级标签拆解等表达。
- `auto_disposal_accuracy_trend`: 命中下降、波动、趋势、撞线、预警。
- `dimension_breakdown`: 用户要求按一级标签、三级标签、是否安全治理域、权重类型或时间拆解。
- `notification_request`: 用户要求通知、卡片、触达、群发或 POC 路由。
- `resolution_tracking`: 用户要求闭环、跟进、状态、关闭或 tracking。
- `unknown`: 无法唯一识别任务类型。

## Readiness 检查

必须检查:

- 场景是否唯一命中 `efficiency-auto-disposal-accuracy`。
- 是否与打标率、质检准确率、底线事故数或人工审核准确率混淆。
- 分析型任务是否有明确 `time_window`；若为 `auto_disposal_root_label_accuracy_breakdown` 或 `auto_disposal_alert_grading` 且用户未指定日期，可使用默认 T-1 / 最近闭合周口径。
- 用户指定维度是否在本场景列举范围内。
- 是否要求 SQL 执行、真实通知、自动拉群、线上写状态或敏感明细导出。
- 通知 / 闭环请求是否已有前置分析或 tracking 产物。

状态规则:

- `ready`: 场景、任务、必要时间窗口和维度均明确，或命中具备默认 T-1 / 最近闭合周口径的一级风险标签拆解、预警分级，且无越权动作。
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
- `看一下自动处置准确率 P0/P1/P2 预警。` -> `task_type=auto_disposal_alert_grading`
- `看一下昨天一级风险标签维度的自动处置准确率。` -> `task_type=auto_disposal_root_label_accuracy_breakdown`
- `三级标签准确率按一级风险标签拆一下。` -> `task_type=auto_disposal_root_label_accuracy_breakdown`
- `按三级标签维度看自动处置准确率。` -> `task_type=dimension_breakdown`
- `自动处置准确率预警应该找谁？` -> 命中本场景；若缺少分析产物，不直接进入通知

反例:

- `近 7 天有哪些低打标 reason？` -> 不命中本场景，候选为 `efficiency-label-rate`
- `质检准确率下降了。` -> 不命中本场景
- `底线事故数上升了。` -> 不命中本场景
- `直接群发自动处置预警并把状态写成已处理。` -> `blocked`
