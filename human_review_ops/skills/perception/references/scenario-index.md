# 感知 Skill 场景索引

感知 Skill 运行时只加载当前 Skill 内部的单场景文档，不引用外部场景包或旧拆分快照。

## efficiency-label-rate

- 场景文档：`scenarios/efficiency-label-rate.md`
- 指标对象：打标率
- 触发摘要：打标率、进审量、完审量、打标量、高 / 低打标 reason、P0/P1/P2/notice 低效策略分级、机审一级标签或策略维度拆解。
- 排除摘要：自动处置准确率、质检准确率、底线事故数、真实通知、闭环写状态、敏感明细导出。

## efficiency-auto-disposal-accuracy

- 场景文档：`scenarios/efficiency-auto-disposal-accuracy.md`
- 指标对象：自动处置准确率
- 触发摘要：自动处置准确率下降、波动、撞线预警，按策略、队列、风险域、三级标签拆解。
- 排除摘要：打标率、质检准确率、底线事故数、人工审核准确率、真实通知、闭环写状态、敏感明细导出。
