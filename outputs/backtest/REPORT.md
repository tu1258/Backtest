# RS90 Backtest Report

## Data summary
- ticker_list_rows: 5288
- downloaded_price_rows: 484808
- downloaded_unique_tickers: 1000
- date_min: 2024-04-29
- date_max: 2026-05-15

## Recent RS90 counts
- 2026-05-11: 100
- 2026-05-12: 100
- 2026-05-13: 100
- 2026-05-14: 100
- 2026-05-15: 100

## Strategy summary
| strategy_combo     | entry_strategy   | exit_mode   |   trade_count |   win_rate |   profit_factor |   avg_r |   median_r |   avg_win_loss_ratio |   max_consecutive_losses |     final_equity |   total_return |   max_drawdown |   avg_holding_days |
|:-------------------|:-----------------|:------------|--------------:|-----------:|----------------:|--------:|-----------:|---------------------:|-------------------------:|-----------------:|---------------:|---------------:|-------------------:|
| breakout_ma10      | breakout         | ma10        |            32 |   0.125    |          0.2639 | -0.5296 |    -0.8002 |               1.8474 |                       24 | 988371           |      -0.011629 |      -0.011641 |               1.5  |
| breakout_pivot_low | breakout         | pivot_low   |            30 |   0.166667 |          0.3157 | -0.4627 |    -0.7211 |               1.5784 |                       14 | 989879           |      -0.010121 |      -0.010572 |               1.77 |
| rsi2_ma10          | rsi2             | ma10        |             1 |   1        |        nan      |  1.9013 |     1.9013 |             nan      |                        0 |      1.00037e+06 |       0.000371 |       0        |               1    |
| rsi2_pivot_low     | rsi2             | pivot_low   |             1 |   0        |          0      | -1      |    -1      |             nan      |                        1 | 999805           |      -0.000195 |      -0.000212 |               2    |

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
