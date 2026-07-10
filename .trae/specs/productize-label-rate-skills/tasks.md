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

# Parallelization Notes

- Task 3、Task 4、Task 5 在 Task 1 和 Task 2 完成后可并行实施。
- Task 3 和 Task 4 的 runner 改造需要分别保持阶段 1、阶段 2 既有 validator 通过。
- Task 6 的 standalone smoke validator 依赖前三类 Skill 脚本稳定后再统一接入。
- Task 10、Task 11、Task 12 的目录合并可由不同子 Agent 并行处理，但都必须遵守各自 Skill 定位。
- Task 14 的验证群发送必须在所有回归通过后执行；若缺少唯一群标识，不得使用猜测目标。
