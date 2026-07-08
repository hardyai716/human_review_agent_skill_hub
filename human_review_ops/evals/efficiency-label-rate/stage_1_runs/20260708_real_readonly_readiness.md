# 阶段 1 P1 真实只读 Tool 接入准备度检查：打标率

## 基础信息

- 调试日期：2026-07-08
- 场景：`efficiency-label-rate`
- 原则：YAGNI
- 运行脚本：`human_review_ops/tools/runners/run_stage_1_real_readonly_readiness.py`
- 校验脚本：`human_review_ops/tools/validators/validate_stage_1_real_readonly_readiness.py`
- 结果文件：`20260708_real_readonly_readiness.json`

## 运行结论

当前状态：`ready`。

结论：真实只读查询入口已确认，可基于现有风神数据集执行 `label_rate` 查询。继续开发时应直接复用该入口，不再额外设计通用查询框架。

## 已确认入口

| 项目 | 值 |
| --- | --- | --- |
| Region | `cn` |
| App ID | `1128` |
| Dataset ID | `3888816` |
| Dataset | `[重点模型]-社区_人工审核明细数据` |
| 查询命令 | `bytedcli -j aeolus query -r cn 3888816 "<SQL>" --limit 1000` |
| 打标率指标 | `打标率__reviewid` |
| Aeolus metric ID | `10000036292379` |

## 已满足项

- 本地指标契约已定义 `label_rate` 和公式。
- 受控 raw source 已记录：`olap_content_security_community.dws_sft_tcs_review_task_detail_di`。
- freshness gate 已定义：`MAX(p_date)` 和目标分区行数。
- 字段映射已覆盖 reason、日期、场景、机审一级标签、完审量、打标量等核心字段。
- 敏感明细和人员字段已排除。
- 只读工具绑定已确认：`bytedcli -j aeolus query`。

## 风险提示

- Owner 仍是角色级 Owner，当前作为 warning，不阻断 mock 链路。
- 进入真实只读 Tool 前，应补具体 Owner 或明确批准的值班/群机制。

## 下一步

- 将 mock 只读执行 runner 替换为基于 `bytedcli -j aeolus query` 的真实只读执行。
- 保留 QueryPlan、tool_call_record、analysis_result、source_footer 和 provenance 契约。
- 补具体数据 / 指标 Owner，或明确的 Owner 兜底机制。

## YAGNI 决策

直接复用已确认的风神数据集和 `bytedcli aeolus query` 能力，不设计额外通用查询框架。
