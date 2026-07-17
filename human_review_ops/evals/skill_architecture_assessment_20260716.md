# Human Review Ops Skills 全面架构与代码评估

评估日期：2026-07-16

评估范围：`human_review_ops/skills`

## 修复后状态

修复完成日期：2026-07-16

结论：**评估发现的 1 个 P0、14 个 P1、10 个 P2 已全部关闭，当前代码通过发布门禁。**

本轮不是仅修改文档，已完成以下运行态修复：

- 跨日准确率按分子、分母重算。
- dry-run 全层统一为 `not_executed` / `mock_readonly_no_real_query`。
- Analysis JSON 可由 Notification CLI 原样消费。
- `report_flow` 支持显式日期、稳定 Key、量率重算和完整通知产物。
- 查询失败或截断进入 STOP，不生成业务结论。
- `+1` 治理资产打入 Analysis 独立包，真实资源 token 改为环境配置。
- Card Hash 覆盖完整证据、QueryPlan、source footer、周期和 sheet URL。
- Resolution 实现动作、证据、结论三件套与合法状态迁移。
- Perception 支持三类注册场景、歧义阻断、否定语义、run mode 和 source ref 校验。
- 建立 5 份运行态 JSON Schema 与中央 Schema validator。
- 场景包收敛为唯一 `references/scenario_contract.md`，由 canonical 源生成并通过 hash 同步。
- 27 条 test prompt 已由可执行 runner 全量验证。

修复后关键验证：

| 验证项 | 结果 |
| --- | --- |
| 5 个 Skill `selfcheck.py` | 通过 |
| Strict productization | 通过 |
| Standalone smoke | 通过 |
| 27 条 Test Prompt | 通过 |
| Runtime Schema smoke | 通过 |
| Analysis / Notification / Perception 专项 validator | 通过 |
| Label-rate capability matrix | 通过 |
| Aeolus field contract | 通过 |
| Skill path registry | 通过 |
| Scenario package / Skill package | 通过 |
| Scenario bundle hash sync | 通过 |
| 历史 Stage 1 真实只读产物兼容 | 通过 |
| 历史 Stage 2 POC / manual tracking 兼容 | 通过 |

以下章节保留修复前评估基线与问题成因，问题状态均为 **已关闭**。

## 一、结论摘要

本次完整检查了 5 个已发布 Skill、78 个文件、19,345 行内容：

- `perception`
- `analysis`
- `notification`
- `resolution`
- `efficiency-label-rate-ops`

修复前综合评分：**64.2/100**。修复后以可执行发布门禁为准，当前建议进入发布前人工复核。

项目的“四节点”业务模型合理，默认安全边界总体有效。5 个 `selfcheck.py` 全部通过，Python 编译通过，默认 dry-run 没有真实发送通知或写线上状态。

但现有检查主要证明“内置 happy path fixture 可以运行”，不能证明跨 Skill 可串联、接口契约一致、失败分支有效以及业务指标正确。当前主要发布阻断项：

1. 自动处置准确率周指标错误地采用日准确率算术平均，可能直接改变 P1/P0 分级。
2. dry-run 的嵌套对象仍宣称真实查询成功。
3. 文档声明的原子 Skill 交接无法由 CLI 直接执行。
4. `report_flow` 忽略显式日期，且不能完成声明的通知全链路。
5. Resolution 在 `can_close=false` 时仍输出关闭方向的下一状态。
6. 场景发布包当前无法通过自身同步校验。

问题统计：

| 严重度 | 数量 | 含义 |
| --- | ---: | --- |
| P0 | 1 | 已关闭 |
| P1 | 14 | 已关闭 |
| P2 | 10 | 已关闭 |

## 二、Skill 设计评分

评分采用 9 维 Skill 评估口径：Frontmatter、工作流、失败模式、检查点、可执行具体性、资源整合、整体架构、实测表现、反例与黑名单。

| Skill | 得分 | 主要优点 | 主要短板 |
| --- | ---: | --- | --- |
| `perception` | 66.6 | 安全边界清楚，路由输出结构化 | 声明为多场景路由，实际脚本只处理打标率 |
| `analysis` | 62.7 | QueryPlan 和 SQL 约束详细 | 指标聚合错误，执行状态存在误导 |
| `notification` | 68.1 | 发送门禁明确，产物生成较完整 | 输入契约、举报方向、哈希和在线写审计不完整 |
| `resolution` | 60.9 | 禁止线上写入的边界明确 | 闭环判定和状态机核心能力未实现 |
| `efficiency-label-rate-ops` | 62.5 | 场景级发布包方向合理 | 双源、触发重叠、发布漂移 |
| **平均** | **64.2** | 四节点模型清晰 | 缺少统一、可执行的接口权威 |

实测维度主要来自 dry-run 和本地负例。仓库目前没有 test prompt 全量执行器，因此分数不能替代生产验收。

## 三、P0 问题

### P0-1：周自动处置准确率错误使用日准确率算术平均

证据：

- `human_review_ops/skills/analysis/references/scenarios/efficiency-auto-disposal-accuracy.md:68-72`
- `human_review_ops/skills/analysis/references/scenarios/efficiency-auto-disposal-accuracy.md:310-373`

P1/P0 分级 SQL 当前计算：

```sql
sum(rlabel_acc_weight_rate) / count(distinct date)
```

只有每天分母完全相同时该算法才正确。契约中已经存在准确量和误伤量，应按以下公式跨日重算：

```sql
SUM(`[一级标签准确量]`) /
  NULLIF(SUM(`[一级标签准确量]`) + SUM(`[mach_rlabel_injury_cnt_1d]`), 0)
```

影响：日样本量不同时，周准确率及是否低于 80% 的结果会失真，直接改变 P1/P0 告警。

改进：所有跨日 rate 必须回到分子、分母聚合；增加“每天分母不同”的回归用例。

## 四、P1 问题

### P1-1：dry-run 嵌套对象宣称真实查询成功

证据：

- `analysis/scripts/label_rate_analysis.py:163-187`
- `analysis/scripts/label_rate_analysis.py:1043-1085`
- `analysis/scripts/label_rate_analysis.py:1423-1577`

实测结果：

- 顶层 `safety.real_query_executed=false`
- 嵌套 `analysis_result.readonly_execution.execution_mode=real_readonly_query`
- 嵌套 `status=success`
- 嵌套质量检查声明数据新鲜、证据完整

下游只要读取 `analysis_result`，就可能把 smoke fixture 当作真实业务证据。

改进：只构造一份 execution status 并在全部层级复用。dry-run 必须统一为 `not_executed` 或 `mock_readonly_no_real_query`。

### P1-2：`report_flow` 忽略显式日期并违反稳定 Key 规范

证据：

- `analysis/scripts/label_rate_analysis.py:151-164`
- `analysis/scripts/label_rate_analysis.py:440-453`

传入 `--start-date 2026-07-08 --end-date 2026-07-14` 后，SQL 仍为：

```sql
[进审日期] >= today() - 7 AND [进审日期] < today()
```

同时 SQL 使用 `AS enpool_reason GROUP BY enpool_reason`，没有先生成 `enpool_reason_key`。

改进：两种数据方向统一消费显式时间参数；内层按 `enpool_reason_key` 聚合，外层再映射为输出字段。

### P1-3：查询失败和截断没有进入 STOP 分支

证据：

- `analysis/scripts/label_rate_analysis.py:1013-1035`
- `analysis/scripts/label_rate_analysis.py:1193-1239`
- `analysis/scripts/label_rate_analysis.py:1423-1479`

失败 payload 会直接触发 `KeyError`；`truncated=true` 时仍输出 `status=success` 和 `truncation_check=passed`。

改进：先把执行结果归一为 `success/blocked/failed/degraded`；失败时只输出 `stop_reason`、QueryPlan 和 source footer，不生成业务结论。

### P1-4：Analysis 依赖 Skill 外部的 `+1` 资产

证据：

- `analysis/scripts/label_rate_analysis.py:1276-1307`
- `skill_release_manifest.json:114-129`

Analysis 声明 `external_dependencies=[]`，包内却没有 `plus1_agreed_strategy_updates.json`。脚本实际越界搜索根场景包或 `efficiency-label-rate-ops`；独立安装后会静默返回空索引，并把所有策略标记为“未 +1 同意”。

改进：将治理资产打入 Analysis 包，或改为必需显式输入；资产缺失时必须 fail closed，不能静默降级。

### P1-5：Analysis 到 Notification 的公开交接格式不可执行

证据：

- `notification/SKILL.md:38-45`
- `notification/scripts/resolve_label_rate_poc_routing.py:70-91`

Analysis CLI 输出单个格式化 JSON；Notification CLI 要求 JSONL，并要求存在 `record_type=sample` 和 envelope 级 `analysis_mode`。直接串联会在 JSONL 解析阶段失败。

改进：定义唯一的版本化 `AnalysisArtifact`，两个 CLI 严格读写同一格式；不要把内层 `analysis_result` 和 Stage 1 sample envelope 都称为 `analysis_result`。

### P1-6：举报方向通知全链路未实现

证据：

- `notification/SKILL.md:68-77`
- `notification/scripts/label_rate_notification_artifacts.py:956-977`

举报方向只提供 `enpool_reason`、`avg_report_review_done_cnt`、`avg_report_label_cnt`、`report_label_rate`。Card 生成代码直接索引 `avg_review_in_cnt` 等人工审核字段，会触发 `KeyError`。

改进：按 `source_profile` 增加适配层，把两种数据方向归一到共同 Notification Evidence Model；或者拆成两个明确的 renderer。

### P1-7：在线 Sheet 写入成功后审计状态仍为 false

证据：

- `notification/scripts/label_rate_notification_artifacts.py:189-197`
- `notification/scripts/label_rate_notification_artifacts.py:774-785`
- `notification/scripts/label_rate_notification_artifacts.py:827-840`

`auto_import_sheet=true` 成功返回真实 `sheet_url` 后，`notification_draft` 和 `send_plan` 仍记录 `online_write_executed=false`。

改进：导入函数返回结构化结果，并在 draft、send plan、provenance 中传播 `attempted/status/online_write_executed/resource_url`。

### P1-8：Card Hash 未覆盖完整证据集

证据：

- `notification/scripts/label_rate_notification_artifacts.py:598-618`
- `notification/scripts/render_label_rate_grading_card.py:377-395`

Hash 只覆盖汇总行和各等级 Top-N。Top-N 之外的明细、来源信息或 `sheet_url` 变化不会使 hash 失效。

改进：对完整报表摘要、QueryPlan ID、source footer digest、周期、sheet URL 和卡片展示行生成规范化 manifest 后统一计算 hash。

### P1-9：不可关闭事件仍被推进到关闭态

证据：

- `resolution/scripts/build_label_rate_manual_tracking.py:57-62`
- `resolution/scripts/build_label_rate_manual_tracking.py:85-103`
- `resolution/references/scenarios/efficiency-label-rate.md:75-113`

脚本固定输出：

- `next_state=DEBUG_CLOSED_AFTER_MANUAL_REVIEW`
- `can_close=false`
- `overall_status=pending_manual_confirmation`

同时场景状态机只定义了 `DEBUG_CLOSED`，没有 `DEBUG_CLOSED_AFTER_MANUAL_REVIEW`。

改进：由 closure gate 推导状态，并使用唯一状态枚举校验迁移。

### P1-10：Resolution 无法执行声明的闭环职责

证据：

- `resolution/SKILL.md:37-66`
- `resolution/scripts/build_label_rate_manual_tracking.py:15-46`
- `resolution/scripts/build_label_rate_manual_tracking.py:52-104`

Skill 声明必需 `analysis_result`、`current_state`、`manual_action`，并支持 evidence、response、resolution note。CLI 实际只接收 notification draft 和 send plan，永远返回 `can_close=false`，也没有文档要求的 `follow_up`。

改进：实现动作/证据/结论三件套，或把职责明确收窄为“创建待跟踪记录”，删除关闭判定声明。

### P1-11：Perception 未可靠执行唯一场景和任务路由

证据：

- `perception/scripts/label_rate_perception.py:388-405`
- `perception/scripts/label_rate_perception.py:474-529`

实测失败：

- 明确 reason 维度拆解返回 `low_label_rate_grading`，而非 `dimension_breakdown`
- “自动处置准确率和打标率都看”被直接判为 label-rate 且 `ready`
- Skill reference 注册三个场景，执行脚本却把自动处置和质检准确率当排除项

改进：通用多场景路由和打标率解析分层；输出候选场景集合，冲突时必须阻断澄清。

### P1-12：仓库 JSON Schema 不是运行时接口权威，且与输出不兼容

证据：

- `schemas/analysis_result.schema.json:8-19`
- `schemas/analysis_result.schema.json:45-153`
- `schemas/analysis_result.schema.json:175-185`
- `schemas/analysis_result.schema.json:248-280`
- `schemas/analysis_result.schema.json:443-582`
- `schemas/resolution_result.schema.json:8-15`

具体冲突：

- 实际 QueryPlan 包含 `additionalProperties=false` 禁止的字段
- 运行时可输出 `notice`、`none`，Schema 只允许 P0-P3/unknown
- source footer 实际包含大量 Schema 禁止的字段
- provenance 要求顶层 `limitations`，实现没有
- resolution 输出不具备 `resolution_id/actions/manual_tracking/closure/follow_up`

改进：把版本化 JSON Schema 设为唯一接口权威，并在 selfcheck 和 CI 中逐次校验。

### P1-13：场景包和原子 Skill 形成双路由、双实现源

证据：

- `efficiency-label-rate-ops/SKILL.md:63-88`
- `efficiency-label-rate-ops/package_manifest.json:6-12`
- `efficiency-label-rate-ops/package_manifest.json:79-96`
- `efficiency-label-rate-ops/package_manifest.json:179-235`

场景包覆盖四个原子 Skill 的全部打标率触发词，同时发布：

- 1,139 行合并场景文档
- 拆分的 9 份 reference
- 6 个逐字节相同脚本和 3 个逐字节相同资产
- 2 个仅路径不同的近似镜像脚本

改进：一个场景只暴露一个用户入口；发布包从 canonical implementation 和单一 `scenario_contract.md` 生成，生成物不可手工编辑。

### P1-14：发布完整性与自包含策略当前不成立

证据：

- `skill_release_manifest.json:5-9`
- `perception/references/scenarios/efficiency-label-rate.md:33-40`
- `perception/references/scenarios/efficiency-label-rate.md:121-124`
- `perception/references/scenarios/efficiency-label-rate.md:381-395`
- `efficiency-label-rate-ops/package_manifest.json:179-199`

问题：

- 运行态 reference 指向 `.trae/skills/...`
- `forbid_real_tokens=true`，但文档包含真实飞书资源 token
- package hash 已过期
- `validate_efficiency_label_rate_ops_skill.py` 的 `--check-sync` 失败

当前 hash 漂移涉及评审前已存在的 perception、analysis、notification 未提交改动。本次评审没有回退或覆盖这些改动。

改进：移除环境特定引用；治理资源 ID 由配置注入；bundle sync 必须成为发布门禁。

## 五、P2 问题

### P2-1：`task_type` 词表不统一

同一流程同时出现 `low_label_rate_grading`、`readonly_analysis`、`query_only`、`notification_request`、`notification_only`。

建议：拆分为稳定的 `intent`、`analysis_mode`、`requested_action`，避免一个字段承载多个阶段语义。

### P2-2：`run_mode` 未做枚举校验

Perception 接收 `production` 等任意值后仍可返回 ready。

建议：使用共享 enum，未知模式直接阻断。

### P2-3：Notification 必需输出超出实现

`SKILL.md` 要求 `escalation_draft`、`evidence_refs`、`failure_branches`，实际顶层通知产物没有这些字段。

建议：纳入版本化 Schema 并实现，或从“必需输出”中删除。

### P2-4：高危 Prompt 的 trigger 语义自相矛盾

真实群发、线上关闭等 Prompt 被标记为 `trigger=false`，但又要求 Skill 接管并输出阻断结果。

建议：分离 `skill_selected=true` 和 `action_allowed=false`。

### P2-5：副作用元数据不一致

顶层 release policy 声称 “dry-run only”，脚本条目同时声明 `none` 和 conditional online write。

建议：使用结构化副作用枚举，例如 `none`、`local_file_write`、`online_write_requires_opt_in`；有写操作时不得同时标记 `none`。

### P2-6：Resolution 场景索引存在无效锚点

`resolution/references/scenario-index.md:29-37` 指向 label-rate 文档中不存在的章节，且 Owner/POC 锚点顺序错误。

建议：CI 增加 Markdown 文件和章节锚点校验。

### P2-7：独立 bundle manifest 未声明运行依赖

`openpyxl` 只写在仓库级 release manifest，未写入 bundle 的 `package_manifest.json`。

建议：独立包只依赖自身 manifest 即可完成安装和 preflight。

### P2-8：Test Prompt 只是资产，不是验收测试

现有 validator 只检查 JSON 结构与关键词，没有逐条执行 Prompt。这导致 Perception 5 条正式用例仅 4 条语义通过，但产品化校验仍显示通过。

建议：增加 Prompt runner 和字段级断言，所有 case 必须通过。

### P2-9：举报 POC fallback 未校验数据方向

`resolve_row_poc()` 只要看到 `enpool_reason` 且没有机审标签，就 fallback 到“举报”，没有确认 `data_direction=report_flow`。

建议：只有 source profile 已验证为 report flow 时才启用 fallback。

### P2-10：`+1` cutoff 使用宽松字符串比较

非零填充日期或时间戳可能被错误判定为周期前后。

建议：统一解析 ISO date，非法格式阻断，按日期对象比较。

## 六、跨 Skill 接口矩阵

| 阶段 | 文档输入 | 实际可执行输入 | 主要差距 |
| --- | --- | --- | --- |
| Perception | 自然语言和可选 hints | CLI flags/string lists | 无版本化输出 Schema，歧义值可放行 |
| Analysis | Perception 输出字段 | 独立 CLI flags，不消费 Perception artifact | 交接只存在于概念层 |
| Notification | `analysis_result` JSONL | 完整 Stage 1 sample envelope JSONL | 同名对象定义冲突，序列化不兼容 |
| Resolution | 分析、状态、草稿、计划、动作、证据、结论 | 仅 draft + send plan | 无法判断闭环和状态迁移 |
| 场景包 | 原始请求或上游产物 | 多个脚本和临时文件格式 | 没有 orchestrator 执行声明的工作流 |

## 七、职责划分评估

### Perception

“只分类和路由”的目标合理。但当前 683 行打标率 reference 包含 SQL、数据集、治理同步和分析细节，明显越过感知职责，并增加模型加载负担。

### Analysis

QueryPlan、只读 SQL 和结果标准化属于同一职责。POC enrichment 和搜索 Skill 外治理资产不属于分析，应只输出证据及路由 key。

### Notification

草稿、报表、Card、路由计划和 send plan 相关性较高，但已偏重。在线 Sheet 导入是独立副作用适配器，应由 host capability 承担，不应嵌入核心 artifact builder。

### Resolution

声明的职责合理，但实现目前只是“生成待跟踪本地记录”，尚不是完整的解决/闭环能力。

### 场景包

作为发布单位合理，但当前同时是第二套可发现 Skill 和第二份源码树。应明确为生成式分发产物，而不是独立编辑层。

## 八、推荐目标架构

推荐方案：

1. `efficiency-label-rate-ops` 作为该场景唯一用户入口。
2. 四节点作为场景包内部模块；若保留通用原子 Skill，则不得与场景包同时暴露重叠触发词。
3. 唯一业务契约为 `scenario_contract.md`。
4. 唯一接口权威为版本化 JSON Schema。
5. 使用一个 `scenario_flow.py` 编排四节点，并在每个边界校验 artifact。
6. 发布包只复制 canonical code/assets；生成文件只读，并由 CI 校验 hash。

最小产物链：

```text
PerceptionResult.v1
  -> QueryPlan.v1
  -> AnalysisArtifact.v1
  -> NotificationArtifact.v1
  -> ResolutionArtifact.v1
```

每个 artifact 统一包含：

- `schema_version`
- `scenario_key`
- 阶段专属 mode
- `run_mode`
- `status`
- `source_refs`
- `quality_checks`
- `safety`
- `provenance`

## 九、改进路线

### Phase 0：阻断发布并修正业务结果

1. 修正周准确率公式。
2. 统一 dry-run 全层执行状态。
3. 将显式日期传入 report flow，并增加稳定 Key。
4. 查询失败/截断必须 STOP。
5. 修正 Resolution 下一状态。
6. 重新生成并校验场景包。

### Phase 1：建立可执行接口契约

1. 选定 JSON Schema 为唯一权威。
2. 补充 perception、notification、send plan、POC routing、manual tracking Schema。
3. Analysis CLI 输出必须能被 Notification CLI 原样消费。
4. 为两种数据方向增加 source-profile adapter。
5. 实现 Resolution 闭环判定，或明确删除该职责。

### Phase 2：消除架构重复

1. 收敛为一个 `scenario_contract.md`。
2. 每个脚本只保留一个 canonical implementation。
3. 场景包全部由 canonical source 生成。
4. 定义触发优先级，或禁止重叠 Skill 同时安装。
5. 在线写入移到 host-owned adapter，并强制显式确认。

### Phase 3：升级验证体系

1. 执行全部 `assets/test-prompts.json`。
2. 对每个运行态产物执行 Schema 校验。
3. 补权限失败、分区未就绪、分母为 0、截断、非法 enum、矛盾安全字段测试。
4. 增加 Markdown 锚点和 manifest hash 校验。
5. 在“只有独立包及声明依赖”的环境运行 standalone test。

## 十、验证结果

通过：

- 5 个 Skill 的 `selfcheck.py`
- 全 Skill Python 编译
- strict productization
- standalone smoke
- label-rate capability matrix
- analysis scripts validator
- notification scripts validator
- perception scripts validator
- Stage 2 manual tracking validator
- Aeolus field contract validator
- runtime-neutrality 扫描

失败：

- 场景包同步校验
- Analysis CLI 直接交接 Notification CLI
- report-flow 显式日期传播
- Perception reason breakdown 正式用例
- 混合场景歧义门禁
- Resolution 状态/关闭一致性负例
- dry-run 嵌套执行状态一致性

本次评估没有执行真实 SQL、通知发送、群操作、在线 Sheet 导入或线上状态写入。
