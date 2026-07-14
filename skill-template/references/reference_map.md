# 引用地图

所有路径都以 Skill 根目录为基准。禁止绝对路径、IDE 私有路径和项目外引用。

## 运行加载

1. `SKILL.md`
2. `references/scenario_contract.md`
3. 需要了解文件边界时读本文件
4. 需要产物时读 `assets/` 或运行 `scripts/scenario_flow.py`

## 文件分工

| 文件 | 职责 |
| --- | --- |
| `SKILL.md` | 触发、红线、工作流。 |
| `references/scenario_contract.md` | 唯一业务契约：场景、口径、数据、分析、通知、解决、失败分支。 |
| `assets/test-prompts.template.json` | 触发、反触发、越权样例。 |
| `assets/owner_mapping.template.json` | Owner 路由模板，不存敏感身份。 |
| `assets/notification_card_template.json` | Card 结构模板，不代表已发送。 |
| `scripts/scenario_flow.py` | 本地 dry-run 产物生成。 |
| `scripts/selfcheck.py` | 结构、安全边界和 dry-run 自检。 |

## 维护规则

- 业务口径只写 `scenario_contract.md`。
- `SKILL.md` 不复制字段、阈值、模板正文。
- assets 放机器可读模板，不放解释长文。
- scripts 默认无外部副作用；新增副作用必须同步写入 `SKILL.md` 和 manifest。
