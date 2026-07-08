# 阶段 1 P1 mock / 只读 Tool 接入记录：打标率

## 基础信息

- 调试日期：2026-07-08
- 场景：`efficiency-label-rate`
- 运行模式：`debug_only`
- Tool 模式：`mock_readonly_no_real_query`
- 运行脚本：`human_review_ops/tools/runners/run_stage_1_mock_tool_chain.py`
- 校验脚本：`human_review_ops/tools/validators/validate_stage_1_mock_tool_chain.py`
- 结果文件：`20260708_mock_tool_chain_results.jsonl`

## 运行结论

阶段 1 P1 已完成 mock / 只读 Tool 接入。

本轮确认：

- 正例均输出 `tool_call_record`。
- QueryPlan 的 `tool_calls` 与顶层 `tool_call_records[*].tool_call_id` 对齐。
- `permission_checks.tool_calls` 与 QueryPlan 对齐。
- 所有工具调用均为 `permission_level=readonly`。
- 所有工具调用均为 `real_query_executed=false`。
- 本轮未连接真实 Semantic Layer / Aeolus / Hive / ClickHouse。
- 本轮未发送真实通知，未写线上状态。

## 工具记录覆盖

| 样例 | 模式 | tool_call_record 数量 | 工具记录 |
| --- | --- | ---: | --- |
| `ELR-P-001` | `label_rate_trend` | 1 | `mock_semantic_layer_catalog` |
| `ELR-P-002` | `label_rate_ranking` | 1 | `mock_semantic_layer_catalog` |
| `ELR-P-003` | `label_rate_ranking` | 1 | `mock_semantic_layer_catalog` |
| `ELR-P-004` | `low_label_rate_grading` | 2 | `mock_semantic_layer_catalog`, `mock_curated_sql_guard` |
| `ELR-P-005` | `dimension_breakdown` | 2 | `mock_semantic_layer_catalog`, `mock_curated_sql_guard` |
| `ELR-P-006` | `dimension_discovery` | 2 | `mock_semantic_layer_catalog`, `mock_governed_dataset_catalog` |
| `ELR-N-001` | 反例拒绝 | 0 | 无 |
| `ELR-N-002` | 反例拒绝 | 0 | 无 |
| `ELR-L-001` | 低信息量澄清 | 0 | 无 |

## 来源与状态统计

| 统计项 | 数量 |
| --- | ---: |
| `semantic_layer` mock 预检 | 6 |
| `curated_raw_sql` guard | 2 |
| `governed_dataset` 字段发现 | 1 |
| `success` | 6 |
| `blocked` | 2 |
| `degraded` | 1 |
| 真实查询执行 | 0 |

## 边界说明

- `mock_semantic_layer_catalog` 只模拟指标、维度和 freshness 预检记录，不返回真实数据。
- `mock_curated_sql_guard` 只记录受控 SQL fallback 的人工确认要求，真实 SQL 执行保持 blocked。
- `mock_governed_dataset_catalog` 只记录未列举维度的字段发现要求，字段未确认前不得拼接查询。
- 当前 source_footer 仍保持 `data_freshness=not_queried`。

## 后续动作

阶段 1 后续可以继续做：

- 生成通知草稿和 Owner 建议。
- 记录人工处理状态 `manual_tracking`。
- 接入真实只读工具前，补齐真实 Semantic Layer / Aeolus 指标 ID 和具体治理 Owner。
