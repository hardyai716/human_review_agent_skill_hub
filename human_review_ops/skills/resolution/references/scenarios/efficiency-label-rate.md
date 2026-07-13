# 解决闭环场景：efficiency-label-rate

## 运行态定位

本文件是 resolution Skill 的运行态单场景文档，由根场景包合并生成。运行态只记录人工处理状态、闭环检查、继续观察和升级建议；不重新查数、不生成通知内容、不执行线上写入。

## 闭环门禁

- 必须消费前置分析、通知草稿、send_plan、人工动作和证据引用。
- 关闭前必须具备动作、证据、结论三件套。
- `send_plan.sent=false` 或 `group_send_blocked=true` 时不得写成已通知完成。
- 真实通知、线上写状态、自动关闭、处罚或资源调整进入 `HUMAN_REVIEW_REQUIRED`，只记录阻断原因。

## 场景定位

## 场景标识

- `scenario_key`：`efficiency-label-rate`
- 模块：效率模块
- 指标对象：打标率
- 运营对象：策略三维、风险域、送审原因 / reason、举报入池原因 / enpool_reason 在不同维度下的打标率表现
- 当前状态：阶段 1 主线样板场景

## 数据方向

本场景下存在两个已治理数据方向，二者共用打标率业务语义，但数据集、字段和默认筛选不同。感知阶段必须识别 `data_direction`，分析阶段必须按方向选择对应 source profile，不得混用字段。

| `data_direction` | source profile | 数据集 | 适用问题 | 主维度 | 口径摘要 |
| --- | --- | --- | --- | --- | --- |
| `manual_review_detail` | `community_manual_review` | `[重点模型]-社区_人工审核明细数据` / `3888816` / appId `1128` | 人工审核明细、策略、机审一级标签、`reason` 维度的打标率查询和低效策略治理。 | 默认分级：`mach_root_label_name`、`strategy_id`、`strategy_name`；可选拆解：`reason` | `打标量__reviewid / 完审量_reviewid` |
| `report_flow` | `report_flow_review` | `举报流转任务明细数据集` / `3952594` / appId `555137` | 举报场景、举报流转、`enpool_reason`、`report_id`、一轮/终轮队列维度的打标率查询。 | `enpool_reason` | `打标量_report_id / 人审完结量_report_id` |

## 参考来源

本场景只吸收以下已验证 Skill 中与打标率流程直接相关的内容：

- `.trae/skills/warehouse-skill/`：数据治理、Semantic Layer first、provenance、字段映射和数据质量 gate。
- `.trae/skills/low-efficiency-strategy-analysis/`：低打标率分级、维度拆解和输出结构。

不直接迁移旧 Skill 的完整实现、历史目录结构或在线工具权限。

## 触发意图

- 查询打标率、进审量、完审量、打标量趋势，并要求可复核口径。
- 查询高打标率或低打标率的策略 / reason。
- 按机审一级标签、场景、项目等维度拆解打标率。
- 查询举报场景下的打标率、低打标率 `enpool_reason`、举报流转任务的进审 / 人审完结 / 打标量。
- 近 N 天有哪些高完审、低打标策略或 reason。
- 打标率低的策略是否需要按 notice/P2/P1/P0 分级。
- notice、P2、P1、P0 低效策略清单，以及风险域维度爆量预警。

## 排除意图

- 自动处置准确率分析。
- 质检准确率分析。
- 底线事故数分析。
- 审核员个人明细、手机号、open_id 等敏感明细导出。
- 责任人触达、建群、工单推进等后续运营流转。

## 方向识别规则

- 命中 `举报`、`举报场景`、`举报流转`、`enpool_reason`、`report_id`、`一轮队列`、`终轮队列`、`举报流转任务明细数据集`、`3952594` 时，设置 `data_direction=report_flow`。
- 命中 `机审一级标签`、`策略ID`、`策略名称`、`reason` 且未出现举报相关字段时，默认 `data_direction=manual_review_detail`。其中低效分级默认按 `机审一级标签 × 策略ID × 策略名称`，`reason` 仅在用户明确要求拆解时作为分组维度。
- 用户只说“打标率 reason”且上下文无举报字段时，默认 `manual_review_detail`；若同时出现 `举报` 或 `enpool_reason`，必须切换到 `report_flow`。
- 方向不唯一时，感知阶段应输出澄清问题，不得同时拼接两个数据源字段。

## 默认运行约束

- 第一阶段默认 `debug_only`。
- 默认只读。
- 默认先生成 QueryPlan；QueryPlan 通过断言后，可执行符合权限策略的 mock / 只读查询链路。
- 覆盖样本池、未治理字段、权限不足、真实飞书触达、状态写入或高风险动作必须人工确认。
- 数据未就绪、权限不足、口径不清时停止，不输出“无异常”结论。

## 状态机

## 调试状态

```text
INTAKE
  -> SCENARIO_RESOLVED
  -> PERCEPTION_READY
  -> QUERY_PLAN_READY
  -> ANALYSIS_READY
  -> OWNER_SUGGESTED
  -> NOTIFICATION_DRAFTED
  -> MANUAL_TRACKING_RECORDED
  -> DEBUG_CLOSED
```

## 异常状态

```text
NEED_MORE_INFO
DATA_NOT_READY
PERMISSION_BLOCKED
HUMAN_REVIEW_REQUIRED
STOPPED_NO_CONCLUSION
```

## 状态说明

| 状态 | 含义 | 输出 |
| --- | --- | --- |
| `INTAKE` | 接收用户问题 | 原始输入 |
| `SCENARIO_RESOLVED` | 命中打标率场景 | `scenario_key` |
| `PERCEPTION_READY` | 识别任务类型、指标、时间窗口和维度 | `task_type`、`metric_id`、`dimensions` |
| `QUERY_PLAN_READY` | 生成 QueryPlan | QueryPlan |
| `ANALYSIS_READY` | 完成趋势、分级或维度拆解分析 | 分析摘要、evidence |
| `OWNER_SUGGESTED` | 生成 Owner 建议 | Owner 依据、置信度 |
| `NOTIFICATION_DRAFTED` | 生成通知草稿 | 草稿文本 |
| `MANUAL_TRACKING_RECORDED` | 记录人工处理状态 | manual tracking |
| `DEBUG_CLOSED` | 调试闭环 | 调试结论 |

## 流转规则

- 用户只问趋势：`QUERY_PLAN_READY -> ANALYSIS_READY -> DEBUG_CLOSED`。
- 用户问低打标率策略分级或风险域预警：`QUERY_PLAN_READY -> ANALYSIS_READY -> OWNER_SUGGESTED`。
- 用户问举报场景低打标率或 `enpool_reason`：仍命中 `efficiency-label-rate`，但必须在 `PERCEPTION_READY` 和 `QUERY_PLAN_READY` 中保留 `data_direction=report_flow`、`source_profile=report_flow_review`。
- 用户问高打标率或普通趋势：`QUERY_PLAN_READY -> ANALYSIS_READY -> DEBUG_CLOSED`。
- 用户要求通知：必须先 `OWNER_SUGGESTED`，再 `NOTIFICATION_DRAFTED`。
- 口径、时间窗口或指标不明确：进入 `NEED_MORE_INFO`。
- 数据未就绪：进入 `DATA_NOT_READY`，不得输出低效结论。
- 权限不足：进入 `PERMISSION_BLOCKED`。
- QueryPlan 通过且工具权限为只读时，可以进入只读查询执行。
- 真实通知、线上写状态、覆盖样本池、未治理字段、禁用来源或高风险动作：进入 `HUMAN_REVIEW_REQUIRED`。

## Owner / POC 路由

## 路由原则

本场景用于基于低打标率数据生成 POC / 触达对象路由计划。当前 POC 找人逻辑按 `mach_root_label_name`（机审一级标签）映射到 POC 姓名；真实触达前必须再完成飞书 open_id 解析、目标确认和发送门禁校验。

## 当前开发阶段决策

- POC 路由粒度：优先按 `mach_root_label_name` 映射 POC；`warning_dimension`、`strategy_id`、`strategy_name` 作为证据字段保留。默认低效分级不按 `reason` 分组。
- 风险域维度行的 `strategy_id`、`strategy_name` 为空，表示该机审一级标签下低效策略汇总后的风险域预警；此类行仍按 `mach_root_label_name` 映射 POC。
- 若原始机审一级标签为空，分析取数层会先按策略名称补齐为高热、政媒、商业化或指令舆情相关，再进入 POC 路由。
- 当前 POC 映射资产尚未包含 `商业化`，命中商业化补映射的行会进入未映射 / 人工确认路径。
- 举报流转方向（`data_direction=report_flow`）默认没有 `mach_root_label_name`，以 `enpool_reason` 作为证据字段，Owner 建议先路由到“举报”POC，占位 POC 为韩晶晶；真实触达前必须由人审运营确认是否需要按风险域或队列进一步拆分。
- 路由脚本在输入只有 `enpool_reason` 且无机审一级标签时，必须把路由标签 fallback 为 `举报`，用于姓名级 POC 预览；manual tracking 需把该 fallback 标为待人工确认。
- 映射来源：飞书表格 `https://bytedance.larkoffice.com/sheets/TpxwsA8zohUZkVtJ4J9cDcXUnbg?sheet=HKdm9w`。
- 当前身份粒度：仅完成 POC 姓名映射，`poc_open_id` 尚未解析。
- 默认收件人：当输入数据缺少 `mach_root_label_name` 或标签未映射时，开发验证阶段 fallback 到用户本人，即 `default_recipient=self`。
- 群推送：当前不自动群发，真实触达前必须人工确认目标群 / POC 收件人。
- 回收闭环：暂不做联系人回复收集、卡片按钮回调或结果回收。

## 机审一级标签 POC 映射

| 机审一级标签 | POC |
| --- | --- |
| 国家安全 | 杜衡 |
| 领导人 | 宋诗慧 |
| 指令舆情相关 | 张发奇 |
| 偏激社会情绪和涉外言论 | 张发奇 |
| 党和国家形象负面 | 李中涛 |
| 举报 | 韩晶晶 |
| 不良行为或争议价值观 | 陈雅静 |
| 色情性化 | 刘小楷 |
| 高热 | 闫秦河 |
| 侵犯未成年权益 | 张宇轩 |
| 引人不适 | 陈思乔 |
| 短期策略迁移 | 陈思乔 |
| 危险行为 | 陈雅静 |
| 政媒 | 杜衡 |
| 违法违规 | 叶健 |

## 等级触达规则

| 等级 | 触达范围 | 动作要求 | 当前占位 |
| --- | --- | --- | --- |
| `notice` | 群内同步策略明细和数据链接。 | 周知明细，纳入观察。 | `default_recipient=self`，默认发给用户本人预览。 |
| `P2` | 治理 BP、审核 VOC 的 POC 角色、人审运营。 | 请相关 POC 说明低打标原因和后续处理计划。 | `default_recipient=self`，默认发给用户本人预览。 |
| `P1` | P2 范围 + 治理 BP 的 +1、VOC 负责人、人审运营负责人。 | 要求负责人关注，并推动原因说明和处理计划。 | `default_recipient=self`，默认发给用户本人预览。 |
| `P0` | P1 范围 + 治理负责人。 | 高优先级周知，要求重点关注和处理。 | `default_recipient=self`，默认发给用户本人预览。 |

## 输出要求

- POC / 触达对象路由计划。
- 等级触达范围。
- 动作要求。
- 命中依据。
- POC 姓名、命中的机审一级标签、未映射标签和缺失路由维度计数。
- 默认三维分级闭环证据必须保留 `是否+1同意`、`更新日期`、`+1同意日期是否在本次统计周期前`，并引用完整口径与剔除 `+1同意` 口径报表：`综合`、`综合_剔除+1同意`、`汇总统计`、`汇总统计_剔除+1同意`。
- 举报流转 manual tracking 必须保留 `enpool_reason`、日均人审完结量、日均打标量、举报打标率、`data_direction=report_flow` 和 source_footer 作为 evidence；`举报` POC fallback 不等同于已完成真实负责人确认。
- 置信度：`high` / `medium` / `low`。
- 是否需要人工确认。

## 低置信度条件

- 输入数据只有 reason 名称，没有 `mach_root_label_name`。
- 输入数据为风险域维度但 `mach_root_label_name` 为空或未映射。
- 输入数据来自举报流转方向，仅有 `enpool_reason`，尚未完成风险域或队列 Owner 拆分。
- `mach_root_label_name` 未命中 POC 映射。
- POC 只有姓名，尚未解析飞书 open_id。
- 触达角色仍为角色级占位。
- 数据来源 fallback 到 curated raw SQL。
- 用户问题涉及正式汇报、处罚、资源调整或高风险决策。

## 调试阶段约束

- 不在未确认 open_id 和目标群前真实触达 POC。
- 不创建飞书群。
- 不自动群发消息。
- 不写状态存储。

## SLA、继续观察与升级

## 分级响应

| 等级 | 响应建议 | 处理建议 | 升级条件 |
| --- | --- | --- | --- |
| `P0` | 当日确认 | 当日完成 Owner 定位和治理方案确认 | 超过 1 个工作日未确认 |
| `P1` | 1 个工作日内确认 | 2 个工作日内给出治理动作 | 连续两轮仍未改善 |
| `P2` | 2 个工作日内确认 | 3 个工作日内完成复盘 | 进审量继续增长或打标率继续下降 |
| `notice` | 周期性观察 | 纳入周报或观察清单 | 连续命中或升级到 P2+ |

## 调试阶段

- 不启动真实 SLA 计时。
- 只输出建议等级、建议响应时间和升级条件。
- 真实触达、状态流转和升级必须人工确认。

## 停止条件

以下情况不进入 SLA：

- 数据未就绪。
- 查询失败。
- 口径未确认。
- Owner 置信度为 low 且无人确认。
- 当前只做普通趋势或高打标率查询，不做低打标率治理。

## 正反例

## 正例

### 查询低打标率 reason

输入：

```text
近 7 天有哪些高完审低打标的 reason？
```

期望：

- 命中 `efficiency-label-rate`。
- `task_type` 为 `query_only` 或 `partial_workflow`。
- 输出 QueryPlan 和 source_footer。
- 若需要低效分级，默认包含 notice/P2/P1/P0。

### 查询高打标率 reason

输入：

```text
近 7 天打标率最高的策略有哪些？
```

期望：

- 命中 `efficiency-label-rate`。
- 命中 `label_rate_ranking` 模式。
- 按打标率降序输出，并带进审量、完审量、打标量和打标率。
- 不套用低效分级。

### 分级分析

输入：

```text
帮我看下近 7 天低打标率策略分 P0/P1/P2/notice 的情况。
```

期望：

- 命中 `low_label_rate_grading` 模式。
- 输出四级分级规则摘要，默认包含 `单策略维度` 和 `风险域维度`。
- 单策略维度按 `机审一级标签 × strategy_id × strategy_name` 聚合；风险域维度按机审一级标签汇总低效策略，策略ID和策略名称为空。
- 说明打标率口径为打标量 / 完审量。

### 维度拆解

输入：

```text
按机审一级标签拆一下打标率。
```

期望：

- 命中 `dimension_breakdown` 模式。
- 读取 `mach_root_label_name` 维度。
- 输出 `dimensions × reason` 和 `dimensions` 汇总结构。

### 举报场景低打标率

输入：

```text
举报场景近七天打标率小于 10% 的 enpool_reason 有哪些？输出日均人审完结量、日均打标量和打标率。
```

期望：

- 命中 `efficiency-label-rate`。
- `data_direction=report_flow`，`source_profile=report_flow_review`。
- 使用 Dataset `3952594` / appId `555137`。
- 时间字段使用 `进审日期`。
- 输出字段为 `enpool_reason`、`日均人审完结量`、`日均打标量`、`打标率`。
- 不得走人工审核明细 Dataset `3888816`。

### 用户指定未列举维度

输入：

```text
按业务线看打标率。
```

期望：

- 不直接猜字段。
- 先查 Semantic Layer / 数据集字段说明中是否存在业务线维度。
- 字段确认后再加入 QueryPlan。

## 反例

### 自动处置准确率

输入：

```text
分析一下自动处置准确率为什么下降。
```

期望：

- 不命中本场景。
- 提示这是自动处置准确率场景，不可用打标率替代。

### 质量准确率

输入：

```text
质检准确率下降了。
```

期望：

- 不命中本场景。
- 提示需要质量模块场景包。

### 底线事故

输入：

```text
底线事故数上升了。
```

期望：

- 不命中本场景。
- 提示需要底线事故监控场景包。

## 低信息量

输入：

```text
这个策略怎么了？
```

期望：

- 不直接查询。
- 先询问指标、时间窗口和策略 / reason。
- 不生成最终结论。
