# 通知模板：打标率

## 调试阶段原则

- 只生成通知草稿。
- 不发送真实飞书消息。
- 不创建群。
- 不写入状态。

## 低打标率策略预警草稿

```text
【人审效率预警｜低效策略 / 风险域】

场景：{scenario_key}
等级：{severity}
周期：{time_window}

摘要：
{summary}

证据：
- 预警维度：{warning_dimension}
- 机审一级标签：{mach_root_label_name}
- 策略ID：{strategy_id}
- 策略名称：{strategy_name}
- 日均进审量：{avg_review_in_cnt}
- 日均完审量：{avg_review_done_cnt}
- 日均打标量：{avg_label_cnt}
- 打标率：{label_rate}
- 命中规则：{hit_rule_id}
- 命中条件：{hit_condition}
- 是否+1同意：{is_plus1_agreed}
- 更新日期：{plus1_update_date}

建议 Owner：{owner}
Owner 依据：{routing_evidence}
置信度：{confidence}

说明：
- 本通知为 debug_only 草稿，未真实发送。
- 打标率口径：打标量 / 完审量。
- 风险域维度行的策略ID、策略名称可为空，POC 按机审一级标签映射。
- source_footer：{source_footer}
```

## 打标率维度拆解摘要草稿

```text
【人审效率分析｜打标率维度拆解】

维度：{dimensions}
周期：{time_window}

核心发现：
{summary}

TOP 低效组合：
{top_dimension_reason_rows}

限制说明：
{limitations}

本结果仅为调试草稿，真实触达前需要人工确认。
```

## 举报流转低打标率摘要草稿

```text
【人审效率分析｜举报场景低打标率】

数据方向：report_flow / 举报流转
数据集：举报流转任务明细数据集（3952594 / appId 555137）
周期：{time_window}

核心发现：
{summary}

低打标率 enpool_reason：
{top_enpool_reason_rows}

口径：
- 时间字段：进审日期
- 打标率：打标量_report_id / 人审完结量_report_id
- 基础筛选：举报专项一轮/终轮队列范围 + 任务类型 + 一轮队列排除兜底/海外/特殊

限制说明：
{limitations}

本结果仅为调试草稿，真实触达前需要人工确认。
```

## 升级草稿

```text
【需人工确认｜打标率分析】

触发原因：{review_reason}
待确认事项：
1. 指标口径是否确认。
2. 数据分区是否就绪。
3. Owner 是否准确。
4. 是否允许真实触达或线上状态写入。

当前不会发送真实通知或写入线上状态。
```
