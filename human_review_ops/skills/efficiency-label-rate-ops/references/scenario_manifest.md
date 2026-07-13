# 场景清单：效率模块 / 打标率

## 场景标识

- `scenario_key`：`efficiency-label-rate`
- 模块：效率模块
- 指标对象：打标率
- 运营对象：送审原因 / reason、举报入池原因 / enpool_reason 在不同维度下的打标率表现
- 当前状态：阶段 1 主线样板场景

## 数据方向

本场景下存在两个已治理数据方向，二者共用打标率业务语义，但数据集、字段和默认筛选不同。感知阶段必须识别 `data_direction`，分析阶段必须按方向选择对应 source profile，不得混用字段。

| `data_direction` | source profile | 数据集 | 适用问题 | 主维度 | 口径摘要 |
| --- | --- | --- | --- | --- | --- |
| `manual_review_detail` | `community_manual_review` | `[重点模型]-社区_人工审核明细数据` / `3888816` / appId `1128` | 人工审核明细、策略、机审一级标签、`reason` 维度的打标率查询和低效策略治理。 | `reason`、`mach_root_label_name`、`strategy_id`、`strategy_name` | `打标量__reviewid / 完审量_reviewid` |
| `report_flow` | `report_flow_review` | `举报流转任务明细数据集` / `3952594` / appId `555137` | 举报场景、举报流转、`enpool_reason`、`report_id`、一轮/终轮队列维度的打标率查询。 | `enpool_reason` | `打标量_report_id / 人审完结量_report_id` |

## 参考来源

本场景只吸收以下已验证 Skill 中与打标率流程直接相关的内容：

- `.trae/skills/warehouse-skill/`：数据治理、Semantic Layer first、provenance、字段映射和数据质量 gate。
- `.trae/skills/low-efficiency-strategy-analysis/`：低打标率分级、维度拆解和输出结构。

不直接迁移旧 Skill 的完整实现、历史目录结构或在线工具权限。

## 触发意图

- 查询打标率、进审量、完审量、打标量趋势，并要求可复核口径。
- 查询高打标率或低打标率的策略 / reason。
- 按机审一级标签、场景、项目等维度拆解打标率。
- 查询举报场景下的打标率、低打标率 `enpool_reason`、举报流转任务的进审 / 人审完结 / 打标量。
- 近 N 天有哪些高完审、低打标 reason。
- 打标率低的策略 / reason 是否需要分级。
- notice、P2、P1、P0 低效策略清单。

## 排除意图

- 自动处置准确率分析。
- 质检准确率分析。
- 底线事故数分析。
- 审核员个人明细、手机号、open_id 等敏感明细导出。
- 责任人触达、建群、工单推进等后续运营流转。

## 方向识别规则

- 命中 `举报`、`举报场景`、`举报流转`、`enpool_reason`、`report_id`、`一轮队列`、`终轮队列`、`举报流转任务明细数据集`、`3952594` 时，设置 `data_direction=report_flow`。
- 命中 `机审一级标签`、`策略ID`、`策略名称`、`reason` 且未出现举报相关字段时，默认 `data_direction=manual_review_detail`。
- 用户只说“打标率 reason”且上下文无举报字段时，默认 `manual_review_detail`；若同时出现 `举报` 或 `enpool_reason`，必须切换到 `report_flow`。
- 方向不唯一时，感知阶段应输出澄清问题，不得同时拼接两个数据源字段。

## 默认运行约束

- 第一阶段默认 `debug_only`。
- 默认只读。
- 默认先生成 QueryPlan；QueryPlan 通过断言后，可执行符合权限策略的 mock / 只读查询链路。
- 覆盖样本池、未治理字段、权限不足、真实飞书触达、状态写入或高风险动作必须人工确认。
- 数据未就绪、权限不足、口径不清时停止，不输出“无异常”结论。
