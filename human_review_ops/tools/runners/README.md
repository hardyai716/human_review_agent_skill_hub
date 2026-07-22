# Runners

本目录存放只读、可回放的阶段性运行脚本。

## 当前脚本

- `run_stage_1_real_readonly_label_rate.py`：使用 `bytedcli -j aeolus query -r cn 3888816` 执行真实只读打标率查询，支持 `--days`、`--dimensions` 和 `--query-mode` 参数。
- `run_stage_1_real_readonly_label_rate_grading.py`：使用真实只读 Aeolus 查询执行低打标率 notice/P2/P1/P0 分级，输出等级结果、综合去重结果和 provenance。
- `run_stage_2_label_rate_notification_draft.py`：将阶段 1 低打标率分级结果转换为通知草稿产物、xlsx、飞书 Card 2.0；工作簿包含 P0/P1/P2/Notice/综合/综合_剔除+1同意/汇总统计/汇总统计_剔除+1同意，Card 按 P0/P1/P2/Notice 分表展示 Top10，并可在用户明确要求时单人或测试群推送。
- `run_stage_2_label_rate_poc_routing.py`：基于阶段 1 低打标率分级结果，按 `mach_root_label_name` 生成姓名级 POC / 触达对象路由产物；真实触达前仍需 open_id 确认、目标群确认和发送门禁。
- `run_custom_label_rate_breakdown_e2e.py`：执行自定义多维低打标率查询，默认输出汇总、TopN、CSV/XLSX、飞书电子表格和按机审一级标签生成的 POC 路由计划；仅显式传入 `--send-chat-id` 时才发送群消息。
- `run_label_rate_formal_flow.py`：正式 Skill-first 编排入口。先调用 perception 识别复合诉求和前置 analysis 任务，再用 analysis Skill 生成 QueryPlan/SQL 并执行只读查询，最后用 notification Skill 生成通知产物；支持 `--data-direction manual_review_detail|report_flow|combined|auto`，其中 `combined` 会分别执行人审明细与举报流转两套全等级查询后合并；真实群发只在宿主层显式 `--confirm-send` 后执行，并生成 `host_dispatch_record.json`。
- `run_label_rate_weekly_summary_comparison.py`：输入两个显式周期，分别执行全等级只读分级，读取两个 `汇总统计_剔除+1同意.csv` 后生成截图式周对比 XLSX；仅传 `--import-sheet` 才导入飞书表格，仅同时传目标、`--confirm-send` 才发送链接。
- `demo_aeolus_viz_query_vs_query.py`：演示同一个 Aeolus 查询任务分别用 `aeolus viz-query` 和 `aeolus query` 执行；默认 dry-run 打印命令，传 `--execute` 才真实查询。

## 使用约束

- 默认 runner 不连接真实 Aeolus / Hive / ClickHouse；名称带 `real_readonly` 的 runner 只允许连接治理后的只读数据源。
- runner 不发送通知，不写线上状态。
- runner 只读取场景包和 eval 样例，生成结构化调试结果。
- 涉及可空维度聚合时，必须先生成内部 `*_key` 字段再 `GROUP BY`，例如 `mach_root_label_key`、`strategy_id_key`、`strategy_name_key`、`reason_key`；不要把 `ifNull(...)` 的别名写成底表字段名或输出字段名，否则 Aeolus / ClickHouse 可能解析到原始字段，漏掉 NULL 维度桶。

## 示例

```bash
python3 human_review_ops/tools/runners/run_stage_1_real_readonly_label_rate.py --days 14
python3 human_review_ops/tools/runners/run_stage_1_real_readonly_label_rate.py --days 7 --start-date 2026-07-06 --end-date 2026-07-12
python3 human_review_ops/tools/validators/validate_stage_1_real_readonly_label_rate.py --days 14
python3 human_review_ops/tools/runners/run_stage_1_real_readonly_label_rate.py --days 14 --dimensions reason --query-mode group_count
python3 human_review_ops/tools/validators/validate_stage_1_real_readonly_label_rate.py --days 14 --dimensions reason --query-mode group_count
python3 human_review_ops/tools/runners/run_stage_1_real_readonly_label_rate.py --days 14 --dimensions reason,scene
python3 human_review_ops/tools/validators/validate_stage_1_real_readonly_label_rate.py --days 14 --dimensions reason,scene --query-mode ranking
python3 human_review_ops/tools/runners/run_stage_1_real_readonly_label_rate_grading.py
python3 human_review_ops/tools/runners/run_stage_1_real_readonly_label_rate_grading.py --start-date 2026-07-06 --end-date 2026-07-12
python3 human_review_ops/tools/validators/validate_stage_1_real_readonly_label_rate_grading.py
python3 human_review_ops/tools/runners/run_stage_2_label_rate_notification_draft.py --sheet-url 'https://bytedance.larkoffice.com/sheets/dry_run_sheet_token'
python3 human_review_ops/tools/validators/validate_stage_2_label_rate_notification_draft.py
python3 human_review_ops/tools/runners/run_stage_2_label_rate_poc_routing.py
python3 human_review_ops/tools/validators/validate_stage_2_label_rate_poc_routing.py
python3 human_review_ops/tools/runners/run_custom_label_rate_breakdown_e2e.py --start-date 2026-06-29 --end-date 2026-07-05
python3 human_review_ops/tools/validators/validate_custom_label_rate_breakdown_e2e.py
python3 human_review_ops/tools/validators/validate_label_rate_poc_mapping.py
python3 human_review_ops/tools/runners/run_label_rate_formal_flow.py --send-chat-id oc_9c691aa76c22a16207c6f443eac25816 --confirm-send
python3 human_review_ops/tools/runners/run_label_rate_formal_flow.py --request '执行低效打标全等级结果，周期为 2026-07-06~2026-07-12，结果输出为飞书表格链接。' --no-import-workbook
python3 human_review_ops/tools/runners/run_label_rate_formal_flow.py \
  --data-direction combined \
  --start-date 2026-07-14 --end-date 2026-07-20 \
  --run-id 20260721_combined_0714_0720_full_levels \
  --no-import-workbook
python3 human_review_ops/tools/runners/run_stage_2_label_rate_notification_draft.py \
  --source human_review_ops/evals/efficiency-label-rate/stage_1_runs/20260721_combined_0714_0720_full_levels_formal_skill_flow_results.jsonl \
  --output-dir human_review_ops/evals/efficiency-label-rate/stage_2_runs/20260721_combined_0714_0720_full_levels_formal_skill_flow \
  --top-n 10 --import-workbook --send-user-id <open_id> --identity bot \
  --title '人审明细+举报流转低效打标全等级结果（2026-07-14~2026-07-20）'
python3 human_review_ops/tools/validators/validate_label_rate_formal_flow.py human_review_ops/evals/efficiency-label-rate/stage_2_runs/<run_id>_formal_skill_flow --expect-sent
python3 human_review_ops/tools/validators/validate_label_rate_combined_flow.py
python3 human_review_ops/tools/runners/run_label_rate_weekly_summary_comparison.py \
  --previous-start-date 2026-07-06 --previous-end-date 2026-07-12 \
  --current-start-date 2026-07-13 --current-end-date 2026-07-19 \
  --import-sheet --send-chat-id oc_9c691aa76c22a16207c6f443eac25816 --confirm-send
python3 human_review_ops/tools/runners/demo_aeolus_viz_query_vs_query.py
python3 human_review_ops/tools/runners/demo_aeolus_viz_query_vs_query.py --execute
```

## Combined 查询注意事项

- `combined` 结果用于把人审数据集打标率结果与举报场景结果合并交付；不要跨数据集拼接单条 SQL。
- `run_label_rate_formal_flow.py --data-direction combined` 会顺序执行 `manual_review_detail` 与 `report_flow`；任一数据源失败、超时或返回截断时，必须停止合并。
- 如果某一源超时，可单独重跑失败方向（例如 `--data-direction report_flow`），再用成功的 Stage 1 结果生成合并 Stage 1；合并后必须跑 `validate_label_rate_combined_flow.py`。
- 飞书导入与发送建议拆成两步：先跑 formal flow 生成 Stage 1，再用 `run_stage_2_label_rate_notification_draft.py --import-workbook --send-user-id <open_id>` 导入并私聊推送。
- 如果 workbook 已导入但 Card 发送失败，重试时传 `--sheet-url <已生成的表格链接>`，避免重复创建飞书表格。
