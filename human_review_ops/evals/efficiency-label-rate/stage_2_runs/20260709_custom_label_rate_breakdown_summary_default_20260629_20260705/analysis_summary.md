# 自定义低打标率多维查询汇总

## 结论摘要

- 时间窗口：`2026-06-29` ~ `2026-07-05`。
- 维度：`机审一级标签 × strategy_id × strategy_name × reason`。
- 命中打标率 `<0.1` 的分组数：`10293`。
- 命中分组加权打标率：`5.02%`。
- 完整飞书电子表格：https://bytedance.larkoffice.com/sheets/WwjIsQK4Ahn6RCtT9NOckMxUnpc

## Top 分组

| 排名 | 机审一级标签 | strategy_id | strategy_name | reason | 日均进审量 | 日均完审量 | 日均打标量 | 打标率 |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | 领导人 | 10003788046 | 【送人审】N1-title词表 | title_leader_table_8578 | 9105 | 8993 | 586 | 6.51% |
| 2 | 国家安全 | 10013031733 | 【人审】国家安全-常规词表-OCR | national_security_regular_OCR_words_review | 6854 | 6765 | 415 | 6.14% |
| 3 | 指令舆情相关 | 10008330225 | 【ZL送人审】指令地理条件命中召回-300vv | fence_recall | 6482 | 6483 | 261 | 4.03% |
| 4 | 指令舆情相关 | 10027554497 | 【ZL送人审】综合_指令自见综合&举报-副本34 | ZL_eva_227415_general_multi_rept_review | 4732 | 4747 | 245 | 5.15% |
| 5 | 领导人 | 10006128216 | 核心政务号\|政务号白名单 | core_protection_gov_user | 4620 | 4620 | 0 | 0.01% |
| 6 | 色情性化 | 10013833877 | 色情低俗-色情导流-词表-高准机审 | sqds_sqdl_key_word_high_acc_review | 4398 | 4397 | 353 | 8.04% |
| 7 | 领导人 | 15811696 | 【送审】领导人标题敏感词-旧 | leader_antidirt | 4374 | 4320 | 350 | 8.10% |
| 8 | 国家安全 | 10012811198 | 【人审-LS风险】BASE_OCR_LS常规词表_8883 | LS_regular_BASE_OCR_words_review | 4266 | 4201 | 65 | 1.54% |
| 9 | 国家安全 | 10032388172 | 【人审-藏语队列】藏语风险用户全量进审 | national_security_tibetan_risk_user_list_manual | 3325 | 3443 | 235 | 6.83% |
| 10 | 国家安全 | 10033554719 | 识别_gandalf策略替换_时政8分类p2LS | model_llm_gandalf_8class_p2_ls_manual | 3387 | 3347 | 167 | 4.98% |

## 口径方法

- 日均进审量：`SUM(进审量_reviewid) / COUNT(DISTINCT p_date)`。
- 日均完审量：`SUM(完审量_reviewid) / COUNT(DISTINCT p_date)`。
- 日均打标量：`SUM(打标量__reviewid) / COUNT(DISTINCT p_date)`。
- 打标率：`SUM(打标量__reviewid) / SUM(完审量_reviewid)`。
- 过滤：标准 A/B/C/D 过滤、`完审量 > 0`、`打标率 < 0.1`。

## Provenance

> Source: governed_dataset  
> Confidence: high  
> Freshness: checked_at=2026-07-09T11:50:02.983+08:00  
> Owner: 人审效率域数据 Owner  
> Reviewed: sql_review_passed
