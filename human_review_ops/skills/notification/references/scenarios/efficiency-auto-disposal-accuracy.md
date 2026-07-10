# 通知场景：自动处置准确率

## 定位

本场景用于在 `efficiency-auto-disposal-accuracy` 分析完成后，生成自动处置准确率异常的调试态通知草稿、Owner 路由建议、发送门禁说明和 SLA 建议。通知 Skill 只生成触达前产物，不真实发送、不自动催办、不写线上状态。

## 输入产物要求

必需输入：

- `scenario_key=efficiency-auto-disposal-accuracy`。
- 分析结果包含风险等级、时间窗口、核心结论和证据引用。
- 存在可解释的异常指标、策略或队列维度。
- 存在 `source_footer` 或等价来源说明。

建议字段：

- `risk_level`：异常等级。
- `time_range`：分析窗口。
- `summary`：核心结论。
- `evidence_refs`：策略、队列、样本、指标或报表证据。
- `owner_candidates`：上游分析或用户提供的 Owner 候选。

## Owner 路由

Owner 建议按以下优先级生成：

1. 策略 Owner。
2. 队列 Owner。
3. 数据 Owner。
4. 业务模块 Owner。
5. 人审运营兜底 Owner。

调试阶段只输出建议 Owner 和路由依据。没有无歧义 open_id、目标群和人工确认时，不得真实触达。

## 通知模板

```text
[调试] 自动处置准确率异常分析

场景：自动处置准确率
等级：{risk_level}
时间窗口：{time_range}
核心结论：{summary}
建议 Owner：{owner}
Owner 依据：{routing_evidence}
证据：{evidence_refs}
下一步动作：请人工确认是否需要正式触达。

说明：
- 本通知为调试草稿，未真实发送。
- 真实触达前必须确认接收人、目标群、正文和附件。
- 当前不会自动催办，也不会写入线上状态。
```

人工确认草稿：

```text
[需人工确认] 自动处置准确率通知门禁

触发原因：{review_reason}
待确认事项：
1. 异常口径和时间窗口是否确认。
2. Owner 路由是否准确。
3. 是否已解析无歧义 open_id 或目标群。
4. 是否允许在通知 Skill 外进入真实发送审批。

当前只生成草稿和 send_plan，不执行真实发送。
```

## send_plan 门禁

默认发送计划必须保持：

```json
{
  "send_mode": "preview_only",
  "default_recipient": "self",
  "requires_confirmation": true,
  "group_send_blocked": true,
  "group_send_allowed": false,
  "group_recipients": [],
  "sent": false,
  "real_group_send_executed": false,
  "online_write_executed": false
}
```

进入真实发送审批前必须满足：

- 用户明确确认发送对象、目标群、正文和附件。
- Owner 已解析到无歧义 open_id，或目标群已唯一确认。
- 发送身份、权限和内容已人工复核。
- 通知内容与当前分析证据一致。

## SLA 与升级话术

调试阶段建议：

- 查询分析：当次会话内完成。
- 责任人定位：当次会话内完成。
- 通知草稿：当次会话内完成。

调试阶段不触发自动催办和自动升级。需要升级时使用：

```text
[自动处置准确率升级建议｜{risk_level}]
{time_range} 自动处置准确率出现异常：{summary}
建议 Owner：{owner}；证据：{evidence_refs}
请人工确认责任归属和处理计划。当前仍为调试草稿，未真实发送。
```

## 失败处理

- 缺少 `scenario_key` 或场景不匹配：停止，交回感知或分析阶段确认。
- 缺少风险等级、时间窗口、核心结论或证据：停止，要求补齐分析结果。
- Owner 只能定位到角色级占位：保留低置信度标记，只允许 `self` 预览。
- 缺少 open_id 或目标群：保持 `requires_confirmation=true` 和 `group_send_blocked=true`。
- 用户要求直接群发、拉群、自动催办或写状态：拒绝执行，输出门禁失败原因。

## 正反例

正例：

```text
基于 efficiency-auto-disposal-accuracy 的异常分析结果，生成调试通知草稿和 Owner 路由建议，不要真实发送。
```

期望：

- 读取 `references/scenarios/efficiency-auto-disposal-accuracy.md`。
- 输出通知草稿、Owner 路由依据和阻断态 `send_plan`。
- `sent=false`、`group_send_blocked=true`、`online_write_executed=false`。

反例：

```text
把自动处置准确率异常直接发到治理群，并自动催办 Owner。
```

处理：

- 不发送、不催办、不写状态。
- 输出缺少人工确认、目标群和权限门禁的阻断原因。
