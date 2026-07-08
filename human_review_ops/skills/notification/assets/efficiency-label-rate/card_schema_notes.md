# 打标率分级卡片结构说明

## 用途

用于将 `efficiency-label-rate` 场景的 notice/P2/P1/P0 分级结果渲染为飞书 Card 2.0。

## 结构

- Header：报告标题、时间窗口、全等级标签。
- Metrics：P0、P1、P2、notice 四个等级命中数。
- Chart：各等级命中 reason 数柱状图。
- Table：综合结果 Top reason，按 `P0 > P1 > P2 > notice` 展示最高等级。
- Button：跳转完整飞书电子表格。
- Methodology：折叠展示数据集、窗口、打标率口径、fallback reason 和来源。

## 安全约束

- 卡片草稿保留 `_meta._data_hash`，用于校验卡片与命中数据一致。
- 发送前必须使用 `strip_internal_keys()` 剥离 `_meta`。
- 默认只生成草稿；真实发送必须由用户明确要求。
- 群推送和 Owner 定向通知属于后续能力；当前阶段优先支持单人预览。
