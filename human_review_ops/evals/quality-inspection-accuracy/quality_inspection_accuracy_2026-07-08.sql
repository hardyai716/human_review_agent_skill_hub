WITH agg AS (
  SELECT
    if(`[p_date]` = '2026-07-08', 'cur', 'prev') AS period,
    `[队列分类汇总]` AS queue_category_summary,
    `[队列分类 (上游+群组)]` AS queue_category_group,
    `[审核准确率]` AS audit_accuracy,
    `[抽检量]` / count(DISTINCT `[p_date]`) AS avg_daily_sample_cnt,
    `[审核错误量]` / count(DISTINCT `[p_date]`) AS avg_daily_error_cnt,
    `[通过准确率]` AS pass_accuracy,
    `[通过抽检量]` / count(DISTINCT `[p_date]`) AS avg_daily_pass_sample_cnt,
    `[打标准确率]` AS label_accuracy,
    `[打标抽检量]` / count(DISTINCT `[p_date]`) AS avg_daily_label_sample_cnt
  FROM `aeolus_data_db_cqc_core_202509`.`aeolus_data_table_8_2974603_migrate_v2_prod`
  WHERE `[p_date]` IN ('2026-07-08', '2026-07-07')
    AND `[质检模式]` = '抽检模式'
    AND `[视频质量_队列范围]` IN ('【大盘】安全', '【大盘】画风')
    AND `[抽检质量-是否剔除]` NOT LIKE '%剔除%'
  GROUP BY period, queue_category_summary, queue_category_group
)
SELECT
  cur.queue_category_summary,
  cur.queue_category_group,
  cur.audit_accuracy,
  cur.audit_accuracy - prev.audit_accuracy AS audit_accuracy_diff_1d,
  cur.avg_daily_sample_cnt,
  cur.avg_daily_error_cnt,
  cur.pass_accuracy,
  cur.avg_daily_pass_sample_cnt,
  cur.label_accuracy,
  cur.avg_daily_label_sample_cnt
FROM agg AS cur
ANY LEFT JOIN agg AS prev
  ON cur.queue_category_summary = prev.queue_category_summary
 AND cur.queue_category_group = prev.queue_category_group
 AND prev.period = 'prev'
WHERE cur.period = 'cur'
ORDER BY cur.queue_category_summary, cur.queue_category_group
LIMIT 100
SETTINGS
  enable_case_when_prop = 1,
  enable_sharding_optimize = 1,
  max_plan_segment_num = 50,
  enable_optimizer = 1,
  enable_split_countd_to_state_merge = 1
