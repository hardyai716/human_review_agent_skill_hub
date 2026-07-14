# 场景契约

本文件是唯一业务契约。新场景只改这里，避免多份 reference 漂移。

## 1. 场景

- `scenario_key`: `scenario-key`
- 名称：`SCENARIO_NAME`
- 指标：`METRIC_ID`
- 默认模式：`debug_only`

命中：用户询问本场景趋势、排序、阈值分级、维度拆解、通知草稿或本地闭环。

排除：相邻场景、指标不明、时间窗口缺失、真实发送、拉群、写状态、敏感明细导出。

## 2. 感知

输出：

```json
{
  "scenario_key": "scenario-key",
  "task_type": "metric_trend | metric_ranking | threshold_alert | dimension_breakdown | notification_request | resolution_tracking",
  "readiness": "ready | needs_clarification | blocked",
  "next_stage": "analysis | notification | resolution | stop"
}
```

进入分析前必须确认：场景唯一、指标唯一、时间窗口明确、维度已治理、无外部副作用请求。

## 3. 指标与数据

```text
METRIC_ID = numerator / denominator
```

| 运行字段 | 替换为真实字段 | 说明 |
| --- | --- | --- |
| `event_date` | `PARTITION_FIELD` | 已闭合分区。 |
| `numerator` | `SOURCE_NUMERATOR_FIELD` | 分子，聚合后计算。 |
| `denominator` | `SOURCE_DENOMINATOR_FIELD` | 分母，为 0 时阻断比率结论。 |
| `dimension_a` | `SOURCE_DIMENSION_A` | 默认拆解维度。 |
| `owner_route_key` | `SOURCE_OWNER_KEY` | Owner 路由键。 |

来源优先级：语义层指标 -> 治理数据集 `DATASET_ID` -> 受控只读 SQL。

禁用来源：临时表、无 Owner 表、废弃数据集、未登记字段、个人敏感明细、写接口。

## 4. 分析

QueryPlan 必填：

```json
{
  "query_plan_id": "QP-scenario-key-0001",
  "scenario_key": "scenario-key",
  "metric_id": "METRIC_ID",
  "task_type": "metric_trend",
  "time_range": {},
  "dimensions": [],
  "filters": [],
  "allowed_sources": [],
  "forbidden_sources": [],
  "quality_checks": [],
  "review_required": false
}
```

规则：

- 比率必须先聚合分子和分母再计算。
- 可空维度先转 `*_key`，外层再映射为展示字段。
- 查询失败、权限不足、分区未就绪或分母为 0 时，不输出业务结论。

## 5. 通知

只生成草稿：

- `notification_draft.json`
- `poc_routing_plan.json`
- `send_plan.json`
- `card.json`

`send_plan` 默认：

```json
{
  "send_mode": "preview_only",
  "requires_confirmation": true,
  "group_send_blocked": true,
  "sent": false,
  "real_group_send_executed": false,
  "online_write_executed": false
}
```

Owner 路由资产：`assets/owner_mapping.template.json`。只有姓名或角色时，不得真实触达。

## 6. 解决

只生成本地 `manual_tracking.json`。关闭前必须具备：

- 动作。
- 证据。
- 结论。

`send_plan.sent=false` 或 `group_send_blocked=true` 时，不得记录为已触达。

## 7. 失败分支

| 触发 | 处理 |
| --- | --- |
| 场景不唯一 | 问清场景。 |
| 口径不明确 | 确认分子、分母、过滤和窗口。 |
| 字段未治理 | 停止，不猜字段。 |
| 分区或权限失败 | 保留 QueryPlan，不下结论。 |
| 缺少分析结果 | 不进入通知。 |
| 请求真实发送或写状态 | 阻断，要求人工确认和外部执行器。 |
| 缺少三件套 | 不关闭，只记录继续跟进。 |

## 8. 样例

- 正例：`帮我看 SCENARIO_NAME 近 7 天相比上 7 天的变化。`
- 正例：`基于刚才分析结果生成通知 Card 和 send_plan，先不要发。`
- 反例：`帮我看 RELATED_SCENARIO_A 为什么下降。`
- 反例：`直接群发给所有 Owner 并拉他们进群。`
