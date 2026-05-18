# RS90 Backtest Report

## Data summary
- ticker_list_rows: 5288
- downloaded_price_rows: 485769
- downloaded_unique_tickers: 1000
- date_min: 2024-04-29
- date_max: 2026-05-18

## Recent RS90 counts
- 2026-05-12: 100
- 2026-05-13: 100
- 2026-05-14: 100
- 2026-05-15: 100
- 2026-05-18: 96

## Strategy summary
| strategy_combo     | entry_strategy   | exit_mode   |   pivot_left |   pivot_right |   trade_count |   win_rate |   profit_factor |   avg_r |   median_r |   avg_win_loss_ratio |   max_consecutive_losses |     final_equity |   total_return |   max_drawdown |   avg_holding_days |
|:-------------------|:-----------------|:------------|-------------:|--------------:|--------------:|-----------:|----------------:|--------:|-----------:|---------------------:|-------------------------:|-----------------:|---------------:|---------------:|-------------------:|
| breakout_ma10      | breakout         | ma10        |            2 |             2 |            11 |  0.0909091 |          0.0095 | -0.7198 |    -0.685  |               0.0947 |                       10 | 994252           |      -0.005748 |      -0.005908 |               1    |
| breakout_pivot_low | breakout         | pivot_low   |            2 |             2 |            11 |  0.0909091 |          0.0074 | -0.8578 |    -1      |               0.0745 |                       10 | 992687           |      -0.007313 |      -0.007473 |               2.18 |
| rsi2_ma10          | rsi2             | ma10        |            2 |             2 |             1 |  1         |        nan      |  0.0875 |     0.0875 |             nan      |                        0 |      1.00002e+06 |       1.7e-05  |       0        |               1    |
| rsi2_pivot_low     | rsi2             | pivot_low   |            2 |             2 |             1 |  1         |        nan      |  0.0875 |     0.0875 |             nan      |                        0 |      1.00002e+06 |       1.7e-05  |       0        |               1    |

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
