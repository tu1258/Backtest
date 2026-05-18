# RS90 Daily Backtester

A standalone Python repo for testing a mechanical RS90 system:

1. Download daily OHLCV from yfinance.
2. Compute point-in-time daily RS rank from historical prices.
3. Export the recent RS90 universe.
4. Backtest two daily strategies:
   - `breakout`: RS90 + buy stop above latest confirmed daily pivot high 1,1.
   - `rsi2`: RS90 + prior-day RSI(2) < 5 + prior-day close > 50MA, then buy next open.
5. Export trade log, equity curve, and performance report.

## Current assumptions

These are intentional MVP assumptions.

- Long-only.
- Position size is fixed notional: `equity * position_pct`. Default is `1%`.
- Initial stop is the previous day's low / setup day's low.
- If entry and stop both happen on the same daily bar, assume the trade enters and then gets stopped.
- If multiple exits are touched on the same daily bar, initial stop has priority.
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

Run backtest only after data already exists:

```bash
python scripts/run_backtest.py \
  --price-csv data/stock_data.csv \
  --output-dir outputs/backtest \
  --position-pct 0.01 \
  --rs-threshold 90 \
  --recent-days 7 \
  --exit-mode either
```

## GitHub Actions usage

1. Create a new GitHub repo.
2. Upload all files from this repo.
3. Go to **Actions → RS90 Backtest → Run workflow**.
4. Choose:
   - `years`: `1`, `2`, `5`, `10`, `20`
   - `max_tickers`: leave empty for all tickers, or use a number for quick tests
   - `exit_mode`: `ma10`, `pivot_low`, or `either`
   - `position_pct`: default `0.01`
5. Download the artifact named `rs90-backtest-outputs`.

## Outputs

The workflow writes:

```text
outputs/backtest/rs90_daily_recent.csv
outputs/backtest/trades.csv
outputs/backtest/equity_curve.csv
outputs/backtest/equity_curve.png
outputs/backtest/performance_report.json
data/stock_data.csv
```

### `trades.csv`

Main columns:

```text
strategy, ticker, entry_date, entry_price, initial_stop, risk_per_share,
exit_date, exit_price, exit_reason, shares, position_size, pnl, pnl_pct,
r_multiple, mae, mfe, holding_days, rs_rank_at_entry, signal_details
```

### `performance_report.json`

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
- strategy-level breakdown

## Strategy definitions

### Daily RS90 universe

For each date, the system calculates RS score using only prices available up to that date.
The formula follows the same spirit as the existing RS ranking script: average geometric monthly returns over 1 to 12 months, using 21 trading days per month.

### Breakout

Entry condition:

```text
RS rank >= 90
current high >= latest confirmed pivot high 1,1
```

Execution:

```text
entry = max(current open, pivot high)
initial_stop = previous day low
```

### RSI2

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

### Exit modes

`ma10`:

```text
exit if low <= 10MA
exit_price = 10MA
```

`pivot_low`:

```text
exit if low <= latest confirmed pivot low 1,1
exit_price = pivot low
```

`either`:

```text
use both 10MA and pivot-low stop orders; whichever level is touched is used.
initial stop always has priority.
```

## Notes before trusting results

- yfinance data is adjusted when `auto_adjust: true` is used.
- The ticker list is survivorship-biased because it uses current listed stocks.
- Delisted stocks are not included.
- Daily OHLCV cannot perfectly model stop-order sequence. The current assumption is conservative for same-day entry/stop cases.
- For the final RSI2 intraday version, add 5-minute data and intraday order sequencing.
