# 评估策略

## 第一阶段评估目标

- 场景识别正确。
- 任务类型识别正确。
- Skill 调用路径正确。
- 场景包读取路径正确。
- QueryPlan 和 source_footer 完整。
- 低置信度、反例和混淆字段能被阻断或转人工确认。

## 样例来源

- `human_review_ops/evals/efficiency-auto-disposal-accuracy/eval_samples.jsonl`
- `human_review_ops/evals/efficiency-auto-disposal-accuracy/expected_outputs.md`
- `human_review_ops/evals/efficiency-auto-disposal-accuracy/query_plan_assertions.md`
- `human_review_ops/evals/efficiency-label-rate/eval_samples.jsonl`
- `human_review_ops/evals/efficiency-label-rate/expected_outputs.md`
- `human_review_ops/evals/efficiency-label-rate/query_plan_assertions.md`

## 阻断条件

- 正例无法命中目标场景。
- 反例误命中目标场景。
- 输出缺少 QueryPlan。
- 输出缺少 source_footer。
- 命中混淆字段后仍继续分析。
- 调试阶段尝试发送真实通知或写线上状态。

## 通过标准

- 样板场景正例命中率达到标准。
- 反例拒绝率达到标准。
- 混淆字段拒绝率达到标准。
- 每次失败都有可复盘记录。
