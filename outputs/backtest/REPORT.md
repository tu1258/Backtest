# RS90 Backtest Report

## Matrix

Entries: breakout_1_1, breakout_2_2, rsi2

Exits: trail_0_5atr, trail_1atr, ma10, 5_day_low, prev_day_low

## Data summary
- ticker_list_rows: 5288
- downloaded_price_rows: 2582967
- downloaded_unique_tickers: 5282
- date_min: 2024-04-29
- date_max: 2026-05-18

## Recent RS90 counts
- 2026-05-12: 525
- 2026-05-13: 525
- 2026-05-14: 525
- 2026-05-15: 525
- 2026-05-18: 525

## Strategy summary
| strategy_combo            | entry_strategy   | exit_mode    |   pivot_left |   pivot_right |   atr_period |   atr_multiple |   n_day_low_period |   trade_count |   win_rate |   profit_factor |   avg_r |   median_r |   avg_win_loss_ratio |   max_consecutive_losses |     final_equity |   total_return |   max_drawdown |   avg_holding_days |
|:--------------------------|:-----------------|:-------------|-------------:|--------------:|-------------:|---------------:|-------------------:|--------------:|-----------:|----------------:|--------:|-----------:|---------------------:|-------------------------:|-----------------:|---------------:|---------------:|-------------------:|
| breakout_1_1_trail_0_5atr | breakout_1_1     | trail_0_5atr |            1 |             1 |           14 |            0.5 |                  5 |            65 |  0.0615385 |          0.0287 | -0.5601 |    -0.4452 |               0.4382 |                       33 | 974675           |      -0.025325 |      -0.024471 |               0.94 |
| breakout_1_1_trail_1atr   | breakout_1_1     | trail_1atr   |            1 |             1 |           14 |            1   |                  5 |            57 |  0.0877193 |          0.0399 | -0.6244 |    -0.6462 |               0.4146 |                       36 | 971909           |      -0.028091 |      -0.02724  |               1.32 |
| breakout_1_1_ma10         | breakout_1_1     | ma10         |            1 |             1 |           14 |            1   |                  5 |            56 |  0.107143  |          0.0779 | -0.6197 |    -0.9193 |               0.6493 |                       45 | 970822           |      -0.029178 |      -0.028328 |               1.48 |
| breakout_1_1_5_day_low    | breakout_1_1     | 5_day_low    |            1 |             1 |           14 |            1   |                  5 |            55 |  0.109091  |          0.0688 | -0.7265 |    -1      |               0.5615 |                       40 | 966607           |      -0.033393 |      -0.032546 |               1.78 |
| breakout_1_1_prev_day_low | breakout_1_1     | prev_day_low |            1 |             1 |           14 |            1   |                  5 |            57 |  0.0701754 |          0.0276 | -0.6064 |    -0.5955 |               0.3657 |                       35 | 973091           |      -0.026909 |      -0.026057 |               1.25 |
| breakout_2_2_trail_0_5atr | breakout_2_2     | trail_0_5atr |            2 |             2 |           14 |            0.5 |                  5 |            47 |  0         |          0      | -0.586  |    -0.4527 |             nan      |                       47 | 981576           |      -0.018424 |      -0.017307 |               0.94 |
| breakout_2_2_trail_1atr   | breakout_2_2     | trail_1atr   |            2 |             2 |           14 |            1   |                  5 |            40 |  0.075     |          0.0443 | -0.6692 |    -0.8424 |               0.5465 |                       20 | 981194           |      -0.018806 |      -0.017689 |               1.35 |
| breakout_2_2_ma10         | breakout_2_2     | ma10         |            2 |             2 |           14 |            1   |                  5 |            39 |  0.0512821 |          0.0948 | -0.5975 |    -0.6604 |               1.753  |                       34 | 982850           |      -0.017151 |      -0.016265 |               1.36 |
| breakout_2_2_5_day_low    | breakout_2_2     | 5_day_low    |            2 |             2 |           14 |            1   |                  5 |            39 |  0.0769231 |          0.0845 | -0.7459 |    -1      |               1.0136 |                       30 | 978420           |      -0.02158  |      -0.020466 |               1.85 |
| breakout_2_2_prev_day_low | breakout_2_2     | prev_day_low |            2 |             2 |           14 |            1   |                  5 |            40 |  0.05      |          0.0146 | -0.6171 |    -0.5015 |               0.2765 |                       34 | 983520           |      -0.01648  |      -0.015361 |               1.27 |
| rsi2_trail_0_5atr         | rsi2             | trail_0_5atr |            1 |             1 |           14 |            0.5 |                  5 |             5 |  0.4       |         54.691  |  0.876  |    -0.3317 |              82.0366 |                        2 |      1.0315e+06  |       0.031498 |      -0.00933  |               0.8  |
| rsi2_trail_1atr           | rsi2             | trail_1atr   |            1 |             1 |           14 |            1   |                  5 |             5 |  0.4       |         44.7396 |  0.7424 |    -1      |              67.1093 |                        2 |      1.03137e+06 |       0.031366 |      -0.00933  |               1    |
| rsi2_ma10                 | rsi2             | ma10         |            1 |             1 |           14 |            1   |                  5 |             5 |  0.6       |         87.7006 |  1.5486 |     0.0875 |              58.467  |                        2 |      1.04592e+06 |       0.045918 |      -0.003183 |               1    |
| rsi2_5_day_low            | rsi2             | 5_day_low    |            1 |             1 |           14 |            1   |                  5 |             5 |  0.4       |         64.0897 |  1.3311 |    -1      |              96.1346 |                        3 |      1.0457e+06  |       0.045698 |      -0.003183 |               1.2  |
| rsi2_prev_day_low         | rsi2             | prev_day_low |            1 |             1 |           14 |            1   |                  5 |             5 |  0.4       |         86.0769 |  1.5211 |    -0.05   |             129.115  |                        3 |      1.04589e+06 |       0.045889 |      -0.003183 |               1    |

## Output files
- `outputs/backtest/REPORT.md`
- `outputs/backtest/all_reports.json`
- `outputs/backtest/breakout_1_1_5_day_low/equity_curve.csv`
- `outputs/backtest/breakout_1_1_5_day_low/equity_curve.png`
- `outputs/backtest/breakout_1_1_5_day_low/performance_report.json`
- `outputs/backtest/breakout_1_1_5_day_low/rs90_daily_recent.csv`
- `outputs/backtest/breakout_1_1_5_day_low/trades.csv`
- `outputs/backtest/breakout_1_1_ma10/equity_curve.csv`
- `outputs/backtest/breakout_1_1_ma10/equity_curve.png`
- `outputs/backtest/breakout_1_1_ma10/performance_report.json`
- `outputs/backtest/breakout_1_1_ma10/rs90_daily_recent.csv`
- `outputs/backtest/breakout_1_1_ma10/trades.csv`
- `outputs/backtest/breakout_1_1_prev_day_low/equity_curve.csv`
- `outputs/backtest/breakout_1_1_prev_day_low/equity_curve.png`
- `outputs/backtest/breakout_1_1_prev_day_low/performance_report.json`
- `outputs/backtest/breakout_1_1_prev_day_low/rs90_daily_recent.csv`
- `outputs/backtest/breakout_1_1_prev_day_low/trades.csv`
- `outputs/backtest/breakout_1_1_trail_0_5atr/equity_curve.csv`
- `outputs/backtest/breakout_1_1_trail_0_5atr/equity_curve.png`
- `outputs/backtest/breakout_1_1_trail_0_5atr/performance_report.json`
- `outputs/backtest/breakout_1_1_trail_0_5atr/rs90_daily_recent.csv`
- `outputs/backtest/breakout_1_1_trail_0_5atr/trades.csv`
- `outputs/backtest/breakout_1_1_trail_1atr/equity_curve.csv`
- `outputs/backtest/breakout_1_1_trail_1atr/equity_curve.png`
- `outputs/backtest/breakout_1_1_trail_1atr/performance_report.json`
- `outputs/backtest/breakout_1_1_trail_1atr/rs90_daily_recent.csv`
- `outputs/backtest/breakout_1_1_trail_1atr/trades.csv`
- `outputs/backtest/breakout_2_2_5_day_low/equity_curve.csv`
- `outputs/backtest/breakout_2_2_5_day_low/equity_curve.png`
- `outputs/backtest/breakout_2_2_5_day_low/performance_report.json`
- `outputs/backtest/breakout_2_2_5_day_low/rs90_daily_recent.csv`
- `outputs/backtest/breakout_2_2_5_day_low/trades.csv`
- `outputs/backtest/breakout_2_2_ma10/equity_curve.csv`
- `outputs/backtest/breakout_2_2_ma10/equity_curve.png`
- `outputs/backtest/breakout_2_2_ma10/performance_report.json`
- `outputs/backtest/breakout_2_2_ma10/rs90_daily_recent.csv`
- `outputs/backtest/breakout_2_2_ma10/trades.csv`
- `outputs/backtest/breakout_2_2_prev_day_low/equity_curve.csv`
- `outputs/backtest/breakout_2_2_prev_day_low/equity_curve.png`
- `outputs/backtest/breakout_2_2_prev_day_low/performance_report.json`
- `outputs/backtest/breakout_2_2_prev_day_low/rs90_daily_recent.csv`
- `outputs/backtest/breakout_2_2_prev_day_low/trades.csv`
- `outputs/backtest/breakout_2_2_trail_0_5atr/equity_curve.csv`
- `outputs/backtest/breakout_2_2_trail_0_5atr/equity_curve.png`
- `outputs/backtest/breakout_2_2_trail_0_5atr/performance_report.json`
- `outputs/backtest/breakout_2_2_trail_0_5atr/rs90_daily_recent.csv`
- `outputs/backtest/breakout_2_2_trail_0_5atr/trades.csv`
- `outputs/backtest/breakout_2_2_trail_1atr/equity_curve.csv`
- `outputs/backtest/breakout_2_2_trail_1atr/equity_curve.png`
- `outputs/backtest/breakout_2_2_trail_1atr/performance_report.json`
- `outputs/backtest/breakout_2_2_trail_1atr/rs90_daily_recent.csv`
- `outputs/backtest/breakout_2_2_trail_1atr/trades.csv`
- `outputs/backtest/breakout_atr_trail/equity_curve.csv`
- `outputs/backtest/breakout_atr_trail/equity_curve.png`
- `outputs/backtest/breakout_atr_trail/performance_report.json`
- `outputs/backtest/breakout_atr_trail/rs90_daily_recent.csv`
- `outputs/backtest/breakout_atr_trail/trades.csv`
- `outputs/backtest/breakout_ma10/equity_curve.csv`
- `outputs/backtest/breakout_ma10/equity_curve.png`
- `outputs/backtest/breakout_ma10/performance_report.json`
- `outputs/backtest/breakout_ma10/rs90_daily_recent.csv`
- `outputs/backtest/breakout_ma10/trades.csv`
- `outputs/backtest/data_summary.json`
- `outputs/backtest/rs90_daily_recent.csv`
- `outputs/backtest/rsi2_5_day_low/equity_curve.csv`
- `outputs/backtest/rsi2_5_day_low/equity_curve.png`
- `outputs/backtest/rsi2_5_day_low/performance_report.json`
- `outputs/backtest/rsi2_5_day_low/rs90_daily_recent.csv`
- `outputs/backtest/rsi2_5_day_low/trades.csv`
- `outputs/backtest/rsi2_atr_trail/equity_curve.csv`
- `outputs/backtest/rsi2_atr_trail/equity_curve.png`
- `outputs/backtest/rsi2_atr_trail/performance_report.json`
- `outputs/backtest/rsi2_atr_trail/rs90_daily_recent.csv`
- `outputs/backtest/rsi2_atr_trail/trades.csv`
- `outputs/backtest/rsi2_ma10/equity_curve.csv`
- `outputs/backtest/rsi2_ma10/equity_curve.png`
- `outputs/backtest/rsi2_ma10/performance_report.json`
- `outputs/backtest/rsi2_ma10/rs90_daily_recent.csv`
- `outputs/backtest/rsi2_ma10/trades.csv`
- `outputs/backtest/rsi2_prev_day_low/equity_curve.csv`
- `outputs/backtest/rsi2_prev_day_low/equity_curve.png`
- `outputs/backtest/rsi2_prev_day_low/performance_report.json`
- `outputs/backtest/rsi2_prev_day_low/rs90_daily_recent.csv`
- `outputs/backtest/rsi2_prev_day_low/trades.csv`
- `outputs/backtest/rsi2_trail_0_5atr/equity_curve.csv`
- `outputs/backtest/rsi2_trail_0_5atr/equity_curve.png`
- `outputs/backtest/rsi2_trail_0_5atr/performance_report.json`
- `outputs/backtest/rsi2_trail_0_5atr/rs90_daily_recent.csv`
- `outputs/backtest/rsi2_trail_0_5atr/trades.csv`
- `outputs/backtest/rsi2_trail_1atr/equity_curve.csv`
- `outputs/backtest/rsi2_trail_1atr/equity_curve.png`
- `outputs/backtest/rsi2_trail_1atr/performance_report.json`
- `outputs/backtest/rsi2_trail_1atr/rs90_daily_recent.csv`
- `outputs/backtest/rsi2_trail_1atr/trades.csv`
- `outputs/backtest/strategy_summary.csv`
