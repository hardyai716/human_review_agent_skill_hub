---
name: efficiency-label-rate-ops
description: "当用户需要处理 efficiency-label-rate 打标率场景时使用：可识别打标率意图和数据方向，生成 QueryPlan 与只读分析，按 notice/P2/P1/P0 分级，产出报表、通知/Card 草稿、POC 路由和本地 manual tracking；默认 debug_only 与只读，只生成本地草稿/报表/跟踪记录，不真实发送、不写线上状态、不执行在线表格导入，外部动作必须用户确认。"
allowed-tools:
  - Read
  - Bash
---

# 打标率场景发布包

## 触发条件

- 用户明确询问打标率、低打标率、低效打标策略、进审量、完审量、打标量、reason、机审一级标签拆解。
- 用户要求对 `notice/P2/P1/P0` 低效打标策略分级。
- 用户要求基于既有分析结果生成通知草稿、飞书 Card、XLSX 报表、`sheet_url` 或 `send_plan`。
- 用户要求记录本地人工跟踪、继续观察或闭环检查。

## 禁止使用

- 不用于自动处置准确率、质检准确率、底线事故等其他场景。
- 不默认真实群发、不拉群、不解析敏感身份、不写线上状态。
- 不替代 calling_agent 的权限判断、人工确认和真实外部执行。
- 不把未执行查询的草稿当成业务事实；结论必须来自 QueryPlan 约束下的只读查询结果或用户提供的可复核证据。

## 🔴 CHECKPOINT · 安全边界

- 真实群发、拉群或外部通知发送：必须先由 calling_agent 获得用户明确确认；本包只生成草稿和 send_plan。
- 在线表格导入（`--import-sheet` / `auto_import_sheet=true`）：默认关闭，确认后才写入飞书 Sheet 并回填 `sheet_url`。
- 线上状态写入、关闭事件或改业务工单：禁止由本包直接执行，只能生成本地 `manual_tracking.json`。
- 敏感身份解析、open_id 反查或扩散：必须单独确认授权；默认保持已有 POC 映射，不主动解析。

## 输入

- `raw_user_request` 或上游感知结果。
- 可选 `analysis_result.jsonl`、`sheet_url`、通知草稿、`send_plan`。
- 可选时间窗口、维度和运行模式；默认 `debug_only`，即只生成本地草稿、报表和跟踪记录。

## 运行模式与安全边界

- `debug_only`：仅生成本地感知结果、QueryPlan、分析报表、通知草稿、POC 路由草稿和 manual tracking；不真实发送消息、不创建群、不写线上状态。
- 默认只读：只允许 `SELECT` 或平台受控只读查询；禁止 DML / DDL、线上配置变更、工单状态变更和未授权在线表格导入。
- `QueryPlan`：查询前的字段、指标口径、维度、过滤条件、数据方向、来源优先级、权限要求和质量检查计划；未通过断言或人工确认时不得查询。
- `mock / 只读查询链路`：没有外部查询权限时只生成计划或用内置样例验证输出结构，mock 结果不得伪造业务结论；具备权限且 QueryPlan 通过后，才可由受控执行器执行只读查询。

## 输出

- 感知结果：`scenario_key`、`task_type`、`readiness`、`workflow_plan`。
- 分析结果：`QueryPlan`、SQL、`analysis_result`、`source_footer`、`provenance`。
- 通知产物：`notification_draft.json`、`send_plan.json`、`poc_routing_plan.json`、Card JSON、CSV/XLSX 报表、可选 `sheet_url`。
- 解决记录：`manual_tracking.json`。

## 打标率能力矩阵

本 Skill 独立覆盖以下打标率能力口径，单独安装时即可按这些规则执行。

- 数据方向：`manual_review_detail`（3888816）与 `report_flow`（3952594 / `enpool_reason`）。
- 默认分级：`mach_root_label_name × strategy_id × strategy_name`；`reason` 不作为默认分组，只用于样本清洗或显式 `dimension_breakdown`。
- 预警维度：`单策略维度` 与 `风险域维度`。
- 治理标记：`是否+1同意`、`更新日期`、`+1同意日期是否在本次统计周期前`。
- 报表口径：`综合`、`综合_剔除+1同意`、`汇总统计`、`汇总统计_剔除+1同意`。
- 通知和闭环：POC 路由；`report_flow` 仅有 `enpool_reason` 时 fallback 到 `举报` POC；在线导入门禁 `--import-sheet` / `auto_import_sheet=true` 默认关闭；manual tracking (`manual_tracking`) 只记录本地调试闭环。

## 工作流

1. 使用 `scripts/label_rate_perception.py` 识别场景、任务类型和运行模式。
2. 使用 `references/scenario-index.md` 定位指标契约、数据集说明、分析规则、通知模板和状态机。
3. 使用 `scripts/label_rate_analysis.py` 生成 QueryPlan、SQL、分级规则和 source_footer；真实只读查询由具备权限的受控执行器执行。
4. 使用 `scripts/label_rate_notification_artifacts.py` 生成通知草稿、报表、Card 和 send_plan；只有显式授权 `--import-sheet` / `auto_import_sheet=true` 时才导入 XLSX 并回填 `sheet_url`。
5. 使用 `scripts/build_label_rate_manual_tracking.py` 记录本地人工处理状态；不写线上状态。

## SQL 生成约束

- 可空维度聚合前必须先生成内部稳定 key，再参与 `GROUP BY`。内部 key 统一使用 `*_key`，例如 `mach_root_label_key`、`strategy_id_key`、`strategy_name_key`、`reason_key`。
- 禁止把 `ifNull(...)`、`coalesce(...)` 或 `case` 的归一化别名写成底表物理字段名或输出字段名，例如禁止 `ifNull(`[机审一级标签]`, '（空/机审一级标签）') AS mach_root_label_name GROUP BY mach_root_label_name`。
- 外层输出时再把内部 key 映射回标准字段名，例如 `mach_root_label_key AS mach_root_label_name`。这是为了避免 Aeolus / ClickHouse 在别名与底表字段同名时解析到原始字段，漏掉 NULL 维度桶。

## 参考资料加载

- `references/scenario-index.md`
- `references/scenarios/efficiency-label-rate.md`
- `references/metric_contract.md`
- `references/dataset_reference.md`
- `references/analysis.md`
- `references/notification_templates.md`
- `references/owner_routing.md`
- `references/state_machine.md`
- `references/sla.md`
- `references/examples.md`

## 脚本

```bash
python3 scripts/selfcheck.py
python3 scripts/label_rate_perception.py --dry-run --request "帮我看近7天低打标率策略，按P0/P1/P2/notice分级。"
python3 scripts/label_rate_analysis.py --dry-run --levels notice,P2,P1,P0
python3 scripts/label_rate_notification_artifacts.py --source <analysis_result.jsonl> --output-dir <output>
python3 scripts/build_label_rate_manual_tracking.py --notification-draft <draft.json> --send-plan <send_plan.json> --output <tracking.json>
```

## 失败处理

- 场景不唯一：停止并要求 calling_agent 补充场景。
- 时间窗口或维度缺失：只输出 readiness，不进入查询。
- 缺少分析结果：不生成通知草稿，要求先补齐分析产物。
- 缺少人工确认：保持 `group_send_blocked=true` 和 `sent=false`。
- 缺少证据三件套：不关闭事件，只记录继续跟进。

## 验证

发布包内至少运行：

```bash
python3 scripts/selfcheck.py
```

独立安装后的自检命令记录在 `package_manifest.json` 的 `check_command` 字段；仓库内构建同步检查只作为 `build_provenance` 记录。
