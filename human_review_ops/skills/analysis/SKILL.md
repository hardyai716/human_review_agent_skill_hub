---
name: analyzing-ops-metrics
description: Builds governed QueryPlan, applies metric contracts and dataset references, and returns analysis results with source footers.
allowed-tools: []
disallowed-tools:
  - write
---

# 分析 Skill

## 触发条件

当用户需要对已识别的人审运营指标或场景做查询计划、字段选择、归因分析和结论输出时使用。

## 输入

- `scenario_key`
- `metric_ids`
- `task_type`
- 时间窗口
- 维度要求

## 输出

- QueryPlan
- 分析摘要
- 候选根因
- source_footer
- tool_call_record（仅 mock / 只读预检阶段）
- 质量检查结果

## 调试约束

- 默认只读。
- 查询前必须生成 QueryPlan。
- 当前阶段可先生成 mock / 只读 `tool_call_record`；接入真实只读 Tool 后，QueryPlan 通过断言即可执行治理数据源只读查询。
- 输出必须包含 source_footer。
- 不使用未授权数据源。

## 参考资料

- `references/common.md`
- `references/scenario-index.md`
