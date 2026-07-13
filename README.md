# Human Review Agent Skill Hub

人审运营 Agent + Skill + Tool/MCP/CLI 重构项目。

本仓库用于沉淀：

- 人审运营调度 Agent 的身份、路由、权限和调试配置。
- 感知、分析、通知、解决四类通用 Skill。
- 打标率场景级 Skill：`efficiency-label-rate-ops`。
- 人审运营场景流程包和评估样例。
- TRAE 自定义调试智能体「人审运营智能体」的调试记录与检查清单。

当前开发主计划见：

- `docs/implementation_plan.md`

运行态开发产物统一放在：

- `human_review_ops/`

当前阶段目标：

1. 维护效率模块样板主线：`efficiency-label-rate`。
2. 保留 `efficiency-auto-disposal-accuracy` 作为相邻场景和误触发校验。
3. 以 `efficiency-label-rate-ops` 作为打标率场景级 Skill canonical path，旧四能力 Skill 保留 legacy compatibility path。
4. 使用 `skill_path_registry.json` 和 resolver 管理 `auto/canonical/legacy` 路径模式。
5. 真实通知、在线表格导入、线上状态写入均保持显式确认或 opt-in。
