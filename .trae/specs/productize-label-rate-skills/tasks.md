# Tasks

- [x] Task 1: 建立 Skill 产品化基线评估资产。
  - [x] SubTask 1.1: 为 perception、analysis、notification、resolution 四个 Skill 增加 `test-prompts.json`，包含 should-trigger 和 should-not-trigger 示例。
  - [x] SubTask 1.2: 新增或增强 validator，检查 `SKILL.md` 必备章节、触发测试文件、脚本编译和本机路径风险。
  - [x] SubTask 1.3: 运行产品化基线 validator，并保留可复现的校验命令。

- [x] Task 2: 增强四个核心 `SKILL.md` 为可执行操作手册。
  - [x] SubTask 2.1: 增强 perception Skill，补齐使用边界、输入输出、workflow、reference loading、scripts、failure modes、validation、examples。
  - [x] SubTask 2.2: 增强 analysis Skill，补齐 QueryPlan、SQL、分级、source_footer、只读查询边界和禁止事项。
  - [x] SubTask 2.3: 增强 notification Skill，补齐通知草稿、POC 路由、Card、send_plan、群发门禁和失败分支。
  - [x] SubTask 2.4: 增强 resolution Skill，补齐 manual tracking、状态流转、闭环三件套、线上写入禁止和验证步骤。

- [x] Task 3: 下沉 analysis Skill 打标率核心脚本。
  - [x] SubTask 3.1: 在 `human_review_ops/skills/analysis/scripts/` 增加 QueryPlan、source_footer、打标率 SQL 构造、分级规则和输出标准化脚本。
  - [x] SubTask 3.2: 改造阶段 1 相关 runner，使其调用 analysis scripts，保留原有输出契约。
  - [x] SubTask 3.3: 增加脚本级 smoke test 或 validator，验证 analysis scripts 可独立生成结构化结果。
  - [x] SubTask 3.4: 运行阶段 1 相关回归验证。

- [x] Task 4: 补全 notification Skill 可复用脚本。
  - [x] SubTask 4.1: 在 `human_review_ops/skills/notification/scripts/` 增加通知草稿、send_plan、CSV/XLSX 报表构造脚本。
  - [x] SubTask 4.2: 改造阶段 2 通知 runner，使其复用 notification scripts，真实发送仍留在 runner 门禁。
  - [x] SubTask 4.3: 增加脚本级 smoke test 或 validator，验证 notification scripts 可独立生成草稿、send_plan、Card 和表格。
  - [x] SubTask 4.4: 运行阶段 2 通知相关回归验证。

- [x] Task 5: 可执行化 perception Skill。
  - [x] SubTask 5.1: 在 `human_review_ops/skills/perception/scripts/` 增加打标率场景识别脚本。
  - [x] SubTask 5.2: 增加 readiness 结构化生成脚本，输出 `scenario_key`、`task_type`、`run_mode`、`metric_ids`、`retrieval_policy`、`readiness`。
  - [x] SubTask 5.3: 增加脚本级 smoke test 或 validator，验证信息充足和信息不足两类输入。

- [x] Task 6: 建立单 Skill 独立运行门禁。
  - [x] SubTask 6.1: 新增 standalone smoke validator，覆盖四个 Skill 的 `SKILL.md`、references/assets/scripts、脚本编译和最小 dry-run。
  - [x] SubTask 6.2: 生成或校验 `skill_release_manifest.json`，记录每个 Skill 的可发布资产、脚本入口和外部依赖。
  - [x] SubTask 6.3: 将 standalone smoke validator 纳入发布前推荐命令。

- [x] Task 7: 文档、回归和提交收尾。
  - [x] SubTask 7.1: 更新 `docs/implementation_plan.md`，同步本次 Skill 产品化任务完成状态和后续注意事项。
  - [x] SubTask 7.2: 运行完整轻量回归：场景包校验、AgentBuddy 发布校验、POC 映射校验、阶段 1/阶段 2 相关 validator。
  - [x] SubTask 7.3: 提交并推送全部变更到 `origin/main`。

- [x] Task 8: 修复系统化验证发现的 `analysis/SKILL.md` 操作手册内容不一致。
  - [x] SubTask 8.1: 更新 `human_review_ops/skills/analysis/SKILL.md` 的脚本章节，删除“尚未提供下沉后的分析脚本”和“不调用不存在的 `scripts/` 入口”等过期描述，改为明确调用 `scripts/label_rate_analysis.py` 生成 QueryPlan、source_footer、SQL、分级规则和标准化输出。
  - [x] SubTask 8.2: 重新运行 `validate_skill_productization.py --strict`、`validate_label_rate_analysis_scripts.py`、`validate_skill_standalone_smoke.py`，并复核 checklist 第 3 项。

- [x] Task 9: Refresh Stage 2 default validator targets: The no-argument Stage 2 validator commands still point to stale `20260709_low_label_rate_grading_notification_draft` artifacts, causing failures for missing `汇总统计.csv` and outdated `routing_mode` fields even though the newer `20260709_low_label_rate_grading_min_review_in_draft` artifacts pass with explicit paths.

- [x] Task 10: 收敛 perception Skill 为运行态自包含单场景文档结构。
  - [x] SubTask 10.1: 将 `perception/references/scenarios/efficiency-label-rate.*.md` 合并为 `perception/references/scenarios/efficiency-label-rate.md`，内容只保留感知阶段需要的场景标识、触发/排除、别名、task_type 判定、readiness、handoff、阻断条件和正反例。
  - [x] SubTask 10.2: 将 `perception/references/scenarios/efficiency-auto-disposal-accuracy.*.md` 合并为同名单场景文档，避免保留外部场景包引用。
  - [x] SubTask 10.3: 更新 `perception/SKILL.md`、`perception/references/scenario-index.md`、`perception/scripts/label_rate_perception.py` 和 release manifest，使 required refs 指向单场景文档。
  - [x] SubTask 10.4: 运行 perception 脚本 validator 和 productization validator，确认 readiness 输出和阻断行为不回退。

- [x] Task 11: 收敛 notification Skill 为运行态自包含单场景文档结构。
  - [x] SubTask 11.1: 将 `notification/references/scenarios/efficiency-label-rate.*.md` 合并为 `notification/references/scenarios/efficiency-label-rate.md`，内容覆盖输入产物要求、POC 路由、通知模板、Card 要求、send_plan 门禁、SLA/升级话术、失败处理和正反例。
  - [x] SubTask 11.2: 将 `notification/references/scenarios/efficiency-auto-disposal-accuracy.*.md` 合并为同名单场景文档，保留通知阶段必要信息。
  - [x] SubTask 11.3: 保留 `assets/efficiency-label-rate/` 下 Card 模板、POC mapping JSON 和 schema notes 作为结构化资产，不合并进 Markdown。
  - [x] SubTask 11.4: 更新 `notification/SKILL.md`、`notification/references/scenario-index.md`、notification scripts 的 reference/provenance 字段和 release manifest。
  - [x] SubTask 11.5: 运行 notification 脚本 validator、Card/hash 校验和 Stage 2 通知相关 validator。

- [x] Task 12: 收敛 resolution Skill 为运行态自包含单场景文档结构。
  - [x] SubTask 12.1: 将 `resolution/references/scenarios/efficiency-label-rate.*.md` 合并为 `resolution/references/scenarios/efficiency-label-rate.md`，内容覆盖输入产物要求、状态机、闭环三件套、manual tracking、关闭条件、继续观察/升级规则、失败处理和正反例。
  - [x] SubTask 12.2: 将 `resolution/references/scenarios/efficiency-auto-disposal-accuracy.*.md` 合并为同名单场景文档，保留解决阶段必要信息。
  - [x] SubTask 12.3: 更新 `resolution/SKILL.md`、`resolution/references/scenario-index.md`、`build_label_rate_manual_tracking.py` 默认 state_machine ref 和 release manifest，移除外部根场景包依赖。
  - [x] SubTask 12.4: 运行 resolution standalone smoke 和 Stage 2 manual tracking validator。

- [x] Task 13: 更新跨 Skill 打包、校验和发布资产规则。
  - [x] SubTask 13.1: 更新 `tools/packagers/build_skill_package.py`，让 perception、notification、resolution 也按各自定位生成单场景运行态文档。
  - [x] SubTask 13.2: 更新 `skill_release_manifest.json`，四个 Skill 的 references 均指向单场景文档和必要 methods/assets。
  - [x] SubTask 13.3: 增加或更新 validator，检查四个 Skill 不再引用 `../../../references/scenarios`、`human_review_ops/references/scenarios` 或旧四件套路径。

- [x] Task 14: 跑通感知、分析、通知全流程并发送验证群。
  - [x] SubTask 14.1: 运行严格回归：`validate_skill_productization.py --strict`、`validate_skill_standalone_smoke.py`、perception/analysis/notification/resolution 脚本 validator、Stage 1/Stage 2 关键 validator、AgentBuddy publish validator 和 `git diff --check`。
  - [x] SubTask 14.2: 使用真实或已保存的当前 canonical stage artifact 跑通 `perception -> analysis -> notification`，确认输出包含 readiness、QueryPlan、source_footer、notification_draft、Card、poc_routing_plan、send_plan。
  - [x] SubTask 14.3: 定位“验证群”的唯一目标群；若无法从配置或用户上下文中唯一确定 chat_id，则记录阻断原因，不伪造发送。
  - [x] SubTask 14.4: 在目标群唯一且权限满足时发送验证摘要；发送内容必须包含本次结构调整摘要、关键验证命令结果、send_plan/card 产物路径和未执行线上写入声明。
  - [x] SubTask 14.5: 将发送结果或阻断原因记录到本规格 progress，并更新 checklist。

- [ ] Task 15: 上传当前工作态到 Git 仓库和 AgentBuddy，建立收敛前基线。
  - [ ] SubTask 15.1: 审阅当前 `git status`、`git diff --stat` 和新增文件，确认本轮上传范围，不回滚用户改动。
  - [ ] SubTask 15.2: 运行最小安全检查：`git diff --check`、`validate_skill_path_registry.py`、场景包 `--check-sync`、场景级 Skill smoke；若失败，记录阻断原因。
  - [ ] SubTask 15.3: 提交并推送当前工作态到 `origin/main`。
  - [ ] SubTask 15.4: 将当前受影响 Skill 发布到 AgentBuddy restricted 空间，至少覆盖 `efficiency-label-rate-ops`、`analysis`、`notification`，必要时覆盖五个可发布 Skill。
  - [ ] SubTask 15.5: 记录发布摘要文件，包含 skill、版本/ID、commit、命令和状态。

- [ ] Task 16: 收敛发布资产声明和安全副作用声明。
  - [ ] SubTask 16.1: 将 `plus1_agreed_strategy_updates.json` 纳入 `skill_release_manifest.json`、场景级 package manifest 和必要的 registry/validator 覆盖。
  - [ ] SubTask 16.2: 将 `sheet_importer.py` 与 `label_rate_notification_artifacts.py --import-sheet` 的副作用声明改为“默认无线上写入，显式 opt-in 后在线写入”。
  - [ ] SubTask 16.3: 在 `efficiency-label-rate-ops/SKILL.md` 增加短版 `🔴 CHECKPOINT`，覆盖真实群发、在线表格导入、线上状态写入和敏感身份解析。
  - [ ] SubTask 16.4: 运行 `build_skill_package.py efficiency-label-rate --target scenario-bundle --check-sync` 和相关 manifest/registry validator。

- [ ] Task 17: 对齐四能力 Skill 与 `efficiency-label-rate-ops` 的打标率能力覆盖。
  - [ ] SubTask 17.1: 建立打标率能力矩阵，覆盖手工审核明细方向、举报流转方向、默认三维分级、风险域维度、`+1同意`、剔除口径报表、POC 路由、在线导入门禁、manual tracking。
  - [ ] SubTask 17.2: 更新四能力 Skill 的打标率运行态文档、`SKILL.md` 片段和 `assets/test-prompts.json`，消除默认按 `reason` 分级的过期表达。
  - [ ] SubTask 17.3: 新增或增强一致性 validator，确保四能力 Skill 与场景级 Skill 的打标率能力矩阵无 gap。
  - [ ] SubTask 17.4: 运行 perception、analysis、notification、resolution 自检和脚本级 validator。

- [ ] Task 18: 修复 Aeolus 字段契约门禁，使全量产品化 strict 恢复通过。
  - [ ] SubTask 18.1: 调整字段契约文档或 validator，使字段表头采用可校验格式，不误伤业务映射说明。
  - [ ] SubTask 18.2: 让字段契约 validator 正确处理 `3888816` 与 `3952594` 双数据源，不把另一数据源字段判为当前数据集缺失字段。
  - [ ] SubTask 18.3: 避免 JSON 数组、`forbidden_sources`、`fallback_reason` 等非字段内容被识别为 Aeolus 字段。
  - [ ] SubTask 18.4: 运行 `validate_aeolus_field_contracts.py` 和 `validate_skill_productization.py --strict --profile all_releaseable`。

- [ ] Task 19: 清理文档、Card 模板和迁移状态中的已知冲突。
  - [ ] SubTask 19.1: 在 SOP 中明确“治理目标阈值 `<10%` / `<5%`”与“notice/P2/P1/P0 通知严重等级”是两个层级。
  - [ ] SubTask 19.2: 清理 Card 模板中的“reason 数柱状图”旧描述，并处理未使用 chart 代码或校验字段，避免与当前卡片实现冲突。
  - [ ] SubTask 19.3: 同步 `docs/skill_scenario_migration_checklist.md` 中 `efficiency-label-rate-ops` AgentBuddy 发布状态。
  - [ ] SubTask 19.4: 更新相关回归样例，确保文档、模板和 validator 口径一致。

- [ ] Task 20: 最终回归、提交、推送并再次发布 AgentBuddy。
  - [ ] SubTask 20.1: 运行全量回归：productization strict all_releaseable、standalone smoke all_releaseable、skill path registry、scenario package check-sync、能力一致性 validator、analysis/notification/perception/resolution 脚本 validator、Stage 1/Stage 2 关键 validator、AgentBuddy publish validator、`git diff --check`。
  - [ ] SubTask 20.2: 修复回归发现的问题，直到全部关键门禁通过。
  - [ ] SubTask 20.3: 提交并推送收敛后的最终状态到 `origin/main`。
  - [ ] SubTask 20.4: 重新发布受影响 Skill 到 AgentBuddy restricted 空间，并记录最终发布摘要。
  - [ ] SubTask 20.5: 汇总本轮完成情况到 `progress.md`。

# Task Dependencies

- Task 2 depends on Task 1.
- Task 3 depends on Task 1 and Task 2.
- Task 4 depends on Task 1 and Task 2.
- Task 5 depends on Task 1 and Task 2.
- Task 6 depends on Task 3, Task 4, and Task 5.
- Task 7 depends on Task 6.
- Task 10、Task 11、Task 12 可并行执行。
- Task 13 depends on Task 10、Task 11、Task 12.
- Task 14 depends on Task 13.
- Task 16、Task 17、Task 18、Task 19 depend on Task 15.
- Task 16、Task 17、Task 18、Task 19 可并行，但同一文件出现冲突时以后完成者必须先 re-read 后再改。
- Task 20 depends on Task 16、Task 17、Task 18、Task 19.

# Parallelization Notes

- Task 3、Task 4、Task 5 在 Task 1 和 Task 2 完成后可并行实施。
- Task 3 和 Task 4 的 runner 改造需要分别保持阶段 1、阶段 2 既有 validator 通过。
- Task 6 的 standalone smoke validator 依赖前三类 Skill 脚本稳定后再统一接入。
- Task 10、Task 11、Task 12 的目录合并可由不同子 Agent 并行处理，但都必须遵守各自 Skill 定位。
- Task 14 的验证群发送必须在所有回归通过后执行；若缺少唯一群标识，不得使用猜测目标。
- Task 16 偏发布清单和安全边界，Task 17 偏四能力 Skill 内容一致性，Task 18 偏字段契约门禁，Task 19 偏文档/Card 状态清理，四者可由不同子 Agent 并行推进。
