# 完成阶段 2 POC 触达路由 Spec

## Why

阶段 2 已完成低打标率分级卡片草稿与单人预览推送，但 POC / 触达对象路由、群推送门禁、人工处理本地记录和局部调度回归仍未完成。需要在不接真实 POC 映射、不自动群发、不写线上状态的前提下，把阶段 2 闭环补齐。

## What Changes

- 新增 POC / 触达对象路由占位能力，当前所有等级 fallback 到用户本人。
- 固化 notice/P2/P1/P0 等级触达规则。
- 增强通知草稿，合并卡片草稿与 POC 路由占位信息。
- 新增群推送门禁计划 `send_plan.json`，默认阻断群推送。
- 新增本地人工处理状态记录 `manual_tracking.json`。
- 新增局部调度回归，覆盖 `owner_lookup_only`、`notification_only`、`resolution_only`。
- 每完成一个任务后，更新 `docs/implementation_plan.md`，提交并推送到远程仓库。

## Impact

- Affected specs: `efficiency-label-rate` 阶段 2、Notification Skill、Resolution Skill、Agent routing policy。
- Affected code: `human_review_ops/skills/notification/`、`human_review_ops/skills/resolution/`、`human_review_ops/tools/runners/`、`human_review_ops/tools/validators/`、`human_review_ops/evals/efficiency-label-rate/stage_2_runs/`、`docs/implementation_plan.md`。

## ADDED Requirements

### Requirement: POC / 触达对象路由占位
The system SHALL generate a local `poc_routing_plan.json` from the stage 1 grading result without inventing real POCs.

#### Scenario: 路由占位生成成功
- **WHEN** 阶段 1 低打标率分级结果存在
- **THEN** 系统生成 `poc_routing_plan.json`
- **AND** `routing_mode=placeholder`
- **AND** `fallback_to_default_user=true`
- **AND** notice/P2/P1/P0 均包含 `target_roles`、`action_required`、`default_recipient=self`

### Requirement: 等级触达规则固化
The system SHALL encode notice/P2/P1/P0 touch audience rules as verifiable local data.

#### Scenario: 等级规则符合 SOP
- **WHEN** validator 校验触达规则
- **THEN** notice 包含群内同步策略明细和数据链接
- **AND** P2 包含治理 BP、审核 VOC POC、人审运营
- **AND** P1 包含 P2 范围加治理 BP +1、VOC 负责人、人审运营负责人
- **AND** P0 包含 P1 范围加治理负责人

### Requirement: 通知草稿增强
The system SHALL generate `notification_draft.json` that combines the card draft, data link, POC routing placeholder, and source/provenance context.

#### Scenario: 通知草稿生成成功
- **WHEN** 阶段 2 卡片草稿和 POC 路由计划存在
- **THEN** 系统生成 `notification_draft.json`
- **AND** 草稿说明当前为默认本人验证
- **AND** 草稿包含等级统计、数据链接、POC 占位策略、口径说明和禁止群发标记

### Requirement: 群推送门禁计划
The system SHALL generate a `send_plan.json` that blocks group sending unless a future explicit confirmation path is added.

#### Scenario: 群推送默认阻断
- **WHEN** 系统生成阶段 2 发送计划
- **THEN** `requires_confirmation=true`
- **AND** `group_send_blocked=true`
- **AND** `sent=false`
- **AND** 不调用真实群推送 CLI

### Requirement: 本地人工处理状态记录
The system SHALL generate `manual_tracking.json` locally without writing Lark Base or any online state store.

#### Scenario: 人工状态记录生成成功
- **WHEN** 阶段 2 产物存在
- **THEN** 系统生成 `manual_tracking.json`
- **AND** 状态符合 `state_machine.md`
- **AND** 包含 `evidence_refs`、`operator_note`、`next_action`、`continue_observation`
- **AND** `online_write_executed=false`

### Requirement: 局部调度回归
The system SHALL validate that `owner_lookup_only`、`notification_only`、`resolution_only` can run from existing artifacts without re-querying data.

#### Scenario: 局部调度通过
- **WHEN** validator 校验局部调度结果
- **THEN** 三种 task_type 均有结果记录
- **AND** `real_query_executed=false`
- **AND** `group_send_blocked=true`
- **AND** 不重复生成阶段 1 查询

### Requirement: 每任务提交推送
The system SHALL update `docs/implementation_plan.md`, commit, and push after each completed stage 2 task.

#### Scenario: 单任务完成后可回溯
- **WHEN** 一个任务验收通过
- **THEN** `docs/implementation_plan.md` 对应状态更新
- **AND** Git 产生一个可回溯提交
- **AND** `main` 推送到 `origin/main`

## MODIFIED Requirements

### Requirement: Notification Skill 语义
Notification Skill SHALL use “POC / 触达对象路由” instead of generic “Owner 建议” for the efficiency-label-rate stage 2 flow.

## REMOVED Requirements

### Requirement: 阶段 2 真实 POC 映射
**Reason**: 真实 `reason/strategy -> POC` 映射后续补充，当前阶段没有稳定数据源。
**Migration**: 当前统一使用 placeholder routing 和 `default_recipient=self`。
