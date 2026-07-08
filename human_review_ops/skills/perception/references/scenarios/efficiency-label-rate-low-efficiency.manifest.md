# 场景清单：效率模块 / 打标率低效 reason 分析

## 场景标识

- `scenario_key`：`efficiency-label-rate-low-efficiency`
- 模块：效率模块
- 指标对象：打标率
- 运营对象：高完审、低打标的送审 reason / 策略
- 当前状态：阶段 1 主线样板场景

## 参考来源

本场景只吸收以下已验证 Skill 中与打标率流程直接相关的内容：

- `.trae/skills/warehouse-skill/`：数据治理、Semantic Layer first、provenance、字段映射和数据质量 gate。
- `.trae/skills/low-efficiency-strategy-analysis/`：低效 reason 分级、维度拆解和输出结构。

不直接迁移旧 Skill 的完整实现、历史目录结构或在线工具权限。

## 触发意图

- 近 N 天有哪些高完审、低打标 reason。
- 打标率低的策略 / reason 是否需要分级。
- notice、P2、P1、P0 低效策略清单。
- 按机审一级标签、场景、项目等维度拆解低效 reason。
- 查询打标率、进审量、完审量、打标量趋势，并要求可复核口径。

## 排除意图

- 自动处置准确率分析。
- 质检准确率分析。
- 底线事故数分析。
- 审核员个人明细、手机号、open_id 等敏感明细导出。
- 责任人触达、建群、工单推进等后续运营流转。

## 默认运行约束

- 第一阶段默认 `debug_only`。
- 默认只读。
- 默认先生成 QueryPlan，不直接执行真实查询。
- 真实 Aeolus / Hive 查询、飞书触达、状态写入都必须人工确认。
- 数据未就绪、权限不足、口径不清时停止，不输出“无异常”结论。
