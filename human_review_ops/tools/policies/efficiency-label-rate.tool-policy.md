# 工具策略：打标率

## 调试阶段默认策略

- 默认 `debug_only`。
- 默认只读。
- 默认不发送真实通知。
- 默认不写线上状态。
- 默认不执行配置变更。

## 允许

- 读取本地场景包。
- 读取 Skill 内调试快照。
- 生成 QueryPlan。
- 生成 source_footer。
- 生成打标率趋势、排序、低打标率分级或维度拆解的查询计划。
- 生成通知草稿。
- 记录调试检查清单。

## 需要人工确认

- 调用真实 Semantic Layer、Aeolus、Hive 或 ClickHouse 查询。
- 运行会产生线上副作用的 CLI。
- 上传或发送正式报表。
- 发送飞书消息。
- 写入 Lark Base 或其他状态存储。
- 创建或更新工单。

## 禁止

- 自动修改策略配置。
- 自动审批。
- 自动删除或覆盖场景包。
- 输出未脱敏线上明细。
- 查询审核员个人敏感信息。
- 把查询失败解释为“无异常”或“无低打标率策略”。

## tool_call_record 要求

进入真实只读查询前，必须记录：

- `tool_name`
- `source_tier`
- `scenario_key`
- `metric_id`
- `permission_level`
- `review_required`
- `fallback_reason`
- `status`
