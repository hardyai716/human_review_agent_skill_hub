# human_review_ops

本目录是人审运营 Agent + Skill 的运行态开发产物区。

放在这里的内容包括：

- `agents/`：人审运营调度 Agent 的身份、路由、权限和 TRAE 调试配置。
- `skills/`：感知、分析、通知、解决四类通用 Skill。
- `references/scenarios/`：目标态完整场景流程包，是长期唯一业务事实来源。
- `evals/`：样板场景评估样例和断言。
- `schemas/`：结构化输入输出契约。
- `tools/`：工具策略、打包脚本和校验脚本。
- `configs/`：状态机、评估和 Lark Base 配置草案。

根目录的 `docs/`、`demo/`、`references/claude_self_service_analytics_framework/` 保留为文档、演示和外部方法论参考，不直接作为运行态开发目录。
