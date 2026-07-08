# 阶段 1 P1 只读执行结果记录：打标率

## 基础信息

- 调试日期：2026-07-08
- 场景：`efficiency-label-rate`
- 运行模式：`debug_only`
- 执行模式：`mock_readonly_execution`
- 运行脚本：`human_review_ops/tools/runners/run_stage_1_readonly_execution_chain.py`
- 校验脚本：`human_review_ops/tools/validators/validate_stage_1_readonly_execution_chain.py`
- 结果文件：`20260708_readonly_execution_results.jsonl`

## 运行结论

阶段 1 P1 已从 mock Tool 预检推进到 mock 只读执行结果。

本轮确认：

- 正例均输出 `readonly_execution`、`analysis_result` 和 `provenance`。
- 成功执行样例均输出 evidence 字段：`review_done_cnt`、`label_cnt`、`label_rate`、`time_window`。
- `source_footer` 已从预检口径升级为执行口径。
- `provenance` 已记录 QueryPlan、Tool 调用 ID、指标口径、过滤条件、质量检查和场景参考文件。
- 反例和低信息量样例不生成 QueryPlan、不执行查询、不输出业务结论。
- 本轮未连接真实 Semantic Layer / Aeolus / Hive / ClickHouse。
- 本轮未发送真实通知，未写线上状态。

## 样例结果

| 样例 | 模式 | 执行状态 | source_tier | 行数 |
| --- | --- | --- | --- | ---: |
| `ELR-P-001` | `label_rate_trend` | `success` | `semantic_layer` | 7 |
| `ELR-P-002` | `label_rate_ranking` | `success` | `semantic_layer` | 3 |
| `ELR-P-003` | `label_rate_ranking` | `success` | `semantic_layer` | 3 |
| `ELR-P-004` | `low_label_rate_grading` | `success` | `curated_raw_sql` | 3 |
| `ELR-P-005` | `dimension_breakdown` | `success` | `curated_raw_sql` | 3 |
| `ELR-P-006` | `dimension_discovery` | `blocked` | `governed_dataset` | 0 |
| `ELR-N-001` | 反例拒绝 | 无执行 | 无 | 0 |
| `ELR-N-002` | 反例拒绝 | 无执行 | 无 | 0 |
| `ELR-L-001` | 低信息量澄清 | 无执行 | 无 | 0 |

## 输出结构

正例输出：

- `QueryPlan`
- `tool_call_records`
- `readonly_execution`
- `analysis_result`
- `source_footer`
- `provenance`

`analysis_result` 已包含：

- `readonly_execution`
- `impact_assessment`
- `root_cause_hypotheses`
- `sop_decision`
- `quality_checks`
- `source_footer`
- `provenance`

## 边界说明

- 当前结果来自 mock fixture，不代表真实线上数据。
- `real_query_executed=false`，所有 Tool 调用仍是只读调试记录。
- `ELR-P-006` 的业务线维度未在场景契约支持维度中，已按规则阻断执行，并输出字段发现后续要求。
- 通知草稿、Owner 建议和人工处理状态未作为查询类任务默认产出。

## 后续动作

阶段 1 后续可以继续做：

- 将 mock fixture 替换为真实只读 Tool 输出。
- 接入真实 Semantic Layer / Aeolus 指标 ID。
- 增加真实只读执行结果断言，校验 source tier、字段映射、新鲜度和分母非零。
