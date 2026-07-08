# 能力清单

## 已启用 Skill

| Skill | 路径 | 状态 | 用途 |
| --- | --- | --- | --- |
| 感知 Skill | `human_review_ops/skills/perception/` | debug_enabled | 识别场景、指标、任务类型和数据就绪。 |
| 分析 Skill | `human_review_ops/skills/analysis/` | debug_enabled | 生成 QueryPlan、分析结论和 source_footer。 |
| 通知 Skill | `human_review_ops/skills/notification/` | debug_enabled | 生成通知草稿和 Owner 建议。 |
| 解决 Skill | `human_review_ops/skills/resolution/` | debug_enabled | 记录人工处理状态、结论和证据。 |

## 已启用场景

| 场景 | 路径 | 状态 |
| --- | --- | --- |
| 自动处置准确率 | `human_review_ops/references/scenarios/efficiency-auto-disposal-accuracy/` | debug_enabled |

## 调试约束

- 默认 `debug_only`。
- 默认只读。
- 真实通知和写状态必须人工确认。
