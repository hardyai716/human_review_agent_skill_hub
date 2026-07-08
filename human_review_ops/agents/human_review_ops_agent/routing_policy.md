# 路由策略

## 支持运行模式

```text
debug_only
full_workflow
query_only
owner_lookup_only
notification_only
resolution_only
partial_workflow
```

## 调试阶段默认策略

- 默认使用 `debug_only`。
- 能局部调度时不强制进入完整闭环。
- 查询类任务进入 `query_only` 或 `partial_workflow`。
- 找人类任务进入 `owner_lookup_only`。
- 通知类任务只生成草稿。
- 解决类任务只记录人工状态和证据。

## 场景读取优先级

1. 优先验证根目录 `human_review_ops/references/scenarios/{scenario_key}/`。
2. 如果 TRAE 跨目录读取不稳定，使用 `human_review_ops/skills/{skill_name}/references/scenarios/` 调试快照。
3. 任一路径失败时必须记录失败原因。
