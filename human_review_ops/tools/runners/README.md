# Runners

本目录存放只读、可回放的阶段性运行脚本。

## 当前脚本

- `run_stage_1_minimal_chain.py`：围绕 `efficiency-label-rate` 运行阶段 1 的感知 + 分析最小链路。
- `run_stage_1_mock_tool_chain.py`：在最小链路基础上接入 mock 只读 Tool 记录，生成 `tool_call_record`，但不执行真实查询。
- `run_stage_1_readonly_execution_chain.py`：在 mock Tool 记录基础上生成 mock 只读执行结果、`analysis_result` 和 `provenance`。
- `run_stage_1_real_readonly_readiness.py`：检查真实只读 Tool 接入准备度，按 YAGNI 原则阻断缺少真实资产的提前实现。
- `run_stage_1_real_readonly_label_rate.py`：使用 `bytedcli -j aeolus query -r cn 3888816` 执行真实只读打标率查询，支持 `--days`、`--dimensions` 和 `--query-mode` 参数。
- `run_stage_1_real_readonly_label_rate_grading.py`：使用真实只读 Aeolus 查询执行低打标率 notice/P2/P1/P0 分级，输出等级结果、综合去重结果和 provenance。
- `run_stage_2_label_rate_notification_draft.py`：将阶段 1 低打标率分级结果转换为通知草稿产物、xlsx、飞书 Card 2.0，并可在用户明确要求时单人推送。
- `run_stage_2_label_rate_poc_routing.py`：基于阶段 1 低打标率分级结果生成 POC / 触达对象路由占位产物，当前固定 `routing_mode=placeholder`、`default_recipient=self`，不做真实 POC 映射。

## 使用约束

- 默认 runner 不连接真实 Aeolus / Hive / ClickHouse；名称带 `real_readonly` 的 runner 只允许连接治理后的只读数据源。
- runner 不发送通知，不写线上状态。
- runner 只读取场景包和 eval 样例，生成结构化调试结果。

## 示例

```bash
python3 human_review_ops/tools/runners/run_stage_1_minimal_chain.py
python3 human_review_ops/tools/validators/validate_stage_1_minimal_chain.py
python3 human_review_ops/tools/runners/run_stage_1_mock_tool_chain.py
python3 human_review_ops/tools/validators/validate_stage_1_mock_tool_chain.py
python3 human_review_ops/tools/runners/run_stage_1_readonly_execution_chain.py
python3 human_review_ops/tools/validators/validate_stage_1_readonly_execution_chain.py
python3 human_review_ops/tools/runners/run_stage_1_real_readonly_readiness.py
python3 human_review_ops/tools/validators/validate_stage_1_real_readonly_readiness.py
python3 human_review_ops/tools/runners/run_stage_1_real_readonly_label_rate.py --days 14
python3 human_review_ops/tools/validators/validate_stage_1_real_readonly_label_rate.py --days 14
python3 human_review_ops/tools/runners/run_stage_1_real_readonly_label_rate.py --days 14 --dimensions reason --query-mode group_count
python3 human_review_ops/tools/validators/validate_stage_1_real_readonly_label_rate.py --days 14 --dimensions reason --query-mode group_count
python3 human_review_ops/tools/runners/run_stage_1_real_readonly_label_rate.py --days 14 --dimensions reason,scene
python3 human_review_ops/tools/validators/validate_stage_1_real_readonly_label_rate.py --days 14 --dimensions reason,scene --query-mode ranking
python3 human_review_ops/tools/runners/run_stage_1_real_readonly_label_rate_grading.py
python3 human_review_ops/tools/validators/validate_stage_1_real_readonly_label_rate_grading.py
python3 human_review_ops/tools/runners/run_stage_2_label_rate_notification_draft.py --sheet-url 'https://bytedance.larkoffice.com/sheets/dry_run_sheet_token'
python3 human_review_ops/tools/validators/validate_stage_2_label_rate_notification_draft.py
python3 human_review_ops/tools/runners/run_stage_2_label_rate_poc_routing.py
python3 human_review_ops/tools/validators/validate_stage_2_label_rate_poc_routing.py
```
