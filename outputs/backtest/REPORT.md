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
| breakout_ma10      | breakout         | ma10        |           136 |   0.213235 |          0.5465 | -0.3306 |    -0.6332 |               2.0163 |                       56 |         969842 |      -0.030158 |      -0.032723 |               1.42 |
| breakout_pivot_low | breakout         | pivot_low   |           115 |   0.26087  |          0.6355 | -0.2605 |    -0.6897 |               1.8007 |                       60 |         979050 |      -0.02095  |      -0.027117 |               1.85 |
| rsi2_ma10          | rsi2             | ma10        |             4 |   0.5      |          0.6884 |  0.4945 |     0.5383 |               0.6884 |                        1 |         999633 |      -0.000367 |      -0.001228 |               1.5  |
| rsi2_pivot_low     | rsi2             | pivot_low   |             4 |   0.25     |          0.0891 | -0.4233 |    -0.5866 |               0.2672 |                        3 |         998177 |      -0.001823 |      -0.001823 |               1.5  |

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
