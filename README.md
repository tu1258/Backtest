# RS90 Daily Backtester

A standalone Python repo for testing a mechanical RS90 system.

The default GitHub Actions flow now runs the full **2 x 2 strategy matrix**:

| Entry strategy | Exit strategy | Output folder |
|---|---|---|
| `breakout` | `ma10` | `outputs/backtest/breakout_ma10/` |
| `breakout` | `pivot_low` | `outputs/backtest/breakout_pivot_low/` |
| `rsi2` | `ma10` | `outputs/backtest/rsi2_ma10/` |
| `rsi2` | `pivot_low` | `outputs/backtest/rsi2_pivot_low/` |

There is no `either` exit mode in the default workflow. Each exit rule is tested separately so the reports are directly comparable.

## Workflow

1. Download daily OHLCV from yfinance.
2. Compute point-in-time daily RS rank from historical prices.
3. Export the recent RS90 universe.
4. Run four independent backtests:
   - Pivot breakout + MA10 exit
   - Pivot breakout + pivot-low exit
   - RSI2 pullback + MA10 exit
   - RSI2 pullback + pivot-low exit
5. Export trade logs, equity curves, and performance reports for each strategy combination.

## Current assumptions

- Long-only.
- Position size is fixed notional: `equity * position_pct`. Default is `1%`.
- Initial stop is the previous day's low / setup day's low.
- If entry and stop both happen on the same daily bar, assume the trade enters and then gets stopped.
- If initial stop and strategy exit are both touched on the same daily bar, initial stop has priority.
- Pivot high/low 1,1 is only tradable after confirmation. A pivot at day `t` becomes usable from day `t+2`.
- Daily data cannot know exact intraday sequence. Use 5-minute data later for a stricter execution model.

## Repo structure

```text
.
├── .github/workflows/backtest.yml
├── configs/config.yaml
├── data/stock_ticker.csv
├── outputs/
├── scripts/
│   ├── build_data.py
│   ├── run_backtest.py
│   └── run_all.py
├── src/rs90_backtester/
│   ├── config.py
│   ├── data.py
│   ├── engine.py
│   ├── indicators.py
│   └── universe.py
├── tests/
├── requirements.txt
└── pyproject.toml
```

## Local quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
pip install -e .
```

Quick smoke test with only 100 tickers and 2 years of data:

```bash
python scripts/run_all.py --years 2 --max-tickers 100
```

Full run using the bundled ticker list:

```bash
python scripts/run_all.py --years 2
```

Run the 2 x 2 backtest matrix only after data already exists:

```bash
python scripts/run_backtest.py \
  --price-csv data/stock_data.csv \
  --output-dir outputs/backtest \
  --position-pct 0.01 \
  --rs-threshold 90 \
  --recent-days 7 \
  --matrix
```

Run a single strategy combination manually:

```bash
python scripts/run_backtest.py \
  --price-csv data/stock_data.csv \
  --output-dir outputs/backtest/single_test \
  --strategies breakout \
  --exit-mode ma10
```

## GitHub Actions usage

1. Create a new GitHub repo.
2. Upload all files from this repo.
3. Go to **Actions → RS90 Backtest → Run workflow**.
4. Choose:
   - `years`: `1`, `2`, `5`, `10`, `20`
   - `max_tickers`: leave empty for all tickers, or use a number for quick tests
   - `position_pct`: default `0.01`
5. Download the artifact named `rs90-backtest-outputs`, or inspect committed files under `outputs/backtest/` and `logs/` if `commit_outputs=true`.


## Important GitHub Actions notes

- `max_tickers` empty means full ticker list. If the log says `max_tickers=500`, then the run was intentionally limited to 500 tickers.
- A line like `Downloading 500 tickers ... in 7 batches` means **7 download batches**, not 7 stocks.
- `commit_outputs=true` commits `outputs/backtest/` and `logs/` back to the repo.
- `commit_stock_data=false` by default because full-universe `data/stock_data.csv` can exceed GitHub's 100MB single-file limit. It is still uploaded as an artifact.

## Outputs

The workflow writes and, by default, commits reports/logs back to the repo:

```text
outputs/backtest/rs90_daily_recent.csv
outputs/backtest/strategy_summary.csv
outputs/backtest/all_reports.json
outputs/backtest/REPORT.md
outputs/backtest/data_summary.json
logs/01_install.log
logs/02_build_data.log
logs/03_data_summary.log
logs/04_run_backtest.log
logs/05_output_summary.log
logs/workflow_inputs.json
outputs/backtest/breakout_ma10/trades.csv
outputs/backtest/breakout_ma10/equity_curve.csv
outputs/backtest/breakout_ma10/equity_curve.png
outputs/backtest/breakout_ma10/performance_report.json
outputs/backtest/breakout_pivot_low/...
outputs/backtest/rsi2_ma10/...
outputs/backtest/rsi2_pivot_low/...
data/stock_data.csv
```

### `rs90_daily_recent.csv`

Recent daily RS90 universe. By default this exports the most recent 5 trading days. Each date should contain all tickers whose point-in-time RS rank is >= 90.

### `strategy_summary.csv`

One-row-per-strategy summary for the four strategy combinations:

```text
strategy_combo, entry_strategy, exit_mode, trade_count, win_rate,
profit_factor, avg_r, median_r, avg_win_loss_ratio,
max_consecutive_losses, final_equity, total_return, max_drawdown,
avg_holding_days
```

### Per-strategy `trades.csv`

Main columns:

```text
strategy, ticker, entry_date, entry_price, initial_stop, risk_per_share,
exit_date, exit_price, exit_reason, shares, position_size, pnl, pnl_pct,
r_multiple, mae, mfe, holding_days, rs_rank_at_entry, signal_details
```

### Per-strategy `performance_report.json`

Includes:

- trade count
- win rate
- gross profit / gross loss
- profit factor
- average R / median R
- average win / average loss
- win-loss ratio
- largest winner / loser in R
- max consecutive losses
- final equity
- total return
- max drawdown

## Strategy definitions

### Daily RS90 universe

For each date, the system calculates RS score using only prices available up to that date.
The formula follows the same spirit as the existing RS ranking script: average geometric monthly returns over 1 to 12 months, using 21 trading days per month.

### Breakout entry

```text
RS rank >= 90
current high >= latest confirmed pivot high 1,1
entry = max(current open, pivot high)
initial_stop = previous day low
```

### RSI2 entry

Setup condition on previous day:

```text
RS rank >= 90
RSI(2) < 5
close > 50MA
```

Execution:

```text
entry = current open
initial_stop = setup day low
```

### MA10 exit

```text
exit if low <= 10MA
exit_price = 10MA
```

### Pivot-low exit

```text
exit if low <= latest confirmed pivot low 1,1
exit_price = pivot low
```

## Notes before trusting results

- yfinance data is adjusted when `auto_adjust: true` is used.
- The ticker list is survivorship-biased because it uses current listed stocks.
- Delisted stocks are not included.
- Daily OHLCV cannot perfectly model stop-order sequence. The current assumption is conservative for same-day entry/stop cases.
- For the final RSI2 intraday version, add 5-minute data and intraday order sequencing.
