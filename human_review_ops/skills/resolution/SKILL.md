---
name: tracking-ops-resolution
description: "当用户需要记录人审运营事件的人工跟踪 (manual tracking)、状态流转、闭环检查、继续观察或复查计划时使用；用于 efficiency-label-rate 等场景的本地调试闭环，不发送通知、不写线上状态。"
allowed-tools:
  - Read
  - Bash
---

# 解决 Skill

## 触发条件

当用户需要记录人审运营事件的人工处理状态、证据、处理结论、复查标记、继续观察或闭环检查时使用本技能 (Skill)。

- 通知技能 (notification Skill) 已产出通知草稿、负责人 (POC) 路由和发送计划 (send_plan)，需要形成手工跟踪记录。
- 用户要求判断某个低打标率事件是否可关闭、是否继续观察、是否需要升级或是否缺少闭环信息。
- 用户要求基于状态机输出 `next_state`、`closure_check`、`follow_up` 或人工跟踪 (manual tracking)。
- 用户要求记录“已通知/已确认/待 POC 反馈/继续观察”等调试阶段处理状态。

## 禁止使用

- 不用于识别场景、指标或任务类型；这些交给感知技能 (perception Skill)。
- 不用于生成 QueryPlan、执行 SQL 或分析业务原因；这些交给分析技能 (analysis Skill)。
- 不用于生成通知草稿、卡片 (Card)、负责人 (POC) 路由或发送计划 (send_plan)；这些交给通知技能。
- 不写线上状态、不更新工单、不修改数据库、不回写报表、不发送飞书消息。
- 不在缺少动作、证据、结论三件套时关闭事件。
- 不把“已生成草稿”当作“已发送”或“已解决”。

## 🔴 CHECKPOINT · 处置阶段红线

命中以下任一情况时，🛑 STOP：只输出本地调试记录和阻断原因，不写任何线上状态，直到人工审批。

- 用户要求“直接关闭线上事件”“回写状态”“更新工单”或线上写入 → 进入 `HUMAN_REVIEW_REQUIRED`，`online_write_executed=false`、`online_state_write_allowed=false`，说明需要人工审批和外部权限门禁。
- `send_plan.sent=false` 或 `group_send_blocked=true` → 不得记录为“已发送”“已触达完成”。
- 闭环三件套（动作/证据/结论）任一缺失 → `closure_check.can_close=false`，保持继续观察，不给关闭结论。

## 输入

必需输入：

- `scenario_key`：例如 `efficiency-label-rate`。
- `current_state`：当前状态机节点。
- `analysis_result`：分析摘要、分级、证据和来源页脚。
- `notification_draft`：通知草稿或其文件引用。
- `send_plan`：发送计划 (send_plan)，用于校验是否真实发送、是否仍阻断。
- `manual_action`：人工动作，例如确认 POC、要求复盘、继续观察。

可选输入：

- `manual_response`：负责人 (POC) 或运营同学回复。
- `evidence_refs`：报表、卡片哈希、source_footer、通知草稿、send_plan、`综合_剔除+1同意`、`汇总统计_剔除+1同意` 等引用；举报流转方向还需保留 `enpool_reason`、日均人审完结量、日均打标量和举报打标率证据。
- `resolution_note`：处理结论。
- `follow_up_due`：建议复查时间。
- `operator`：记录人或当前执行者。

## 输出

输出必须包含：

- 人工跟踪 (`manual_tracking`)：本地调试记录，包含状态、证据、下一步、是否继续观察。
- 状态机 (`state_machine`)：`state_machine_ref`、`previous_state`、`current_state`、`next_state`。
- 来源引用 (`source_refs`)：通知草稿、send_plan、POC 路由计划、卡片、完整报表和剔除 `+1同意` 口径报表链接等前置产物路径。
- 闭环检查 (`closure_check`)：是否可关闭、缺失项和阻断原因。
- 继续跟进 (`follow_up`)：负责人、建议响应时间、复查条件和升级条件。
- 安全字段 (`safety`)：`group_send_blocked`、`real_group_send_executed`、`online_write_executed`、`online_state_write_allowed`。
- 证据引用 (`evidence_refs`)：分析、通知、路由、卡片、报表和人工回复引用。

## 打标率能力矩阵

命中 `efficiency-label-rate` 时，本 Skill 路径必须覆盖以下闭环口径；解决阶段只记录本地 manual tracking，不写线上状态。

- 数据方向：`manual_review_detail`（3888816）与 `report_flow`（3952594 / `enpool_reason`）。
- 默认分级：`mach_root_label_name × strategy_id × strategy_name`；`reason` 不作为默认分组，只用于样本清洗或显式 `dimension_breakdown`。
- 预警维度：`单策略维度` 与 `风险域维度`。
- 治理标记：`是否+1同意`、`更新日期`、`+1同意日期是否在本次统计周期前`。
- 报表口径：`综合`、`综合_剔除+1同意`、`汇总统计`、`汇总统计_剔除+1同意`。
- 通知和闭环：POC 路由；`report_flow` 仅有 `enpool_reason` 时 fallback 到 `举报` POC；在线导入门禁 `--import-sheet` / `auto_import_sheet=true` 默认关闭；manual tracking (`manual_tracking`) 只记录本地调试闭环。

## 工作流

1. 加载当前场景单文档，读取状态机、SLA、Owner 路由、manual tracking、关闭条件和示例章节。
2. 校验输入来自前置阶段：分析结果应有 source_footer，通知阶段应有 `notification_draft` 和 `send_plan`；低打标率默认三维分级需保留 `是否+1同意`、`更新日期` 和剔除口径报表引用。
3. 校验发送计划 (send_plan)：如果 `group_send_blocked=true` 或 `sent=false`，不得记录为“已发送”。
4. 建立状态流转：从 `NOTIFICATION_DRAFTED`、`MANUAL_TRACKING_RECORDED`、异常状态或用户指定状态推导 `next_state`。
5. 收集闭环三件套：动作、证据、结论。任一缺失时，`closure_check.can_close=false`。
6. 生成人工跟踪 (manual tracking)：记录每个等级的处理状态、目标角色、下一步和证据引用。
7. 输出继续观察或升级建议：结合分级 SLA，给出复查条件和升级条件。
8. 保持线上写入禁止：本技能只输出本地调试记录，不调用任何写入、通知或工单接口。

## manual tracking

人工跟踪 (manual tracking) 最小字段：

```json
{
  "schema_version": "stage_2_manual_tracking.v1",
  "scenario_key": "efficiency-label-rate",
  "tracking_mode": "local_debug_only",
  "overall_status": "pending_manual_confirmation",
  "tracking_records": [],
  "closure_check": {
    "can_close": false,
    "missing_before_close": []
  },
  "safety": {
    "group_send_blocked": true,
    "real_group_send_executed": false,
    "online_write_executed": false,
    "online_state_write_allowed": false
  }
}
```

记录原则：

- `tracking_mode` 默认 `local_debug_only`。
- POC 只有姓名级映射时，状态保持 `pending_manual_follow_up`。
- `+1同意` 仅作为治理状态和剔除口径依据，不代表事件已解决；关闭前仍需动作、证据、结论三件套。
- report_flow 事件的证据主键是 `enpool_reason`，路由可先 fallback 到 `举报` POC，但需要人工确认是否进一步按风险域或队列拆分。
- 未完成人工确认、open_id 确认和真实响应前，不得关闭。
- 每条记录必须包含证据来源，而不是只写结论。

## 状态流转

状态流转以 `references/scenarios/efficiency-label-rate.md#状态机` 为准。

常见路径：

- `NOTIFICATION_DRAFTED -> MANUAL_TRACKING_RECORDED -> DEBUG_CLOSED_AFTER_MANUAL_REVIEW`
- 数据未就绪：进入 `DATA_NOT_READY`，不关闭业务问题。
- 权限不足：进入 `PERMISSION_BLOCKED`。
- 需要真实发送、线上写状态或高风险动作：进入 `HUMAN_REVIEW_REQUIRED`。
- 缺少口径、时间窗口、Owner 或人工确认：进入 `NEED_MORE_INFO`。

只有在调试闭环且三件套完整时，才能输出关闭建议；该建议不等同于线上关闭。

## 闭环三件套

关闭前必须具备：

- 动作：已经采取或明确决定的处理动作，例如“已人工确认 POC 并要求复盘”。
- 证据：分析结果、source_footer、通知草稿、send_plan、卡片哈希、POC 回复或人工备注。
- 结论：是否误报、是否继续观察、是否升级、是否已完成治理动作。

缺任一项时：

- `closure_check.can_close=false`
- `overall_status=pending_manual_confirmation`
- `missing_before_close` 列出缺失项
- `follow_up` 给出下一步和复查条件

## 线上写入禁止

- 本技能不得调用写接口，不更新线上状态机、工单、数据库、飞书消息或报表。
- 输出中的 `online_write_executed` 必须为 `false`。
- 输出中的 `online_state_write_allowed` 默认 `false`。
- 用户要求“直接关闭线上事件”“回写状态”“更新工单”时，必须输出 `HUMAN_REVIEW_REQUIRED`，并说明需要人工审批和外部权限门禁。

## 参考资料加载

加载顺序固定如下：

- `references/common.md`
- `references/scenario-index.md`
- 当前场景主文档，例如 `references/scenarios/efficiency-label-rate.md`

只读取当前场景所需文件和章节；不从通知草稿中推断未记录的真实发送状态。

## 脚本

可用脚本：

- `scripts/build_label_rate_manual_tracking.py`：基于 `notification_draft.json` 和 `send_plan.json` 生成本地人工跟踪 (manual tracking) 记录。

脚本示例：

```bash
python3 human_review_ops/skills/resolution/scripts/build_label_rate_manual_tracking.py --notification-draft <notification_draft.json> --send-plan <send_plan.json> --output <manual_tracking.json> --state-machine-ref references/scenarios/efficiency-label-rate.md#状态机
```

脚本只写本地输出文件；不得把它包装成线上状态写入。

## 失败处理

- 缺少 `notification_draft` 或 `send_plan`：停止，要求先补齐通知阶段产物。
- `send_plan.sent=false`：不得写“已发送”，只能写“待人工确认”。
- `group_send_blocked=true`：不得推进到真实触达完成状态。
- 缺少人工动作：关闭检查失败，要求补充处理动作。
- 缺少证据引用：关闭检查失败，要求补充分析、通知、报表或回复证据。
- 缺少处理结论：关闭检查失败，保持继续观察。
- 用户要求线上写入或自动关闭：进入 `HUMAN_REVIEW_REQUIRED`，不执行写入。

## 验证

运行 Skill 内自包含 smoke 校验：

```bash
python3 scripts/selfcheck.py
```

该脚本用内置 smoke 通知草稿和 send_plan 生成本地人工跟踪记录，只调用本 Skill 内脚本，不引用 Skill 外部路径、不发送通知、不写线上状态。

人工验证点：

- 输出包含人工跟踪 (manual tracking)、状态流转、闭环检查和继续跟进。
- `closure_check` 明确 `can_close` 和缺失项。
- 安全字段保持 `online_write_executed=false`、`online_state_write_allowed=false`。
- 未真实发送时不写“已通知完成”。
- 三件套不完整时不得给关闭结论。

## 示例

用户输入：

```text
基于刚才的低打标率通知草稿和 send_plan，记录一份 manual tracking，当前还没真实群发，只需要本地调试闭环。
```

期望输出要点：

```json
{
  "manual_tracking": {
    "tracking_mode": "local_debug_only",
    "overall_status": "pending_manual_confirmation"
  },
  "state_machine": {
    "previous_state": "NOTIFICATION_DRAFTED",
    "current_state": "MANUAL_TRACKING_RECORDED",
    "next_state": "DEBUG_CLOSED_AFTER_MANUAL_REVIEW"
  },
  "closure_check": {
    "can_close": false,
    "missing_before_close": [
      "poc_open_id_confirmation",
      "human_confirmation",
      "manual_response_or_resolution_note"
    ]
  },
  "safety": {
    "real_group_send_executed": false,
    "online_write_executed": false
  }
}
```
