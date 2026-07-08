# Validators

本目录存放人审运营 Agent + Skill 开发过程中的轻量校验脚本。

## 当前脚本

- `validate_scenario_package.py`：校验指定场景流程包是否包含最小必需文件。
- `validate_skill_package.py`：校验四类 Skill 是否具备 `SKILL.md`、`common.md`、`scenario-index.md` 和调试快照目录。
- `validate_query_plan.py`：校验 QueryPlan JSON 是否包含治理字段。
- `validate_source_footer.py`：校验 source_footer JSON 是否包含来源说明字段。
- `validate_trae_stage_0_5.py`：校验阶段 0.5 TRAE 调试记录是否覆盖环境、样例、权限和读取策略。
- `validate_stage_1_minimal_chain.py`：校验阶段 1 感知 + 分析最小链路是否输出 `scenario_key`、`task_type`、QueryPlan 和 source_footer，且不触发真实查询或写入。
- `validate_stage_1_mock_tool_chain.py`：校验阶段 1 P1 的 mock 只读 Tool 调用记录，确保 `tool_call_record` 与 QueryPlan 对齐，且不会执行真实查询、通知或写状态。
- `validate_stage_1_readonly_execution_chain.py`：校验阶段 1 P1 的 mock 只读执行结果，确保输出 `readonly_execution`、`analysis_result` 和 `provenance`，且不发送通知、不写状态。
- `validate_stage_1_real_readonly_readiness.py`：校验真实只读 Tool 接入准备度报告，确保缺少真实指标 ID、治理数据集 ID 或只读工具绑定时不会误判为 ready。

## 使用约束

- 校验脚本只检查结构和调试记录，不连接真实线上数据源。
- 阶段 0.5 默认 `debug_only`，不得发送真实通知，不得写入线上状态。
- 每次修改场景包、Skill 调试快照或调试记录后，应重新运行相关校验脚本。
