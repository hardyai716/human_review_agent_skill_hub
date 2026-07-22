# Validators

本目录存放人审运营 Agent + Skill 开发过程中的轻量校验脚本。

## 当前脚本

- `validate_scenario_package.py`：校验指定场景流程包是否包含最小必需文件。
- `validate_skill_package.py`：校验四类 Skill 是否具备 `SKILL.md`、`common.md`、`scenario-index.md` 和调试快照目录。
- `validate_agentbuddy_publish.py`：校验 `.agentbuddy/publish.yaml` 是否符合 AgentBuddy Git 仓库上传协议，并检查已声明 Skill 的 `SKILL.md` frontmatter、调试快照、脚本编译和本机绝对路径。
- `validate_skill_productization.py`：校验 Skill 产品化基线资产。默认 profile 为 `legacy_core`；可通过 `--profile scenario_label_rate|all_releaseable` 覆盖场景级 Skill 或全量可发布 Skill。默认模式检查 `SKILL.md` 基础 frontmatter、`test-prompts.json` 或 `assets/test-prompts.json` 结构、现有脚本编译和本机路径风险；`--strict` 额外检查必备章节。
- `validate_skill_standalone_smoke.py`：校验 Skill 独立发布包门禁，默认 profile 为 `legacy_core`；可通过 `--profile scenario_label_rate|all_releaseable` 覆盖场景级 Skill 或全量可发布 Skill。覆盖 `SKILL.md`、`references/`、`assets/`、`scripts/`、`skill_release_manifest.json`、Python 编译、外部依赖声明和最小 dry-run；四能力 Skill 复用脚本级 smoke，场景级 Skill 读取 manifest 中的 smoke command。
- `validate_skill_path_registry.py`：校验 `configs/skill_path_registry.json` 中的 `auto/canonical/legacy` 路径、validation profile、canonical 场景 Skill、legacy fallback、脚本、资产和参考文件是否存在且可解析。
- `validate_efficiency_label_rate_ops_skill.py`：聚合校验打标率场景级 Skill，串联路径注册表、场景级产品化、场景级 standalone smoke 和场景包 sync 检查。
- `validate_label_rate_capability_matrix.py`：校验 `efficiency-label-rate-ops` 与 perception/analysis/notification/resolution 四能力 Skill 的打标率能力矩阵一致性，覆盖 manual_review_detail、report_flow、默认三维分级且 `reason` 非默认分组、风险域维度、`+1同意`、剔除口径报表、POC 路由、在线导入门禁和 manual tracking，并验证 report_flow `enpool_reason` 到“举报”POC 的 fallback。
- `validate_label_rate_combined_flow.py`：校验人审明细 + 举报流转合并全等级能力，覆盖 `combined` QueryPlan、`数据来源` 字段、两源按级合并、举报 `reason/enpool_reason` 的 `+1同意` 标记和风险域预聚合剔除。
- `validate_aeolus_field_contracts.py`：校验 analysis 场景文档和脚本中的 Aeolus 语义字段契约，确认 `` `[数据集字段名]` `` 已登记、存在于数据集字段缓存、字段表表头符合 `common.md` 规范，且脚本 SQL 使用的语义字段已在场景文档登记。默认读取 `aeolus_dataset_fields_cache.json`；需要更新字段缓存时可运行 `--refresh-cache`。
- `validate_query_plan.py`：校验 QueryPlan JSON 是否包含治理字段。
- `validate_source_footer.py`：校验 source_footer JSON 是否包含来源说明字段。
- `validate_trae_stage_0_5.py`：校验阶段 0.5 TRAE 调试记录是否覆盖环境、样例、权限和读取策略。
- `validate_stage_1_real_readonly_label_rate.py`：校验真实只读打标率查询结果，支持 `--days`、`--dimensions` 和 `--query-mode` 校验对应 SQL，确保 SQL 包含 A/B/C/D 过滤、结果未截断，明细行满足 `label_rate < 0.1`，计数模式返回合法分组数。
- `validate_stage_1_real_readonly_label_rate_grading.py`：校验真实只读低打标率分级结果，确保 notice/P2/P1/P0 全等级执行、证据字段完整、综合结果按最高等级去重且不触发通知或写状态。
- `validate_stage_2_label_rate_notification_draft.py`：校验阶段 2 通知草稿产物，确保 summary、分等级 CSV、`汇总统计.csv`、xlsx、分等级 Card 2.0、hash、`_meta` 清洗和发送摘要一致。
- `validate_stage_2_label_rate_poc_routing.py`：校验阶段 2 POC / 触达对象路由产物，确保 `routing_mode=mach_root_label_mapping`、`routing_key=mach_root_label_name`、各等级角色和动作固定、姓名级 POC 可解析，且不群发、不写线上状态。
- `validate_label_rate_poc_mapping.py`：校验打标率场景 `mach_root_label_name -> POC` 映射配置、Skill 内自包含快照，以及自定义多维查询生成的 `poc_routing_plan.json`。
- `validate_label_rate_formal_flow.py`：校验正式 Skill-first 全流程产物，覆盖 perception `workflow_plan`、analysis QueryPlan、notification 产物、飞书表格链接、`host_dispatch_record.json` 和发送前置检查。

## 使用约束

- 校验脚本只检查结构和调试记录，不连接真实线上数据源。
- 阶段 0.5 默认 `debug_only`，不得发送真实通知，不得写入线上状态。
- 每次修改场景包、Skill 调试快照或调试记录后，应重新运行相关校验脚本。

## Skill 产品化基线命令

- Task 1 验收默认命令：`python3 human_review_ops/tools/validators/validate_skill_productization.py`
- Task 2 前置缺口识别：`python3 human_review_ops/tools/validators/validate_skill_productization.py --strict`
- 场景级 Skill 产品化：`python3 human_review_ops/tools/validators/validate_skill_productization.py --strict --profile scenario_label_rate`
- 场景级 Skill 独立运行：`python3 human_review_ops/tools/validators/validate_skill_standalone_smoke.py --profile scenario_label_rate`
- 场景级 Skill 聚合校验：`python3 human_review_ops/tools/validators/validate_efficiency_label_rate_ops_skill.py`
- 全量可发布 Skill 产品化：`python3 human_review_ops/tools/validators/validate_skill_productization.py --strict --profile all_releaseable`
- 全量可发布 Skill 独立运行：`python3 human_review_ops/tools/validators/validate_skill_standalone_smoke.py --profile all_releaseable`
- 路径注册表：`python3 human_review_ops/tools/validators/validate_skill_path_registry.py`
- Task 6 独立运行门禁：`python3 human_review_ops/tools/validators/validate_skill_standalone_smoke.py`
- Aeolus 字段契约单项校验：`python3 human_review_ops/tools/validators/validate_aeolus_field_contracts.py`
- Aeolus 字段缓存刷新：`python3 human_review_ops/tools/validators/validate_aeolus_field_contracts.py --refresh-cache`
- 发布前推荐命令：
  - `python3 human_review_ops/tools/validators/validate_skill_productization.py --strict`
  - `python3 human_review_ops/tools/validators/validate_skill_standalone_smoke.py`
  - `python3 human_review_ops/tools/validators/validate_skill_path_registry.py`
  - `git diff --check`
