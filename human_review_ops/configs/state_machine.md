# 人审运营闭环状态机配置

## 1. 状态机目标

状态机用于统一管理从多源问题接入到处理结论回收的全生命周期。它解决三类问题：

- 每个事件当前处于什么阶段。
- 下一步应该由 Agent、运营、数据 Owner 还是升级负责人处理。
- 什么时候需要补信息、人工确认、催办、升级、退回或关闭。

## 2. 状态列表

| 状态编码 | 中文名称 | 状态说明 | 责任方 |
| --- | --- | --- | --- |
| `INTAKE_RECEIVED` | 已接入 | 接收到自然语言、告警、工单、群聊或手工录入。 | Agent |
| `FAST_PATH_HANDLING` | 快路径处理中 | 被判断为简单咨询，尝试知识问答或轻量只读查询。 | Agent |
| `FAST_PATH_CLOSED` | 快路径已完成 | 简单咨询已回答，不进入正式事件闭环。 | Agent |
| `EVENT_CREATED` | 已创建事件 | 输入被转化为正式事件对象。 | Agent |
| `PERCEPTION_COLLECTING` | 感知收集中 | 正在收集事件画像、数据证据、SOP、Owner 和历史案例。 | Agent |
| `NEED_MORE_INFO` | 需要补充信息 | 关键字段或证据不足，无法进入标准分析。 | 运营值班 |
| `ANALYZING` | 分析中 | 正在执行影响评估、归因定位、SOP 判定。 | Agent |
| `HUMAN_REVIEW_REQUIRED` | 等待人工确认 | 命中分级卡点，需要人工确认分析、通知、执行或闭环。 | 运营专家/运营值班 |
| `OWNER_ROUTED` | 已确定责任人 | 已解析数据 Owner、备份人和升级链路。 | Agent |
| `NOTIFIED` | 已通知 | 已向责任人发送通知。 | Agent |
| `WAITING_RESPONSE` | 等待响应 | 正在等待责任人确认收到或认领。 | 数据 Owner |
| `IN_PROGRESS` | 处理中 | 责任人正在处理，或已给出处理计划。 | 数据 Owner |
| `ESCALATED` | 已升级 | SLA 超时、等级触发、重复失败或人工标记导致升级。 | 升级负责人 |
| `RESOLUTION_SUBMITTED` | 已提交处理结果 | 责任人已回填处理动作、证据和结论。 | 数据 Owner |
| `CLOSURE_REVIEW` | 闭环审核中 | 正在确认动作、证据、结论三件套是否完整。 | 运营专家/运营值班 |
| `CLOSED` | 已闭环 | 事件满足闭环标准并沉淀。 | 运营专家/运营值班 |
| `CANCELED` | 已取消 | 误报、重复、非本流程范围或人工取消。 | 运营值班 |

## 3. 主流程

```text
INTAKE_RECEIVED
  -> FAST_PATH_HANDLING
  -> FAST_PATH_CLOSED

INTAKE_RECEIVED
  -> EVENT_CREATED
  -> PERCEPTION_COLLECTING
  -> ANALYZING
  -> HUMAN_REVIEW_REQUIRED
  -> OWNER_ROUTED
  -> NOTIFIED
  -> WAITING_RESPONSE
  -> IN_PROGRESS
  -> RESOLUTION_SUBMITTED
  -> CLOSURE_REVIEW
  -> CLOSED
```

`HUMAN_REVIEW_REQUIRED` 不是所有事件必经状态，是否进入由场景权限和事件等级决定。

## 4. 流转规则

| 起始状态 | 触发条件 | 目标状态 | 守卫条件 | 动作 |
| --- | --- | --- | --- | --- |
| `INTAKE_RECEIVED` | 判断为低风险咨询 | `FAST_PATH_HANDLING` | 不涉及处理、审批、SLA、Owner 跟进 | 调用知识问答或轻量只读查询。 |
| `INTAKE_RECEIVED` | 需要跟进或风险不低 | `EVENT_CREATED` | 需要正式记录和闭环 | 创建统一事件对象。 |
| `FAST_PATH_HANDLING` | 已输出答案 | `FAST_PATH_CLOSED` | 用户未要求跟进，未命中风险阈值 | 记录答案摘要和依据。 |
| `FAST_PATH_HANDLING` | 信息不足或风险升高 | `EVENT_CREATED` | 需要 Owner 处理或持续跟进 | 转正式事件。 |
| `EVENT_CREATED` | 事件对象创建完成 | `PERCEPTION_COLLECTING` | event_id 已生成 | 收集画像、证据、SOP、Owner。 |
| `PERCEPTION_COLLECTING` | 数据就绪为 insufficient | `NEED_MORE_INFO` | 缺少关键字段且无法只读补齐 | 请求运营补信息。 |
| `PERCEPTION_COLLECTING` | 数据就绪为 quick/standard/deep | `ANALYZING` | 有足够证据进入分析 | 调用分析模板。 |
| `NEED_MORE_INFO` | 信息补齐 | `PERCEPTION_COLLECTING` | 关键字段已补充 | 重新感知。 |
| `NEED_MORE_INFO` | 人工判定非本流程 | `CANCELED` | 需要记录取消原因 | 取消事件。 |
| `ANALYZING` | 命中人工卡点 | `HUMAN_REVIEW_REQUIRED` | 场景或等级要求人工确认 | 等待确认。 |
| `ANALYZING` | 无需人工卡点 | `OWNER_ROUTED` | Owner 可解析，分析质量检查通过 | 生成路由。 |
| `HUMAN_REVIEW_REQUIRED` | 人工通过 | `OWNER_ROUTED` | 分析、通知或执行被确认 | 继续流程。 |
| `HUMAN_REVIEW_REQUIRED` | 人工要求补充 | `PERCEPTION_COLLECTING` | 证据或字段不足 | 补充证据。 |
| `HUMAN_REVIEW_REQUIRED` | 人工取消 | `CANCELED` | 误报、重复或非本流程 | 取消事件。 |
| `OWNER_ROUTED` | Owner 已解析 | `NOTIFIED` | 通知模板和必填证据齐全 | 发送通知。 |
| `OWNER_ROUTED` | Owner 缺失 | `HUMAN_REVIEW_REQUIRED` | 兜底失败 | 人工指定 Owner。 |
| `NOTIFIED` | 通知发送成功 | `WAITING_RESPONSE` | 发送状态为 sent | 启动响应 SLA。 |
| `NOTIFIED` | 通知发送失败 | `ESCALATED` | 重试或备用渠道失败 | 通知备份人或升级人。 |
| `WAITING_RESPONSE` | Owner 确认收到 | `IN_PROGRESS` | 响应 SLA 未超时或允许继续 | 启动处理 SLA。 |
| `WAITING_RESPONSE` | 响应 SLA 超时 | `ESCALATED` | 超时触发 | 催办或升级。 |
| `IN_PROGRESS` | 提交处理结果 | `RESOLUTION_SUBMITTED` | 包含动作、证据、结论 | 进入闭环审核。 |
| `IN_PROGRESS` | 处理 SLA 超时 | `ESCALATED` | 超时触发 | 催办或升级。 |
| `ESCALATED` | 升级负责人重新分派 | `OWNER_ROUTED` | 新 Owner 已确定 | 重新通知。 |
| `ESCALATED` | 升级负责人直接处理 | `IN_PROGRESS` | 已认领处理 | 继续处理。 |
| `RESOLUTION_SUBMITTED` | 三件套完整且无需人工复核 | `CLOSED` | 动作完成、证据确认、结论沉淀 | 关闭事件。 |
| `RESOLUTION_SUBMITTED` | 需要闭环审核 | `CLOSURE_REVIEW` | 场景或等级要求复核 | 等待运营确认。 |
| `RESOLUTION_SUBMITTED` | 证据或结论不足 | `IN_PROGRESS` | 三件套不完整 | 退回补充。 |
| `CLOSURE_REVIEW` | 审核通过 | `CLOSED` | 三件套完整 | 关闭并沉淀案例。 |
| `CLOSURE_REVIEW` | 审核退回 | `IN_PROGRESS` | 证据、动作或结论不足 | 要求补充。 |
| `CLOSURE_REVIEW` | 审核认为需升级 | `ESCALATED` | 高风险或处理无效 | 升级。 |

## 5. 快路径规则

快路径适用条件：

- 问题是 SOP、规则、口径或历史结论查询。
- 只需要轻量只读指标查询。
- 不需要通知 Owner。
- 不需要 SLA 跟进。
- 不涉及执行动作、审批或业务状态变更。

必须转事件的条件：

- 结果提示异常或风险。
- 需要责任人处理。
- 信息不足但用户要求跟进。
- 涉及 SLA、升级、审批、执行或闭环。
- Agent 置信度不足。

## 6. 人工卡点

人工卡点按事件等级和场景配置。

| 节点 | 建议触发条件 | 确认内容 |
| --- | --- | --- |
| 分析后 | 高等级事件、低置信度、证据不足 | 分析结论、等级、下一步动作是否合理。 |
| 通知前 | 高风险通知、Owner 不确定、敏感事件 | 通知对象、文案、证据是否正确。 |
| 执行前 | 涉及业务状态、策略、配置、审批 | 动作是否允许、是否需要审批、是否可回滚。 |
| 闭环前 | 高等级事件、处理无效风险、专家抽检 | 动作、证据、结论三件套是否完整。 |

## 7. 升级触发

升级由组合条件触发：

- 响应 SLA 超时。
- 处理 SLA 超时。
- 结论回收 SLA 超时。
- 事件等级达到高等级。
- 同类问题重复发生。
- 多次处理无效。
- 人工标记需要升级。

升级必须记录：

- 触发节点。
- 触发原因。
- 原责任人。
- 升级对象。
- 通知内容。
- 响应时间。
- 后续处理结果。

## 8. 终态要求

### 8.1 `CLOSED`

进入 `CLOSED` 前必须满足：

- 动作完成。
- 证据确认。
- 结论沉淀。
- 如命中迭代触发条件，已写入迭代候选池。

### 8.2 `FAST_PATH_CLOSED`

进入 `FAST_PATH_CLOSED` 前必须满足：

- 输出答案。
- 记录依据。
- 未命中转事件条件。

### 8.3 `CANCELED`

进入 `CANCELED` 前必须记录：

- 取消原因。
- 取消人。
- 是否为重复事件。
- 是否需要补充到规则或快路径判断。
