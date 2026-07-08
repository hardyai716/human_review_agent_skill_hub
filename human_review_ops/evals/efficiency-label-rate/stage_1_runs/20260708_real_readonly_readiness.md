# 阶段 1 P1 真实只读 Tool 接入准备度检查：打标率

## 基础信息

- 调试日期：2026-07-08
- 场景：`efficiency-label-rate`
- 原则：YAGNI
- 运行脚本：`human_review_ops/tools/runners/run_stage_1_real_readonly_readiness.py`
- 校验脚本：`human_review_ops/tools/validators/validate_stage_1_real_readonly_readiness.py`
- 结果文件：`20260708_real_readonly_readiness.json`

## 运行结论

当前状态：`blocked`。

结论：当前不应开发真实只读查询适配器。原因不是链路缺代码，而是缺真实治理资产和可执行工具绑定；继续写通用适配层会违反 YAGNI 原则。

## 阻断项

| check_id | 阻断原因 | 证据 |
| --- | --- | --- |
| `real_semantic_metric_id` | 缺真实 Semantic Layer 指标 ID | 未找到 `semantic_metric_id` / `canonical_metric_id` |
| `governed_dataset_id` | 缺真实 Aeolus 治理数据集或报告 ID | 未找到 `aeolus_dataset_id` / `dataset_id` / 数据集 URL |
| `readonly_tool_binding` | 缺预注册只读 Tool / MCP / CLI 绑定 | 工具策略中未声明真实只读执行命令 |

## 已满足项

- 本地指标契约已定义 `label_rate` 和公式。
- 受控 raw source 已记录：`olap_content_security_community.dws_sft_tcs_review_task_detail_di`。
- freshness gate 已定义：`MAX(p_date)` 和目标分区行数。
- 字段映射已覆盖 reason、日期、场景、机审一级标签、完审量、打标量等核心字段。
- 敏感明细和人员字段已排除。

## 风险提示

- Owner 仍是角色级 Owner，当前作为 warning，不阻断 mock 链路。
- 进入真实只读 Tool 前，应补具体 Owner 或明确批准的值班/群机制。

## 下一步需要输入

- 真实 Semantic Layer metric ID 或 Aeolus dataset/report ID。
- 预注册只读 Tool / MCP / CLI 命令。
- 具体数据 / 指标 Owner，或明确的 Owner 兜底机制。

## YAGNI 决策

在以上阻断项补齐前，不开发真实只读适配器、不设计通用查询框架、不增加未来可能用到的抽象。
