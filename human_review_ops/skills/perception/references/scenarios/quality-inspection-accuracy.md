# 感知场景：质量领域 / 质检准确率

## 场景标识

- `scenario_key`: `quality-inspection-accuracy`
- 模块: 质量领域
- 指标对象: 质检准确率
- 当前已接入子指标: 大盘（不含举报）质检准确率
- 待补子指标: 风险域维度质检准确率、举报质检准确率
- 逻辑主指标: `quality_inspection_accuracy`
- 数据集主指标字段: `审核准确率`
- 相关指标: `pass_accuracy`, `label_accuracy`, `inspection_sample_cnt`, `inspection_error_cnt`
- 运营对象: 队列分类汇总、队列分类（上游+群组）下的质检准确率表现

## 触发与排除

应触发:

- 用户询问质检准确率、审核准确率、通过准确率、打标准确率。
- 用户询问质量领域的准确率波动、目标达成或低于目标。
- 用户要求按队列分类汇总、队列分类（上游+群组）拆解大盘（不含举报）质检准确率。
- 用户要求解释质检方式、质检比例、质检量、置信度和目标线。

应排除:

- 打标率、低打标 reason、P0/P1/P2/notice 低效策略分级。
- 自动处置准确率、三级标签准确率、机审自动处置准确率。
- 底线事故数、人工审核准确率。
- 只要求生成通知、触达 POC、闭环记录或线上写状态。
- 用户要求直接执行 SQL、真实群发、拉群或导出敏感明细。

## 用户意图别名

| 意图 | 常见表达 |
| --- | --- |
| 大盘质检准确率 | 质检准确率、大盘质检准确率、大盘不含举报、审核准确率 |
| 通过准确率 | 通过准确率、通过质检、通过抽检 |
| 打标准确率 | 打标准确率、打标质检、打标抽检 |
| 维度拆解 | 按队列分类汇总、按队列分类、上游+群组 |
| 质量知识解释 | 质检方式、随机质检、交叉质检、质检比例、质检量、置信度、质量目标 |

## 指标与维度别名

| `metric_id` | 别名 | 感知说明 |
| --- | --- | --- |
| `quality_inspection_accuracy` | 质检准确率、审核准确率 | Skill 内部逻辑指标 ID；当前子指标的数据集字段为 `审核准确率`。 |
| `pass_accuracy` | 通过准确率 | 围栏指标；数据集字段为 `通过准确率`。 |
| `label_accuracy` | 打标准确率 | 围栏指标；数据集字段为 `打标准确率`。 |
| `inspection_sample_cnt` | 抽检量、日均抽检量 | 数据集字段为 `抽检量`；日均为派生展示口径。 |
| `inspection_error_cnt` | 审核错误量、日均审核错误量 | 数据集字段为 `审核错误量`；日均为派生展示口径。 |

| 维度 | 别名 | 感知说明 |
| --- | --- | --- |
| `date` / `time_window` | 日期分区、统计日期、近 N 天 | 分析型任务必需。 |
| `queue_category_summary` | 队列分类汇总 | 当前已接入维度。 |
| `queue_category_group` | 队列分类、队列分类（上游+群组） | 当前已接入维度。 |
| `quality_mode` | 质检模式 | 必筛项，当前默认 `抽检模式`。 |
| `video_quality_scope` | 视频质量_队列范围、大盘安全、大盘画风 | 必筛项，当前默认 `【大盘】安全`、`【大盘】画风`。 |
| `exclude_flag` | 抽检质量-是否剔除 | 必筛项，默认不包含 `剔除`。 |

未列举维度不得猜字段；需澄清或要求字段发现。

## `task_type` 判定规则

- `quality_market_no_report_accuracy`: 命中大盘（不含举报）质检准确率、队列分类拆解、审核准确率。
- `quality_inspection_trend`: 命中趋势、波动、环比、目标达成。
- `dimension_breakdown`: 用户要求按当前已治理维度拆解。
- `notification_request`: 用户要求通知、卡片、触达、群发或 POC 路由。
- `resolution_tracking`: 用户要求闭环、跟进、状态、关闭或 tracking。
- `unknown`: 无法唯一识别任务类型。

## Readiness 检查

必须检查:

- 场景是否唯一命中 `quality-inspection-accuracy`。
- 是否与打标率、自动处置准确率、底线事故数或人工审核准确率混淆。
- 是否明确为已接入的“大盘（不含举报）”子指标；风险域维度和举报质检准确率暂未接入。
- 分析型任务是否有明确 `time_window`。
- 用户指定维度是否在本场景列举范围内。
- 是否要求 SQL 执行、真实通知、自动拉群、线上写状态或敏感明细导出。

状态规则:

- `ready`: 场景、子指标、任务、必要时间窗口和维度均明确，且无越权动作。
- `needs_clarification`: 缺少时间窗口、子指标、任务类型或维度确认。
- `blocked`: 命中相邻指标、要求越权动作或存在敏感数据风险。

## Handoff 规则

- 分析型任务且 `readiness.status=ready`: `next_skill=analysis`。
- 通知请求且已有分析产物: `next_skill=notification`。
- 闭环请求且已有通知或 tracking 产物: `next_skill=resolution`。
- 其他情况不交接，先输出澄清字段或阻断原因。

感知阶段交接 reference 只指向本单场景文档:

- `references/scenarios/quality-inspection-accuracy.md`

## 阻断条件

- `scenario_not_recognized`
- `excluded_adjacent_metric:<scenario_key>`
- `unsupported_quality_submetric`
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

- `看一下大盘不含举报的质检准确率。` -> `scenario_key=quality-inspection-accuracy`, `task_type=quality_market_no_report_accuracy`
- `按队列分类汇总拆一下审核准确率。` -> `task_type=quality_market_no_report_accuracy`
- `解释一下质检准确率、通过准确率和打标准确率。` -> 命中本场景，可输出口径解释

反例:

- `近 7 天有哪些低打标 reason？` -> 不命中本场景，候选为 `efficiency-label-rate`
- `自动处置准确率下降了。` -> 不命中本场景，候选为 `efficiency-auto-disposal-accuracy`
- `底线事故数上升了。` -> 不命中本场景
- `直接群发质检预警并把状态写成已处理。` -> `blocked`
