---
name: routing-ops-notifications
description: "内部通用通知能力：仅消费已验证的 AnalysisArtifact，生成通知草稿、POC 路由、Card、报表和 send_plan；场景级 Skill 已命中时由其显式委派，不直接竞争原始请求，默认阻断真实群发和拉群。"
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
- 用户要求对两个明确周期的 `汇总统计_剔除+1同意` 做周环比/截图式对比，并生成飞书表格链接。

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

- `analysis_artifact`：Analysis 输出的统一 JSON/JSONL `record_type=sample` 对象，必须包含一致的 `scenario_key`、QueryPlan、`analysis_mode`、`readonly_execution`、`source_footer` 和 `provenance`。
- `scenario_key`：例如 `efficiency-label-rate`。
- `risk_levels`：至少说明涉及 `notice`、`P2`、`P1`、`P0` 中哪些等级。
- `evidence_rows`：每条命中的策略三维、风险域、打标率、日均量、命中条件、`是否+1同意`、`更新日期` 和剔除口径标记；举报流转方向使用 `enpool_reason`、日均人审完结量、日均打标量和举报打标率作为证据。

可选输入：

- `sheet_url`：用户或外部执行环境提供的报表链接；未提供时默认保持为空，通知草稿照常生成。只有显式传入 `--import-sheet` 时，脚本才会把 XLSX 报表导入为飞书在线表格并回填链接（属于真实在线写入，见 CHECKPOINT）。
- `recipient_candidates`：用户提供的触达对象候选。
- `run_mode`：默认调试模式 (`debug_only`)。
- `card_title`：卡片标题。
- `operator_confirmation`：是否已有人工确认；没有则保持阻断。
- `previous_filtered_summary_csv` / `current_filtered_summary_csv`：两个明确周期各自的 `汇总统计_剔除+1同意.csv`；构建周对比时二者必须成对提供，且周期边界必须显式。

## 输出

输出必须包含：

- `notification_draft.json`：通知草稿，包含摘要、等级、证据、限制说明和 source_footer 摘要。
- `poc_routing_plan.json`：负责人 (POC) 或触达对象路由计划。
- `card_json`：飞书卡片 (Card) JSON 草稿，默认只预览。
- `send_plan.json`：发送计划 (send_plan)，必须默认 `group_send_blocked=true`、`requires_confirmation=true`、`sent=false`。
- 分级报表：必须包含完整口径与剔除口径，至少覆盖 `综合.csv`、`综合_剔除+1同意.csv`、`汇总统计.csv`、`汇总统计_剔除+1同意.csv`。
- `escalation_draft`：P0/P1 等需要升级时的话术草稿。
- `evidence_refs`：引用的分析结果、报表、卡片哈希和来源页脚。
- `failure_branches`：未映射负责人、缺少 open_id、缺少报表或用户要求真实群发时的处理分支。
- `weekly_summary_comparison.json` / XLSX：按 `机审一级标签 × POC` 对齐的两周期剔除口径对比，含低效策略数、日均完审量、增量、增幅和加权打标率。

## 打标率能力矩阵

命中 `efficiency-label-rate` 时，本 Skill 路径必须覆盖以下通知口径；通知阶段只生成草稿、报表、POC 路由和 send_plan，不真实发送。

- 数据方向：`manual_review_detail`（3888816）与 `report_flow`（3952594 / `enpool_reason`）。
- 默认分级：`mach_root_label_name × strategy_id × strategy_name`；`reason` 不作为默认分组，只用于样本清洗或显式 `dimension_breakdown`。
- 预警维度：`单策略维度` 与 `风险域维度`。
- 治理标记：`是否+1同意`、`更新日期`、`+1同意日期是否在本次统计周期前`。
- 报表口径：`综合`、`综合_剔除+1同意`、`汇总统计`、`汇总统计_剔除+1同意`。
- 两周期对比：仅可消费每个周期独立生成的 `汇总统计_剔除+1同意`；不得以完整口径、不同 cutoff 或过期快照替代。
- 通知和闭环：POC 路由；`report_flow` 仅有 `enpool_reason` 时 fallback 到 `举报` POC；在线导入门禁 `--import-sheet` / `auto_import_sheet=true` 默认关闭；manual tracking (`manual_tracking`) 只记录本地调试闭环。

## 工作流

1. 校验输入来自分析阶段：`scenario_key=efficiency-label-rate`，`analysis_mode` 为 `low_label_rate_grading` 或 `report_flow_low_label_rate`，执行状态未失败或截断。
2. 校验分析结果包含 `readonly_execution`、分级明细、`level_counts`、查询计划 (QueryPlan) 和来源页脚 (source_footer)。
3. 加载通知通用规则、场景索引、单场景运行态文档、卡片模板和映射资产。
4. 生成或复用负责人 (POC) 路由计划：优先按 `mach_root_label_name` 映射，`reason`、`strategy_id`、`strategy_name` 只作为证据字段；举报流转方向若只有 `enpool_reason` 且无机审标签，先 fallback 到 `举报` POC 低置信度预览。
5. 生成通知草稿：包含等级、周期、摘要、证据、Owner 依据、置信度、限制说明和 debug_only 声明。
6. 生成飞书卡片 (Card) 草稿：使用 Card 2.0 模板，嵌入卡片数据哈希，方便发送前核验数据是否变更。
7. 生成发送计划 (send_plan)：默认只发给用户本人预览，真实群发被阻断。
8. 做群发门禁：没有人工确认、open_id、目标群和发送权限时，不得生成可执行群发动作。
9. 输出失败分支和下一步人工确认项；需要闭环记录时交给解决技能。
10. 用户要求周对比时，先确认两个周期分别已执行真实只读全等级分级，再以 `scripts/label_rate_weekly_summary_comparison.py` 生成截图式对比 XLSX；默认仅落本地，在线导入和外部发送仍由宿主在确认后执行。

## POC 路由

负责人 (POC) 路由规则：

- 路由键：`mach_root_label_name`。
- 映射资产：`assets/efficiency-label-rate/mach_root_label_poc_mapping.json`。
- 姓名级映射可用于草稿和预览；open_id 缺失时不得真实触达。
- 输入缺少 `mach_root_label_name` 或标签未映射时，`fallback_to_default_user=true`，默认收件人为 `self` 预览。
- 输入来自 `report_flow` 且只有 `enpool_reason` 时，先把路由标签补为 `举报`，映射到姓名级 POC 韩晶晶；真实触达前仍需人工确认是否按风险域或队列再拆分。
- 触达范围按等级扩大：`notice` 周知，`P2` 要求 POC 说明，`P1` 扩展到负责人，`P0` 扩展到治理负责人。
- 置信度为 `low` 或 `medium` 时，发送计划必须保持 `requires_confirmation=true`。

## Card 与通知草稿

飞书卡片 (Card) 要求：

- 使用 `assets/efficiency-label-rate/low_efficiency_grading_card_template.json` 和 `assets/efficiency-label-rate/card_schema_notes.md`。
- 展示四个等级指标卡：`P0`、`P1`、`P2`、`notice`。
- 综合表按 `P0 > P1 > P2 > notice` 展示最高等级。
- 保留方法说明、报表按钮和来源页脚摘要。
- 通过 `scripts/card_hash.py` 对完整证据 manifest 计算 `_meta._data_hash`；manifest 覆盖完整明细、QueryPlan ID、source footer、周期和 `sheet_url`，发送前任一数据变化都必须重新生成卡片。

通知草稿要求：

- 明确“本通知为调试草稿，未真实发送”。
- 打标率口径写为“打标量 / 完审量”。
- 每个风险等级写清证据、Owner 依据、置信度和限制。
- 默认三维分级结果必须展示 `是否+1同意`、`更新日期`、`+1同意日期是否在本次统计周期前`；报表链接需同时说明完整口径和剔除 `+1同意` 口径。
- 举报流转摘要必须写明 `data_direction=report_flow`，并展示 `enpool_reason`、日均人审完结量、日均打标量、举报打标率和 source_footer。
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
- `scripts/label_rate_weekly_summary_comparison.py`：消费两个明确周期的 `汇总统计_剔除+1同意.csv`，生成双层分组表头的周对比 XLSX 与 JSON。正向日均完审增量标红，总计打标率按日均打标量/日均完审量加权；`--import-sheet` 是显式在线写入门禁，脚本本身不发送消息。
- `scripts/resolve_label_rate_poc_routing.py`：从 `analysis_result` JSONL 生成 `poc_routing_plan.json`。
- `scripts/render_label_rate_grading_card.py`：作为 Python 模块导入，生成飞书 Card 2.0 JSON 和设计检查结果。
- `scripts/card_hash.py`：计算和校验卡片数据哈希。

通知草稿脚本示例：

```bash
python3 human_review_ops/skills/notification/scripts/label_rate_notification_artifacts.py --source <analysis_result.jsonl> --output-dir <notification_output_dir> --sheet-url <optional_sheet_url>
```

周对比脚本示例：

```bash
python3 human_review_ops/skills/notification/scripts/label_rate_weekly_summary_comparison.py \
  --previous-summary <previous>/汇总统计_剔除+1同意.csv \
  --current-summary <current>/汇总统计_剔除+1同意.csv \
  --previous-start-date YYYY-MM-DD --previous-end-date YYYY-MM-DD \
  --current-start-date YYYY-MM-DD --current-end-date YYYY-MM-DD \
  --output-dir <comparison_output_dir>
```

POC 路由脚本示例：

```bash
python3 human_review_ops/skills/notification/scripts/resolve_label_rate_poc_routing.py --source <analysis_result.jsonl> --output <poc_routing_plan.json>
```

## 失败处理

- 分析产物缺少 `record_type=sample`：停止，要求补齐分析结果。
- `analysis_mode` 不在 `low_label_rate_grading`、`report_flow_low_label_rate` 中：停止，不生成分级预警发送计划。
- 缺少 `readonly_execution`、`level_counts` 或 `source_footer`：停止，交回分析技能补齐。
- 缺少 `mach_root_label_name`：生成低置信度路由，fallback 到 `self` 预览。
- 标签未映射负责人 (POC)：列入 `unmapped_labels`，不得真实发送。
- 只有 POC 姓名、没有 open_id：保持 `requires_contact_resolution_before_real_send=true`。
- 卡片哈希不一致：阻断发送，要求重新生成卡片。
- 两个对比输入缺少任一周期、文件名不是 `汇总统计_剔除+1同意.csv`、列缺失或存在重复 `机审一级标签 × POC`：停止，不生成对比结论。
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
