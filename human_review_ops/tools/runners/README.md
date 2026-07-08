# Runners

本目录存放只读、可回放的阶段性运行脚本。

## 当前脚本

- `run_stage_1_minimal_chain.py`：围绕 `efficiency-label-rate` 运行阶段 1 的感知 + 分析最小链路。
- `run_stage_1_mock_tool_chain.py`：在最小链路基础上接入 mock 只读 Tool 记录，生成 `tool_call_record`，但不执行真实查询。
- `run_stage_1_readonly_execution_chain.py`：在 mock Tool 记录基础上生成 mock 只读执行结果、`analysis_result` 和 `provenance`。
- `run_stage_1_real_readonly_readiness.py`：检查真实只读 Tool 接入准备度，按 YAGNI 原则阻断缺少真实资产的提前实现。

## 使用约束

- runner 不连接真实 Aeolus / Hive / ClickHouse。
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
```
