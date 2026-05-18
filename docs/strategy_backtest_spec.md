# RS90 Breakout / Exhaustion Strategy Backtest Spec

## 0. Purpose

This document is for continuing the strategy/backtesting discussion in another ChatGPT session.

The goal is to build a Python-based backtesting system, likely hosted and run from GitHub, to test a mechanical trading strategy on a dynamic RS90 stock universe.

The user can already generate a daily RS90 list. The main task is to help implement the backtesting engine in Python.

---

## 1. High-Level Objective

The user wants to replace part of the discretionary VCP/manual setup selection process with a more mechanical indicator-based system.

The desired system:

```text
Daily RS90 universe
+ Breakout strategy
+ Exhaustion / mean-reversion strategy
+ Strict stop loss
+ Portfolio-level tracking
+ Python backtesting framework
```

The user wants to reduce subjective judgment and emotional instability in trading decisions.

The system should help answer:

- Does the strategy have positive expectancy?
- What is the max drawdown?
- How many consecutive losses can happen?
- Are losses controlled within approximately 5% per trade?
- Does the breakout strategy generate large enough winners?
- Does the RSI2 exhaustion strategy avoid major losses?
- Can this become a low-subjectivity daily execution system?

---

## 2. User's Broader Investment Context

The user has a long-term asset recovery / catch-up plan.

Current rough context:

- Current assets: around 850k TWD or equivalent unit used by the user.
- Benchmark target: a leveraged index-like comparison portfolio.
- Ultimate goal: catch up to the benchmark, then retire from active trading and move to broad index investing.
- Desired max drawdown for the active strategy: ideally within 20% at portfolio level.
- Desired trade-level loss: around 5% maximum per trade.
- User prefers strategies where downside is mechanically controlled.

Important decision framework for future consultation:

```text
Market condition → determines whether there is edge.
Account stage → determines maximum exposure / position size.
Psychological state → applies a risk discount.
```

However, for this system, the user wants to minimize subjective market-state decisions and instead rely on systematic signals and strategy performance metrics.

---

## 3. Existing User Workflow

The user already does the following:

1. Calculates RS / relative strength for all stocks.
2. Uses technical indicators to create a strong-stock universe.
3. Crawls news data and uses AI to summarize strong themes.
4. Manually reviews setups, especially VCP-like setups.

Problem:

- The user feels manual setup selection is still subjective.
- The success rate is not high enough.
- Emotional instability affects discretionary decisions.
- The user wants a more mechanical system.

The user already has their own VCP strategy, but this document is for a separate mechanical breakout/exhaustion system.

---

## 4. Strategy Scope

Only two strategy families should be tested initially.

### Strategy A: Breakout

Core idea:

```text
Trade RS90 stocks that break above a confirmed daily pivot high.
```

### Strategy B: Exhaustion / Mean Reversion

Core idea:

```text
Trade RS90 stocks that show short-term exhaustion using RSI(2), then enter when intraday reversal occurs.
```

The user does not want many indicators or many variants at first. Too many signals make the system unstable and hard to trust.

---

## 5. Data Assumptions

The user expects to provide or generate the following data.

### Daily OHLCV data

Required columns:

```text
date
ticker
open
high
low
close
volume
```

Optional columns:

```text
adjusted_close
split_factor
dividend
```

Adjusted data is preferred if available.

### Daily RS90 list

The user can generate each day's RS90 universe.

Expected format:

```text
date
ticker
rs_rank
in_rs90
```

At minimum:

```text
date
ticker
```

where each row means the ticker belongs to that day's RS90 universe.

Important:

The RS90 list must be point-in-time. That means the RS90 membership for date `t` must be calculated only using information known at or before date `t`.

### 5-minute intraday OHLCV data

Needed for the final RSI2 exhaustion execution model.

Required columns:

```text
datetime
date
ticker
open
high
low
close
volume
```

If 5-minute data is difficult to get, start with a daily-only MVP first.

---

## 6. Important Backtesting Bias Controls

The system must avoid:

### Look-ahead bias

Examples to avoid:

- Using future RS rank to define past universe.
- Using unconfirmed pivot high as if it were known earlier.
- Using same-day close signals and assuming same-day close execution unless explicitly modeled.

### Survivorship bias

If possible, include delisted stocks. If not possible for MVP, clearly label the backtest as survivorship-biased.

### Repaint / confirmation issue for pivot 1,1

A daily pivot high 1,1 means:

```text
high[t] > high[t-1]
high[t] > high[t+1]
```

Therefore, pivot high at day `t` is only confirmed after day `t+1` completes.

However, the user’s breakout strategy uses previously confirmed pivots only. Therefore, there should be no repaint problem if implemented correctly.

Correct usage:

```text
Day t: candidate pivot high forms.
Day t+1: pivot high is confirmed after this day closes.
Day t+2 onward: pivot high can be used as breakout trigger.
```

---

## 7. Strategy A: Daily Pivot 1,1 Breakout

### Universe

```text
Ticker must be in RS90 universe on the signal date.
```

Optional initial filters:

```text
average volume > minimum liquidity threshold
price > minimum price threshold
```

Avoid adding too many filters in the first version.

### Pivot high definition

Confirmed pivot high 1,1:

```text
high[t] > high[t-1]
high[t] > high[t+1]
```

A pivot high becomes available only after `t+1` is complete.

### Entry

```text
Buy stop at the most recent confirmed daily pivot high.
```

The entry is triggered if:

```text
high[current_day] >= pivot_high_price
```

Entry price assumption for MVP:

```text
entry_price = pivot_high_price
```

A later version can include slippage:

```text
entry_price = pivot_high_price * (1 + slippage_bps / 10000)
```

### Initial stop

The user currently prefers:

```text
stop = current day low
```

But this creates a same-day ambiguity because the final current-day low is only known after the day ends.

Possible interpretations to test:

#### Version 1: Conservative daily approximation

```text
stop = low of entry day
```

This is easier to model but may be optimistic if the low happened after entry or pessimistic if the low happened before entry. Intraday data is needed to know the exact sequence.

#### Version 2: Intraday-correct version

Use intraday data to determine:

- when the breakout trigger occurred;
- what the low of the day was before and after entry;
- whether stop was hit after entry.

#### Version 3: Practical hard stop

```text
stop = min(entry_day_low, entry_price * 0.95)
```

or better for strict risk control:

```text
Only take trade if (entry_price - planned_stop) / entry_price <= 5%.
```

### Risk filter

The user wants max loss around 5% per trade.

Therefore:

```text
If distance from entry to stop > 5%, skip the trade.
```

### Exit

Initial MVP can test simple versions:

#### Exit B1

```text
Exit when price breaks previous day low.
```

#### Exit B2

```text
Exit when price breaks 2-day low.
```

#### Exit B3

```text
Initial stop at entry-day low or hard -5%.
After profit >= 2R, trail using 2-day low.
```

Important: The initial stop and trailing exit should be clearly separated.

### Key metrics for breakout

- Win rate
- Average R
- Median R
- Largest winner in R
- Number of 3R, 5R, 10R winners
- Profit factor
- Max drawdown
- Largest losing streak
- Average holding period

Breakout strategies may have low win rate. That is acceptable only if large winners exist.

---

## 8. Strategy B: RSI2 Exhaustion + 5-Minute Pivot Reversal

This is the user's currently preferred exhaustion strategy.

### Universe

```text
Ticker must be in RS90 universe.
```

### Setup

Using daily RSI(2):

```text
RSI(2) < 5
```

The user is interested in RSI2 appearing intraday, not only after daily close.

Meaning:

On the current trading day, the still-forming daily candle is included in the RSI2 calculation. If intraday price action causes daily RSI2 to drop below 5, the setup becomes active.

TradingView behavior note:

On a daily chart, TradingView indicators generally include the current live daily bar during the trading session. Therefore, RSI2 can appear intraday and later disappear before close.

This strategy intentionally treats intraday RSI2 < 5 as a valid exhaustion event.

### Entry trigger

After intraday daily RSI2 < 5 appears:

```text
Switch to 5-minute chart.
Buy stop when price breaks above a confirmed 5-minute pivot high 1,1.
```

5-minute pivot high 1,1:

```text
high_5m[t] > high_5m[t-1]
high_5m[t] > high_5m[t+1]
```

Again, this pivot is only confirmed after the next 5-minute bar completes.

Entry:

```text
buy stop = confirmed 5-minute pivot high
```

### Stop

```text
stop = current day's low
```

Risk filter:

```text
If distance from entry to current day low > 5%, skip trade.
```

Since the day is still forming, the current day low can update. The implementation must define whether the stop uses:

1. the day low at time of entry;
2. the final day low;
3. the lowest low since RSI2 setup appeared;
4. the lowest low since market open.

The user currently says “停損當日低點” / stop at current day low. The most realistic intraday interpretation is likely:

```text
stop = lowest intraday low of that day observed up to the time of entry
```

If price later makes a new low after entry, that means the stop is hit.

### Exit

Possible simple exits to test:

#### Exit E1

```text
Exit when daily RSI(2) > 70.
```

#### Exit E2

```text
Exit when close > 5-day moving average.
```

#### Exit E3

```text
Exit after fixed holding period: 3 to 5 trading days.
```

For MVP, pick one simple exit first. Suggested initial version:

```text
Exit after 3 trading days or when RSI(2) > 70, whichever comes first.
```

But the user may prefer to keep variables minimal.

### Key metrics for RSI2 strategy

- Win rate
- Average R
- Average win / average loss
- Maximum adverse excursion (MAE)
- Maximum favorable excursion (MFE)
- Average holding period
- Profit factor
- Tail losses
- Whether 5-minute trigger improves entry versus next-open entry

---

## 9. Daily-Only MVP Before Intraday Version

Because intraday backtesting is harder, first build a daily-only MVP.

### Daily Breakout MVP

```text
Universe: RS90
Entry: high breaks previous confirmed daily pivot high 1,1
Entry price: pivot high
Stop: entry_day_low or hard -5%
Risk filter: skip if stop distance > 5%
Exit: previous day low, 2-day low, or fixed trailing rule
```

### Daily RSI2 MVP

```text
Universe: RS90
Setup: daily close RSI(2) < 5
Entry: next day open
Stop: setup day low or hard -5%
Exit: RSI(2) > 70 or fixed 3-5 trading days
```

Purpose:

- Check whether the strategy family has basic edge.
- Build infrastructure.
- Generate trade logs and performance reports.

Then add intraday execution later.

---

## 10. Portfolio-Level Rules

The system should eventually handle multiple signals on the same day.

Questions to implement:

- Max number of new positions per day.
- Max number of open positions.
- Max allocation per trade.
- Max portfolio exposure.
- Whether breakout and exhaustion can both hold the same ticker.
- If the same ticker triggers both systems on the same day, only one trade should be allowed.

Initial simple assumptions:

```text
Initial capital = user-defined
Position size = fixed percentage of equity, e.g. 1% to 5% notional per trade
Risk per trade = based on stop distance, capped by position sizing
Max open positions = user-defined
Same ticker cannot have duplicate open trades
```

For early testing, the user mentioned using 1% capital in live testing. For backtesting, use flexible parameters.

---

## 11. Suggested Python Project Structure

```text
rs90-backtester/
│
├── README.md
├── requirements.txt
├── config.yaml
│
├── data/
│   ├── daily/
│   │   └── daily_ohlcv.parquet
│   ├── intraday_5m/
│   │   └── five_min_ohlcv.parquet
│   └── universe/
│       └── rs90_membership.parquet
│
├── notebooks/
│   ├── 01_data_check.ipynb
│   ├── 02_daily_mvp_backtest.ipynb
│   └── 03_intraday_rsi2_test.ipynb
│
├── src/
│   ├── __init__.py
│   ├── data_loader.py
│   ├── indicators.py
│   ├── universe.py
│   ├── signals.py
│   ├── execution.py
│   ├── portfolio.py
│   ├── metrics.py
│   └── backtest.py
│
├── tests/
│   ├── test_indicators.py
│   ├── test_pivots.py
│   └── test_backtest_no_lookahead.py
│
└── outputs/
    ├── trades.csv
    ├── equity_curve.csv
    └── performance_report.html
```

---

## 12. Core Python Modules

### `data_loader.py`

Responsibilities:

- Load daily OHLCV data.
- Load RS90 universe data.
- Load 5-minute data later.
- Validate required columns.
- Ensure date/datetime sorting.

### `indicators.py`

Implement:

- RSI(2)
- Pivot high / pivot low 1,1
- Moving averages
- ATR
- 2-day low / previous day low

### `universe.py`

Responsibilities:

- Merge OHLCV with daily RS90 membership.
- Ensure only point-in-time RS90 rows are used.

### `signals.py`

Implement:

- Daily pivot breakout signals.
- Daily RSI2 exhaustion signals.
- Later: intraday RSI2 + 5-minute pivot trigger.

### `execution.py`

Responsibilities:

- Convert signals into trades.
- Model stop orders.
- Model stop loss.
- Model same-day high/low ambiguity carefully.
- Add optional slippage and commission.

### `portfolio.py`

Responsibilities:

- Position sizing.
- Equity curve.
- Open positions.
- Max positions.
- Exposure limits.

### `metrics.py`

Implement:

- CAGR
- Total return
- Max drawdown
- Profit factor
- Win rate
- Average R
- Median R
- Avg win / avg loss
- Largest losing streak
- Exposure time
- Trade count

### `backtest.py`

Main orchestration.

---

## 13. Trade Log Format

Each completed trade should output:

```text
strategy
entry_date
entry_datetime optional
ticker
entry_price
initial_stop
risk_per_share
exit_date
exit_datetime optional
exit_price
exit_reason
shares
position_size
pnl
pnl_pct
r_multiple
mae
mfe
holding_days
rs_rank_at_entry
signal_details
```

R-multiple is critical.

```text
R = entry_price - initial_stop for long trades
r_multiple = (exit_price - entry_price) / R
```

---

## 14. Implementation Priorities

### Priority 1: Daily MVP

Build daily-only backtester first.

Must support:

- Dynamic RS90 universe by date.
- Daily pivot 1,1 breakout.
- Daily RSI2 close-based exhaustion.
- Fixed stop / stop distance filter.
- Trade log.
- Equity curve.
- Basic metrics.

### Priority 2: Improve breakout execution

Test variants:

- Stop at entry-day low.
- Stop at previous day low.
- Stop at -5% hard stop.
- Skip if stop distance > 5%.
- Exit by previous day low.
- Exit by 2-day low.

### Priority 3: Intraday RSI2 + 5-minute pivot

Add 5-minute data.

Implement:

- Intraday daily RSI2 calculation using current forming daily candle.
- Once RSI2 < 5 appears, activate 5-minute pivot detection.
- Buy stop above confirmed 5-minute pivot high.
- Stop at observed day low at entry.
- Skip if stop distance > 5%.

### Priority 4: Portfolio realism

Add:

- Multiple simultaneous signals.
- Max open positions.
- Max daily entries.
- Allocation per trade.
- Slippage.
- Commission.
- Liquidity constraints.

---

## 15. Open Design Questions for Next Session

The next session should help decide and implement:

1. What data format will be used? CSV or Parquet?
2. How will RS90 daily list be provided?
3. Should daily MVP assume adjusted OHLCV?
4. For breakout, should stop be entry-day low, previous-day low, or hard -5%?
5. For RSI2 daily MVP, should entry be next open or next day stop above previous high?
6. For RSI2 intraday version, should stop be observed day low at entry?
7. What is the first exit rule to test?
8. How many positions can be open at once?
9. Should position sizing be fixed notional or fixed risk per trade?
10. How should same-day high/low ambiguity be handled in daily-only backtest?

---

## 16. Preferred Initial Defaults

Use these if the user wants to move fast.

### Data

```text
Daily OHLCV: Parquet or CSV
RS90 membership: date + ticker + optional rs_rank
```

### Daily Breakout MVP

```text
Universe: RS90
Entry: high >= most recent confirmed daily pivot high 1,1
Entry price: pivot high
Initial stop: entry price * 0.95
Risk filter: if entry to entry-day low > 5%, still use hard -5% for MVP, but record entry-day low distance
Exit: 2-day low trailing after entry
```

### Daily RSI2 MVP

```text
Universe: RS90
Setup: RSI(2) < 5 on daily close
Entry: next day open
Stop: entry * 0.95
Exit: RSI(2) > 70 or after 5 trading days
```

### Position sizing

```text
Fixed notional percentage per trade first, e.g. 1% or 5% of equity.
Later: risk-based sizing.
```

### Costs

```text
Start with zero cost.
Then add slippage + commission sensitivity test.
```

---

## 17. Philosophy of the System

The goal is not to find a magical indicator.

The goal is to create a system where:

```text
RS90 universe provides strength filter.
Breakout captures momentum continuation.
RSI2 exhaustion captures short-term reversal in strong stocks.
Stops keep losses small.
Backtest reveals whether expectancy exists.
Live execution follows the system instead of emotions.
```

The user wants a system that is simple enough to execute daily:

```text
Generate RS90 list.
Run strategy script.
Get buy/sell orders.
Place orders.
Record trades.
Review metrics.
```

The system should reduce subjective decision-making and help the user avoid emotional trading.

---

## 18. Immediate Request for Next ChatGPT Session

The user likely wants ChatGPT to help implement this in Python.

Suggested opening prompt for next session:

```text
I want to build a Python backtesting system from this spec. Start with the daily MVP only. Please help me design the repo structure and implement the first version that can load daily OHLCV data and daily RS90 membership, calculate RSI(2), calculate confirmed pivot high/low 1,1 without look-ahead bias, generate breakout and RSI2 signals, simulate trades, and output trades.csv plus equity_curve.csv.
```

