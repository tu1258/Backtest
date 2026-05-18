# RS90 Backtest Report

## Data summary
- ticker_list_rows: 5288
- downloaded_price_rows: 2578083
- downloaded_unique_tickers: 5282
- date_min: 2024-04-29
- date_max: 2026-05-15

## Recent RS90 counts
- 2026-05-11: 525
- 2026-05-12: 525
- 2026-05-13: 525
- 2026-05-14: 525
- 2026-05-15: 525

## Strategy summary
| strategy_combo     | entry_strategy   | exit_mode   |   pivot_left |   pivot_right |   trade_count |   win_rate |   profit_factor |   avg_r |   median_r |   avg_win_loss_ratio |   max_consecutive_losses |     final_equity |   total_return |   max_drawdown |   avg_holding_days |
|:-------------------|:-----------------|:------------|-------------:|--------------:|--------------:|-----------:|----------------:|--------:|-----------:|---------------------:|-------------------------:|-----------------:|---------------:|---------------:|-------------------:|
| breakout_ma10      | breakout         | ma10        |            2 |             2 |           234 |   0.17094  |          0.2552 | -0.5484 |    -1      |               1.2378 |                      135 | 939542           |      -0.060458 |      -0.060458 |               1.19 |
| breakout_pivot_low | breakout         | pivot_low   |            2 |             2 |           216 |   0.189815 |          0.3003 | -0.5346 |    -1      |               1.2817 |                      129 | 947063           |      -0.052937 |      -0.052937 |               1.35 |
| rsi2_ma10          | rsi2             | ma10        |            2 |             2 |             4 |   0.75     |       1554.26   |  2.5688 |     0.5938 |             518.088  |                        1 |      1.04953e+06 |       0.049534 |       0        |               1    |
| rsi2_pivot_low     | rsi2             | pivot_low   |            2 |             2 |             4 |   0.75     |       1582.66   |  3.2438 |     1.9438 |             527.552  |                        1 |      1.05049e+06 |       0.050486 |       0        |               1.75 |

## Output files
- `outputs/backtest/REPORT.md`
- `outputs/backtest/all_reports.json`
- `outputs/backtest/breakout_ma10/equity_curve.csv`
- `outputs/backtest/breakout_ma10/equity_curve.png`
- `outputs/backtest/breakout_ma10/performance_report.json`
- `outputs/backtest/breakout_ma10/rs90_daily_recent.csv`
- `outputs/backtest/breakout_ma10/trades.csv`
- `outputs/backtest/breakout_pivot_low/equity_curve.csv`
- `outputs/backtest/breakout_pivot_low/equity_curve.png`
- `outputs/backtest/breakout_pivot_low/performance_report.json`
- `outputs/backtest/breakout_pivot_low/rs90_daily_recent.csv`
- `outputs/backtest/breakout_pivot_low/trades.csv`
- `outputs/backtest/data_summary.json`
- `outputs/backtest/rs90_daily_recent.csv`
- `outputs/backtest/rsi2_ma10/equity_curve.csv`
- `outputs/backtest/rsi2_ma10/equity_curve.png`
- `outputs/backtest/rsi2_ma10/performance_report.json`
- `outputs/backtest/rsi2_ma10/rs90_daily_recent.csv`
- `outputs/backtest/rsi2_ma10/trades.csv`
- `outputs/backtest/rsi2_pivot_low/equity_curve.csv`
- `outputs/backtest/rsi2_pivot_low/equity_curve.png`
- `outputs/backtest/rsi2_pivot_low/performance_report.json`
- `outputs/backtest/rsi2_pivot_low/rs90_daily_recent.csv`
- `outputs/backtest/rsi2_pivot_low/trades.csv`
- `outputs/backtest/strategy_summary.csv`
