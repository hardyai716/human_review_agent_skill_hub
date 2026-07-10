# 场景：效率模块 / 打标率解决闭环

## 场景元信息

| 项 | 内容 |
| --- | --- |
| `scenario_key` | `efficiency-label-rate` |
| 主指标 | `label_rate` / 打标率 |
| 解决阶段职责 | 记录人工处理状态、闭环检查、继续观察和升级建议 |
| 默认运行模式 | `local_debug_only` |
| 线上副作用 | 禁止真实群发、禁止写线上状态、禁止更新工单或数据库 |

## 输入产物要求

解决阶段只消费前置阶段产物，不重新查数、不生成通知内容。

必需输入：

- `analysis_result` 或等价分析摘要：包含低打标率分级、证据字段、source_footer。
- `notification_draft`：通知草稿，包含 `scenario_key`、`level_counts`、数据链接、POC 路由规则。
- `send_plan`：发送计划，必须显式给出 `requires_confirmation`、`group_send_blocked`、`sent`、`real_group_send_executed`。
- `current_state`：通常为 `NOTIFICATION_DRAFTED`，若缺失则按“已生成通知草稿但未真实发送”处理。
- `manual_action`：人工动作或待动作说明，例如确认 POC、要求复盘、继续观察。

可选输入：

- `manual_response`：POC 或运营同学回复。
- `evidence_refs`：分析结果、source_footer、卡片哈希、报表、草稿、send_plan、人工回复等引用。
- `resolution_note`：处理结论。
- `follow_up_due`：建议复查时间。
- `operator`：记录人。

缺少 `notification_draft` 或 `send_plan` 时停止；缺少人工动作、证据或结论时不得关闭。

## 状态机

调试态主路径：

```text
INTAKE
  -> SCENARIO_RESOLVED
  -> PERCEPTION_READY
  -> QUERY_PLAN_READY
  -> ANALYSIS_READY
  -> OWNER_SUGGESTED
  -> NOTIFICATION_DRAFTED
  -> MANUAL_TRACKING_RECORDED
  -> DEBUG_CLOSED_AFTER_MANUAL_REVIEW
```

异常状态：

```text
NEED_MORE_INFO
DATA_NOT_READY
PERMISSION_BLOCKED
HUMAN_REVIEW_REQUIRED
STOPPED_NO_CONCLUSION
```

| 状态 | 含义 | 解决阶段处理 |
| --- | --- | --- |
| `NOTIFICATION_DRAFTED` | 已生成通知草稿和发送计划 | 可进入 manual tracking，但不得当作已发送 |
| `MANUAL_TRACKING_RECORDED` | 已记录本地人工跟踪 | 输出状态、证据、下一步和关闭检查 |
| `DEBUG_CLOSED_AFTER_MANUAL_REVIEW` | 调试闭环建议 | 仅代表本地调试闭环，不代表线上关闭 |
| `NEED_MORE_INFO` | 口径、窗口、Owner、人工动作或结论缺失 | 要求补充信息 |
| `DATA_NOT_READY` | 分区或分析产物不可用 | 不输出业务闭环结论 |
| `PERMISSION_BLOCKED` | 权限不足 | 停止并记录阻断原因 |
| `HUMAN_REVIEW_REQUIRED` | 真实发送、线上写状态或高风险动作 | 转人工审批，不执行写入 |
| `STOPPED_NO_CONCLUSION` | 证据不足或无明确结论 | 保持观察 |

流转规则：

- 用户只问趋势：`QUERY_PLAN_READY -> ANALYSIS_READY -> DEBUG_CLOSED_AFTER_MANUAL_REVIEW`，不进入 manual tracking。
- 用户要求通知后跟踪：必须先到 `NOTIFICATION_DRAFTED`，再进入 `MANUAL_TRACKING_RECORDED`。
- `send_plan.sent=false` 或 `group_send_blocked=true` 时，不得写“已通知完成”。
- 真实通知、线上写状态、覆盖样本池、未治理字段、禁用来源或处罚类动作，进入 `HUMAN_REVIEW_REQUIRED`。
- 只有动作、证据、结论三件套完整，且不涉及线上写入时，才能输出本地调试关闭建议。

## 闭环三件套

关闭前必须同时具备：

- 动作：已经采取或明确决定的处理动作，例如“已确认 POC 并要求复盘”。
- 证据：分析结果、source_footer、通知草稿、send_plan、卡片哈希、POC 回复或人工备注。
- 结论：是否误报、是否继续观察、是否升级、是否已完成治理动作。

任一缺失时：

- `closure_check.can_close=false`
- `overall_status=pending_manual_confirmation`
- `missing_before_close` 列出缺失项
- `follow_up` 给出下一步、建议响应时间和复查条件

## Manual Tracking

输出 schema 使用 `stage_2_manual_tracking.v1`。

最小结构：

```json
{
  "schema_version": "stage_2_manual_tracking.v1",
  "scenario_key": "efficiency-label-rate",
  "report_type": "low_efficiency_grading",
  "tracking_mode": "local_debug_only",
  "state_machine": {
    "state_machine_ref": "references/scenarios/efficiency-label-rate.md#状态机",
    "previous_state": "NOTIFICATION_DRAFTED",
    "current_state": "MANUAL_TRACKING_RECORDED",
    "next_state": "DEBUG_CLOSED_AFTER_MANUAL_REVIEW"
  },
  "overall_status": "pending_manual_confirmation",
  "continue_observation": true,
  "tracking_records": [],
  "closure_check": {
    "can_close": false,
    "missing_before_close": []
  },
  "safety": {
    "requires_confirmation": true,
    "group_send_blocked": true,
    "group_send_sent": false,
    "real_group_send_executed": false,
    "online_write_executed": false,
    "online_state_write_allowed": false
  }
}
```

记录原则：

- `tracking_mode` 固定为 `local_debug_only`。
- `tracking_records` 默认覆盖 `notice`、`P2`、`P1`、`P0`。
- 每条记录包含 `severity_level`、`status`、`reason_count`、`target_roles`、`action_required`、`recipient_resolution`、`evidence_refs`、`next_action`。
- POC 只有姓名级映射时，状态保持 `pending_manual_follow_up`。
- 未确认 open_id、目标群、真实响应和处理结论前，不得关闭。
- 每条记录必须写证据来源，不得只写主观结论。

## POC / Owner 路由

本场景解决阶段只记录建议 Owner 和人工处理结果，不自动触达。

路由原则：

- POC 路由粒度：优先按 `mach_root_label_name` 映射 POC；`reason`、`strategy_id`、`strategy_name` 作为证据字段保留。
- 映射来源：飞书表格 `https://bytedance.larkoffice.com/sheets/TpxwsA8zohUZkVtJ4J9cDcXUnbg?sheet=HKdm9w`。
- 当前身份粒度：仅完成 POC 姓名映射，`poc_open_id` 尚未解析。
- 默认收件人：缺少 `mach_root_label_name` 或标签未映射时，开发验证阶段 fallback 到用户本人，即 `default_recipient=self`。
- 群推送：不自动群发，真实触达前必须人工确认目标群和 POC 收件人。
- 回收闭环：暂不做联系人回复收集、卡片按钮回调或结果回收。

机审一级标签 POC 映射：

| 机审一级标签 | POC |
| --- | --- |
| 国家安全 | 杜衡 |
| 领导人 | 宋诗慧 |
| 指令舆情相关 | 张发奇 |
| 偏激社会情绪和涉外言论 | 张发奇 |
| 党和国家形象负面 | 李中涛 |
| 举报 | 韩晶晶 |
| 不良行为或争议价值观 | 陈雅静 |
| 色情性化 | 刘小楷 |
| 高热 | 闫秦河 |
| 侵犯未成年权益 | 张宇轩 |
| 引人不适 | 陈思乔 |
| 短期策略迁移 | 陈思乔 |
| 危险行为 | 陈雅静 |
| 政媒 | 杜衡 |
| 违法违规 | 叶健 |

等级触达规则：

| 等级 | 触达范围 | 动作要求 | 当前处理 |
| --- | --- | --- | --- |
| `notice` | 群内同步策略明细和数据链接 | 周知明细，纳入观察 | 命中 POC 姓名后仍需人工确认 |
| `P2` | 治理 BP、审核 VOC 的 POC 角色、人审运营 | 请相关 POC 说明低打标原因和后续处理计划 | 命中 POC 姓名后仍需人工确认 |
| `P1` | P2 范围 + 治理 BP 的 +1、VOC 负责人、人审运营负责人 | 要求负责人关注，并推动原因说明和处理计划 | 命中 POC 姓名后仍需人工确认 |
| `P0` | P1 范围 + 治理负责人 | 高优先级周知，要求重点关注和处理 | 命中 POC 姓名后仍需人工确认 |

低置信度条件：

- 输入数据只有 reason 名称，没有 `mach_root_label_name`。
- `mach_root_label_name` 未命中 POC 映射。
- POC 只有姓名，尚未解析飞书 open_id。
- 触达角色仍为角色级占位。
- 数据来源 fallback 到 curated raw SQL。
- 用户问题涉及正式汇报、处罚、资源调整或高风险决策。

## SLA、继续观察与升级

调试阶段不启动真实 SLA 计时，只输出建议响应时间和升级条件；真实触达、状态流转和升级必须人工确认。

| 等级 | 响应建议 | 处理建议 | 升级条件 |
| --- | --- | --- | --- |
| `P0` | 当日确认 | 当日完成 Owner 定位和治理方案确认 | 超过 1 个工作日未确认 |
| `P1` | 1 个工作日内确认 | 2 个工作日内给出治理动作 | 连续两轮仍未改善 |
| `P2` | 2 个工作日内确认 | 3 个工作日内完成复盘 | 进审量继续增长或打标率继续下降 |
| `notice` | 周期性观察 | 纳入周报或观察清单 | 连续命中或升级到 P2+ |

继续观察规则：

- `send_plan.sent=false`、`group_send_blocked=true` 或 `real_group_send_executed=false` 时继续观察。
- POC 仅姓名级映射、open_id 未确认或目标群未确认时继续观察。
- 已有动作和证据但缺少 POC 回复或治理结论时继续观察。
- notice 连续命中、P2+ 指标继续下降或进审量继续增长时，输出升级建议。

停止 SLA 条件：

- 数据未就绪。
- 查询失败。
- 口径未确认。
- Owner 置信度为 low 且无人确认。
- 当前只做普通趋势或高打标率查询，不做低打标率治理。

## 关闭条件

可以输出本地调试关闭建议的条件：

- 前置分析、通知草稿和 send_plan 均有证据引用。
- 人工动作、证据、结论三件套完整。
- `send_plan` 状态未被误写：未真实发送时仍记录为未发送。
- `online_write_executed=false` 且 `online_state_write_allowed=false`。
- 不涉及处罚、资源调整、线上状态写入或真实群发。

不得关闭的情况：

- 缺少动作、证据或结论。
- POC 身份、目标群或 open_id 未确认。
- 只有“已生成草稿”，没有真实发送或人工确认。
- 数据未就绪、权限不足或查询失败。
- 用户要求线上关闭、工单回写、数据库更新或自动群发。

## 失败处理

- 缺少 `notification_draft` 或 `send_plan`：停止，要求补齐通知阶段产物。
- `send_plan.sent=false`：不得写“已发送”，只能写“待人工确认”。
- `group_send_blocked=true`：不得推进到真实触达完成状态。
- 缺少人工动作：关闭检查失败，要求补充处理动作。
- 缺少证据引用：关闭检查失败，要求补充分析、通知、报表或回复证据。
- 缺少处理结论：关闭检查失败，保持继续观察。
- Owner 低置信度：要求人工指定或确认 Owner，不自动升级。
- 用户要求线上写入或自动关闭：进入 `HUMAN_REVIEW_REQUIRED`，不执行写入。

## 正反例

正例：记录 manual tracking

```text
基于刚才的低打标率通知草稿和 send_plan，记录一份 manual tracking，当前还没真实群发，只需要本地调试闭环。
```

期望：

- 命中 `efficiency-label-rate`。
- `current_state=MANUAL_TRACKING_RECORDED`。
- `closure_check.can_close=false`，缺失项包含 POC open_id、人工确认或处理结论。
- `continue_observation=true`。
- `online_write_executed=false`。

正例：判断是否升级

```text
P1 低打标率策略已经连续两轮没改善，POC 还没反馈，帮我判断下一步。
```

期望：

- 保持本地记录，不真实催办。
- 输出 P1 升级建议：连续两轮仍未改善时升级。
- 要求补齐 POC 反馈或人工确认。

反例：自动处置准确率

```text
分析一下自动处置准确率为什么下降，并记录闭环。
```

期望：

- 不使用本场景；应使用 `efficiency-auto-disposal-accuracy`。

反例：线上关闭

```text
这批低打标率问题直接关闭线上状态。
```

期望：

- 进入 `HUMAN_REVIEW_REQUIRED`。
- 不写线上状态，不更新工单。

低信息量：

```text
这个策略怎么了？
```

期望：

- 先要求补充指标、时间窗口、策略 / reason 和前置产物。
- 不生成最终闭环结论。
