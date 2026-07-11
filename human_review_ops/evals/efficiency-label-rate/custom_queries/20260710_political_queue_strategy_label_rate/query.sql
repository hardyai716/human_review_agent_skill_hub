WITH base AS (
  SELECT
    `[p_date]` AS p_date,
    `[review_project_id]` AS review_project_id,
    `[review_project_title]` AS review_project_title,
    `[机审一级标签]` AS mach_root_label_name,
    `[strategy_id]` AS strategy_id,
    `[strategy_name]` AS strategy_name,
    `[reason]` AS reason,
    `[进审量_reviewid]` AS review_in_cnt,
    `[完审量_reviewid]` AS review_done_cnt,
    `[打标量__reviewid]` AS label_cnt
  FROM olap_content_security_community.dws_sft_tcs_review_task_detail_di
  WHERE `[p_date]` >= today() - 1
    AND `[p_date]` < today()
    AND `[机审一级标签]` IN ('领导人', '党和国家形象负面', '国家安全', '偏激社会情绪和涉外言论')
    AND `[scene]` IN ('community_audit_safe', 'community_audit_style', 'community_audit_moderate')
    AND toString(`[review_project_id]`) IN ('7561019147132453414', '7563544443979137563', '7561019068371780142')
  GROUP BY
    p_date,
    review_project_id,
    review_project_title,
    mach_root_label_name,
    strategy_id,
    strategy_name,
    reason
)
SELECT
  p_date,
  review_project_id,
  review_project_title,
  mach_root_label_name,
  strategy_id,
  strategy_name,
  reason,
  review_in_cnt,
  review_done_cnt,
  label_cnt,
  if(review_done_cnt = 0, 0, label_cnt / review_done_cnt) AS label_rate
FROM base
WHERE review_done_cnt >= 100
ORDER BY label_rate ASC, review_done_cnt DESC, label_cnt ASC
LIMIT 1000
