# 通知场景：打标率

## 定位

本场景用于在 `efficiency-label-rate` 分析完成后，生成低打标率治理的通知草稿、POC 路由计划、飞书 Card 草稿、分级报表和 `send_plan`。通知 Skill 只负责触达前预览和门禁说明，不真实发送、不拉群、不写线上状态。

## 输入产物要求

必需输入来自 analysis Skill 生成的分析产物，且满足：

- `scenario_key=efficiency-label-rate`。
- `analysis_mode=low_label_rate_grading`。
- 存在 `record_type=sample` 的 JSONL 记录。
- 包含 `readonly_execution.level_counts`、`readonly_execution.level_results`、`readonly_execution.comprehensive_results` 和 `readonly_execution.metric_formula`。
- 包含 `QueryPlan`、`source_footer` 和 `provenance`。
- 明细行应包含 `mach_root_label_name`、`strategy_id`、`strategy_name`、`reason`、`avg_review_in_cnt`、`avg_review_done_cnt`、`avg_label_cnt`、`label_rate`、`hit_conditions`。

可选输入：

- `sheet_url`：完整报表链接，用于 Card 按钮和通知草稿；未提供时，通知脚本会尝试将生成的 XLSX 报表导入为飞书在线表格并回填链接。
- `top_n`：Card 每级展示 TopN，默认 10。
- `title`：Card 标题。
- `identity`：预览发送身份，仅用于输出计划；不代表真实群发授权。

## 输出产物

输出必须保持调试态：

- `summary.json`：通知汇总、分级计数、报表路径和来源页脚。
- `notification_draft.json`：通知草稿、数据链接、Card 草稿路径、POC 路由摘要和发送安全状态。
- `poc_routing_plan.json`：按机审一级标签生成的 POC 路由计划。
- `send_plan.json`：发送计划，默认阻断群发。
- 分等级 CSV：`notice.csv`、`P2.csv`、`P1.csv`、`P0.csv`、`综合.csv`。
- `汇总统计.csv` 和 XLSX 工作簿。
- `publish/low_efficiency_grading.card.json`、`publish/low_efficiency_grading.card.with_meta.json`、`publish/card_hash_check.json`。

## POC 路由

- 路由键固定为 `mach_root_label_name`。
- 结构化映射资产为 `assets/efficiency-label-rate/mach_root_label_poc_mapping.json`，不要把映射表复制进 Markdown。
- `reason`、`strategy_id`、`strategy_name` 只作为证据字段，不作为 POC 主路由键。
- 当前映射只到 POC 姓名，`poc_open_id` 缺失时必须保持 `requires_contact_resolution_before_real_send=true`。
- 输入缺少 `mach_root_label_name` 时标记 `missing_route_dimension`。
- 标签未命中映射时标记 `unmapped_label`。
- 存在未映射或缺失路由维度时，`fallback_to_default_user=true`，默认只给 `self` 预览。

等级触达规则：

| 等级 | 触达范围 | 动作要求 |
| --- | --- | --- |
| `notice` | 群内同步策略明细和数据链接 | 周知明细，纳入观察。 |
| `P2` | 治理 BP、审核 VOC POC、人审运营 | 请相关 POC 说明低打标原因和后续处理计划。 |
| `P1` | P2 范围 + 治理 BP +1、VOC 负责人、人审运营负责人 | 要求负责人关注，并推动原因说明和处理计划。 |
| `P0` | P1 范围 + 治理负责人 | 高优先级周知，要求重点关注和处理。 |

## 通知模板

低打标率策略预警草稿：

```text
【人审效率预警｜低打标率 reason】

场景：{scenario_key}
等级：{severity}
周期：{time_window}

摘要：
{summary}

证据：
- 机审一级标签：{mach_root_label_name}
- 策略：{strategy_id} / {strategy_name}
- reason：{reason}
- 日均进审量：{avg_review_in_cnt}
- 日均完审量：{avg_review_done_cnt}
- 日均打标量：{avg_label_cnt}
- 打标率：{label_rate}
- 命中条件：{hit_condition}

建议 Owner：{owner}
Owner 依据：mach_root_label_name POC mapping
置信度：{confidence}

说明：
- 本通知为 debug_only 草稿，未真实发送。
- 打标率口径：打标量 / 完审量。
- source_footer：{source_footer}
```

维度拆解摘要草稿：

```text
【人审效率分析｜打标率维度拆解】

维度：{dimensions}
周期：{time_window}

核心发现：
{summary}

TOP 低效组合：
{top_dimension_reason_rows}

限制说明：
{limitations}

本结果仅为调试草稿，真实触达前需要人工确认。
```

人工确认草稿：

```text
【需人工确认｜打标率通知发送门禁】

触发原因：{review_reason}
待确认事项：
1. 指标口径和时间窗口是否确认。
2. POC 姓名是否准确，是否已解析为无歧义 open_id。
3. 目标群、接收人、正文、附件和 Card 哈希是否确认。
4. 是否允许在通知 Skill 外进入真实发送审批。

当前不会发送真实通知、不会拉群、不会写入线上状态。
```

## Card 要求

- 使用 `assets/efficiency-label-rate/low_efficiency_grading_card_template.json` 和 `assets/efficiency-label-rate/card_schema_notes.md`，不要把模板或 schema notes 合并进本 Markdown。
- 展示 `P0`、`P1`、`P2`、`notice` 四个等级指标卡。
- 综合表按 `P0 > P1 > P2 > notice` 展示最高等级。
- 分等级表展示 P0/P1/P2/notice TopN 明细。
- 保留报表按钮、方法说明、数据窗口、打标率口径、fallback reason 和 source_footer 摘要。
- `card.with_meta.json` 必须包含 `_meta._data_hash`。
- `card.json` 发送前必须移除 `_meta`。
- 发送前若输入命中数据变化，必须重新渲染 Card 并重新校验 hash。

## send_plan 门禁

默认发送计划必须包含：

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
  "requires_contact_resolution_before_real_send": true,
  "online_write_executed": false
}
```

只有同时满足以下条件，具备发送权限的外部执行环境才能在通知 Skill 外进入真实发送审批：

- 用户明确确认发送范围、目标群、正文、附件和 Card。
- POC 姓名已解析到无歧义 open_id。
- 目标群和接收人已通过权限门禁。
- Card hash 与当前数据一致。
- P0/P1/P2/notice 的触达对象已人工复核。

即使满足上述条件，通知 Skill 仍只输出计划，不执行真实发送。

## SLA 与升级话术

| 等级 | 响应建议 | 处理建议 | 升级条件 |
| --- | --- | --- | --- |
| `P0` | 当日确认 | 当日完成 Owner 定位和治理方案确认 | 超过 1 个工作日未确认 |
| `P1` | 1 个工作日内确认 | 2 个工作日内给出治理动作 | 连续两轮仍未改善 |
| `P2` | 2 个工作日内确认 | 3 个工作日内完成复盘 | 进审量继续增长或打标率继续下降 |
| `notice` | 周期性观察 | 纳入周报或观察清单 | 连续命中或升级到 P2+ |

升级话术：

```text
【打标率治理升级建议｜{severity}】
{mach_root_label_name} / {strategy_name} 在 {time_window} 持续命中低打标率规则。
建议 Owner：{owner}；当前证据：完审量 {avg_review_done_cnt}、打标率 {label_rate}、命中条件 {hit_condition}。
请在 {response_sla} 内确认原因和处理计划。当前仍为通知草稿，真实触达前需完成人工确认。
```

调试阶段不启动真实 SLA 计时，只输出建议等级、建议响应时间和升级条件。

## 失败处理

- 缺少 `record_type=sample`：停止，要求补齐分析结果。
- `scenario_key` 不是 `efficiency-label-rate`：停止，交回感知或分析阶段确认。
- `analysis_mode` 不是 `low_label_rate_grading`：只允许生成通用摘要草稿，不生成分级预警发送计划。
- 缺少 `readonly_execution`、`level_counts`、`level_results`、`comprehensive_results` 或 `source_footer`：停止，交回 analysis Skill 补齐。
- 缺少 `mach_root_label_name`：生成低置信度路由，fallback 到 `self` 预览。
- 标签未映射 POC：列入 `unmapped_labels`，不得真实发送。
- 只有 POC 姓名、没有 open_id：保持 `requires_contact_resolution_before_real_send=true`。
- 缺少 `sheet_url`：优先尝试将 XLSX 报表导入为飞书在线表格；导入失败时仍生成草稿和本地报表，Card 按钮为空，正式触达前必须补齐。
- Card hash 校验失败：阻断发送，重新生成 Card。
- 用户要求绕过确认群发、拉群或写状态：拒绝执行，输出门禁失败原因。

## 正反例

正例：

```text
基于 efficiency-label-rate 的低打标率分级分析产物，生成通知草稿、POC 路由、Card 和 send_plan，保持 debug_only。
```

期望：

- 读取 `references/scenarios/efficiency-label-rate.md` 和 `assets/efficiency-label-rate/` 下结构化资产。
- 输出 `notification_draft.json`、`poc_routing_plan.json`、`send_plan.json`、CSV/XLSX 和 Card JSON。
- `send_plan.group_send_blocked=true`、`requires_confirmation=true`、`sent=false`。

反例：

```text
直接把 P0 低打标率结果群发给所有 POC，并把状态写成处理中。
```

处理：

- 不群发、不拉群、不写线上状态。
- 输出阻断原因：缺少人工确认、open_id 解析、目标群确认和发送权限。
- 如需状态流转，交给 resolution Skill。
