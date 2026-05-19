from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json

import numpy as np
import pandas as pd


@dataclass
class BacktestConfig:
    initial_capital: float = 1_000_000
    position_pct: float = 0.01
    rs_threshold: float = 90
    recent_days: int = 7
    exit_mode: str = "ma10"  # ma10, atr_trail, n_day_low, prev_day_low
    max_open_positions: int = 100
    max_new_positions_per_day: int = 100
    allow_same_ticker_overlap: bool = False
    slippage_bps: float = 0
    commission_per_trade: float = 0
    max_stop_pct: float | None = None
    start_date: str | None = None
    end_date: str | None = None
    strategies: tuple[str, ...] = ("breakout", "rsi2")
    entry_name: str | None = None
    pivot_left: int = 1
    pivot_right: int = 1
    atr_period: int = 14
    atr_multiple: float = 1.0
    n_day_low_period: int = 5
    same_day_stop_rule: str = "red_candle_only"

    # Shared RS90 universe filters.
    min_avg_value_10: float = 25.0
    min_adr20: float = 2.5
    max_adr20: float = 25.0
    require_close_above_ma50: bool = True

    # Breakout-only filters.
    breakout_require_dr_lt_adr5: bool = True
    breakout_require_near_ma5_within_adr10: bool = True
    breakout_require_prev_close_lte_pivot: bool = True


@dataclass
class Position:
    strategy: str
    ticker: str
    entry_date: pd.Timestamp
    entry_price: float
    initial_stop: float
    shares: int
    position_size: float
    risk_per_share: float
    rs_rank_at_entry: float | None
    signal_details: str
    max_high: float
    min_low: float
    trailing_stop: float | None = None


@dataclass
class Trade:
    strategy: str
    ticker: str
    entry_date: str
    entry_price: float
    initial_stop: float
    risk_per_share: float
    exit_date: str
    exit_price: float
    exit_reason: str
    shares: int
    position_size: float
    pnl: float
    pnl_pct: float
    r_multiple: float
    mae: float
    mfe: float
    holding_days: int
    rs_rank_at_entry: float | None
    signal_details: str


def run_backtest(df: pd.DataFrame, cfg: BacktestConfig) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    work = df.copy().sort_values(["date", "ticker"]).reset_index(drop=True)
    if cfg.start_date:
        work = work[work["date"] >= pd.to_datetime(cfg.start_date)]
    if cfg.end_date:
        work = work[work["date"] <= pd.to_datetime(cfg.end_date)]

    dates = sorted(work["date"].unique())
    by_date = {d: g.set_index("ticker", drop=False) for d, g in work.groupby("date")}

    cash_realized = float(cfg.initial_capital)
    positions: list[Position] = []
    trades: list[Trade] = []
    equity_rows: list[dict] = []

    for d in dates:
        day = by_date[d]

        # Existing positions: check exits using stop-order semantics.
        exits_today: list[Position] = []
        for pos in list(positions):
            if pos.ticker not in day.index:
                continue
            row = day.loc[pos.ticker]
            high = float(row["high"])
            low = float(row["low"])

            # Exit uses stop levels known before this session. ATR trail is updated after close.
            exit_price, exit_reason = _exit_for_position(pos, row, cfg)

            pos.max_high = max(pos.max_high, high)
            pos.min_low = min(pos.min_low, low)

            if exit_price is not None:
                trade = _close_trade(pos, d, float(exit_price), exit_reason, cfg)
                trades.append(trade)
                cash_realized += trade.pnl - cfg.commission_per_trade
                exits_today.append(pos)
            else:
                _update_atr_trailing_stop_after_close(pos, row, cfg)

        if exits_today:
            positions = [p for p in positions if p not in exits_today]

        # New entries. User assumption: if same-day entry and stop both trigger, trade is entered then stopped.
        new_entries = 0
        held_tickers = {p.ticker for p in positions}
        candidates = _generate_entries(day, cfg)
        for cand in candidates:
            if new_entries >= cfg.max_new_positions_per_day:
                break
            if len(positions) >= cfg.max_open_positions:
                break
            if (not cfg.allow_same_ticker_overlap) and cand["ticker"] in held_tickers:
                continue
            if cand["initial_stop"] >= cand["entry_price"]:
                continue

            stop_pct = (cand["entry_price"] - cand["initial_stop"]) / cand["entry_price"]
            if cfg.max_stop_pct is not None and stop_pct > cfg.max_stop_pct:
                continue

            notional = _mark_to_market_equity(cash_realized, positions, day) * cfg.position_pct
            shares = int(notional // cand["entry_price"])
            if shares <= 0:
                continue

            row = day.loc[cand["ticker"]]
            pos = Position(
                strategy=cand["strategy"],
                ticker=cand["ticker"],
                entry_date=d,
                entry_price=float(cand["entry_price"]),
                initial_stop=float(cand["initial_stop"]),
                shares=shares,
                position_size=shares * float(cand["entry_price"]),
                risk_per_share=float(cand["entry_price"] - cand["initial_stop"]),
                rs_rank_at_entry=cand.get("rs_rank_at_entry"),
                signal_details=cand.get("signal_details", ""),
                max_high=float(row["high"]),
                min_low=float(row["low"]),
                trailing_stop=_initial_trailing_stop(cand["entry_price"], cand["initial_stop"], row, cfg),
            )

            # Same-day ambiguity rule for daily bars:
            # if entry and stop are both touched on the entry day, only treat it as stopped
            # on a red candle (close < open). A green/doji candle is assumed to have moved up
            # after entry, so the stop is not counted as hit on the same day.
            if _same_day_initial_stop_hit(pos, row, cfg):
                exit_px = _sell_stop_fill_price(row, pos.initial_stop, cfg)
                trade = _close_trade(pos, d, exit_px, "same_day_stop_loss_red_candle", cfg)
                trades.append(trade)
                cash_realized += trade.pnl - cfg.commission_per_trade
            else:
                _update_atr_trailing_stop_after_close(pos, row, cfg)
                positions.append(pos)
                held_tickers.add(pos.ticker)

            new_entries += 1

        equity = _mark_to_market_equity(cash_realized, positions, day)
        equity_rows.append({
            "date": pd.Timestamp(d).strftime("%Y-%m-%d"),
            "equity": equity,
            "cash_realized": cash_realized,
            "open_positions": len(positions),
            "exposure": sum(p.position_size for p in positions),
            "exposure_pct": (sum(p.position_size for p in positions) / equity) if equity else 0.0,
        })

    if dates:
        last_d = dates[-1]
        last_day = by_date[last_d]
        for pos in positions:
            if pos.ticker in last_day.index:
                px = float(last_day.loc[pos.ticker, "close"])
                trades.append(_close_trade(pos, last_d, px, "end_of_backtest", cfg))

    trades_df = pd.DataFrame([asdict(t) for t in trades])
    equity_df = pd.DataFrame(equity_rows)
    report = performance_report(trades_df, equity_df, cfg)
    return trades_df, equity_df, report


def _generate_entries(day: pd.DataFrame, cfg: BacktestConfig) -> list[dict]:
    out: list[dict] = []
    day = day.sort_values(["rs_rank", "rs_score"], ascending=[False, False])

    for _, row in day.iterrows():
        ticker = str(row["ticker"])

        # Exact date+ticker RS90 membership check. If this pair is not in the allowed RS90 table, no entry.
        if not bool(row.get("in_rs90", False)) or float(row.get("rs_rank", -1)) < cfg.rs_threshold:
            continue
        if not _passes_common_universe_filters(row, cfg):
            continue

        if "breakout" in cfg.strategies and _passes_breakout_filters(row, cfg):
            pivot = row.get("confirmed_pivot_high")
            prev_low = row.get("prev_low")
            prev_close = row.get("prev_close")
            if pd.notna(pivot) and pd.notna(prev_low) and float(row["high"]) >= float(pivot):
                if cfg.breakout_require_prev_close_lte_pivot:
                    if pd.isna(prev_close) or float(prev_close) > float(pivot):
                        continue
                raw_entry = max(float(row["open"]), float(pivot))
                entry = raw_entry * (1 + cfg.slippage_bps / 10000)
                label = cfg.entry_name or f"breakout_{cfg.pivot_left}_{cfg.pivot_right}"
                out.append({
                    "strategy": label,
                    "ticker": ticker,
                    "entry_price": entry,
                    "initial_stop": float(prev_low),
                    "rs_rank_at_entry": float(row["rs_rank"]),
                    "signal_details": (
                        f"buy_stop=pivot_high_{cfg.pivot_left}_{cfg.pivot_right}:{float(pivot):.4f}; entry=max(open,pivot); "
                        f"prev_close={_fmt(prev_close)}; require_prev_close_lte_pivot={cfg.breakout_require_prev_close_lte_pivot}; "
                        f"avg_value_10={_fmt(row.get('avg_value_10'))}M; adr20={_fmt(row.get('adr20'))}; "
                        f"dr={_fmt(row.get('dr'))}; adr5={_fmt(row.get('adr5'))}; "
                        f"distance_to_ma5={_fmt(row.get('distance_to_ma5'))}; adr10_price={_fmt(row.get('adr10_price'))}"
                    ),
                })

        if "rsi2" in cfg.strategies:
            setup_rsi2 = row.get("setup_rsi2")
            setup_low = row.get("setup_low")
            if pd.notna(setup_rsi2) and pd.notna(setup_low) and float(setup_rsi2) < 5:
                entry = float(row["open"]) * (1 + cfg.slippage_bps / 10000)
                out.append({
                    "strategy": cfg.entry_name or "rsi2",
                    "ticker": ticker,
                    "entry_price": entry,
                    "initial_stop": float(setup_low),
                    "rs_rank_at_entry": float(row["rs_rank"]),
                    "signal_details": (
                        f"setup_rsi2={float(setup_rsi2):.2f}; next_open_entry; "
                        f"avg_value_10={_fmt(row.get('avg_value_10'))}M; adr20={_fmt(row.get('adr20'))}; close_gt_ma50=True"
                    ),
                })
    return out


def _passes_common_universe_filters(row: pd.Series, cfg: BacktestConfig) -> bool:
    checks = [
        pd.notna(row.get("avg_value_10")) and float(row.get("avg_value_10")) > cfg.min_avg_value_10,
        pd.notna(row.get("adr20")) and cfg.min_adr20 <= float(row.get("adr20")) <= cfg.max_adr20,
    ]
    if cfg.require_close_above_ma50:
        checks.append(pd.notna(row.get("ma50")) and float(row.get("close")) > float(row.get("ma50")))
    return all(checks)


def _passes_breakout_filters(row: pd.Series, cfg: BacktestConfig) -> bool:
    if cfg.breakout_require_dr_lt_adr5:
        if pd.isna(row.get("dr")) or pd.isna(row.get("adr5")) or not (float(row.get("dr")) < float(row.get("adr5"))):
            return False
    if cfg.breakout_require_near_ma5_within_adr10:
        if pd.isna(row.get("distance_to_ma5")) or pd.isna(row.get("adr10_price")):
            return False
        if not (float(row.get("distance_to_ma5")) < float(row.get("adr10_price"))):
            return False
    return True


def _same_day_initial_stop_hit(pos: Position, row: pd.Series, cfg: BacktestConfig) -> bool:
    if float(row["low"]) > pos.initial_stop:
        return False
    if cfg.same_day_stop_rule == "always":
        return True
    if cfg.same_day_stop_rule == "never":
        return False
    if cfg.same_day_stop_rule == "red_candle_only":
        return float(row["close"]) < float(row["open"])
    raise ValueError(f"unsupported same_day_stop_rule: {cfg.same_day_stop_rule}")


def _initial_trailing_stop(entry_price: float, initial_stop: float, row: pd.Series, cfg: BacktestConfig) -> float | None:
    if cfg.exit_mode != "atr_trail":
        return None
    # ATR trail starts from the original strategy stop. It is only raised after
    # a later close updates max_high_since_entry - ATR * multiple. This keeps
    # the entry stop definition unchanged: stop = previous day's low / setup low.
    return float(initial_stop)


def _exit_for_position(pos: Position, row: pd.Series, cfg: BacktestConfig) -> tuple[float | None, str | None]:
    # Conservative priority: initial stop first when several levels are touched on the same daily bar.
    if float(row["low"]) <= pos.initial_stop:
        return _sell_stop_fill_price(row, pos.initial_stop, cfg), "stop_loss"

    levels: list[tuple[str, float]] = []
    if cfg.exit_mode == "ma10" and pd.notna(row.get("ma10")):
        levels.append(("ma10_break", float(row["ma10"])))
    elif cfg.exit_mode == "atr_trail" and pos.trailing_stop is not None:
        levels.append((f"atr_trail_{cfg.atr_multiple:g}x", float(pos.trailing_stop)))
    elif cfg.exit_mode == "n_day_low" and pd.notna(row.get("n_day_low")):
        levels.append((f"{cfg.n_day_low_period}_day_low_break", float(row["n_day_low"])))
    elif cfg.exit_mode == "prev_day_low" and pd.notna(row.get("prev_low")):
        levels.append(("prev_day_low_break", float(row["prev_low"])))

    touched = [(reason, level) for reason, level in levels if float(row["low"]) <= level]
    if not touched:
        return None, None

    reason, level = max(touched, key=lambda x: x[1])
    return _sell_stop_fill_price(row, level, cfg), reason


def _sell_stop_fill_price(row: pd.Series, stop_price: float, cfg: BacktestConfig) -> float:
    # If open gaps through a sell stop, fill at open; otherwise fill at stop.
    raw = float(row["open"]) if float(row["open"]) <= float(stop_price) else float(stop_price)
    return raw * (1 - cfg.slippage_bps / 10000)


def _update_atr_trailing_stop_after_close(pos: Position, row: pd.Series, cfg: BacktestConfig) -> None:
    if cfg.exit_mode != "atr_trail":
        return
    atr = row.get("atr")
    if pd.isna(atr):
        return
    new_stop = pos.max_high - cfg.atr_multiple * float(atr)
    floor = pos.initial_stop
    if pos.trailing_stop is None:
        pos.trailing_stop = max(floor, new_stop)
    else:
        pos.trailing_stop = max(pos.trailing_stop, floor, new_stop)


def _close_trade(pos: Position, exit_date: pd.Timestamp, exit_price: float, exit_reason: str, cfg: BacktestConfig) -> Trade:
    pnl = (exit_price - pos.entry_price) * pos.shares - cfg.commission_per_trade
    pnl_pct = (exit_price / pos.entry_price - 1) if pos.entry_price else np.nan
    r_multiple = (exit_price - pos.entry_price) / pos.risk_per_share if pos.risk_per_share else np.nan
    mae = (pos.min_low - pos.entry_price) / pos.risk_per_share if pos.risk_per_share else np.nan
    mfe = (pos.max_high - pos.entry_price) / pos.risk_per_share if pos.risk_per_share else np.nan
    holding_days = int(np.busday_count(pd.Timestamp(pos.entry_date).date(), pd.Timestamp(exit_date).date()))
    return Trade(
        strategy=pos.strategy,
        ticker=pos.ticker,
        entry_date=pd.Timestamp(pos.entry_date).strftime("%Y-%m-%d"),
        entry_price=round(pos.entry_price, 4),
        initial_stop=round(pos.initial_stop, 4),
        risk_per_share=round(pos.risk_per_share, 4),
        exit_date=pd.Timestamp(exit_date).strftime("%Y-%m-%d"),
        exit_price=round(float(exit_price), 4),
        exit_reason=exit_reason,
        shares=int(pos.shares),
        position_size=round(pos.position_size, 2),
        pnl=round(float(pnl), 2),
        pnl_pct=round(float(pnl_pct), 6),
        r_multiple=round(float(r_multiple), 4) if pd.notna(r_multiple) else np.nan,
        mae=round(float(mae), 4) if pd.notna(mae) else np.nan,
        mfe=round(float(mfe), 4) if pd.notna(mfe) else np.nan,
        holding_days=holding_days,
        rs_rank_at_entry=pos.rs_rank_at_entry,
        signal_details=pos.signal_details,
    )


def _mark_to_market_equity(cash_realized: float, positions: list[Position], day: pd.DataFrame) -> float:
    unrealized = 0.0
    for pos in positions:
        if pos.ticker in day.index:
            close = float(day.loc[pos.ticker, "close"])
            unrealized += (close - pos.entry_price) * pos.shares
    return cash_realized + unrealized


def performance_report(trades: pd.DataFrame, equity: pd.DataFrame, cfg: BacktestConfig) -> dict:
    report = {
        "initial_capital": cfg.initial_capital,
        "position_pct": cfg.position_pct,
        "rs_threshold": cfg.rs_threshold,
        "strategies": list(cfg.strategies),
        "entry_name": cfg.entry_name,
        "exit_mode": cfg.exit_mode,
        "pivot_left": cfg.pivot_left,
        "pivot_right": cfg.pivot_right,
        "atr_period": cfg.atr_period,
        "atr_multiple": cfg.atr_multiple,
        "n_day_low_period": cfg.n_day_low_period,
        "same_day_stop_rule": cfg.same_day_stop_rule,
        "leverage_model": "allowed: position sizing uses equity * position_pct for every accepted entry and does not reserve/deduct cash; exposure can exceed 100% subject to max_open_positions and max_new_positions_per_day",
        "trade_count": int(len(trades)),
        "filters": {
            "common": {
                "avg_value_10_min_musd": cfg.min_avg_value_10,
                "adr20_min": cfg.min_adr20,
                "adr20_max": cfg.max_adr20,
                "close_gt_ma50": cfg.require_close_above_ma50,
            },
            "breakout_only": {
                "dr_lt_adr5": cfg.breakout_require_dr_lt_adr5,
                "distance_to_ma5_lt_adr10_price": cfg.breakout_require_near_ma5_within_adr10,
                "prev_close_lte_pivot": cfg.breakout_require_prev_close_lte_pivot,
            },
            "atr_trail": {
                "atr_period": cfg.atr_period,
                "atr_multiple": cfg.atr_multiple,
                "stop_formula": "highest_high_since_entry - atr_multiple * current_ATR; updated after each close and active next session",
            },
            "n_day_low": {
                "period": cfg.n_day_low_period,
                "stop_formula": "previous N trading days' lowest low; shifted 1 day so the stop is known before the session",
            },
            "prev_day_low": {
                "stop_formula": "previous trading day's low; if open gaps below the stop, fill at open; otherwise fill at previous low",
            },
            "same_day_stop": {
                "rule": cfg.same_day_stop_rule,
                "description": "If entry day low touches initial stop, stop out only when the entry day candle is red (close < open). Green/doji candle does not trigger same-day stop.",
            },
        },
    }

    if not trades.empty:
        wins = trades[trades["pnl"] > 0]
        losses = trades[trades["pnl"] < 0]
        gross_profit = float(wins["pnl"].sum())
        gross_loss = float(losses["pnl"].sum())
        report.update({
            "win_rate": float(len(wins) / len(trades)),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "profit_factor": round(gross_profit / abs(gross_loss), 4) if gross_loss < 0 else None,
            "avg_r": round(float(trades["r_multiple"].mean()), 4),
            "median_r": round(float(trades["r_multiple"].median()), 4),
            "avg_win": round(float(wins["pnl"].mean()), 2) if len(wins) else None,
            "avg_loss": round(float(losses["pnl"].mean()), 2) if len(losses) else None,
            "avg_win_loss_ratio": round(float(wins["pnl"].mean() / abs(losses["pnl"].mean())), 4) if len(wins) and len(losses) else None,
            "largest_winner_r": round(float(trades["r_multiple"].max()), 4),
            "largest_loser_r": round(float(trades["r_multiple"].min()), 4),
            "max_consecutive_losses": int(max_consecutive_losses(trades["pnl"].tolist())),
            "avg_holding_days": round(float(trades["holding_days"].mean()), 2),
        })
        by_strategy = {}
        for strategy, g in trades.groupby("strategy"):
            w = g[g["pnl"] > 0]
            l = g[g["pnl"] < 0]
            by_strategy[strategy] = {
                "trades": int(len(g)),
                "win_rate": float(len(w) / len(g)) if len(g) else None,
                "avg_r": round(float(g["r_multiple"].mean()), 4),
                "profit_factor": round(float(w["pnl"].sum() / abs(l["pnl"].sum())), 4) if len(l) and l["pnl"].sum() < 0 else None,
            }
        report["by_strategy"] = by_strategy
    else:
        report.update({
            "win_rate": None,
            "profit_factor": None,
            "avg_r": None,
            "median_r": None,
            "max_consecutive_losses": 0,
        })

    if not equity.empty:
        eq = equity["equity"].astype(float)
        dd = eq / eq.cummax() - 1
        report.update({
            "final_equity": round(float(eq.iloc[-1]), 2),
            "total_return": round(float(eq.iloc[-1] / cfg.initial_capital - 1), 6),
            "max_drawdown": round(float(dd.min()), 6),
        })

    return report


def max_consecutive_losses(pnls: list[float]) -> int:
    best = cur = 0
    for pnl in pnls:
        if pnl < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def save_outputs(output_dir: str | Path, trades: pd.DataFrame, equity: pd.DataFrame, report: dict, rs90_recent: pd.DataFrame) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    trades.to_csv(output_dir / "trades.csv", index=False)
    equity.to_csv(output_dir / "equity_curve.csv", index=False)
    rs90_recent.to_csv(output_dir / "rs90_daily_recent.csv", index=False)
    with (output_dir / "performance_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    try:
        import matplotlib.pyplot as plt
        if not equity.empty:
            ax = equity.assign(date=pd.to_datetime(equity["date"])).plot(x="date", y="equity", legend=False, title="Equity Curve")
            ax.set_xlabel("Date")
            ax.set_ylabel("Equity")
            fig = ax.get_figure()
            fig.tight_layout()
            fig.savefig(output_dir / "equity_curve.png", dpi=150)
            plt.close(fig)
    except Exception as e:
        print(f"Warning: failed to save equity curve plot: {e}")


def _fmt(value) -> str:
    try:
        if pd.isna(value):
            return "nan"
        return f"{float(value):.4f}"
    except Exception:
        return str(value)
