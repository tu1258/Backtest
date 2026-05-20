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
    rs_bucket: str | None = None
    recent_days: int = 7
    entry_name: str = "rsi2_next_open"  # rsi2_next_open, rsi2_intraday_limit
    exit_name: str = "hold_1d_open"
    max_open_positions: int = 100_000
    max_new_positions_per_day: int = 100_000
    allow_same_ticker_overlap: bool = False
    slippage_bps: float = 1.0
    commission_per_trade: float = 0
    max_stop_pct: float | None = None
    same_day_stop_rule: str = "red_candle_only"
    atr_period: int = 14
    min_avg_value_10: float = 25.0
    min_adr20: float = 2.5
    max_adr20: float = 25.0
    require_close_above_ma50: bool = True
    use_initial_stop_loss: bool = False


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
    work["date"] = pd.to_datetime(work["date"])
    dates = sorted(work["date"].unique())
    by_date = {d: g.set_index("ticker", drop=False) for d, g in work.groupby("date")}

    cash_realized = float(cfg.initial_capital)
    positions: list[Position] = []
    trades: list[Trade] = []
    equity_rows: list[dict] = []

    for d in dates:
        day = by_date[d]

        exits_today: list[Position] = []
        for pos in list(positions):
            if pos.ticker not in day.index:
                continue
            row = day.loc[pos.ticker]
            exit_price, exit_reason = _exit_for_position(pos, row, d, cfg)
            pos.max_high = max(pos.max_high, float(row["high"]))
            pos.min_low = min(pos.min_low, float(row["low"]))
            if exit_price is not None:
                trade = _close_trade(pos, d, float(exit_price), str(exit_reason), cfg)
                trades.append(trade)
                cash_realized += trade.pnl - cfg.commission_per_trade
                exits_today.append(pos)
            else:
                _update_atr_trailing_stop_after_close(pos, row, cfg)
        if exits_today:
            positions = [p for p in positions if p not in exits_today]

        new_entries = 0
        held_tickers = {p.ticker for p in positions}
        for cand in _generate_entries(day, cfg):
            if new_entries >= cfg.max_new_positions_per_day:
                break
            if len(positions) >= cfg.max_open_positions:
                break
            if (not cfg.allow_same_ticker_overlap) and cand["ticker"] in held_tickers:
                continue
            initial_stop = cand.get("initial_stop")
            if _has_valid_stop(initial_stop):
                if float(initial_stop) >= float(cand["entry_price"]):
                    continue
                stop_pct = (float(cand["entry_price"]) - float(initial_stop)) / float(cand["entry_price"])
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
                risk_per_share=_risk_per_share(float(cand["entry_price"]), cand.get("initial_stop")),
                rs_rank_at_entry=cand.get("rs_rank_at_entry"),
                signal_details=cand.get("signal_details", ""),
                max_high=float(row["high"]),
                min_low=float(row["low"]),
                trailing_stop=_initial_trailing_stop(cand["initial_stop"], cfg),
            )
            if _same_day_initial_stop_hit(pos, row, cfg):
                exit_px = _sell_stop_fill_price(row, pos.initial_stop, cfg)
                trade = _close_trade(pos, d, exit_px, "same_day_stop_loss_red_candle", cfg)
                trades.append(trade)
                cash_realized += trade.pnl - cfg.commission_per_trade
            elif cfg.exit_name == "hold_0d_close":
                exit_px = float(row["close"]) * (1 - cfg.slippage_bps / 10000)
                trade = _close_trade(pos, d, exit_px, "hold_0d_close", cfg)
                trades.append(trade)
                cash_realized += trade.pnl - cfg.commission_per_trade
                new_entries += 1
            else:
                _update_atr_trailing_stop_after_close(pos, row, cfg)
                positions.append(pos)
                held_tickers.add(pos.ticker)
                new_entries += 1

        equity = _mark_to_market_equity(cash_realized, positions, day)
        exposure = sum(p.position_size for p in positions)
        equity_rows.append({
            "date": pd.Timestamp(d).strftime("%Y-%m-%d"),
            "equity": equity,
            "cash_realized": cash_realized,
            "open_positions": len(positions),
            "gross_exposure": exposure,
            "exposure_pct": (exposure / equity) if equity else 0.0,
        })

    if dates:
        last_d = dates[-1]
        last_day = by_date[last_d]
        for pos in positions:
            if pos.ticker in last_day.index:
                px = float(last_day.loc[pos.ticker, "close"]) * (1 - cfg.slippage_bps / 10000)
                trades.append(_close_trade(pos, last_d, px, "end_of_backtest", cfg))

    trades_df = pd.DataFrame([asdict(t) for t in trades])
    equity_df = pd.DataFrame(equity_rows)
    report = performance_report(trades_df, equity_df, cfg)
    return trades_df, equity_df, report


def _generate_entries(day: pd.DataFrame, cfg: BacktestConfig) -> list[dict]:
    out: list[dict] = []
    sort_rank = "entry_rs_rank" if "entry_rs_rank" in day.columns else "rs_rank"
    sort_score = "entry_rs_score" if "entry_rs_score" in day.columns else "rs_score"
    day = day.sort_values([sort_rank, sort_score], ascending=[False, False])
    stop_label = "setup_low_stop" if cfg.use_initial_stop_loss else "no_stop"

    for _, row in day.iterrows():
        ticker = str(row["ticker"])
        if not bool(row.get("in_rs_universe", row.get("in_rs90", False))):
            continue
        if not _passes_common_universe_filters(row, cfg):
            continue

        if cfg.entry_name == "rsi2_next_open":
            setup_rsi2 = row.get("setup_rsi2")
            setup_low = row.get("setup_low")
            if pd.notna(setup_rsi2) and pd.notna(setup_low) and float(setup_rsi2) < 5:
                raw_entry = float(row["open"])
                initial_stop = float(setup_low) if cfg.use_initial_stop_loss else np.nan

                # If next open is already below/equal to setup-day low, the setup has failed.
                # Do not create an artificial buy-and-immediate-stop trade.
                if cfg.use_initial_stop_loss and raw_entry <= initial_stop:
                    continue

                entry = raw_entry * (1 + cfg.slippage_bps / 10000)
                if cfg.use_initial_stop_loss and initial_stop >= entry:
                    continue

                out.append({
                    "strategy": f"{cfg.rs_bucket or 'rs'}_{cfg.entry_name}_{cfg.exit_name}_{stop_label}",
                    "ticker": ticker,
                    "entry_price": entry,
                    "initial_stop": initial_stop,
                    "rs_rank_at_entry": float(row.get("entry_rs_rank", row["rs_rank"])),
                    "signal_details": f"entry=rsi2_next_open; setup_rsi2={float(setup_rsi2):.2f}; raw_entry=open:{raw_entry:.4f}; slippage_bps={cfg.slippage_bps}; initial_stop_mode={stop_label}; initial_stop={initial_stop if pd.notna(initial_stop) else np.nan}; decision_date={row.get('decision_date', '')}; filter_close={row.get('entry_filter_close', np.nan):.4f}; filter_ma50={row.get('entry_filter_ma50', np.nan):.4f}; filter_avg_value_10={row.get('entry_filter_avg_value_10', np.nan):.2f}; filter_adr20={row.get('entry_filter_adr20', np.nan):.2f}; rs_bucket={cfg.rs_bucket}",
                })

        elif cfg.entry_name == "rsi2_intraday_limit":
            trigger = row.get("rsi2_5_trigger_price")
            if pd.notna(trigger) and float(row["low"]) <= float(trigger):
                raw_entry = float(row["open"]) if float(row["open"]) <= float(trigger) else float(trigger)
                # For intraday entry, setup day is the entry day. The stop is only active from next day.
                initial_stop = float(row["low"]) if cfg.use_initial_stop_loss else np.nan
                entry = raw_entry * (1 + cfg.slippage_bps / 10000)

                if cfg.use_initial_stop_loss and initial_stop >= entry:
                    continue

                out.append({
                    "strategy": f"{cfg.rs_bucket or 'rs'}_{cfg.entry_name}_{cfg.exit_name}_{stop_label}",
                    "ticker": ticker,
                    "entry_price": entry,
                    "initial_stop": initial_stop,
                    "rs_rank_at_entry": float(row.get("entry_rs_rank", row["rs_rank"])),
                    "signal_details": f"entry=rsi2_intraday_limit; rsi2<5_trigger={float(trigger):.4f}; raw_entry={raw_entry:.4f}; slippage_bps={cfg.slippage_bps}; initial_stop_mode={stop_label}; initial_stop={initial_stop if pd.notna(initial_stop) else np.nan}; initial_stop_active_from=next_trading_day; decision_date={row.get('decision_date', '')}; filter_close={row.get('entry_filter_close', np.nan):.4f}; filter_ma50={row.get('entry_filter_ma50', np.nan):.4f}; filter_avg_value_10={row.get('entry_filter_avg_value_10', np.nan):.2f}; filter_adr20={row.get('entry_filter_adr20', np.nan):.2f}; rs_bucket={cfg.rs_bucket}",
                })
        else:
            raise ValueError(f"unsupported entry_name: {cfg.entry_name}")
    return out


def _passes_common_universe_filters(row: pd.Series, cfg: BacktestConfig) -> bool:
    # These filters are entry-decision filters. They must be based on the previous
    # completed daily bar, not the entry day's still-forming/final daily bar.
    avg_value = row.get("entry_filter_avg_value_10")
    adr20 = row.get("entry_filter_adr20")
    prev_close = row.get("entry_filter_close")
    prev_ma50 = row.get("entry_filter_ma50")
    checks = [
        pd.notna(avg_value) and float(avg_value) > cfg.min_avg_value_10,
        pd.notna(adr20) and cfg.min_adr20 <= float(adr20) <= cfg.max_adr20,
    ]
    if cfg.require_close_above_ma50:
        checks.append(pd.notna(prev_close) and pd.notna(prev_ma50) and float(prev_close) > float(prev_ma50))
    return all(checks)


def _has_valid_stop(value: object) -> bool:
    try:
        return pd.notna(value) and np.isfinite(float(value))
    except Exception:
        return False


def _risk_per_share(entry_price: float, initial_stop: object) -> float:
    if _has_valid_stop(initial_stop):
        risk = float(entry_price) - float(initial_stop)
        return risk if risk > 0 else np.nan
    return np.nan


def _same_day_initial_stop_hit(pos: Position, row: pd.Series, cfg: BacktestConfig) -> bool:
    if not _has_valid_stop(pos.initial_stop):
        return False
    if float(row["low"]) > float(pos.initial_stop):
        return False

    # rsi2_next_open enters at the open, so an entry-day low below setup-day low
    # is a valid stop-order exit. No red/green candle assumption is needed.
    if "entry=rsi2_next_open" in pos.signal_details:
        return True

    # rsi2_intraday_limit enters during the day. With daily bars we cannot know
    # whether the entry-day low happened before or after the intraday entry, so
    # the setup-low stop becomes active only from the next trading day.
    if "entry=rsi2_intraday_limit" in pos.signal_details:
        return False

    if cfg.same_day_stop_rule == "always":
        return True
    if cfg.same_day_stop_rule == "never":
        return False
    if cfg.same_day_stop_rule == "red_candle_only":
        return float(row["close"]) < float(row["open"])
    raise ValueError(f"unsupported same_day_stop_rule: {cfg.same_day_stop_rule}")


def _initial_trailing_stop(initial_stop: float, cfg: BacktestConfig) -> float | None:
    if not cfg.exit_name.startswith("trail_"):
        return None
    return float(initial_stop) if _has_valid_stop(initial_stop) else None


def _exit_for_position(pos: Position, row: pd.Series, current_date: pd.Timestamp, cfg: BacktestConfig) -> tuple[float | None, str | None]:
    if _has_valid_stop(pos.initial_stop) and float(row["low"]) <= float(pos.initial_stop):
        return _sell_stop_fill_price(row, float(pos.initial_stop), cfg), "stop_loss"

    name = cfg.exit_name
    if name.startswith("trail_") and pos.trailing_stop is not None:
        level = float(pos.trailing_stop)
        if float(row["low"]) <= level:
            return _sell_stop_fill_price(row, level, cfg), name

    if name.endswith("_day_low"):
        n = int(name.split("_")[0])
        col = f"n_day_low_{n}"
        if col in row and pd.notna(row[col]):
            level = float(row[col])
            if float(row["low"]) <= level:
                return _sell_stop_fill_price(row, level, cfg), name

    if name.startswith("rsi2_gt_"):
        threshold = float(name.replace("rsi2_gt_", ""))
        if pd.notna(row.get("rsi2")) and float(row["rsi2"]) > threshold:
            return float(row["close"]) * (1 - cfg.slippage_bps / 10000), name

    if name.startswith("hold_"):
        n, price_type = _parse_hold_exit(name)
        days_held = int(np.busday_count(pd.Timestamp(pos.entry_date).date(), pd.Timestamp(current_date).date()))
        if price_type == "open" and days_held >= n:
            return float(row["open"]) * (1 - cfg.slippage_bps / 10000), name
        if price_type == "close" and days_held >= n:
            return float(row["close"]) * (1 - cfg.slippage_bps / 10000), name

    return None, None


def _parse_hold_exit(name: str) -> tuple[int, str]:
    parts = name.split("_")
    if len(parts) != 3 or parts[0] != "hold" or not parts[1].endswith("d"):
        raise ValueError(f"invalid hold exit name: {name}")
    return int(parts[1][:-1]), parts[2]


def _sell_stop_fill_price(row: pd.Series, stop_price: float, cfg: BacktestConfig) -> float:
    raw = float(row["open"]) if float(row["open"]) <= float(stop_price) else float(stop_price)
    return raw * (1 - cfg.slippage_bps / 10000)


def _update_atr_trailing_stop_after_close(pos: Position, row: pd.Series, cfg: BacktestConfig) -> None:
    if not cfg.exit_name.startswith("trail_"):
        return
    atr = row.get("atr")
    if pd.isna(atr):
        return
    multiple = 0.5 if cfg.exit_name == "trail_0_5atr" else 1.0
    new_stop = pos.max_high - multiple * float(atr)
    candidates = [new_stop]
    if pos.trailing_stop is not None and np.isfinite(float(pos.trailing_stop)):
        candidates.append(float(pos.trailing_stop))
    if _has_valid_stop(pos.initial_stop):
        candidates.append(float(pos.initial_stop))
    pos.trailing_stop = max(candidates)


def _close_trade(pos: Position, exit_date: pd.Timestamp, exit_price: float, exit_reason: str, cfg: BacktestConfig) -> Trade:
    pnl = (exit_price - pos.entry_price) * pos.shares - cfg.commission_per_trade
    pnl_pct = (exit_price / pos.entry_price - 1) if pos.entry_price else np.nan
    valid_risk = pd.notna(pos.risk_per_share) and np.isfinite(float(pos.risk_per_share)) and float(pos.risk_per_share) > 0
    r_multiple = (exit_price - pos.entry_price) / pos.risk_per_share if valid_risk else np.nan
    mae = (pos.min_low - pos.entry_price) / pos.risk_per_share if valid_risk else np.nan
    mfe = (pos.max_high - pos.entry_price) / pos.risk_per_share if valid_risk else np.nan
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
        "rs_bucket": cfg.rs_bucket,
        "entry_name": cfg.entry_name,
        "exit_name": cfg.exit_name,
        "slippage_bps_each_side": cfg.slippage_bps,
        "same_day_stop_rule": cfg.same_day_stop_rule,
        "use_initial_stop_loss": cfg.use_initial_stop_loss,
        "trade_count": int(len(trades)),
        "leverage_model": "allowed: every accepted entry uses equity * position_pct; cash is not reserved/deducted, so gross exposure can exceed 100%",
    }
    if not trades.empty:
        wins = trades[trades["pnl"] > 0]
        losses = trades[trades["pnl"] < 0]
        gross_profit = float(wins["pnl"].sum())
        gross_loss = float(losses["pnl"].sum())
        avg_win_pct = float(wins["pnl_pct"].mean()) if len(wins) else None
        avg_loss_pct = float(losses["pnl_pct"].mean()) if len(losses) else None
        avg_win_loss_pct_ratio = (
            round(avg_win_pct / abs(avg_loss_pct), 4)
            if avg_win_pct is not None and avg_loss_pct is not None and avg_loss_pct < 0
            else None
        )
        report.update({
            "win_rate": float(len(wins) / len(trades)),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "profit_factor": round(gross_profit / abs(gross_loss), 4) if gross_loss < 0 else None,
            "avg_win_pct": round(avg_win_pct, 6) if avg_win_pct is not None else None,
            "avg_loss_pct": round(avg_loss_pct, 6) if avg_loss_pct is not None else None,
            "avg_win_loss_pct_ratio": avg_win_loss_pct_ratio,
            "largest_winner_r": round(float(trades["r_multiple"].max()), 4),
            "largest_loser_r": round(float(trades["r_multiple"].min()), 4),
            "max_consecutive_losses": int(max_consecutive_losses(trades["pnl"].tolist())),
            "avg_holding_days": round(float(trades["holding_days"].mean()), 2),
        })
    else:
        report.update({
            "win_rate": None,
            "profit_factor": None,
            "avg_win_pct": None,
            "avg_loss_pct": None,
            "avg_win_loss_pct_ratio": None,
            "max_consecutive_losses": 0,
        })
    if not equity.empty:
        eq = equity["equity"].astype(float)
        dd = eq / eq.cummax() - 1
        exposure = equity["exposure_pct"].astype(float) if "exposure_pct" in equity else pd.Series(dtype=float)
        report.update({
            "final_equity": round(float(eq.iloc[-1]), 2),
            "total_return": round(float(eq.iloc[-1] / cfg.initial_capital - 1), 6),
            "max_drawdown": round(float(dd.min()), 6),
            "avg_exposure_pct": round(float(exposure.mean()), 6) if len(exposure) else None,
            "max_exposure_pct": round(float(exposure.max()), 6) if len(exposure) else None,
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


def save_outputs(output_dir: str | Path, trades: pd.DataFrame, equity: pd.DataFrame, report: dict, rs_recent: pd.DataFrame) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    trades.to_csv(output_dir / "trades.csv", index=False)
    equity.to_csv(output_dir / "equity_curve.csv", index=False)
    if not equity.empty and "exposure_pct" in equity:
        equity[["date", "open_positions", "gross_exposure", "exposure_pct"]].to_csv(output_dir / "exposure_curve.csv", index=False)
    rs_recent.to_csv(output_dir / "rs_membership_recent.csv", index=False)
    with (output_dir / "performance_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    try:
        import matplotlib.pyplot as plt
        if not equity.empty:
            ax = equity.assign(date=pd.to_datetime(equity["date"])).plot(x="date", y="equity", legend=False, title="Equity Curve")
            fig = ax.get_figure(); fig.tight_layout(); fig.savefig(output_dir / "equity_curve.png", dpi=150); plt.close(fig)
            ax = equity.assign(date=pd.to_datetime(equity["date"])).plot(x="date", y="exposure_pct", legend=False, title="Exposure Curve")
            fig = ax.get_figure(); fig.tight_layout(); fig.savefig(output_dir / "exposure_curve.png", dpi=150); plt.close(fig)
    except Exception as e:
        print(f"Warning: failed to save plots: {e}")
