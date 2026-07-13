---
name: routing-ops-notifications
description: "当用户需要基于人审运营分析结果生成通知草稿、负责人 (POC) 路由、飞书卡片 (Card)、分级报表或发送计划 (send_plan) 时使用；用于 efficiency-label-rate 等场景的触达前预览与人工确认门禁，默认阻断真实群发和拉群。"
allowed-tools:
  - Read
  - Bash
---

# 通知 Skill

## 触发条件

当用户需要基于已完成的人审运营分析结果生成通知草稿、负责人 (POC) 路由、飞书卡片 (Card)、发送计划 (send_plan) 或升级话术时使用本技能 (Skill)。

- 输入已经包含分析技能 (analysis Skill) 输出的 `scenario_key`、分级结果、证据、查询计划 (QueryPlan) 和来源页脚 (source_footer)。
- 用户要求把低打标率 `notice`、`P2`、`P1`、`P0` 结果整理成通知草稿。
- 用户要求按 `mach_root_label_name` 映射负责人 (POC) 或生成触达对象计划。
- 用户要求生成飞书 Card 2.0 预览、报表链接说明、升级话术或发送前检查清单。

## 禁止使用

- 不用于识别场景或判断指标；场景不明确时先交给感知技能 (perception Skill)。
- 不用于生成 QueryPlan、执行 SQL 或解释业务根因；这些交给分析技能。
- 不用于记录人工跟踪 (manual tracking)、事件关闭或线上状态流转；这些交给解决技能 (resolution Skill)。
- 不真实发送飞书消息、不群发、不拉人入群、不创建群、不短信/电话加急。
- 不解析或猜测 open_id；只有姓名级负责人 (POC) 时必须保持 `requires_contact_resolution_before_real_send=true`。
- 不绕过人工确认发送 P0/P1/P2/notice 预警。

## 🔴 CHECKPOINT · 通知阶段红线

命中以下任一情况时，🛑 STOP：只输出草稿和门禁失败原因，不执行真实动作，直到用户人工确认。

- 用户要求真实群发、拉群、创建群、短信/电话加急，或绕过人工确认 → 拒绝执行，输出门禁失败原因，`send_plan` 保持 `group_send_blocked=true`、`sent=false`。
- 请求把 XLSX 导入为飞书在线表格（`--import-sheet` / `auto_import_sheet=true`）→ 这是真实在线写入；默认关闭，只有用户明确同意后才启用，并在输出中标注 `online_write_executed=true`。
- POC 只解析到姓名级、缺少无歧义 open_id → 保持 `requires_contact_resolution_before_real_send=true`，不生成可执行群发动作。
- 卡片哈希与当前数据不一致 → 阻断发送，要求重新生成卡片。

## 输入

必需输入：

- `analysis_result`：分析结果或 `analysis_result` JSONL，必须包含 `analysis_mode`、`readonly_execution`、`level_counts`、分级明细和 `source_footer`。
- `scenario_key`：例如 `efficiency-label-rate`。
- `risk_levels`：至少说明涉及 `notice`、`P2`、`P1`、`P0` 中哪些等级。
- `evidence_rows`：每条命中的 reason、策略、打标率、日均量和命中条件。

可选输入：

- `sheet_url`：用户或外部执行环境提供的报表链接；未提供时默认保持为空，通知草稿照常生成。只有显式传入 `--import-sheet` 时，脚本才会把 XLSX 报表导入为飞书在线表格并回填链接（属于真实在线写入，见 CHECKPOINT）。
- `recipient_candidates`：用户提供的触达对象候选。
- `run_mode`：默认调试模式 (`debug_only`)。
- `card_title`：卡片标题。
- `operator_confirmation`：是否已有人工确认；没有则保持阻断。

## 输出

输出必须包含：

- `notification_draft.json`：通知草稿，包含摘要、等级、证据、限制说明和 source_footer 摘要。
- `poc_routing_plan.json`：负责人 (POC) 或触达对象路由计划。
- `card_json`：飞书卡片 (Card) JSON 草稿，默认只预览。
- `send_plan.json`：发送计划 (send_plan)，必须默认 `group_send_blocked=true`、`requires_confirmation=true`、`sent=false`。
- `escalation_draft`：P0/P1 等需要升级时的话术草稿。
- `evidence_refs`：引用的分析结果、报表、卡片哈希和来源页脚。
- `failure_branches`：未映射负责人、缺少 open_id、缺少报表或用户要求真实群发时的处理分支。

## 工作流

1. 校验输入来自分析阶段：`scenario_key=efficiency-label-rate`，且分级任务应为 `low_label_rate_grading`。
2. 校验分析结果包含 `readonly_execution`、分级明细、`level_counts`、查询计划 (QueryPlan) 和来源页脚 (source_footer)。
3. 加载通知通用规则、场景索引、单场景运行态文档、卡片模板和映射资产。
4. 生成或复用负责人 (POC) 路由计划：优先按 `mach_root_label_name` 映射，`reason`、`strategy_id`、`strategy_name` 只作为证据字段。
5. 生成通知草稿：包含等级、周期、摘要、证据、Owner 依据、置信度、限制说明和 debug_only 声明。
6. 生成飞书卡片 (Card) 草稿：使用 Card 2.0 模板，嵌入卡片数据哈希，方便发送前核验数据是否变更。
7. 生成发送计划 (send_plan)：默认只发给用户本人预览，真实群发被阻断。
8. 做群发门禁：没有人工确认、open_id、目标群和发送权限时，不得生成可执行群发动作。
9. 输出失败分支和下一步人工确认项；需要闭环记录时交给解决技能。

## POC 路由

负责人 (POC) 路由规则：

- 路由键：`mach_root_label_name`。
- 映射资产：`assets/efficiency-label-rate/mach_root_label_poc_mapping.json`。
- 姓名级映射可用于草稿和预览；open_id 缺失时不得真实触达。
- 输入缺少 `mach_root_label_name` 或标签未映射时，`fallback_to_default_user=true`，默认收件人为 `self` 预览。
- 触达范围按等级扩大：`notice` 周知，`P2` 要求 POC 说明，`P1` 扩展到负责人，`P0` 扩展到治理负责人。
- 置信度为 `low` 或 `medium` 时，发送计划必须保持 `requires_confirmation=true`。

## Card 与通知草稿

飞书卡片 (Card) 要求：

- 使用 `assets/efficiency-label-rate/low_efficiency_grading_card_template.json` 和 `assets/efficiency-label-rate/card_schema_notes.md`。
- 展示四个等级指标卡：`P0`、`P1`、`P2`、`notice`。
- 综合表按 `P0 > P1 > P2 > notice` 展示最高等级。
- 保留方法说明、报表按钮和来源页脚摘要。
- 通过 `scripts/card_hash.py` 嵌入 `_meta._data_hash`，发送前如数据变化必须重新生成卡片。

通知草稿要求：

- 明确“本通知为调试草稿，未真实发送”。
- 打标率口径写为“打标量 / 完审量”。
- 每个风险等级写清证据、Owner 依据、置信度和限制。
- 不能把 POC 姓名当作已确认 open_id。

## send_plan 门禁

发送计划 (send_plan) 默认字段：

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

只有同时满足以下条件，具备发送权限的外部执行环境才能在本技能之外进入真实发送审批：

- 用户明确确认发送范围、目标群、正文和附件。
- 负责人 (POC) 已解析到无歧义 open_id。
- 目标群和接收人已通过权限门禁。
- 卡片哈希与当前数据一致。
- P0/P1/P2 触达对象已人工复核。

即使满足上述条件，本技能仍只输出计划，不执行真实发送。

## 参考资料加载

加载顺序固定如下：

- `references/common.md`
- `references/scenario-index.md`
- `references/scenarios/efficiency-label-rate.md`
- `assets/efficiency-label-rate/mach_root_label_poc_mapping.json`
- `assets/efficiency-label-rate/low_efficiency_grading_card_template.json`
- `assets/efficiency-label-rate/card_schema_notes.md`

其他场景按 `references/scenario-index.md` 选择对应 `references/scenarios/<scenario_key>.md`。只读取当前 Skill 内当前场景所需文件；不读取 Skill 外部 reference 目录，不从聊天上下文猜测 POC、open_id 或目标群。

## 脚本

可用脚本：

- `scripts/label_rate_notification_artifacts.py`：从打标率分级 `analysis_result` JSONL 生成 `notification_draft.json`、`send_plan.json`、`poc_routing_plan.json`、分等级 CSV、`综合.csv`、`综合_剔除+1同意.csv`、`汇总统计.csv`、`汇总统计_剔除+1同意.csv`、XLSX 报表和 Card JSON；默认只写本地文件、不发送消息、不导入在线表格。只有显式传入 `--import-sheet`（或调用方传 `auto_import_sheet=True`）时才把 XLSX 导入为飞书在线表格，导入失败降级为空链接。
- `scripts/sheet_importer.py`：通用 XLSX 到飞书电子表格导入工具，提供 `import_xlsx_as_feishu_sheet`，供需要在通知产物中回填 `sheet_url` 的场景复用。
- `scripts/resolve_label_rate_poc_routing.py`：从 `analysis_result` JSONL 生成 `poc_routing_plan.json`。
- `scripts/render_label_rate_grading_card.py`：作为 Python 模块导入，生成飞书 Card 2.0 JSON 和设计检查结果。
- `scripts/card_hash.py`：计算和校验卡片数据哈希。

通知草稿脚本示例：

```bash
python3 human_review_ops/skills/notification/scripts/label_rate_notification_artifacts.py --source <analysis_result.jsonl> --output-dir <notification_output_dir> --sheet-url <optional_sheet_url>
```

POC 路由脚本示例：

```bash
python3 human_review_ops/skills/notification/scripts/resolve_label_rate_poc_routing.py --source <analysis_result.jsonl> --output <poc_routing_plan.json>
```

## 失败处理

- 分析产物缺少 `record_type=sample`：停止，要求补齐分析结果。
- `analysis_mode` 不是 `low_label_rate_grading`：只允许生成通用摘要草稿，不生成分级预警发送计划。
- 缺少 `readonly_execution`、`level_counts` 或 `source_footer`：停止，交回分析技能补齐。
- 缺少 `mach_root_label_name`：生成低置信度路由，fallback 到 `self` 预览。
- 标签未映射负责人 (POC)：列入 `unmapped_labels`，不得真实发送。
- 只有 POC 姓名、没有 open_id：保持 `requires_contact_resolution_before_real_send=true`。
- 卡片哈希不一致：阻断发送，要求重新生成卡片。
- 用户要求绕过人工确认群发或拉人入群：拒绝执行，输出门禁失败原因。

## 验证

运行 Skill 内自包含 smoke 校验：

```bash
python3 scripts/selfcheck.py
```

该脚本用内置 smoke 分级数据在临时目录生成通知产物，只调用本 Skill 内脚本，不引用 Skill 外部路径、不发送飞书消息、不写线上状态。

人工验证点：

- 输出包含通知草稿、负责人 (POC) 路由、卡片 (Card) 草稿和发送计划 (send_plan)。
- `send_plan.group_send_blocked=true`、`requires_confirmation=true`、`sent=false`。
- 未解析 open_id 时没有真实触达动作。
- POC 路由记录了 unmapped、missing route dimension 和默认 self 预览分支。
- 卡片携带 `_meta._data_hash`，并能通过设计检查函数确认基础结构。

## 示例

用户输入：

```text
基于 efficiency-label-rate 的 P0/P1/P2/notice 分级结果，生成飞书 Card 2.0 通知草稿和按机审一级标签映射的 POC 触达计划，保持 debug_only。
```

期望输出要点：

```json
{
  "notification_draft": {
    "scenario_key": "efficiency-label-rate",
    "debug_only": true
  },
  "poc_routing_plan": {
    "routing_key": "mach_root_label_name",
    "requires_contact_resolution_before_real_send": true
  },
  "send_plan": {
    "send_mode": "preview_only",
    "group_send_blocked": true,
    "requires_confirmation": true,
    "sent": false
  }
}
```
