# 分析 Skill 场景索引

本索引只指向 Skill 内部运行态资料。不要从这里跳转到 `human_review_ops/references/` 外部场景包。

## 加载规则

1. 先读 `references/common.md`。
2. 按 `scenario_key` 从下表定位唯一场景文档。
3. 只读取命中场景文档；需要公共方法时再读 `references/methods/*.md`。
4. 不再读取同场景四件套文件。

## 场景表

| `scenario_key` | 场景文档 | 指标 | 主要任务类型 | 脚本 |
| --- | --- | --- | --- | --- |
| `efficiency-label-rate` | `scenarios/efficiency-label-rate.md` | `label_rate`、`review_in_cnt`、`review_done_cnt`、`label_cnt` | `label_rate_trend`、`label_rate_ranking`、`low_label_rate_grading`、`dimension_breakdown`、`weighted_attribution` | `../scripts/label_rate_analysis.py` |
| `efficiency-auto-disposal-accuracy` | `scenarios/efficiency-auto-disposal-accuracy.md` | `auto_disposal_accuracy` | `accuracy_trend`、`accuracy_ranking`、`dimension_breakdown` | 待补充 |

## 公共方法

| 方法 | 文档 | 适用场景 |
| --- | --- | --- |
| QueryPlan 生成 | `methods/query_plan.md` | 所有场景 |
| source_footer | `methods/source_footer.md` | 所有场景 |
| 加权归因 | `methods/weighted_attribution.md` | 比率类指标，当前默认用于打标率下探 |
