# Human Review Agent Skill Hub

人审运营 Agent + Skill + Tool/MCP/CLI 重构项目。

本仓库用于沉淀：

- 人审运营调度 Agent 的身份、路由、权限和调试配置。
- 感知、分析、通知、解决四类通用 Skill。
- 人审运营场景流程包和评估样例。
- TRAE 自定义调试智能体「人审运营智能体」的调试记录与检查清单。

当前开发主计划见：

- `docs/implementation_plan.md`

运行态开发产物统一放在：

- `human_review_ops/`

当前阶段目标：

1. 先跑通效率模块样板场景：`efficiency-auto-disposal-accuracy`。
2. 使用 TRAE 自定义智能体「人审运营智能体」完成前期调试。
3. 验证 Skill 能正确读取场景包、输出 QueryPlan 和 source_footer。
4. 在真实工具接入前，保持只读、mock 或人工确认模式。
