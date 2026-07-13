---
name: perceiving-ops-events
description: "当用户以自然语言提出人审运营查询、分析、通知、闭环或复合诉求，而意图尚未被明确分类时使用；识别场景、任务类型、指标意图、维度、数据就绪状态和跨 Skill 编排计划，输出可交给 analysis、notification 或 resolution 的结构化路由。不执行 SQL、通知或线上状态写入。"
allowed-tools:
  - Read
  - Bash
---

# 感知 Skill

## 触发条件

当用户问题需要先判断人审运营场景、指标对象、任务类型、运行模式、数据就绪状态或跨阶段执行顺序时使用本技能 (Skill)。用户通常不会明确说“调用 analysis / notification / resolution”，只会提出自然语言诉求；只要意图没有被可靠分类，就应先用本技能做感知和路由。

- 用户提到打标率、进审量、完审量、打标量、高/低打标 reason、低效策略分级、机审一级标签拆解等效率指标。
- 用户问题尚未明确应交给分析技能 (analysis Skill)、通知技能 (notification Skill) 还是解决技能 (resolution Skill)。
- 用户给出自然语言任务，需要输出 `scenario_key`、`task_type`、`metric_ids`、`retrieval_policy` 和 `readiness`。
- 用户要求确认场景包、参考资料、指标口径或是否具备继续执行条件。
- 用户提出复合诉求，例如“查询后推送到飞书测试群”“分析并生成卡片”“通知后记录闭环”，需要先拆成 `analysis -> notification -> resolution` 中的一个或多个步骤。
- 用户表达存在模糊词或口误，例如“达标率”可能指“打标率”，需要输出候选场景和澄清项，而不是直接查询。

命中 `efficiency-label-rate` 时，本技能只完成路由和就绪判断，不进入 SQL、通知或闭环记录。

## 禁止使用

- 不用于执行 SQL、查询数据集、生成业务结论或解释低效原因；这些交给分析技能。
- 不用于生成飞书通知、卡片 (Card)、负责人 (POC) 路由或发送计划 (send_plan)；这些交给通知技能。
- 不用于记录人工跟踪 (manual tracking)、状态流转、关闭事件或线上写入；这些交给解决技能。
- 不导出审核员个人明细、手机号、open_id 等敏感明细。
- 不自动覆盖样本池、使用未治理字段、触发真实通知、创建群或写线上状态。

## 🔴 CHECKPOINT · 感知阶段红线

命中以下任一情况时，🛑 STOP：只输出结构化路由和阻断原因，不下发任何下游 Skill，直到用户人工确认。

- 用户要求真实发送、群发、拉群、跑线上 SQL、写线上状态或导出敏感明细 → `readiness.status=blocked`、`human_confirmation_required=true`，`handoff.next_skill=null`。
- 场景无法唯一识别 → `scenario_key=unknown`，列出候选与澄清项，不猜测。
- 通知或解决诉求缺少已落地的分析产物 → 保持阻断，`workflow_plan` 写出先补 analysis，不直接交接 notification/resolution。

## 输入

必需输入：

- `raw_user_request`：用户原始问题。

可选输入：

- `scenario_hint`：用户或上游给出的场景提示。
- `run_mode`：默认使用调试模式 (`debug_only`)。
- `time_window`：用户指定的时间窗口。
- `metric_hint`：用户提到的指标或业务概念。
- `dimension_hint`：用户要求的拆解维度。
- `source_refs`：用户提供的数据集、报表、文档或上游产物引用。

## 输出

输出必须是结构化对象，至少包含：

```json
{
  "scenario_key": "efficiency-label-rate",
  "task_type": "low_label_rate_grading",
  "run_mode": "debug_only",
  "metric_ids": ["label_rate"],
  "retrieval_policy": {
    "reference_first": true,
    "semantic_layer_first": true,
    "allow_readonly_query_after_query_plan": true,
    "forbid_notification": true,
    "forbid_online_write": true
  },
  "readiness": {
    "status": "ready",
    "blocking_reasons": [],
    "clarification_fields": [],
    "human_confirmation_required": false
  },
  "handoff": {
    "next_skill": "analysis",
    "required_refs": [
      "references/scenarios/efficiency-label-rate.md"
    ]
  },
  "workflow_plan": {
    "intent_type": "analysis",
    "steps": [
      {"step": 1, "skill": "perception", "status": "completed"},
      {"step": 2, "skill": "analysis", "task_type": "low_label_rate_grading", "status": "ready"}
    ],
    "requires_host_send_confirmation": false
  }
}
```

当信息不足时，`readiness.status` 必须为 `blocked` 或 `needs_clarification`，并列出 `blocking_reasons` 和 `clarification_fields`；不得假设缺失字段。

## 打标率能力矩阵

命中 `efficiency-label-rate` 时，本 Skill 路径必须保留以下能力口径用于下游编排；感知阶段只识别和传递，不执行 SQL、通知或闭环动作。

- 数据方向：`manual_review_detail`（3888816）与 `report_flow`（3952594 / `enpool_reason`）。
- 默认分级：`mach_root_label_name × strategy_id × strategy_name`；`reason` 不作为默认分组，只用于样本清洗或显式 `dimension_breakdown`。
- 预警维度：`单策略维度` 与 `风险域维度`。
- 治理标记：`是否+1同意`、`更新日期`、`+1同意日期是否在本次统计周期前`。
- 报表口径：`综合`、`综合_剔除+1同意`、`汇总统计`、`汇总统计_剔除+1同意`。
- 通知和闭环：POC 路由；`report_flow` 仅有 `enpool_reason` 时 fallback 到 `举报` POC；在线导入门禁 `--import-sheet` / `auto_import_sheet=true` 默认关闭；manual tracking (`manual_tracking`) 只记录本地调试闭环。

## 工作流

1. 保留用户原文，不改写业务含义。
2. 读取 `references/common.md` 和 `references/scenario-index.md`，先确认可用场景列表。
3. 按场景索引加载最小必要参考资料；命中打标率时只加载 `references/scenarios/efficiency-label-rate.md`。
4. 识别 `scenario_key`。无法唯一识别时输出 `scenario_key=unknown` 并要求澄清。
5. 识别 `task_type`：可选值包括 `label_rate_trend`、`label_rate_ranking`、`low_label_rate_grading`、`dimension_breakdown`、`notification_request`、`resolution_tracking`、`unknown`。复合诉求按最终用户目标识别，例如“查询并推送”识别为 `notification_request`，但必须在 `workflow_plan.prerequisites` 中声明先补 analysis 产物。
6. 识别 `metric_ids`。打标率场景默认使用 `label_rate`，相关证据指标包括 `review_in_cnt`、`review_done_cnt`、`label_cnt`。
7. 建立 `retrieval_policy`：默认参考资料优先、语义层优先、只读查询需先有查询计划 (QueryPlan)、禁止通知和线上写入。
8. 做就绪检查：指标口径、时间窗口、维度、权限风险、敏感字段、越权动作、是否需要人工确认。
9. 生成下游交接信息和 `workflow_plan`。只在 `readiness.status=ready` 时交给单一下一跳；通知或解决请求如果缺少前置产物，应保持阻断，但 `workflow_plan` 必须写出先执行哪个 Skill。

## 参考资料加载

加载顺序固定如下：

1. `references/common.md`
2. `references/scenario-index.md`
3. 场景索引中列出的具体文件。

打标率场景的最小参考资料：

- `references/scenarios/efficiency-label-rate.md`

相邻自动处置准确率场景只读取：

- `references/scenarios/efficiency-auto-disposal-accuracy.md`

相邻质量领域质检准确率场景只读取：

- `references/scenarios/quality-inspection-accuracy.md`

只读取当前问题需要的单场景文件，不批量加载无关场景；不从旧目录、临时文档或记忆中猜测核心口径。

## 脚本

打标率感知 dry-run 入口：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 human_review_ops/skills/perception/scripts/label_rate_perception.py --dry-run --request "帮我看近 7 天低打标率 reason，按 P0/P1/P2/notice 分级。"
```

执行时必须遵守：

- 优先调用 `scripts/label_rate_perception.py` 生成结构化感知结果，再按本手册做人工复核。
- 脚本只做规则化场景识别、任务类型识别和 readiness 输出。
- 脚本不得执行 SQL、发送通知、导出敏感明细或写线上状态。
- 信息不足时保留 `scenario_key`、`task_type`、`run_mode`、`metric_ids`、`retrieval_policy`，并在 `readiness.blocking_reasons` 和 `readiness.clarification_fields` 中列出阻断项。

## 失败处理

- 场景不明确：输出 `scenario_key=unknown`，列出候选场景和澄清问题。
- 时间窗口缺失：将 `time_window` 放入 `clarification_fields`，不要默认替用户选择。
- 指标口径冲突：阻断并提示需要确认分子、分母和样本池。
- 模糊词或疑似口误：输出 `scenario_candidates`，例如“达标率”候选 `efficiency-label-rate`，并要求确认是否指“打标率”。
- 维度未治理：标记 `human_confirmation_required=true`，不得直接进入分析。
- 用户要求真实通知、自动拉群、写线上状态或批量导出敏感明细：输出阻断原因，并建议切换到人工确认流程。
- 用户问题明显属于通知或解决阶段但缺少分析结果：要求先补齐分析产物。

## 验证

运行 Skill 内自包含 smoke 校验：

```bash
python3 scripts/selfcheck.py
```

该脚本只调用本 Skill 内脚本，不引用 Skill 外部路径、不执行 SQL、不发送通知、不写线上状态。

人工验证点：

- 输出包含 `scenario_key`、`task_type`、`run_mode`、`metric_ids`、`retrieval_policy`、`readiness`。
- 命中打标率时指向 `references/scenarios/efficiency-label-rate.md`。
- 信息不足时阻断并列出澄清字段。
- 未执行 SQL、未发送通知、未写线上状态。

## 示例

用户输入：

```text
帮我看近 7 天低打标率 reason，按 P0/P1/P2/notice 分级。
```

期望输出要点：

```json
{
  "scenario_key": "efficiency-label-rate",
  "task_type": "low_label_rate_grading",
  "run_mode": "debug_only",
  "metric_ids": ["label_rate"],
  "readiness": {
    "status": "ready",
    "blocking_reasons": [],
    "clarification_fields": []
  },
  "handoff": {
    "next_skill": "analysis"
  }
}
```

用户输入：

```text
直接把这些 P0 策略群发给所有运营群并拉 POC 入群。
```

期望输出要点：

```json
{
  "scenario_key": "efficiency-label-rate",
  "task_type": "notification_request",
  "readiness": {
    "status": "blocked",
    "blocking_reasons": ["real_group_send_requested", "auto_group_invite_requested"],
    "human_confirmation_required": true
  },
  "handoff": {
    "next_skill": null,
    "candidate_next_skill": "notification"
  }
}
```
