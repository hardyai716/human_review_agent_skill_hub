---
name: routing-ops-notifications
description: Drafts human-review operations notifications, POC routing plans, and escalation messages without sending real notifications in debug mode.
allowed-tools: []
disallowed-tools:
  - write
---

# 通知 Skill

## 触发条件

当用户需要生成预警通知草稿、测试卡片、POC / 触达对象路由计划或升级话术时使用。

## 输入

- 分析结果。
- `scenario_key`
- 风险等级。
- POC / 触达对象候选。

## 输出

- 通知草稿。
- 飞书 Card 2.0 草稿。
- POC / 触达对象路由计划。
- 升级建议。
- 证据引用。

## 调试约束

- 默认不发送真实通知。
- 默认只生成草稿。
- 真实发送必须人工确认。

## 参考资料

- `references/common.md`
- `references/scenario-index.md`
- `assets/efficiency-label-rate/low_efficiency_grading_card_template.json`
- `assets/efficiency-label-rate/card_schema_notes.md`
- `scripts/render_label_rate_grading_card.py`
- `scripts/resolve_label_rate_poc_routing.py`
- `scripts/card_hash.py`
