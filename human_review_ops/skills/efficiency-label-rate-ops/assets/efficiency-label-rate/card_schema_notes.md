# 打标率分级卡片结构说明

## 用途

用于将 `efficiency-label-rate` 场景的 notice/P2/P1/P0 分级结果渲染为飞书 Card 2.0。

## 结构

- Header：报告标题、时间窗口、全等级标签。
- Metrics：P0、P1、P2、notice 四个等级命中数。
- Summary Table：机审一级标签 × POC 汇总统计。
- Level Tables：各等级 TopN 明细，按 `P0 > P1 > P2 > notice` 展示最高等级。
- Button：跳转完整飞书电子表格。
- Methodology：折叠展示数据集、窗口、打标率口径、默认三维分级粒度、reason 显式拆解规则、fallback reason 和来源。

当前 Card 不包含 chart 元素。默认分级粒度为 `机审一级标签 × 策略ID × 策略名称`；`reason` 仅在用户明确要求维度拆解时作为分组字段，不作为默认分级或卡片图表契约。

## 安全约束

- 卡片草稿保留 `_meta._data_hash`，用于校验卡片与命中数据一致。
- 发送前必须使用 `strip_internal_keys()` 剥离 `_meta`。
- 默认只生成草稿；真实发送必须由用户明确要求。
- 群推送和 Owner 定向通知属于后续能力；当前阶段优先支持单人预览。
