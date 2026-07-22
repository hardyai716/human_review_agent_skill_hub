# 样例：打标率

## 正例

### 查询低打标率 reason

输入：

```text
近 7 天有哪些高完审低打标的 reason？
```

期望：

- 命中 `efficiency-label-rate`。
- `task_type=dimension_breakdown`；`run_mode=query_only` 或 `partial_workflow`。
- 输出 QueryPlan 和 source_footer。
- 若需要低效分级，默认包含 notice/P2/P1/P0。

### 查询高打标率 reason

输入：

```text
近 7 天打标率最高的策略有哪些？
```

期望：

- 命中 `efficiency-label-rate`。
- 命中 `label_rate_ranking` 模式。
- 按打标率降序输出，并带进审量、完审量、打标量和打标率。
- 不套用低效分级。

### 分级分析

输入：

```text
帮我看下近 7 天低打标率策略分 P0/P1/P2/notice 的情况。
```

期望：

- 命中 `low_label_rate_grading` 模式。
- 输出四级分级规则摘要，默认包含 `单策略维度` 和 `风险域维度`。
- 单策略维度按 `机审一级标签 × strategy_id × strategy_name` 聚合；风险域维度按机审一级标签汇总低效策略，策略ID和策略名称为空。
- 说明打标率口径为打标量 / 完审量。

### 两周期剔除口径对比

输入：

```text
先跑 2026-07-06 至 2026-07-12 的全等级低效打标结果，再与 2026-07-13 至 2026-07-19 的汇总统计_剔除+1同意按截图格式对比，生成飞书表格并在确认后推送。
```

期望：

- 先分别执行两个显式周期的全等级只读分级，再读取每个周期的 `汇总统计_剔除+1同意`。
- 对比键为 `机审一级标签 × POC`，保留两个周期键的并集；单侧缺失补 `0`。
- 展示低效策略数、日均完审量、增量、增幅和加权打标率；总计打标率按 `SUM(日均打标量) / SUM(日均完审量)` 计算。
- 对比表冻结双层表头和前两列，正向日均完审增量标红，并写入溯源脚注。
- 未显式授权时只生成本地 XLSX 与发送草稿；在线导入和真实发送必须等待确认。

### 维度拆解

输入：

```text
按机审一级标签拆一下打标率。
```

期望：

- 命中 `dimension_breakdown` 模式。
- 读取 `mach_root_label_name` 维度。
- 输出 `dimensions × reason` 和 `dimensions` 汇总结构。

### 举报场景低打标率

输入：

```text
举报场景近七天打标率小于 10% 的 enpool_reason 有哪些？输出日均人审完结量、日均打标量和打标率。
```

期望：

- 命中 `efficiency-label-rate`。
- `data_direction=report_flow`，`source_profile=report_flow_review`，`task_type=low_label_rate_grading`。
- 使用 Dataset `3952594` / appId `555137`。
- 时间字段使用 `进审日期`。
- 输出字段结构与常规分级一致，其中 `机审一级标签=举报`，`策略ID=enpool_reason`，`策略名称=enpool_reason`。
- 不得走人工审核明细 Dataset `3888816`。

### 合并人审与举报结果

输入：

```text
把举报场景的全等级结果和人审数据集下的打标率结果合并到一起，并剔除 +1评估=同意。
```

期望：

- 设置 `data_direction=combined`，分别执行人审 `3888816` 与举报 `3952594` 的只读分级查询。
- 合并表新增 `数据来源` 列，取值为 `人审明细` / `举报流转`。
- `综合_剔除+1同意` 中，人审按 `strategy_id` 剔除，举报按“保持不变明细表”的 `reason` 匹配 `enpool_reason` 剔除。
- 举报风险域固定为 `举报`，并参与 P2/P1/P0 的风险域爆量规则。

推荐调用：

```bash
python3 human_review_ops/tools/runners/run_label_rate_formal_flow.py \
  --data-direction combined \
  --start-date 2026-07-14 \
  --end-date 2026-07-20 \
  --run-id 20260721_combined_0714_0720_full_levels \
  --no-import-workbook

python3 human_review_ops/tools/runners/run_stage_2_label_rate_notification_draft.py \
  --source human_review_ops/evals/efficiency-label-rate/stage_1_runs/20260721_combined_0714_0720_full_levels_formal_skill_flow_results.jsonl \
  --output-dir human_review_ops/evals/efficiency-label-rate/stage_2_runs/20260721_combined_0714_0720_full_levels_formal_skill_flow \
  --top-n 10 \
  --import-workbook \
  --send-user-id <open_id> \
  --identity bot \
  --title '人审明细+举报流转低效打标全等级结果（2026-07-14~2026-07-20）'
```

若表格已导入但卡片发送失败，第二条命令改用 `--sheet-url <已生成的飞书表格链接>`，不要重复导入 workbook。

### 用户指定未列举维度

输入：

```text
按业务线看打标率。
```

期望：

- 不直接猜字段。
- 先查 Semantic Layer / 数据集字段说明中是否存在业务线维度。
- 字段确认后再加入 QueryPlan。

## 反例

### 自动处置准确率

输入：

```text
分析一下自动处置准确率为什么下降。
```

期望：

- 不命中本场景。
- 提示这是自动处置准确率场景，不可用打标率替代。

### 质量准确率

输入：

```text
质检准确率下降了。
```

期望：

- 不命中本场景。
- 提示需要质量模块场景包。

### 底线事故

输入：

```text
底线事故数上升了。
```

期望：

- 不命中本场景。
- 提示需要底线事故监控场景包。

## 低信息量

输入：

```text
这个策略怎么了？
```

期望：

- 不直接查询。
- 先询问指标、时间窗口和策略 / reason。
- 不生成最终结论。
