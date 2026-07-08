---
name: tracking-ops-resolution
description: Tracks manual handling status, evidence, conclusions, and follow-up needs for human-review operations workflows.
allowed-tools: []
disallowed-tools:
  - write
---

# 解决 Skill

## 触发条件

当用户需要记录人工处理状态、处理结论、证据、复查标记或是否继续观察时使用。

## 输入

- 事件状态。
- 分析结果。
- 通知状态。
- 人工处理信息。

## 输出

- manual_tracking
- closure_check
- next_state
- follow_up

## 调试约束

- 默认不写线上状态。
- 默认只输出调试记录。
- 关闭事件前必须具备动作、证据、结论三件套。

## 参考资料

- `references/common.md`
- `references/scenario-index.md`
