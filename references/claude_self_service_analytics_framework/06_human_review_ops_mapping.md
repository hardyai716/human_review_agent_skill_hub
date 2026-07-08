# 06 Claude 框架到人审运营的映射

## 1. 当前 MVP 映射

当前人审运营 MVP 聚焦：

- 感知。
- 分析。

通知和解决先做轻量测试闭环。

对应 Claude 框架：

| Claude 框架 | 人审运营落地 |
| --- | --- |
| Data Foundations | Aeolus/Hive 治理数据集、语义层指标、指标契约 |
| Sources of Truth | 场景流程包、指标注册表、字段描述、血缘、Owner 映射 |
| Knowledge Skill | 感知阶段的场景识别、指标映射、数据源限定 |
| Runbook Skill | 分析阶段的 QueryPlan、查询、质量检查、归因、规则命中 |
| Validation | 离线样例、回测、来源脚注、人工纠错回收 |

## 2. 效率模块：机审策略有效性

### 2.1 核心指标

- 打标率。
- 自动处置准确率。

### 2.2 任务类型

| 任务 | Claude 框架对应 |
| --- | --- |
| 日常低准分析 | Runbook Skill：ad hoc analysis pattern |
| 周度推送 | Scheduled runbook + fixed output template |
| 打标率撞线预警 | Rule evaluation + alert runbook |
| 自动处置准确率撞线预警 | Rule evaluation + alert runbook |

### 2.3 必备治理资产

- `metric_contract.md`
- 策略粒度数据说明。
- 风险域/三级标签维度说明。
- 治理 BP 映射说明。
- 低效策略定级/升级规则。
- 禁止使用的历史字段或临时表。

## 3. 质量模块：质量监控

### 3.1 核心指标

- 质检准确率。

### 3.2 任务类型

| 任务 | Claude 框架对应 |
| --- | --- |
| 日常质量分析 | Runbook Skill：trend + decomposition |
| 质量撞线预警推送 | Rule evaluation + alert runbook |

### 3.3 必备治理资产

- `metric_contract.md`
- 风险域粒度说明。
- CQC 质量负责人映射。
- 整体/风险域达标规则。
- 连续两周不达标升级规则。

## 4. 质量模块：底线事故监控

### 4.1 核心指标

- 底线事故数。

### 4.2 任务类型

| 任务 | Claude 框架对应 |
| --- | --- |
| 底线事故撞线预警 | High-stakes alert runbook + adversarial review |

### 4.3 必备治理资产

- `metric_contract.md`
- 事故类型定义。
- S23 / S01 / N1 / LS 等分层解释。
- 漏放/非底线事故口径。
- CQC 群组质量负责人映射。
- 人审运营升级规则。

## 5. 需要优先建设的资产

第一优先级：

1. 三个场景的 `metric_contract.md`。
2. 人审运营实际使用的 Aeolus/Hive 数据集 `dataset_reference.md`。
3. 相近字段差异说明、推荐字段、禁止字段。
4. 每个场景 3-5 条离线验收样例。
5. QueryPlan 模板。
6. 来源脚注模板。
7. 允许/禁止数据源清单。

第二优先级：

1. 定级/升级规则。
2. 测试通知卡片模板。
3. 人工跟进记录字段。
4. 回测 CLI 或回测脚本。

第三优先级：

1. 动态 Owner 路由。
2. 多级升级。
3. 完整 SLA。
4. 自动催办和闭环复查。

## 6. 对当前架构的约束

当前阶段不要优先做：

- 完整动态 Owner 路由。
- 完整解决闭环。
- 自动处理动作。
- 复杂多级升级。

当前阶段必须优先做：

- 指标实体映射。
- Aeolus/Hive 字段选择治理。
- 数据源限定。
- QueryPlan。
- 数据质量检查。
- 波动归因。
- 规则命中。
- 来源脚注。
- 离线评估样例。
