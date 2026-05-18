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
| strategy_combo     | entry_strategy   | exit_mode   |   trade_count |   win_rate |   profit_factor |   avg_r |   median_r |   avg_win_loss_ratio |   max_consecutive_losses |   final_equity |   total_return |   max_drawdown |   avg_holding_days |
|:-------------------|:-----------------|:------------|--------------:|-----------:|----------------:|--------:|-----------:|---------------------:|-------------------------:|---------------:|---------------:|---------------:|-------------------:|
| breakout_ma10      | breakout         | ma10        |          7901 |   0.283255 |          1.175  |  0.0275 |    -0.4735 |               2.9679 |                       44 |    1.61429e+06 |       0.614294 |      -0.27489  |               5.01 |
| breakout_pivot_low | breakout         | pivot_low   |          5356 |   0.340553 |          1.5394 |  0.2772 |    -0.7721 |               2.9732 |                       42 |    3.15467e+06 |       2.15467  |      -0.298211 |               9.96 |
| rsi2_ma10          | rsi2             | ma10        |           598 |   0.434783 |          2.8492 |  1.0733 |    -1      |               3.693  |                       13 |    1.19479e+06 |       0.194789 |      -0.018842 |               1.08 |
| rsi2_pivot_low     | rsi2             | pivot_low   |           559 |   0.203936 |          1.115  |  0.287  |    -1      |               4.3329 |                       23 |    1.01775e+06 |       0.017752 |      -0.045111 |               5.55 |

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
- `outputs/backtest/equity_curve.csv`
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
