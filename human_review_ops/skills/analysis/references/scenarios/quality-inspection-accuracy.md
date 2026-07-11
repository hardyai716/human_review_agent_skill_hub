# 场景：质量领域 / 质检准确率

## 场景元信息

| 项                            | 内容                                                                                          |
| ---------------------------- | ------------------------------------------------------------------------------------------- |
| `scenario_key`               | `quality-inspection-accuracy`                                                               |
| 当前已接入子指标                     | 大盘（不含举报）质检准确率                                                                               |
| 待补子指标                        | 风险域维度质检准确率、举报质检准确率                                                                          |
| 当前主指标字段                      | `[审核准确率]`                                                                                   |
| 相关指标字段                       | `[通过准确率]`、`[打标准确率]`、`[抽检量]`、`[审核错误量]`                                                       |
| 模块                           | 质量领域                                                                                        |
| 运营对象                         | 队列分类汇总、队列分类（上游+群组）下的质检准确率表现                                                                 |
| 当前状态                         | 字段清单已通过 Aeolus `dataset-fields` 验证；已基于可视化报表 `rid=13057301` 提取底层 SQL 并用 `aeolus query` 复跑通过。 |
| 默认运行模式                       | `debug_only` / readonly                                                                     |

## 触发与排除

触发：

- 查询质检准确率、审核准确率、通过准确率、打标准确率。
- 查询质量领域准确率是否达标、波动或低于目标。
- 按队列分类汇总、队列分类（上游+群组）拆解大盘（不含举报）质检准确率。
- 解释质检方式、质检比例、质检量、置信度和准确率目标。

排除：

- 打标率、低打标 reason、低效策略分级，使用 `efficiency-label-rate`。
- 自动处置准确率、三级标签准确率、机审自动处置准确率，使用 `efficiency-auto-disposal-accuracy`。
- 底线事故数、人工审核准确率。
- 通知草稿、负责人路由、状态写入。

## 指标口径

本节只维护 Aeolus 数据集标准字段及其 `` `[数据集字段名]` `` 查询写法；`metric_id`、内部 alias 和脚本变量不进入字段表。

支持维度字段：

| 概念         | aeolus query 使用字段      | 说明                                                |
| ---------- | --------------------- | ------------------------------------------------- |
| 日期分区       | `[p_date]`             | 数据集字段为 `p_date`，分区字段。                              |
| 队列分类汇总     | `[队列分类汇总]`            | 默认输出维度；通过 `[队列分类 (上游+群组)]`、`[视频质量_队列范围]` 等字段编译而来。 |
| 队列分类（上游+群组） | `[队列分类 (上游+群组)]`     | 默认输出维度。                                          |

默认筛选字段：

| 概念       | aeolus query 使用字段 | 说明                         |
| -------- | ---------------- | -------------------------- |
| 质检模式     | `[质检模式]`         | 固定 `抽检模式`。                |
| 视频质量队列范围 | `[视频质量_队列范围]`    | 固定 `【大盘】安全`、`【大盘】画风`。 |
| 剔除标记     | `[抽检质量-是否剔除]`    | 排除包含 `剔除` 的样本。           |

指标字段与口径：

| 概念            | aeolus query 使用字段 | 口径                                  | 说明                           |
| ------------- | ---------------- | ----------------------------------- | ---------------------------- |
| 质检准确率 / 审核准确率 | `[审核准确率]`        | `[审核准确量] / [抽检量]`                 | 当前主指标字段。                     |
| 审核准确量         | `[审核准确量]`        | `[抽检量] - [审核错误量]`                 | 主指标准确量字段，用于解释 `[审核准确率]`。    |
| 抽检量           | `[抽检量]`          | 数据集标准指标                             | 主指标分母字段；日均抽检量由该字段按查询窗口派生。  |
| 审核错误量         | `[审核错误量]`        | 数据集标准指标                             | 主指标错误量字段；日均审核错误量由该字段按查询窗口派生。 |
| 通过准确率         | `[通过准确率]`        | `([通过抽检量] - [通过错误量]) / [通过抽检量]` | 围栏指标。                        |
| 通过抽检量         | `[通过抽检量]`        | 数据集标准指标                             | 通过准确率分母字段；日均通过抽检量由该字段按查询窗口派生。 |
| 通过错误量         | `[通过错误量]`        | 数据集标准指标                             | 通过准确率口径引用字段，当前默认 SQL 不输出。    |
| 打标准确率         | `[打标准确率]`        | `([打标抽检量] - [打标错误量]) / [打标抽检量]` | 围栏指标。                        |
| 打标抽检量         | `[打标抽检量]`        | 数据集标准指标                             | 打标准确率分母字段；日均打标抽检量由该字段按查询窗口派生。 |
| 打标错误量         | `[打标错误量]`        | 数据集标准指标                             | 打标准确率口径引用字段，当前默认 SQL 不输出。    |

规则：

- 质检准确率 = 质检准确量 / 总质检量。
- 通过准确率 = 通过准确量 / 通过质检量。
- 打标准确率 = 打标准确量 / 打标质检量。
- 数据集没有直接提供“日均”字段；日均指标必须由对应量级字段除以 `COUNT(DISTINCT [p_date])` 派生，不写入字段清单。
- 百分比展示保留两位小数；日均量可保留整数或一位小数。
- 不得用打标率、自动处置准确率或底线事故数替代本指标。

## 质检知识

- 质检方式主要包括随机质检和交叉质检。
- 交叉质检发现问题的能力通常是随机质检的 2 倍以上。
- 交叉质检数据时效性约 T+1，随机质检约 T+3。
- 一般在编 8 人及以上队列采用交叉质检，小于 8 人队列采用随机质检。
- 质检方式需为盲检。
- 质检比例和质检量原则上根据置信度设定。
- 置信度受时间跨度（周度置信或天级置信）、置信区间（95% 或 99%）、误差范围（如 ±1% 或 ±3%）影响。
- 默认建议采用周度置信、95% 置信区间、±1% 误差来定质检量，并按单域通过、打标分别置信。
- 样本量越大，置信抽检比例越低；置信区间越高，质检量越大；误差范围越小，质检量越大。
- 准确率目标：整体 `>=95%`；涉政底线要求 `>=98%`；自营、X 模式、BPO、众包质量目标要求一致。

## 数据源与字段

查询路径优先级：

1. `curated_semantic_sql`：通过 `scripts/quality_inspection_accuracy_query.py` 生成的 Aeolus 语义字段 SQL，适用于当前大盘（不含举报）质检准确率。
2. `saved_report_sql`：从已验证可视化报表 `rid=13057301` 提取底层 SQL，仅作为口径核验材料。
3. `governed_dataset`：Aeolus 数据集 `3533559`，用于字段发现和权限校验。
4. `raw_exploration`：只允许字段探测，不得作为最终结论。

推荐来源：

| 项             | 内容                                                                                                                                                                                                                         |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Region        | `cn`                                                                                                                                                                                                                       |
| App ID        | `555137`                                                                                                                                                                                                                   |
| Dataset ID    | `3533559`                                                                                                                                                                                                                  |
| Dataset 链接    | `https://data.bytedance.net/aeolus/pages/dataManage/detail/3533559?appId=555137`                                                                                                                                           |
| Dataset 名称    | `【抖音群组】抽检明细数据集`                                                                                                                                                                                                            |
| 已验证报表 URL     | `https://data.bytedance.net/aeolus/pages/dataQuery?appId=555137&dashboardId=1464847&id=1783759075005040&isDefault=1&reportQuerySchemaKey=b3f9bf35-f00c-4301-b2df-fd281bc6f01f&rid=13057301&sid=3533559&waitForDataReady=0` |
| 已验证 Report ID | `13057301`                                                                                                                                                                                                                 |
| 已验证 backing 表 | `aeolus_data_db_cqc_core_202509.aeolus_data_table_8_2974603_migrate_v2_prod`                                                                                                                                               |
| 上游表           | `dw_cqc_audit.dm_quality_cqc_dy_task_quality_info_di`、`dw_cqc_audit.dm_task_cqc_quality_midtable_di`、`cqc_manage.cqc_first_appeal_manaual_mark_df`                                                                         |
| 分区            | `p_date`                                                                                                                                                                                                                   |
| 新鲜度           | 随质检方式变化：交叉质检约 T+1，随机质检约 T+3                                                                                                                                                                                                |
| 数据集 Owner     | `yilinliu.123`                                                                                                                                                                                                             |

字段清单基于 `bytedcli -j aeolus dataset-fields -r cn 3533559` 的真实返回。运行态可用字段、指标口径、默认维度和默认筛选项统一维护在上方“指标口径”章节；本节不重复维护字段表，未出现在该数据集中的字段不得写入默认查询口径。

字段写法：

- 遵循 `references/common.md#Aeolus 字段引用快速参考`：通过 `aeolus query` 按数据集 ID 编译 `` `[数据集字段名]` ``，非必要时不手写底层字段逻辑。
- 当前脚本使用数据集 `3533559` 的语义字段，例如 `` `[审核准确率]` ``、`` `[队列分类汇总]` ``。
- 如必须脱离 Aeolus 数据集语义层、直接写纯 ClickHouse SQL，应重新通过 `dataset-fields` 或已验证报表 SQL 确认口径；本场景文档不维护底层字段逻辑。
- 直接 SQL 中使用逻辑表名 `` `3533559` `` 已验证会失败，错误为 `unknownTable`。
- 报表 SQL 尾部自带 `FORMAT JSONCompact /*...*/`；使用 `aeolus query` 复跑时必须去掉尾部 `FORMAT JSONCompact`，否则会在 `FORMAT` 处报 ClickHouse 语法错误。
- 已验证可执行 SQL 使用 backing 表 `aeolus_data_db_cqc_core_202509.aeolus_data_table_8_2974603_migrate_v2_prod`。

## SQL 生成脚本

可维护 SQL 由脚本生成，不手写长 SQL：

```bash
python3 human_review_ops/skills/analysis/scripts/quality_inspection_accuracy_query.py \
  --current-date 2026-07-08 \
  --format sql
```

默认日期：

- `--current-date` 缺省取 T-3，适配随机质检约 T+3 的新鲜度。
- `--previous-date` 缺省取 `current_date - 1 day`。

执行方式：

```bash
SQL="$(python3 human_review_ops/skills/analysis/scripts/quality_inspection_accuracy_query.py --current-date 2026-07-08 --format sql)"
bytedcli -j aeolus query -r cn 3533559 "$SQL" --limit 100
```

脚本职责：

- 使用 Aeolus 语义字段生成可执行 SQL，保持口径与数据集字段定义一致。
- 保留 backing 表 `aeolus_data_db_cqc_core_202509.aeolus_data_table_8_2974603_migrate_v2_prod` 作为 `FROM`，不使用逻辑表名 `` `3533559` ``。
- 默认输出大盘（不含举报）口径：`质检模式=抽检模式`、`视频质量_队列范围 IN 【大盘】安全/画风`、`抽检质量-是否剔除 NOT LIKE '%剔除%'`。
- 默认只生成 SQL，不执行查询、不写文件、不发通知。

已验证结果：

- `--current-date 2026-07-08` 生成的语义字段 SQL 返回 `4` 行，和报表 SQL 结果一致。
- 生成 SQL 为 `44` 行，明显短于旧版长 SQL 和报表原始 SQL，更适合维护。

## 已验证报表 SQL 口径

底层 SQL 抽取命令：

```bash
bytedcli -j aeolus report query \
  --format sql \
  --url "https://data.bytedance.net/aeolus/pages/dataQuery?appId=555137&dashboardId=1464847&id=1783759075005040&isDefault=1&reportQuerySchemaKey=b3f9bf35-f00c-4301-b2df-fd281bc6f01f&rid=13057301&sid=3533559&waitForDataReady=0" \
  --limit 100 \
  --timeout-ms 60000
```

复跑执行要求：

- 提取 `data.sql`。
- 删除 SQL 尾部 `FORMAT JSONCompact /*...*/`。
- 使用 `bytedcli -j aeolus query -r cn 3533559 "<clean_sql>" --limit 100` 执行。

已验证报表过滤：

```text
p_date = '2026-07-08'
对比日期 = '2026-07-07'
质检模式 = '抽检模式'
视频质量_队列范围 IN ('【大盘】安全', '【大盘】画风')
抽检质量-是否剔除 NOT LIKE '%剔除%'
```

已验证结果特征：

- 返回 `4` 行，未截断。
- 队列分类包括 `2轮 / 1-涉政合域`、`2轮 / 4-国家安全(未切换，无宗教)`、`2轮 / 13-非专审队列`、`高热专项 / 高热专项`。
- 报表 SQL 提取长度约 `71647` 字符；收敛后的可维护 SQL 已验证结果一致，但文档不内嵌长 SQL。

## 默认过滤

大盘（不含举报）质检准确率默认过滤已前置在“指标口径”的默认筛选字段表中：

```text
质检模式 IN ('抽检模式')
视频质量_队列范围 IN ('【大盘】安全', '【大盘】画风')
抽检质量-是否剔除 NOT LIKE '%剔除%'
```

## 支持维度与筛选字段

默认支持维度和筛选字段已前置在“指标口径”章节。用户指定新维度时，先确认字段含义、粒度、权限和 Owner；无法确认时停止。

## 分析模式

| 模式      | `task_type`                         | 触发条件            | 主要产出                                    |
| ------- | ----------------------------------- | --------------- | --------------------------------------- |
| 大盘质检准确率 | `quality_market_no_report_accuracy` | 查询大盘（不含举报）质检准确率 | 队列分类维度下的审核准确率、日均抽检量、日均审核错误量、通过准确率、打标准确率 |
| 质检准确率趋势 | `quality_inspection_trend`          | 查询趋势、波动、目标达成    | QueryPlan、趋势结果、source_footer           |
| 维度拆解    | `dimension_breakdown`               | 按当前已治理维度拆解      | `dimensions` 明细和汇总                      |

通用顺序：

1. 确认子指标是否为已接入的大盘（不含举报）质检准确率。
2. 解析时间窗口；缺失时停止澄清。
3. 确认数据源、字段和过滤项。
4. 生成 QueryPlan，默认 source 为 `aeolus_dataset:3533559`。
5. 优先使用脚本生成的语义字段 SQL；保存报表 SQL 仅用于口径核验，复跑报表 SQL 时需去掉尾部 `FORMAT JSONCompact`。
6. 输出数据事实、口径说明、限制说明和 source_footer。

## QueryPlan 要求

必填字段：

- `query_plan_id`
- `scenario_key`
- `metric_id`
- `sub_metric_id`
- `task_type`
- `time_range`
- `dimensions`
- `filters`
- `source_priority`
- `allowed_sources`
- `forbidden_sources`
- `quality_checks`
- `review_required`

大盘（不含举报）质检准确率字段清单和保存报表 SQL 均已验证；同报表口径复用时可设 `review_required=false`，新增时间窗口、维度或过滤时仍需 `review_required=true`。

说明：

- `metric_id`、`sub_metric_id` 是 Skill 运行态路由字段，不是 Aeolus 数据集字段。
- 字段清单、指标口径和维度说明只维护 Aeolus 数据集标准字段及其 `` `[数据集字段名]` `` 查询写法。

## 输出要求

- 展示队列分类汇总、队列分类（上游+群组）。
- 展示审核准确率、日均抽检量、日均审核错误量。
- 展示通过准确率、日均通过抽检量、打标准确率、日均打标抽检量。
- 百分比保留两位小数。
- 日均量说明为派生字段。
- source_footer 必须说明数据集、报表 ID、backing 表、过滤项、时间窗口、新鲜度和 `FORMAT JSONCompact` 清理要求。

source_footer ref 示例：

```json
{
  "metric_contract_ref": "references/scenarios/quality-inspection-accuracy.md#指标口径",
  "dataset_reference_ref": "references/scenarios/quality-inspection-accuracy.md#数据源与字段",
  "analysis_ref": "references/scenarios/quality-inspection-accuracy.md#分析模式"
}
```

## 失败处理

- 子指标不是大盘（不含举报）：停止，说明风险域维度和举报质检准确率仍待补数据源。
- 字段映射失败：停止，列出缺失字段。
- 直接 SQL 逻辑表名失败：不要解释为无数据；改用保存报表 SQL 或 backing 表。
- 报表 SQL 在 `FORMAT JSONCompact` 处失败：删除尾部 `FORMAT JSONCompact /*...*/` 后重试。
- 分母为 0：输出质量风险，不给强结论。

## 正反例

正例：

- 看一下大盘不含举报的质检准确率。
- 按队列分类汇总拆一下审核准确率。
- 看大盘安全、画风的通过准确率和打标准确率。
- 解释一下质检方式和质检量置信度。

反例：

- 近 7 天低打标率 reason 有哪些？
- 自动处置准确率下降了。
- 底线事故数上升了。

低信息量：

- 这个队列怎么了？

处理：先询问指标、子指标、时间窗口和队列范围，不直接查询。
