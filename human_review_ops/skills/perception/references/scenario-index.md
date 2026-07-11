# 感知 Skill 场景索引

感知 Skill 运行时只加载当前 Skill 内部的单场景文档，不引用外部场景包或旧拆分快照。

## efficiency-label-rate

- 场景文档：`scenarios/efficiency-label-rate.md`
- 指标对象：打标率
- 触发摘要：打标率、进审量、完审量、打标量、高 / 低打标 reason、P0/P1/P2/notice 低效策略分级、机审一级标签或策略维度拆解。
- 排除摘要：自动处置准确率、质检准确率、底线事故数、真实通知、闭环写状态、敏感明细导出。

## efficiency-auto-disposal-accuracy

- 场景文档：`scenarios/efficiency-auto-disposal-accuracy.md`
- 指标对象：自动处置准确率 / 一级标签准确率 / 三级标签准确率 / 机审自动处置准确率
- 触发摘要：自动处置准确率下降、波动、撞线预警，按一级标签、三级标签、是否安全治理域、权重类型或日期拆解。
- 排除摘要：打标率、质检准确率、底线事故数、人工审核准确率、真实通知、闭环写状态、敏感明细导出。

## quality-inspection-accuracy

- 场景文档：`scenarios/quality-inspection-accuracy.md`
- 指标对象：质检准确率 / 审核准确率 / 通过准确率 / 打标准确率
- 触发摘要：质量领域质检准确率，大盘（不含举报）质检准确率，按队列分类汇总或队列分类（上游+群组）拆解。
- 排除摘要：打标率、自动处置准确率、底线事故数、人工审核准确率、真实通知、闭环写状态、敏感明细导出。
