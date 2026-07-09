# POC / 触达对象路由：打标率

## 路由原则

本场景用于基于低打标率数据生成 POC / 触达对象路由计划。当前 POC 找人逻辑按 `mach_root_label_name`（机审一级标签）映射到 POC 姓名；真实触达前必须再完成飞书 open_id 解析、目标确认和发送门禁校验。

## 当前开发阶段决策

- POC 路由粒度：优先按 `mach_root_label_name` 映射 POC；`reason`、`strategy_id`、`strategy_name` 作为证据字段保留。
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
- 置信度：`high` / `medium` / `low`。
- 是否需要人工确认。

## 低置信度条件

- 输入数据只有 reason 名称，没有 `mach_root_label_name`。
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
