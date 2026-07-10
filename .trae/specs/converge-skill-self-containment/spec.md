# 收敛 Skill 自包含性 Spec

## Why

`human_review_ops/skills` 下四个 Skill（perception / analysis / notification / resolution）运行态基本自包含，但存在 3 处“跨目录泄漏”：SKILL.md 与发布清单引用了不随 Skill 发布的 `human_review_ops/tools/validators/*` 校验脚本，且 POC 映射 JSON 在根 `references/` 与 skill `assets/` 双份人工同步。安装后这些外部路径即失效或产生 drift。需在不影响现有流程执行的前提下收敛回 Skill 内部。

## What Changes

- 先将当前工作区所有改动（含已删除四件套、新增单场景文档、脚本与清单修改）提交并推送到 `origin/main`，建立干净基线。
- 为每个 Skill 新增 `scripts/selfcheck.py`（skill 内部、零跨目录依赖），运行本 Skill 主脚本的 dry-run 并断言关键输出结构。
- 将四个 `SKILL.md` 的「验证」章节去外部化：改为引用 skill 相对路径 `scripts/selfcheck.py`，移除 `human_review_ops/tools/validators/*` 命令。
- 更新 `skill_release_manifest.json`：`standalone_smoke_validator` 与各脚本 `smoke_command` 改为 skill 相对命令；将 `selfcheck.py` 补入各 skill 的 `scripts[]` 与 `release_assets`。
- POC 映射单源化：让 `tools/packagers/build_skill_package.py` 在构建时把根 `references/scenarios/<scenario>/mach_root_label_poc_mapping.json` 同步复制到 `skills/notification/assets/<scenario>/`，使 skill 副本成为生成产物，消除人工 drift。
- **对抗式加固**：在 `tools/validators/validate_skill_standalone_smoke.py` 的 `FORBIDDEN_RUNTIME_REFERENCE_PATTERNS` 中新增规则，禁止 SKILL.md 出现 `human_review_ops/tools/` 运行态引用，防止回归。

## Impact

- Affected specs: human_review_ops 四个核心 Skill 的发布自包含能力。
- Affected code:
  - `human_review_ops/skills/{perception,analysis,notification,resolution}/SKILL.md`
  - `human_review_ops/skills/{perception,analysis,notification,resolution}/scripts/selfcheck.py`（新增）
  - `human_review_ops/skills/skill_release_manifest.json`
  - `human_review_ops/tools/packagers/build_skill_package.py`
  - `human_review_ops/tools/validators/validate_skill_standalone_smoke.py`
- 不改动：任何 runner（`tools/runners/*`）、分析/通知/解决/感知的业务脚本核心逻辑、场景 .md 业务口径。

## ADDED Requirements

### Requirement: 每个 Skill 具备自包含自检脚本
系统 SHALL 为每个核心 Skill 提供 `scripts/selfcheck.py`，仅依赖 skill 内部资源与标准库（notification 可用其已声明的 openpyxl 之外的轻量路径），运行 dry-run 并断言关键输出。

#### Scenario: 独立运行自检
- **WHEN** 在任意 Skill 目录内执行 `python3 scripts/selfcheck.py`
- **THEN** 脚本以退出码 0 通过，且不执行 SQL、不发送通知、不写线上状态、不引用 skill 外部路径

### Requirement: SKILL.md 验证章节仅引用 Skill 内部路径
系统 SHALL 使四个 SKILL.md 的「验证」章节只包含 skill 相对命令，不出现 `human_review_ops/tools/` 等外部路径。

#### Scenario: 扫描 SKILL.md
- **WHEN** 全仓扫描 SKILL.md 的验证章节
- **THEN** 不出现 `human_review_ops/tools/` 引用，且保留「验证」章节标题以通过 strict 产品化校验

### Requirement: 发布清单命令 Skill 相对化
系统 SHALL 使 `skill_release_manifest.json` 中的 `standalone_smoke_validator` 与各 `smoke_command` 为 skill 相对命令，并将 `selfcheck.py` 纳入可发布资产。

#### Scenario: 校验清单
- **WHEN** 运行 standalone smoke validator 校验清单结构
- **THEN** 校验通过，且 `smoke_command` 与 `release_assets` 覆盖新增 selfcheck 脚本

### Requirement: POC 映射单源生成
系统 SHALL 通过构建脚本将根 references 的 POC 映射同步到 skill assets，使运行态副本为生成产物。

#### Scenario: 构建同步
- **WHEN** 执行 `build_skill_package.py <scenario> --write`
- **THEN** skill assets 下的 POC 映射与根 references 一致，`validate_label_rate_poc_mapping.py` 通过

### Requirement: 防回归门禁
系统 SHALL 在 standalone smoke validator 中禁止 SKILL.md 引用 `human_review_ops/tools/` 运行态路径。

#### Scenario: 引入外部引用即失败
- **WHEN** 某 SKILL.md 重新出现 `human_review_ops/tools/` 引用
- **THEN** `validate_skill_standalone_smoke.py` 报告 forbidden runtime reference 并以非零退出

## MODIFIED Requirements

### Requirement: 现有流程不回退
所有既有 runner、脚本导入关系与 dry-run 输出契约在本次改造后 SHALL 保持不变。

#### Scenario: 回归验证
- **WHEN** 运行 productization、standalone smoke、四个脚本级 validator、Stage 1/Stage 2 关键 validator、POC 映射 validator 与 `git diff --check`
- **THEN** 全部通过，且感知→分析→通知 dry-run 链路输出关键字段不变

## REMOVED Requirements

无。
