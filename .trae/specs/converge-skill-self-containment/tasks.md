# Tasks

- [x] Task 1: 建立干净 git 基线：提交并推送当前工作区改动到 origin/main
  - [x] SubTask 1.1: 审阅 `git status` 与 `git diff --stat`，确认改动均属已完成的 productize-label-rate-skills 重构，无敏感文件
  - [x] SubTask 1.2: 分组暂存并创建提交（skills 重构改动 + spec 进度），提交信息遵循仓库风格
  - [x] SubTask 1.3: `git push origin main`，确认推送成功且无冲突

- [x] Task 2: 为四个 Skill 新增自包含 `scripts/selfcheck.py`
  - [x] SubTask 2.1: analysis/selfcheck.py — 调用 `label_rate_analysis` dry-run，断言含 QueryPlan/source_footer/readonly_execution/analysis_result/provenance
  - [x] SubTask 2.2: perception/selfcheck.py — 调用 `label_rate_perception` dry-run，断言含 scenario_key/task_type/readiness
  - [x] SubTask 2.3: notification/selfcheck.py — 用内置 smoke stage-1 数据在临时目录生成通知产物并断言 send_plan 门禁字段（复用 skill 内脚本，输出到 tempdir）
  - [x] SubTask 2.4: resolution/selfcheck.py — 用内置 smoke notification_draft + send_plan 在 tempdir 运行 `build_label_rate_manual_tracking` 并断言 tracking_mode/safety
  - [x] SubTask 2.5: 四个 selfcheck 均只引用 skill 内相对路径，退出码 0，无副作用

- [x] Task 3: 四个 SKILL.md「验证」章节去外部化
  - [x] SubTask 3.1: 将 `human_review_ops/tools/validators/*` 命令替换为 `python3 scripts/selfcheck.py`（保留「验证」标题与人工验证点）
  - [x] SubTask 3.2: 确认 strict 产品化校验所需章节标题仍在

- [x] Task 4: 更新 `skill_release_manifest.json`
  - [x] SubTask 4.1: `release_policy.standalone_smoke_validator` 改为 skill 相对说明或移除外部绝对引用
  - [x] SubTask 4.2: 每个 skill 的 `scripts[]` 追加 selfcheck 条目，`smoke_command` 改为 `python3 scripts/selfcheck.py`
  - [x] SubTask 4.3: 各 skill `release_assets` 追加 `<skill>/scripts/selfcheck.py`

- [x] Task 5: POC 映射单源生成
  - [x] SubTask 5.1: 在 `build_skill_package.py` 增加把根 `references/scenarios/<scenario>/mach_root_label_poc_mapping.json` 复制到 `skills/notification/assets/<scenario>/` 的逻辑（仅当源存在）
  - [x] SubTask 5.2: 运行 `build_skill_package.py efficiency-label-rate --write` 验证副本一致

- [x] Task 6: 对抗式防回归门禁
  - [x] SubTask 6.1: 在 `validate_skill_standalone_smoke.py` 的 `FORBIDDEN_RUNTIME_REFERENCE_PATTERNS` 增加匹配 SKILL.md 中 `human_review_ops/tools/` 的规则（限定作用于 SKILL.md，避免误伤 manifest/其他）
  - [x] SubTask 6.2: 手动构造一个含外部引用的临时字符串验证规则命中（对抗测试）

- [x] Task 7: 全量回归与对抗式审查
  - [x] SubTask 7.1: 运行 productization(--strict)、standalone smoke、perception/analysis/notification 脚本 validator、resolution smoke
  - [x] SubTask 7.2: 运行 Stage 1 grading validator、Stage 2 notification/poc validator、POC 映射 validator
  - [x] SubTask 7.3: 跑 runner import 冒烟：确认 `run_stage_1_real_readonly_label_rate_grading.py` 仍能 import skill 脚本（不执行真实查询）
  - [x] SubTask 7.4: `git diff --check`；对抗式复查每个改动点是否引入回归

- [ ] Task 8: 提交并推送收敛改动到 origin/main

# Task Dependencies

- Task 2 depends on Task 1
- Task 3 depends on Task 2
- Task 4 depends on Task 2
- Task 5 depends on Task 1
- Task 6 depends on Task 3
- Task 7 depends on Task 3, Task 4, Task 5, Task 6
- Task 8 depends on Task 7
- Task 3, Task 4 可在 Task 2 完成后并行；Task 5 可与 Task 2/3/4 并行
