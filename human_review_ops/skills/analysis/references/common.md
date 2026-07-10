# 分析通用规则

- 查询前必须生成 QueryPlan。
- QueryPlan 必须引用命中的单一场景文档。
- 输出必须包含 source_footer。
- 禁止使用未授权、废弃或混淆字段。
- 禁止读取 Skill 外部的 `human_review_ops/references/` 作为运行态口径。
- 每次只加载一个 `references/scenarios/<scenario_key>.md`。
- 用户覆盖样本池、新增维度或要求真实执行时，必须在 QueryPlan 和 source_footer 中标记人工确认。
- 比率类指标必须用分子和分母重算，不得平均或加总比率字段。
- 查询失败、权限失败、字段失败、分区未就绪时停止，不输出业务结论。

## 目录约定

```text
references/
  common.md
  scenario-index.md
  methods/
    query_plan.md
    source_footer.md
    weighted_attribution.md
  scenarios/
    <scenario_key>.md
```

场景文档是运行态唯一场景资料。公共方法只放跨场景复用规则，不放单一指标口径。
