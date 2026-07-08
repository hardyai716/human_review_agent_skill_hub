# Tasks

- [x] Task 1: 固化阶段 2 计划与术语基线。
  - [x] SubTask 1.1: 将 `docs/implementation_plan.md` 的阶段 2 任务表更新为 POC / 触达对象路由语义。
  - [x] SubTask 1.2: 将打标率场景根包和 Notification Skill 快照中的 `owner_routing.md` 同步为 POC / 触达对象路由。
  - [x] SubTask 1.3: 更新 Notification Skill 文案，避免继续使用泛泛的 Owner 路由概念。
  - [x] SubTask 1.4: 运行格式检查，提交并推送本任务变更。

- [x] Task 2: 实现 POC / 触达对象路由占位。
  - [x] SubTask 2.1: 新增 Notification Skill 脚本，用于生成 `poc_routing_plan.json`。
  - [x] SubTask 2.2: 新增 stage 2 runner，基于现有分级结果输出 POC 路由占位产物。
  - [x] SubTask 2.3: 新增 validator，校验 `routing_mode=placeholder`、等级角色范围和 `default_recipient=self`。
  - [x] SubTask 2.4: 运行验证，更新计划文档，提交并推送。

- [ ] Task 3: 增强通知草稿并生成群推送门禁计划。
  - [ ] SubTask 3.1: 生成 `notification_draft.json`，合并卡片草稿、数据链接、POC 路由占位和口径说明。
  - [ ] SubTask 3.2: 生成 `send_plan.json`，默认 `requires_confirmation=true`、`group_send_blocked=true`、`sent=false`。
  - [ ] SubTask 3.3: 扩展 validator，校验通知草稿和群推送门禁。
  - [ ] SubTask 3.4: 运行验证，更新计划文档，提交并推送。

- [ ] Task 4: 实现本地人工处理状态记录。
  - [ ] SubTask 4.1: 新增 Resolution Skill 脚本或 stage 2 runner，生成 `manual_tracking.json`。
  - [ ] SubTask 4.2: 确保状态符合 `state_machine.md`，并记录 `evidence_refs`、`operator_note`、`next_action`、`continue_observation`。
  - [ ] SubTask 4.3: 新增 validator，确保不写线上状态。
  - [ ] SubTask 4.4: 运行验证，更新计划文档，提交并推送。

- [ ] Task 5: 实现局部调度回归。
  - [ ] SubTask 5.1: 新增 stage 2 局部调度结果，覆盖 `owner_lookup_only`、`notification_only`、`resolution_only`。
  - [ ] SubTask 5.2: 新增 validator，确保局部调度不重复查数、不群发、不写线上状态。
  - [ ] SubTask 5.3: 运行阶段 2 全量验证。
  - [ ] SubTask 5.4: 更新计划文档，提交并推送。

- [ ] Task 6: 阶段 2 收尾与后续规划。
  - [ ] SubTask 6.1: 将阶段 2 已完成任务移动到 `12.2 已完成任务看板`。
  - [ ] SubTask 6.2: 在 `12.3` 规划阶段 3 或后续真实 POC 映射、群推送、回收闭环任务。
  - [ ] SubTask 6.3: 运行最终验证，提交并推送。

# Task Dependencies

- Task 2 depends on Task 1.
- Task 3 depends on Task 2.
- Task 4 depends on Task 2.
- Task 5 depends on Task 3 and Task 4.
- Task 6 depends on Task 5.
