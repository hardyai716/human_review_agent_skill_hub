# 感知场景：效率模块 / 打标率

## 场景标识

- `scenario_key`: `efficiency-label-rate`
- 模块: 效率模块
- 指标对象: 打标率
- 主指标: `label_rate`
- 相关证据指标: `review_in_cnt`, `review_done_cnt`, `label_cnt`
- 运营对象: 送审原因 / reason 在不同维度下的打标率表现

## 触发与排除

应触发:

- 用户询问打标率、进审量、完审量、打标量的趋势、排序、对比或拆解。
- 用户询问高打标率或低打标率策略 / reason。
- 用户要求按机审一级标签、策略 ID、策略名称、送审原因、审核场景或项目标题拆解打标率。
- 用户提到 notice / P2 / P1 / P0 低效策略清单，且语境是打标率或低打标 reason。
- 用户要求先判断是否具备只读分析条件或应交给哪个 Skill。

应排除:

- 自动处置准确率、质检准确率、底线事故数等相邻指标。
- 只要求生成飞书通知、卡片、POC 路由或 send_plan，且已有分析结果。
- 只要求 manual tracking、状态流转、关闭事件或线上写状态。
- 审核员个人明细、手机号、open_id 等敏感明细导出。
- 用户要求直接跑线上 SQL、群发、拉群、写线上状态等越权动作。

## 用户意图别名

| 意图 | 常见表达 |
| --- | --- |
| 低打标分级 | 低打标、低效策略、低打标 reason、P0/P1/P2/notice、分级 |
| 趋势查询 | 趋势、环比、同比、波动、变化、近 N 天打标率 |
| 排名排序 | 最高、最低、Top、排行、排名、高打标 |
| 维度拆解 | 按机审一级标签、按策略、按 reason、按场景、按项目拆 |
| 通知请求 | 通知、飞书、卡片、群发、触达、POC、send_plan |
| 闭环请求 | 闭环、跟进、状态、关闭、tracking、工单 |

## 指标与维度别名

| `metric_id` | 别名 | 感知说明 |
| --- | --- | --- |
| `label_rate` | 打标率、label rate、label_rate | 主指标；口径冲突时阻断并要求确认分子、分母和样本池。 |
| `review_in_cnt` | 进审量、进入人审 | 证据指标。 |
| `review_done_cnt` | 完审量、完成人审 | 打标率分母相关证据指标。 |
| `label_cnt` | 打标量 | 打标率分子相关证据指标。 |

| 维度 | 别名 | 感知说明 |
| --- | --- | --- |
| `reason` | 送审原因、reason | 默认主实体。 |
| `p_date` / `time_window` | 日期、时间窗口、近 N 天 | 分析型任务必需。 |
| `mach_root_label_name` | 机审一级标签、机审标签、一级标签 | 常用拆解维度。 |
| `strategy_id` | 策略 ID、规则 ID、strategy_id | 常用拆解维度。 |
| `strategy_name` | 策略名称、规则名称、strategy_name | 常用拆解维度。 |
| `scene` | 审核场景、scene | 常用拆解维度。 |
| `project_title` | 项目标题、项目、project_title | 常用拆解维度。 |

未列举维度不得猜字段；将 `human_confirmation_required` 置为 `true`，并把 `dimension_hint` 放入澄清字段。

## `task_type` 判定规则

- `notification_request`: 命中通知、卡片、群发、触达、POC、send_plan 等表达。
- `resolution_tracking`: 命中闭环、跟进、状态、已处理、关闭、tracking、工单等表达。
- `low_label_rate_grading`: 命中低打标、低效、分级、P0、P1、P2、notice 等表达。
- `label_rate_trend`: 命中趋势、环比、同比、波动、变化，或只笼统询问打标率。
- `label_rate_ranking`: 命中最高、最低、Top、排序、排行、排名、高打标等表达。
- `dimension_breakdown`: 用户明确要求按已治理维度拆解，但未命中以上更具体任务。
- `unknown`: 无法唯一识别任务类型。

若同时命中通知 / 闭环与分析意图，优先识别为通知 / 闭环请求，并检查是否已有前置分析产物。

## Readiness 检查

必须检查:

- `raw_user_request` 是否存在。
- 场景是否唯一命中 `efficiency-label-rate`。
- `task_type` 是否可识别。
- 分析型任务是否有 `time_window`。
- 用户指定维度是否在本场景列举范围内。
- 是否存在指标口径冲突、样本池覆盖、未治理字段或权限风险。
- 是否要求 SQL 执行、真实通知、自动拉群、线上写状态或敏感明细导出。
- 通知 / 闭环请求是否提供 `source_refs` 指向前置分析、通知或 tracking 产物。
- 本 Skill 内部 reference 是否齐全。

状态规则:

- `ready`: 场景、任务、必要时间窗口和维度均明确，且无越权动作。
- `needs_clarification`: 需要补充时间窗口、任务类型、指标或维度，但未触发高风险动作。
- `blocked`: 命中相邻场景、缺少内部 reference、要求越权动作或存在明确权限 / 敏感数据风险。

## Handoff 规则

- 分析型任务且 `readiness.status=ready`: `next_skill=analysis`。
- 通知请求且已有分析产物: `next_skill=notification`。
- 闭环请求且已有通知或 tracking 产物: `next_skill=resolution`。
- `needs_clarification` 或 `blocked`: `next_skill=null`，只输出 `candidate_next_skill` 和待补齐字段。

感知阶段交接 reference 只指向本单场景文档:

- `references/scenarios/efficiency-label-rate.md`

## 阻断条件

- `scenario_not_recognized`
- `excluded_adjacent_metric:<scenario_key>`
- `task_type_not_clear`
- `missing_time_window`
- `missing_analysis_artifact`
- `missing_notification_or_tracking_source`
- `unsupported_dimension_requires_field_discovery`
- `sql_execution_requested`
- `real_group_send_requested`
- `auto_group_invite_requested`
- `online_write_requested`
- `sensitive_detail_export_requested`
- `sample_pool_override_requested`
- `missing_reference_files`

## 正反例

正例:

- `近 7 天有哪些高完审低打标的 reason？` -> `scenario_key=efficiency-label-rate`, `task_type=low_label_rate_grading`
- `近 7 天打标率最高的策略有哪些？` -> `scenario_key=efficiency-label-rate`, `task_type=label_rate_ranking`
- `帮我看下近 7 天低打标率策略分 P0/P1/P2/notice 的情况。` -> `task_type=low_label_rate_grading`
- `按机审一级标签拆一下打标率。` -> `task_type=dimension_breakdown`, 若缺少时间窗口则 `needs_clarification`

反例:

- `分析一下自动处置准确率为什么下降。` -> 不命中本场景，候选为 `efficiency-auto-disposal-accuracy`
- `质检准确率下降了。` -> 不命中本场景
- `底线事故数上升了。` -> 不命中本场景
- `直接跑线上 SQL 并群发给所有运营群。` -> `blocked`
- `按业务线看打标率。` -> 未治理维度，需字段发现或人工确认
