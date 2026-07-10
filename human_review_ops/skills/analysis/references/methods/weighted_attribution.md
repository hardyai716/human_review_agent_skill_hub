# 加权归因方法

## 适用范围

用于解释比率类指标在两个可比周期之间的变化，当前默认用于打标率下探分析。

## 主排序口径

策略加权影响是默认主排序字段：

```text
weighted_impact_i = cur_share_i * cur_rate_i - prev_share_i * prev_rate_i
```

字段含义：

| 字段 | 含义 |
| --- | --- |
| `cur_share_i` | 本期策略完审量 / 本期当前拆解层总完审量 |
| `prev_share_i` | 上期策略完审量 / 上期当前拆解层总完审量 |
| `cur_rate_i` | 本期策略打标量 / 本期策略完审量 |
| `prev_rate_i` | 上期策略打标量 / 上期策略完审量 |

排序规则：

- 定位下降贡献时按 `weighted_impact` 升序排序，负值越大表示拖累越大。
- `weighted_impact` 可以在同一拆解层内加总解释整体变化。
- 主键使用 `mach_root_label_name × strategy_id`；`strategy_name` 仅用于展示。

## 二级解释字段

Rate / Mix Effect 只用于解释为什么某策略影响大，不作为主排序字段。

```text
rate_effect_i = ((cur_share_i + prev_share_i) / 2) * (cur_rate_i - prev_rate_i)
mix_effect_i = ((cur_rate_i + prev_rate_i) / 2) * (cur_share_i - prev_share_i)
```

输出字段：

| 字段 | 要求 |
| --- | --- |
| `weighted_impact` | 主排序字段。 |
| `impact_share` | `weighted_impact / SUM(weighted_impact)`；分母为 0 时不输出。 |
| `cur_rate` / `prev_rate` | 本期 / 上期打标率。 |
| `rate_diff` | `cur_rate - prev_rate`。 |
| `cur_share` / `prev_share` | 本期 / 上期完审占比。 |
| `share_diff` | `cur_share - prev_share`。 |
| `cur_avg_daily_review_done_cnt` / `prev_avg_daily_review_done_cnt` | 本期 / 上期日均完审量。 |
| `avg_daily_review_done_cnt_diff` | 日均完审量差异。 |
| `rate_effect` | 二级解释字段。 |
| `mix_effect` | 二级解释字段。 |

## 质量要求

- 两个周期长度必须一致，默认近 7 天 vs 前 7 天。
- 比率必须用 `SUM(label_cnt) / SUM(review_done_cnt)` 重算。
- 维度必须来自原始字段或已治理字段，不做人工主题归并。
- 样本过小、字段缺失、分母为 0 时必须标注限制。
