# Claude 自助数据分析实践框架资料包

来源：

- 文章：How Anthropic enables self-service data analytics with Claude
- 链接：https://claude.com/blog/how-anthropic-enables-self-service-data-analytics-with-claude
- 官方发布日期：2026-06-03

说明：

本文档包不是对原文的全文复制，而是面向“人审运营 Agent + Skill 重构”项目整理出的可执行实践框架。内容保留原文的核心方法论，并转换为适合本项目落地的中文结构。

## 核心判断

Claude 官方实践的核心结论是：

> 数据分析 Agent 的准确性问题，本质上不是 SQL 生成问题，而是上下文、实体映射和验证问题。

在人审运营场景中，这意味着 Agent 不能直接自由找表、自由选字段、自由写查询。它必须先完成：

1. 把业务问题映射到唯一治理指标或治理数据实体。
2. 优先使用语义层、指标注册表、场景指标契约和治理数据集。
3. 使用场景 reference 限定可用表、字段、粒度、过滤条件和禁止数据源。
4. 查询前生成 QueryPlan。
5. 查询后做数据质量检查和来源脚注。
6. 高风险结论做复核。
7. 用离线评估和线上纠错持续维护。

## 本资料包结构

| 文件 | 用途 |
| --- | --- |
| `01_failure_modes.md` | 总结数据分析 Agent 的主要失败模式。 |
| `02_agentic_analytics_stack.md` | 总结官方推荐的 agentic analytics stack。 |
| `03_skill_reference_framework.md` | 总结 Knowledge Skill、Runbook Skill、Reference Docs 的组织方式。 |
| `04_validation_framework.md` | 总结离线评估、消融实验、线上验证和纠错回收机制。 |
| `05_templates.md` | 提供可复用的 Skill 和 reference 文档模板。 |
| `06_human_review_ops_mapping.md` | 把 Claude 框架映射到人审运营感知/分析模块。 |

## 对本项目的直接影响

本资料包应作为以下文档的设计依据：

- `docs/data_query_governance.md`
- `docs/skill_interface_and_tool_mcp_spec.md`
- `docs/daily_ops_scenario_scope.md`
- 各场景流程包中的 `metric_contract.md`
- 各场景流程包中的 `analysis.md`
- 后续离线评估集和回测机制
