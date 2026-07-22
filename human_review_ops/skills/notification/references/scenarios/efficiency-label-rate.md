# 通知场景：efficiency-label-rate

## 运行态定位

本文件是 notification Skill 的运行态单场景文档，由仓库构建流程合并生成。运行态只生成通知草稿、Owner/POC 路由、Card 或报表准备说明和 send_plan 门禁；不真实发送、不拉群、不写线上状态。

## 输入与输出门禁

- 必须消费 analysis Skill 或外部执行环境产出的结构化分析结果、QueryPlan、source_footer 和证据引用。
- 默认 `send_mode=preview_only`、`requires_confirmation=true`、`group_send_blocked=true`、`sent=false`、`real_group_send_executed=false`。
- 真实通知前必须由 calling_agent 或 external_executor 在通知 Skill 外完成目标群、接收人、open_id、正文、附件和权限确认。
- 结构化 Card 模板、schema notes、POC mapping 等资产存在时保留在 `assets/<scenario_key>/`，不要合并进 Markdown。

## 场景定位

## 场景标识

- `scenario_key`：`efficiency-label-rate`
- 模块：效率模块
- 指标对象：打标率
- 运营对象：策略三维、风险域、可选 `reason` 拆解、举报入池原因 / enpool_reason 在不同维度下的打标率表现
- 当前状态：阶段 1 主线样板场景

## 数据方向

本场景下存在两个已治理数据方向，二者共用打标率业务语义，但数据集、字段和默认筛选不同。感知阶段必须识别 `data_direction`，分析阶段必须按方向选择对应 source profile，不得混用字段。

| `data_direction` | source profile | 数据集 | 适用问题 | 主维度 | 口径摘要 |
| --- | --- | --- | --- | --- | --- |
| `manual_review_detail` | `community_manual_review` | `[重点模型]-社区_人工审核明细数据` / `3888816` / appId `1128` | 人工审核明细、策略、机审一级标签、`reason` 维度的打标率查询和低效策略治理。 | 默认分级：`mach_root_label_name`、`strategy_id`、`strategy_name`；可选拆解：`reason` | `打标量__reviewid / 完审量_reviewid` |
| `report_flow` | `report_flow_review` | `举报流转任务明细数据集` / `3952594` / appId `555137` | 举报场景、举报流转、`enpool_reason`、`report_id`、一轮/终轮队列维度的打标率查询和低效分级。 | 分级时固定 `mach_root_label_name=举报`，`strategy_id=strategy_name=enpool_reason` | `打标量_report_id / 人审完结量_report_id` |
| `combined` | `manual_review_detail+report_flow_review` | 同时使用 `3888816` 与 `3952594` | 将人审数据集打标率结果与举报场景结果合并展示。 | 两源分别分级后按标准字段合并，额外输出 `数据来源` | 各源使用各自口径，不做跨源二次聚合 |

## 参考来源

本场景固化以下通用业务和安全原则：

- 数据治理原则：优先使用语义层或已治理数据集，查询前确认字段映射、指标口径、数据新鲜度、Owner 和 provenance，查询失败不得解释成业务无异常。
- 低效策略分级规则：按 `notice/P2/P1/P0` 对低打标率策略和风险域预警分级，输出必须包含可复核 evidence、命中规则、维度粒度和限制说明。

本场景不依赖外部 Skill 目录、历史实现目录或在线工具权限；单独安装后以本包内 `SKILL.md`、`references/`、`assets/` 和 `scripts/` 为运行依据。

## 触发意图

- 查询打标率、进审量、完审量、打标量趋势，并要求可复核口径。
- 查询高打标率或低打标率的策略 / reason。
- 按机审一级标签、场景、项目等维度拆解打标率。
- 查询举报场景下的打标率、低打标率 `enpool_reason`、举报流转任务的进审 / 人审完结 / 打标量。
- 近 N 天有哪些高完审、低打标策略或 reason。
- 打标率低的策略是否需要按 notice/P2/P1/P0 分级。
- notice、P2、P1、P0 低效策略清单，以及风险域维度爆量预警。
- 对比本周与上周（或任意两个明确周期）的 `汇总统计_剔除+1同意`，按截图式表头生成飞书表格并在确认后推送链接。

## 排除意图

- 自动处置准确率分析。
- 质检准确率分析。
- 底线事故数分析。
- 审核员个人明细、手机号、open_id 等敏感明细导出。
- 责任人触达、建群、工单推进等后续运营流转。

## 方向识别规则

- 命中 `举报`、`举报场景`、`举报流转`、`enpool_reason`、`report_id`、`一轮队列`、`终轮队列`、`举报流转任务明细数据集`、`3952594` 时，设置 `data_direction=report_flow`；低效分级仍使用 `low_label_rate_grading`，风险域固定为 `举报`，策略 ID 和策略名称均填 `enpool_reason`。
- 命中 `机审一级标签`、`策略ID`、`策略名称`、`reason` 且未出现举报相关字段时，默认 `data_direction=manual_review_detail`。其中低效分级默认按 `机审一级标签 × 策略ID × 策略名称`，`reason` 仅在用户明确要求拆解时作为分组维度。
- 用户只说“打标率 reason”且上下文无举报字段时，默认 `manual_review_detail`；若同时出现 `举报` 或 `enpool_reason`，必须切换到 `report_flow`。
- 方向不唯一时，感知阶段应输出澄清问题，不得同时拼接两个数据源字段。

## 默认运行约束

- 默认 `debug_only`：仅生成本地感知结果、QueryPlan、分析报表、通知草稿、POC 路由草稿和 manual tracking 记录；不真实发送消息、不创建群、不写线上状态、不关闭事件。
- 默认只读：只允许 `SELECT` 或平台受控只读查询，不执行 DML / DDL，不修改业务表、工单状态、线上配置或消息发送状态；在线表格导入必须由用户显式授权后才可执行。
- 默认先生成 QueryPlan：查询前必须列出字段、指标口径、维度、过滤条件、数据方向、来源优先级、权限要求和质量检查；QueryPlan 未通过断言或人工确认时不得进入查询。
- `mock / 只读查询链路`：无外部查询权限时，只能生成 QueryPlan 或使用内置样例验证输出结构，mock 结果不伪造业务结论、不得替代真实数据结论；具备权限且 QueryPlan 通过后，才可由受控执行器发起只读查询。
- 覆盖样本池、未治理字段、权限不足、真实飞书触达、状态写入或高风险动作必须人工确认。
- 数据未就绪、权限不足、口径不清时停止，不输出“无异常”结论。

## 通知模板

## 调试阶段原则

- 只生成通知草稿。
- 不发送真实飞书消息。
- 不创建群。
- 不写入状态。

## 低打标率策略预警草稿

```text
【人审效率预警｜低效策略 / 风险域】

场景：{scenario_key}
等级：{severity}
周期：{time_window}

摘要：
{summary}

证据：
- 预警维度：{warning_dimension}
- 机审一级标签：{mach_root_label_name}
- 策略ID：{strategy_id}
- 策略名称：{strategy_name}
- 日均进审量：{avg_review_in_cnt}
- 日均完审量：{avg_review_done_cnt}
- 日均打标量：{avg_label_cnt}
- 打标率：{label_rate}
- 命中规则：{hit_rule_id}
- 命中条件：{hit_condition}
- 是否+1同意：{is_plus1_agreed}
- 更新日期：{plus1_update_date}

建议 Owner：{owner}
Owner 依据：{routing_evidence}
置信度：{confidence}

说明：
- 本通知为 debug_only 草稿，未真实发送。
- 打标率口径：打标量 / 完审量。
- 风险域维度行的策略ID、策略名称可为空，POC 按机审一级标签映射。
- source_footer：{source_footer}
```

## 打标率维度拆解摘要草稿

```text
【人审效率分析｜打标率维度拆解】

维度：{dimensions}
周期：{time_window}

核心发现：
{summary}

TOP 低效组合：
{top_dimension_reason_rows}

限制说明：
{limitations}

本结果仅为调试草稿，真实触达前需要人工确认。
```

## 举报流转低打标率摘要草稿

```text
【人审效率分析｜举报场景低打标率】

数据方向：report_flow / 举报流转
数据集：举报流转任务明细数据集（3952594 / appId 555137）
周期：{time_window}

核心发现：
{summary}

低打标率 enpool_reason：
{top_enpool_reason_rows}

口径：
- 时间字段：进审日期
- 打标率：打标量_report_id / 人审完结量_report_id
- 基础筛选：举报专项一轮/终轮队列范围 + 任务类型 + 一轮队列排除兜底/海外/特殊

限制说明：
{limitations}

本结果仅为调试草稿，真实触达前需要人工确认。
```

## 两周期剔除 +1 同意汇总对比草稿

```text
【人审效率周对比｜低效策略汇总统计（剔除 +1 同意）】

上周期：{previous_time_window}
本周期：{current_time_window}

汇总：
- 低效策略数：{previous_strategy_count} → {current_strategy_count}（{strategy_count_delta}）
- 低效策略日均完审量：{previous_avg_review_done_cnt} → {current_avg_review_done_cnt}（{avg_review_done_delta}，{avg_review_done_growth_rate}）
- 低效策略加权打标率：{previous_label_rate} → {current_label_rate}

重点变化：
{top_positive_delta_rows}

对比表：{sheet_url}

口径：
- 每个周期分别使用 `汇总统计_剔除+1同意`。
- 每个周期按 `更新日期 < 当前周期开始日` 剔除 +1 同意策略。
- 总计打标率 = SUM(日均打标量) / SUM(日均完审量)，不平均行级打标率。

说明：
- 本通知默认仅为草稿；真实发送、在线表格导入均需用户明确确认。
- source_footer：{source_footer}
```

## 升级草稿

```text
【需人工确认｜打标率分析】

触发原因：{review_reason}
待确认事项：
1. 指标口径是否确认。
2. 数据分区是否就绪。
3. Owner 是否准确。
4. 是否允许真实触达或线上状态写入。

当前不会发送真实通知或写入线上状态。
```

## Owner / POC 路由

## 路由原则

本场景用于基于低打标率数据生成 POC / 触达对象路由计划。当前 POC 找人逻辑按 `mach_root_label_name`（机审一级标签）映射到 POC 姓名；真实触达前必须再完成飞书 open_id 解析、目标确认和发送门禁校验。

## 当前开发阶段决策

- POC 路由粒度：优先按 `mach_root_label_name` 映射 POC；`warning_dimension`、`strategy_id`、`strategy_name` 作为证据字段保留。默认低效分级不按 `reason` 分组。
- 风险域维度行的 `strategy_id`、`strategy_name` 为空，表示该机审一级标签下低效策略汇总后的风险域预警；此类行仍按 `mach_root_label_name` 映射 POC。
- 若原始机审一级标签为空，分析取数层会先按策略名称补齐为高热、政媒、商业化或指令舆情相关，再进入 POC 路由。
- 当前 POC 映射资产尚未包含 `商业化`，命中商业化补映射的行会进入未映射 / 人工确认路径。
- 举报流转方向（`data_direction=report_flow`）默认没有 `mach_root_label_name`，以 `enpool_reason` 作为证据字段，Owner 建议先路由到“举报”POC，占位 POC 为韩晶晶；真实触达前必须由人审运营确认是否需要按风险域或队列进一步拆分。
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
| 党和国家形象负面 | 肖克聪 |
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

## SLA 与升级

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
