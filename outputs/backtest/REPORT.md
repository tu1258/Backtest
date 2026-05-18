# RS90 Backtest Report

## Data summary
- ticker_list_rows: 5288
- downloaded_price_rows: 242409
- downloaded_unique_tickers: 500
- date_min: 2024-04-29
- date_max: 2026-05-15

## Recent RS90 counts
- 2026-05-11: 50
- 2026-05-12: 50
- 2026-05-13: 50
- 2026-05-14: 50
- 2026-05-15: 50

## Strategy summary
| strategy_combo     | entry_strategy   | exit_mode   |   trade_count |   win_rate |   profit_factor |   avg_r |   median_r |   avg_win_loss_ratio |   max_consecutive_losses |   final_equity |   total_return |   max_drawdown |   avg_holding_days |
|:-------------------|:-----------------|:------------|--------------:|-----------:|----------------:|--------:|-----------:|---------------------:|-------------------------:|---------------:|---------------:|---------------:|-------------------:|
| breakout_ma10      | breakout         | ma10        |          3934 |   0.281647 |          1.1454 |  0.0726 |    -0.4731 |               2.9163 |                       44 |    1.24459e+06 |       0.244588 |      -0.155991 |               5.02 |
| breakout_pivot_low | breakout         | pivot_low   |          2631 |   0.353098 |          1.6691 |  0.4187 |    -0.7011 |               3.0525 |                       23 |    2.17203e+06 |       1.17203  |      -0.165347 |              10.3  |
| rsi2_ma10          | rsi2             | ma10        |           306 |   0.405229 |          2.5585 |  1.04   |    -1      |               3.7552 |                       10 |    1.09376e+06 |       0.093759 |      -0.022228 |               1.17 |
| rsi2_pivot_low     | rsi2             | pivot_low   |           283 |   0.183746 |          1.0722 |  0.2313 |    -1      |               4.763  |                       24 |    1.00618e+06 |       0.006184 |      -0.036652 |               5.25 |

## Output files
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
