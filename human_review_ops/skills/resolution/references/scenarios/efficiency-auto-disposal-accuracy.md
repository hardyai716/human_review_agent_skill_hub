# 场景：效率模块 / 自动处置准确率解决闭环

## 场景元信息

| 项 | 内容 |
| --- | --- |
| `scenario_key` | `efficiency-auto-disposal-accuracy` |
| 主指标 | `auto_disposal_accuracy` / 自动处置准确率 |
| 解决阶段职责 | 记录人工状态、建议 Owner、闭环检查、继续观察和升级建议 |
| 当前状态 | 调试态场景，数据源、Owner 和正式 SLA 仍需业务确认 |
| 默认运行模式 | `local_debug_only` |
| 线上副作用 | 禁止真实触达、禁止写线上状态、禁止更新工单或数据库 |

## 输入产物要求

解决阶段只消费前置阶段产物，不重新查数、不生成通知内容。

必需输入：

- `analysis_result`：包含自动处置准确率趋势、维度拆解、候选根因、source_footer。
- `notification_draft` 或人工同步记录：如已进入通知阶段，需提供草稿、建议 Owner 和发送门禁。
- `send_plan`：如存在触达计划，必须显式给出是否需要确认、是否阻断、是否已发送。
- `current_state`：通常为 `ANALYSIS_READY` 或 `NOTIFICATION_DRAFTED`。
- `manual_action`：人工动作或待动作说明，例如确认 Owner、要求复盘、继续观察。

可选输入：

- `manual_response`：Owner 或运营同学回复。
- `evidence_refs`：分析结果、source_footer、通知草稿、send_plan、报表、人工回复等引用。
- `resolution_note`：处理结论。
- `follow_up_due`：建议复查时间。
- `operator`：记录人。

数据源、字段或样本池未确认时，不能输出 high 置信闭环结论。

## 状态机

调试态状态：

```text
INTAKE
SCENARIO_RESOLVED
PERCEPTION_READY
ANALYSIS_READY
NOTIFICATION_DRAFTED
MANUAL_TRACKING_RECORDED
DEBUG_CLOSED_AFTER_MANUAL_REVIEW
NEED_MORE_INFO
DATA_NOT_READY
PERMISSION_BLOCKED
HUMAN_REVIEW_REQUIRED
STOPPED_NO_CONCLUSION
```

最小流转：

```text
INTAKE
  -> SCENARIO_RESOLVED
  -> PERCEPTION_READY
  -> ANALYSIS_READY
  -> DEBUG_CLOSED_AFTER_MANUAL_REVIEW
```

通知后跟踪流转：

```text
ANALYSIS_READY
  -> NOTIFICATION_DRAFTED
  -> MANUAL_TRACKING_RECORDED
  -> DEBUG_CLOSED_AFTER_MANUAL_REVIEW
```

阻断条件：

- 场景置信度不足。
- 指标口径缺失。
- 数据集字段冲突。
- 数据源、字段或样本池未治理确认。
- 权限策略不允许。
- 输出缺少 QueryPlan 或 source_footer。
- 用户要求真实触达、线上写状态或处罚类动作。

## 闭环三件套

关闭前必须同时具备：

- 动作：已经采取或明确决定的人工动作，例如“已指定策略 Owner 复核自动处置准确率下降原因”。
- 证据：分析结果、source_footer、样本池说明、Owner 建议、人工回复或通知门禁。
- 结论：是否误报、是否继续观察、是否升级、是否已完成治理动作。

任一缺失时：

- `closure_check.can_close=false`
- `overall_status=pending_manual_confirmation`
- `missing_before_close` 列出缺失项
- `follow_up` 给出下一步、建议响应时间和复查条件

## Manual Tracking

本场景 manual tracking 用于记录建议 Owner 和人工处理结果，不自动触达。

最小结构：

```json
{
  "schema_version": "resolution_manual_tracking.v1",
  "scenario_key": "efficiency-auto-disposal-accuracy",
  "tracking_mode": "local_debug_only",
  "state_machine": {
    "state_machine_ref": "references/scenarios/efficiency-auto-disposal-accuracy.md#状态机",
    "previous_state": "ANALYSIS_READY",
    "current_state": "MANUAL_TRACKING_RECORDED",
    "next_state": "DEBUG_CLOSED_AFTER_MANUAL_REVIEW"
  },
  "overall_status": "pending_manual_confirmation",
  "continue_observation": true,
  "owner_recommendation": {},
  "closure_check": {
    "can_close": false,
    "missing_before_close": []
  },
  "safety": {
    "requires_confirmation": true,
    "real_group_send_executed": false,
    "online_write_executed": false,
    "online_state_write_allowed": false
  }
}
```

记录原则：

- `tracking_mode` 固定为 `local_debug_only`。
- Owner 只记录建议值、命中依据和置信度；低置信度时转人工指定。
- 数据源、字段或样本池未确认时，必须设置 `continue_observation=true`。
- 每条记录必须包含证据来源，不得只写“已处理”。
- 未获得人工动作、证据和结论前，不得关闭。

## Owner 路由

路由优先级：

1. 策略 Owner。
2. 队列 Owner。
3. 数据 Owner。
4. 业务模块 Owner。
5. 人审运营兜底 Owner。

输出要求：

- 输出建议 Owner。
- 输出命中依据。
- 输出置信度：`high` / `medium` / `low`。
- 低置信度时转人工指定。

调试阶段约束：

- 不真实触达 Owner。
- 不创建群聊。
- 不自动发送消息。
- 只输出建议路由、证据和人工确认要求。

## SLA、继续观察与升级

调试阶段：

- 查询分析：当次会话内完成。
- 责任人定位：当次会话内完成。
- 通知草稿：当次会话内完成。
- 人工处理记录：当次会话内完成。
- 不触发自动催办和自动升级。

目标阶段待业务确认：

- P2 预警响应时限。
- P1 预警响应时限。
- 结论回收时限。

继续观察规则：

- 数据源、字段或样本池仍需治理确认时继续观察。
- Owner 置信度为 `low` 或只有角色级建议时继续观察。
- 已有分析证据但缺少 Owner 回复或治理结论时继续观察。
- 分母过小、分区不完整或字段冲突时继续观察，不输出强结论。

升级规则：

- 自动处置准确率连续多轮下降，且样本池和字段已确认，可建议升级给业务模块 Owner。
- 低置信度 Owner 超过人工确认时限仍无人确认，建议升级给人审运营兜底 Owner。
- 用户要求正式通报、处罚、资源调整或线上写状态时，进入 `HUMAN_REVIEW_REQUIRED`。

## 关闭条件

可以输出本地调试关闭建议的条件：

- 指标口径、数据源、字段、样本池和 source_footer 均已确认。
- Owner 建议有明确命中依据，并获得人工确认。
- 动作、证据、结论三件套完整。
- `online_write_executed=false` 且 `online_state_write_allowed=false`。
- 不涉及真实触达、处罚、资源调整或线上状态写入。

不得关闭的情况：

- 缺少动作、证据或结论。
- 数据源、字段或样本池未确认。
- Owner 置信度为 `low` 且无人确认。
- 只有分析结论，没有人工处理动作。
- 用户要求线上关闭、工单回写、数据库更新或自动触达。

## 失败处理

- 指标口径不明确：停止，要求确认分子和分母。
- 数据源未确认：停止，输出待确认数据源和 Owner。
- 字段映射失败：停止，列出缺失字段。
- 分母为 0：输出质量风险，不给强结论。
- 查询失败：输出错误、QueryPlan、source_footer 和下一步修复建议。
- 缺少人工动作：关闭检查失败，要求补充处理动作。
- 缺少证据引用：关闭检查失败，要求补充分析、通知、报表或回复证据。
- 缺少处理结论：关闭检查失败，保持继续观察。
- 用户要求线上写入或自动关闭：进入 `HUMAN_REVIEW_REQUIRED`，不执行写入。

## 正反例

正例：记录人工处理

```text
自动处置准确率下降的分析结果已经出来了，Owner 还没确认，帮我记录处理状态并判断是否继续观察。
```

期望：

- 命中 `efficiency-auto-disposal-accuracy`。
- 输出 `MANUAL_TRACKING_RECORDED`。
- `closure_check.can_close=false`。
- `continue_observation=true`。
- 不真实触达 Owner，不写线上状态。

正例：已人工处理但等待复查

```text
策略 Owner 已确认会调整自动处置策略，先记录动作和证据，等下个周期复查。
```

期望：

- 记录人工动作和证据。
- 因复查结论未产生，保持继续观察。
- 输出复查条件和建议时间。

正例：误报归档

```text
自动处置准确率下降是样本池口径变更导致的误报，数据 Owner 已确认，帮我记录调试闭环。
```

期望：

- 若动作、证据、结论完整，可输出本地调试关闭建议。
- 安全字段仍保持 `online_write_executed=false`。

反例：打标率

```text
近 7 天低打标率 reason 有哪些，帮我闭环。
```

期望：

- 不使用本场景；应使用 `efficiency-label-rate`。

反例：线上关闭

```text
把自动处置准确率预警直接关闭线上状态。
```

期望：

- 进入 `HUMAN_REVIEW_REQUIRED`。
- 不执行写入。

低信息量：

```text
这个策略怎么了？
```

期望：

- 要求补充指标、时间窗口、策略 / 队列范围和前置产物。
- 不生成最终闭环结论。
