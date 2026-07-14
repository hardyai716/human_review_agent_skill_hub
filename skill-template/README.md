# 人审运营场景集 Skill 模板

这是场景级 Skill 的极简模板。它把四能力链路收敛为一个自包含 Skill：感知、只读分析、通知草稿、本地闭环。

## 原则

- 一个业务契约：`references/scenario_contract.md`。
- 一个执行脚本：`scripts/scenario_flow.py`。
- 一个自检脚本：`scripts/selfcheck.py`。
- 默认 `debug_only`，不真实查询、不发送、不写线上状态。

## 目录结构

```text
skill-template/
  SKILL.md
  README.md
  package_manifest.template.json
  references/
    reference_map.md
    scenario_contract.md
  assets/
    test-prompts.template.json
    owner_mapping.template.json
    notification_card_template.json
  scripts/
    selfcheck.py
    scenario_flow.py
```

## 文件分工

| 文件 | 价值 |
| --- | --- |
| `SKILL.md` | 让 Agent 知道何时用、怎么用、何时停。 |
| `scenario_contract.md` | 所有业务规则唯一来源。 |
| `assets/*.json` | 测试样例、Owner 路由和 Card 模板。 |
| `scenario_flow.py` | 本地 dry-run 串起四段链路。 |
| `selfcheck.py` | 防漂移、防硬编码、防副作用。 |

## 复制步骤

1. 复制目录为新 Skill。
2. 替换占位符：`scenario-key`、`SCENARIO_NAME`、`METRIC_ID`、`OWNER_ROLE`、`DATASET_ID`。
3. 更新 `SKILL.md` frontmatter。
4. 补齐 `references/scenario_contract.md`。
5. 替换 assets 模板。
6. 运行 `python3 scripts/selfcheck.py`。

## 四能力职责边界

| 阶段 | 能做 | 不能做 |
| --- | --- | --- |
| 感知 | 识别场景、任务类型、数据就绪、下游计划。 | 不执行 SQL、不生成业务结论、不发通知、不写状态。 |
| 分析 | 生成 QueryPlan、只读 SQL、source_footer、标准化分析结果。 | 不执行写操作、不把查询失败解释为业务正常、不生成发送动作。 |
| 通知 | 生成通知草稿、Card、POC 路由、send_plan、报表。 | 不真实群发、不拉群、不解析敏感身份、不绕过确认。 |
| 解决 | 记录 manual tracking、状态流转、闭环检查和复查计划。 | 不关闭线上事件、不更新工单、不把草稿当已发送。 |

## 验证

```bash
python3 scripts/selfcheck.py
```
