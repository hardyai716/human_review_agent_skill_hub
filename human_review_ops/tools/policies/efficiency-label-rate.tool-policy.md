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
- 调用 mock / 只读预检 Tool 并生成 `tool_call_record`。
- 在 QueryPlan 通过断言、数据源属于允许来源、工具权限为只读时，执行治理数据源的只读查询。
- 使用 `bytedcli -j aeolus query -r cn 3888816 "<SQL>" --limit 1000` 执行打标率只读查询。
- 生成通知草稿。
- 记录调试检查清单。

## 需要人工确认

- 覆盖标准样本池或绕过默认 A/B/C/D 过滤。
- 查询未治理来源、禁用来源或敏感明细。
- 使用未确认字段、未确认粒度或未确认 Owner 的扩展维度。
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
- `execution_mode`
- `real_query_executed`
- `status`

阶段 1 P1 中，`execution_mode` 可以为 `mock_readonly_no_real_query` 或未来的真实只读查询模式。mock 记录只能证明 QueryPlan 已通过预检，不得作为真实数据结论；真实只读查询记录必须同步写明数据来源、查询范围、指标口径、过滤条件和 source_footer。
