# 阶段 1 感知 + 分析最小链路记录：打标率

## 基础信息

- 调试日期：2026-07-08
- 场景：`efficiency-label-rate`
- 运行模式：`debug_only`
- 运行脚本：`human_review_ops/tools/runners/run_stage_1_minimal_chain.py`
- 结果文件：`20260708_minimal_chain_results.jsonl`

## 运行结论

阶段 1 的感知 + 分析最小链路已跑通。

本轮确认：

- 正例均输出 `scenario_key=efficiency-label-rate`。
- 正例均输出 `task_type=query_only`。
- 正例均输出 QueryPlan。
- 正例均输出 source_footer。
- 反例不生成打标率 QueryPlan。
- 低信息量样例进入澄清，不查询。
- 未列举维度样例进入 `dimension_discovery_required`，不猜字段。
- 本轮未连接真实 Aeolus / Hive / ClickHouse。
- 本轮未发送真实通知，未写线上状态。

## 样例覆盖

| 样例 | 输入 | 模式 | 结论 |
| --- | --- | --- | --- |
| `ELR-P-001` | 近7天打标率和完审量趋势如何 | `label_rate_trend` | 通过 |
| `ELR-P-002` | 近7天打标率最高的策略有哪些 | `label_rate_ranking` | 通过 |
| `ELR-P-003` | 近7天有哪些高完审低打标的reason | `label_rate_ranking` | 通过 |
| `ELR-P-004` | 低打标率策略分 P0/P1/P2/notice | `low_label_rate_grading` | 通过 |
| `ELR-P-005` | 按机审一级标签拆一下打标率 | `dimension_breakdown` | 通过 |
| `ELR-P-006` | 按业务线看打标率 | `dimension_discovery` | 通过 |
| `ELR-N-001` | 自动处置准确率下降 | 反例拒绝 | 通过 |
| `ELR-N-002` | 质检准确率下降 | 反例拒绝 | 通过 |
| `ELR-L-001` | 这个策略怎么了 | 低信息量澄清 | 通过 |

## QueryPlan 输出要求

本轮 QueryPlan 已包含：

- `scenario_key`
- `task_type`
- `analysis_mode`
- `metric_id`
- `time_range`
- `dimensions`
- `filters`
- `source_priority`
- `allowed_sources`
- `forbidden_sources`
- `fallback_reason`
- `quality_checks`
- `review_required`
- `execution_mode=no_real_query`

## source_footer 输出要求

本轮 source_footer 已包含：

- `source_tier`
- `metric_definition_version`
- `data_freshness`
- `owner`
- `confidence_tier`
- `review_status`

## 后续动作

阶段 1 后续可以继续做：

- 接入 mock / 只读 Tool，生成 tool_call_record。
- 引入真实 Semantic Layer / Aeolus 指标 ID。
- 将角色级 Owner 替换为具体治理 Owner、群或值班机制。
- 在接真实查询前继续保持 `debug_only`。
