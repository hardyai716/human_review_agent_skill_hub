---
name: scenario-ops-template
description: "当用户需要处理单个人审运营场景的识别、只读分析、通知草稿和本地闭环时使用；适合把四能力链路收敛为自包含场景级 Skill，默认 debug_only。"
allowed-tools:
  - Read
  - Bash
---

# 场景级 Skill 模板

复制本模板后，替换 `scenario-key`、`SCENARIO_NAME`、`METRIC_ID`、`DATASET_ID`、`OWNER_ROLE`，并只维护本 Skill 内文件。

## 触发条件

- 用户询问 `SCENARIO_NAME`、`METRIC_ID` 或本场景治理对象。
- 用户要求趋势、排序、阈值分级、维度拆解。
- 用户要求基于分析结果生成通知草稿、Card、Owner 路由或 `send_plan`。
- 用户要求记录本地 `manual_tracking`、复查或闭环检查。

## 禁止使用

- 场景不唯一、指标不明确、时间窗口缺失时，不进入分析。
- 不执行真实 SQL、真实通知、拉群、open_id 解析、在线表格导入或线上状态写入。
- 不依赖 Skill 外部路径、历史聊天记忆或临时 SQL 作为核心口径。
- 不把 dry-run、草稿、未发送 `send_plan` 或查询失败写成业务事实。

## 🔴 CHECKPOINT · 安全边界

任一条件命中即停止，只输出阻断原因：

- 真实外部动作未获用户确认。
- QueryPlan 未确认字段、口径、分区、权限和禁用来源。
- 需要敏感身份解析但未授权。
- 闭环缺少动作、证据、结论三件套。

## 最小文件

- `references/reference_map.md`：文件分工和引用规则。
- `references/scenario_contract.md`：唯一业务契约，包含场景、指标、数据、分析、通知、解决和失败分支。
- `assets/test-prompts.template.json`：触发、反触发、越权样例。
- `assets/owner_mapping.template.json`：Owner 路由模板。
- `assets/notification_card_template.json`：Card 结构模板。
- `scripts/scenario_flow.py`：dry-run 感知、分析、通知、闭环产物生成。
- `scripts/selfcheck.py`：结构和安全自检。

## 工作流

1. 读 `references/scenario_contract.md`，确认场景、口径和禁用动作。
2. 运行或参考 `scripts/scenario_flow.py perception --request <request>` 识别 `scenario_key`、`task_type`、`readiness`。
3. readiness 不为 `ready` 时停止。
4. 分析阶段只生成 QueryPlan、只读 SQL 或 dry-run 样例；真实查询由外部只读执行器完成。
5. 通知阶段只生成 `notification_draft.json`、`poc_routing_plan.json`、`send_plan.json`、`card.json`，默认 `sent=false`。
6. 解决阶段只生成本地 `manual_tracking.json`，不写线上状态。

## 输出契约

- 感知：`scenario_key`、`task_type`、`readiness`、`next_stage`。
- 分析：QueryPlan、只读 SQL、`analysis_result`、`source_footer`。
- 通知：通知草稿、Owner 路由、Card、`send_plan`。
- 解决：本地 tracking、`closure_check`、`safety`。

## 脚本

```bash
python3 scripts/selfcheck.py
python3 scripts/scenario_flow.py perception --request "分析 SCENARIO_NAME 近7天异常"
python3 scripts/scenario_flow.py analysis --output <analysis_result.jsonl>
python3 scripts/scenario_flow.py notify --source <analysis_result.jsonl> --output-dir <output>
python3 scripts/scenario_flow.py track --notification-draft <draft.json> --send-plan <send_plan.json> --output <tracking.json>
```

## 失败处理

- 场景不唯一：问清场景。
- 口径不明确：要求确认分子、分母、过滤和窗口。
- 字段映射失败：列缺失字段，不猜字段。
- 权限或分区失败：保留 QueryPlan，不输出业务结论。
- 缺少分析产物：不生成通知。
- `send_plan.sent=false`：不记录为已触达。
- 缺少三件套：不关闭。

## 验证

发布前至少运行：

```bash
python3 scripts/selfcheck.py
```

自检必须只读本 Skill 内部文件，不执行真实 SQL、不发送通知、不导入在线表格、不写线上状态。
