# 阶段 1 P1 真实只读打标率查询记录

## 基础信息

- 调试日期：2026-07-08
- 场景：`efficiency-label-rate`
- 运行模式：`debug_only`
- 执行模式：`real_readonly_query`
- 运行脚本：`human_review_ops/tools/runners/run_stage_1_real_readonly_label_rate.py`
- 校验脚本：`human_review_ops/tools/validators/validate_stage_1_real_readonly_label_rate.py`
- 结果文件：`20260708_real_readonly_label_rate_results.jsonl`

## 运行结论

真实只读打标率查询已跑通。

本轮确认：

- 使用风神数据集 `3888816`。
- 使用命令 `bytedcli -j aeolus query -r cn 3888816 "<SQL>" --limit 1000`。
- SQL 完整包含 A/B/C/D 基础过滤。
- 输出 `QueryPlan`、`tool_call_record`、`readonly_execution`、`analysis_result`、`source_footer` 和 `provenance`。
- 查询结果 `truncated=false`。
- 未发送通知，未写线上状态。

## 查询结果

- 条件：近 7 天 `label_rate < 0.1`，且 `review_done_cnt > 0`。
- 命中 reason 数：`414`。
- 排序：按 `review_done_cnt` 降序。

Top 15：

| reason | 完审量 | 打标量 | 打标率 |
| --- | ---: | ---: | ---: |
| `title_leader_table_8578` | 64038 | 4415 | 0.068943 |
| `national_security_regular_OCR_words_review` | 51263 | 3115 | 0.060765 |
| `fence_recall` | 48322 | 1728 | 0.035760 |
| `core_protection_gov_user` | 33052 | 5 | 0.000151 |
| `sqds_sqdl_key_word_high_acc_review` | 32912 | 2450 | 0.074441 |
| `general_fever_review_high_value` | 31059 | 2075 | 0.066808 |
| `leader_antidirt` | 30376 | 2527 | 0.083191 |
| `LS_regular_BASE_OCR_words_review` | 30018 | 502 | 0.016723 |
| `model_llm_gandalf_8class_p2_ls_manual` | 26894 | 1310 | 0.048710 |
| `national_security_tibetan_risk_user_list_manual` | 23357 | 1578 | 0.067560 |
| `leader_nlp_ocr_antidirt` | 23120 | 1934 | 0.083651 |
| `national_security_regular_title_words_review` | 23004 | 2248 | 0.097722 |
| `leader_recall_xi` | 20692 | 1497 | 0.072347 |
| `is_govB_media` | 18177 | 42 | 0.002311 |
| `ocr_leader_table_500recall` | 18131 | 701 | 0.038663 |

## Source Footer

```text
Source: governed_dataset / Aeolus dataset 3888816
Metric: label_rate = 打标量__reviewid / 完审量_reviewid
Freshness: p_date >= today() - 7 AND p_date < today()
Owner: 人审效率域数据 Owner
Reviewed: real_readonly_query_executed
```

## 后续动作

- 将真实只读 runner 纳入阶段 1 回归。
- 若需要低效分级，再基于当前真实查询入口实现 notice/P2/P1/P0 的注册 SQL 模板。
- 不默认生成通知草稿或 Owner 建议。
