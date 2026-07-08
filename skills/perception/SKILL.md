---
name: perceiving-ops-events
description: Identifies human-review operations scenarios, task types, metrics, and data readiness for debugging and workflow routing.
allowed-tools: []
disallowed-tools:
  - write
---

# 感知 Skill

## 触发条件

当用户问题需要识别运营模块、指标、任务类型、场景包或数据就绪状态时使用。

## 输入

- 用户原始问题。
- 可选场景提示。
- `run_mode`。

## 输出

- `scenario_key`
- `task_type`
- `run_mode`
- `metric_ids`
- `readiness`
- `retrieval_policy`

## 调试约束

- 默认只读。
- 不直接查询数据。
- 不决定最终业务结论。
- 不跳过 `references/scenario-index.md`。

## 参考资料

- `references/common.md`
- `references/scenario-index.md`
