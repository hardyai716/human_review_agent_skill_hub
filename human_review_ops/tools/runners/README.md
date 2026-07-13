# Runners

本目录存放只读、可回放的阶段性运行脚本。

## 当前脚本

- `run_stage_1_real_readonly_label_rate.py`：使用 `bytedcli -j aeolus query -r cn 3888816` 执行真实只读打标率查询，支持 `--days`、`--dimensions` 和 `--query-mode` 参数。
- `run_stage_1_real_readonly_label_rate_grading.py`：使用真实只读 Aeolus 查询执行低打标率 notice/P2/P1/P0 分级，输出等级结果、综合去重结果和 provenance。
- `run_stage_2_label_rate_notification_draft.py`：将阶段 1 低打标率分级结果转换为通知草稿产物、xlsx、飞书 Card 2.0；工作簿包含 P0/P1/P2/Notice/综合/汇总统计，Card 按 P0/P1/P2/Notice 分表展示 Top10，并可在用户明确要求时单人或测试群推送。
- `run_stage_2_label_rate_poc_routing.py`：基于阶段 1 低打标率分级结果，按 `mach_root_label_name` 生成姓名级 POC / 触达对象路由产物；真实触达前仍需 open_id 确认、目标群确认和发送门禁。
- `run_custom_label_rate_breakdown_e2e.py`：执行自定义多维低打标率查询，默认输出汇总、TopN、CSV/XLSX、飞书电子表格和按机审一级标签生成的 POC 路由计划；仅显式传入 `--send-chat-id` 时才发送群消息。
- `run_label_rate_formal_flow.py`：正式 Skill-first 编排入口。先调用 perception 识别复合诉求和前置 analysis 任务，再用 analysis Skill 生成 QueryPlan/SQL 并执行只读查询，最后用 notification Skill 生成通知产物；真实群发只在宿主层显式 `--confirm-send` 后执行，并生成 `host_dispatch_record.json`。
- `demo_aeolus_viz_query_vs_query.py`：演示同一个 Aeolus 查询任务分别用 `aeolus viz-query` 和 `aeolus query` 执行；默认 dry-run 打印命令，传 `--execute` 才真实查询。

## 使用约束

- 默认 runner 不连接真实 Aeolus / Hive / ClickHouse；名称带 `real_readonly` 的 runner 只允许连接治理后的只读数据源。
- runner 不发送通知，不写线上状态。
- runner 只读取场景包和 eval 样例，生成结构化调试结果。
- 涉及可空维度聚合时，必须先生成内部 `*_key` 字段再 `GROUP BY`，例如 `mach_root_label_key`、`strategy_id_key`、`strategy_name_key`、`reason_key`；不要把 `ifNull(...)` 的别名写成底表字段名或输出字段名，否则 Aeolus / ClickHouse 可能解析到原始字段，漏掉 NULL 维度桶。

## 示例

```bash
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
python3 human_review_ops/tools/runners/run_custom_label_rate_breakdown_e2e.py --start-date 2026-06-29 --end-date 2026-07-05
python3 human_review_ops/tools/validators/validate_custom_label_rate_breakdown_e2e.py
python3 human_review_ops/tools/validators/validate_label_rate_poc_mapping.py
python3 human_review_ops/tools/runners/run_label_rate_formal_flow.py --send-chat-id oc_9c691aa76c22a16207c6f443eac25816 --confirm-send
python3 human_review_ops/tools/validators/validate_label_rate_formal_flow.py human_review_ops/evals/efficiency-label-rate/stage_2_runs/<run_id>_formal_skill_flow --expect-sent
python3 human_review_ops/tools/runners/demo_aeolus_viz_query_vs_query.py
python3 human_review_ops/tools/runners/demo_aeolus_viz_query_vs_query.py --execute
```
