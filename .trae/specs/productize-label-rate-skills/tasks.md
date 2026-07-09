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

# Task Dependencies

- Task 2 depends on Task 1.
- Task 3 depends on Task 1 and Task 2.
- Task 4 depends on Task 1 and Task 2.
- Task 5 depends on Task 1 and Task 2.
- Task 6 depends on Task 3, Task 4, and Task 5.
- Task 7 depends on Task 6.

# Parallelization Notes

- Task 3、Task 4、Task 5 在 Task 1 和 Task 2 完成后可并行实施。
- Task 3 和 Task 4 的 runner 改造需要分别保持阶段 1、阶段 2 既有 validator 通过。
- Task 6 的 standalone smoke validator 依赖前三类 Skill 脚本稳定后再统一接入。
