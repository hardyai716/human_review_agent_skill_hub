# 状态机：打标率

## 调试状态

```text
INTAKE
  -> SCENARIO_RESOLVED
  -> PERCEPTION_READY
  -> QUERY_PLAN_READY
  -> ANALYSIS_READY
  -> OWNER_SUGGESTED
  -> NOTIFICATION_DRAFTED
  -> MANUAL_TRACKING_RECORDED
  -> DEBUG_CLOSED
```

## 异常状态

```text
NEED_MORE_INFO
DATA_NOT_READY
PERMISSION_BLOCKED
HUMAN_REVIEW_REQUIRED
STOPPED_NO_CONCLUSION
```

## 状态说明

| 状态 | 含义 | 输出 |
| --- | --- | --- |
| `INTAKE` | 接收用户问题 | 原始输入 |
| `SCENARIO_RESOLVED` | 命中打标率场景 | `scenario_key` |
| `PERCEPTION_READY` | 识别任务类型、指标、时间窗口和维度 | `task_type`、`metric_id`、`dimensions` |
| `QUERY_PLAN_READY` | 生成 QueryPlan | QueryPlan |
| `ANALYSIS_READY` | 完成趋势、分级或维度拆解分析 | 分析摘要、evidence |
| `OWNER_SUGGESTED` | 生成 Owner 建议 | Owner 依据、置信度 |
| `NOTIFICATION_DRAFTED` | 生成通知草稿 | 草稿文本 |
| `MANUAL_TRACKING_RECORDED` | 记录人工处理状态 | manual tracking |
| `DEBUG_CLOSED` | 调试闭环 | 调试结论 |

## 流转规则

- 用户只问趋势：`QUERY_PLAN_READY -> ANALYSIS_READY -> DEBUG_CLOSED`。
- 用户问低打标率策略分级或风险域预警：`QUERY_PLAN_READY -> ANALYSIS_READY -> OWNER_SUGGESTED`。
- 用户问举报场景低打标率或 `enpool_reason`：仍命中 `efficiency-label-rate`，但必须在 `PERCEPTION_READY` 和 `QUERY_PLAN_READY` 中保留 `data_direction=report_flow`、`source_profile=report_flow_review`。
- 用户问高打标率或普通趋势：`QUERY_PLAN_READY -> ANALYSIS_READY -> DEBUG_CLOSED`。
- 用户要求通知：必须先 `OWNER_SUGGESTED`，再 `NOTIFICATION_DRAFTED`。
- 口径、时间窗口或指标不明确：进入 `NEED_MORE_INFO`。
- 数据未就绪：进入 `DATA_NOT_READY`，不得输出低效结论。
- 权限不足：进入 `PERMISSION_BLOCKED`。
- QueryPlan 通过且工具权限为只读时，可以进入只读查询执行。
- 真实通知、线上写状态、覆盖样本池、未治理字段、禁用来源或高风险动作：进入 `HUMAN_REVIEW_REQUIRED`。
