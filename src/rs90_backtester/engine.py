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
    exit_mode: str = "either"  # ma10, pivot_low, either
    max_open_positions: int = 100
    max_new_positions_per_day: int = 100
    allow_same_ticker_overlap: bool = False
    slippage_bps: float = 0
    commission_per_trade: float = 0
    max_stop_pct: float | None = None
    start_date: str | None = None
    end_date: str | None = None
    strategies: tuple[str, ...] = ("breakout", "rsi2")


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
        exits_today: list[Position] = []

        # 1) Existing positions: check exits using stop-order semantics.
        for pos in list(positions):
            if pos.ticker not in day.index:
                continue
            row = day.loc[pos.ticker]
            high = float(row["high"])
            low = float(row["low"])
            close = float(row["close"])
            pos.max_high = max(pos.max_high, high)
            pos.min_low = min(pos.min_low, low)

            exit_price, exit_reason = _exit_for_position(pos, row, cfg)
            if exit_price is not None:
                trade = _close_trade(pos, d, float(exit_price), exit_reason, cfg)
                trades.append(trade)
                cash_realized += trade.pnl - cfg.commission_per_trade
                exits_today.append(pos)

        if exits_today:
            positions = [p for p in positions if p not in exits_today]

        # 2) New entries. User assumption: if same-day entry and stop both trigger, trade is entered then stopped.
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
            pos = Position(
                strategy=cand["strategy"],
                ticker=cand["ticker"],
                entry_date=d,
                entry_price=cand["entry_price"],
                initial_stop=cand["initial_stop"],
                shares=shares,
                position_size=shares * cand["entry_price"],
                risk_per_share=cand["entry_price"] - cand["initial_stop"],
                rs_rank_at_entry=cand.get("rs_rank_at_entry"),
                signal_details=cand.get("signal_details", ""),
                max_high=float(day.loc[cand["ticker"], "high"]),
                min_low=float(day.loc[cand["ticker"], "low"]),
            )

            # Same-day stop assumption: entered then stopped when both are possible.
            row = day.loc[pos.ticker]
            if float(row["low"]) <= pos.initial_stop:
                trade = _close_trade(pos, d, pos.initial_stop, "same_day_stop_loss", cfg)
                trades.append(trade)
                cash_realized += trade.pnl - cfg.commission_per_trade
            else:
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
        })

    # Liquidate remaining positions at final close for closed-trade metrics.
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
        if not bool(row.get("in_rs90", False)) or float(row.get("rs_rank", -1)) < cfg.rs_threshold:
            continue

        if "breakout" in cfg.strategies:
            pivot = row.get("confirmed_pivot_high")
            prev_low = row.get("prev_low")
            if pd.notna(pivot) and pd.notna(prev_low) and float(row["high"]) >= float(pivot):
                raw_entry = max(float(row["open"]), float(pivot))
                entry = raw_entry * (1 + cfg.slippage_bps / 10000)
                out.append({
                    "strategy": "breakout",
                    "ticker": ticker,
                    "entry_price": entry,
                    "initial_stop": float(prev_low),
                    "rs_rank_at_entry": float(row["rs_rank"]),
                    "signal_details": f"buy_stop=pivot_high_1_1:{float(pivot):.4f}; entry=max(open,pivot)",
                })

        if "rsi2" in cfg.strategies:
            setup_rsi2 = row.get("setup_rsi2")
            setup_ma50 = row.get("setup_ma50")
            setup_close = row.get("setup_close")
            setup_low = row.get("setup_low")
            if (
                pd.notna(setup_rsi2)
                and pd.notna(setup_ma50)
                and pd.notna(setup_close)
                and pd.notna(setup_low)
                and float(setup_rsi2) < 5
                and float(setup_close) > float(setup_ma50)
            ):
                entry = float(row["open"]) * (1 + cfg.slippage_bps / 10000)
                out.append({
                    "strategy": "rsi2",
                    "ticker": ticker,
                    "entry_price": entry,
                    "initial_stop": float(setup_low),
                    "rs_rank_at_entry": float(row["rs_rank"]),
                    "signal_details": f"setup_rsi2={float(setup_rsi2):.2f}; setup_close>ma50; next_open_entry",
                })
    return out


def _exit_for_position(pos: Position, row: pd.Series, cfg: BacktestConfig) -> tuple[float | None, str | None]:
    low = float(row["low"])
    # Conservative priority: initial stop first when several levels are touched on the same daily bar.
    if low <= pos.initial_stop:
        return pos.initial_stop * (1 - cfg.slippage_bps / 10000), "stop_loss"

    levels: list[tuple[str, float]] = []
    if cfg.exit_mode in {"ma10", "either"} and pd.notna(row.get("ma10")):
        levels.append(("ma10_break", float(row["ma10"])))
    if cfg.exit_mode in {"pivot_low", "either"} and pd.notna(row.get("confirmed_pivot_low")):
        levels.append(("pivot_low_break", float(row["confirmed_pivot_low"])))

    touched = [(reason, level) for reason, level in levels if low <= level]
    if not touched:
        return None, None

    # Without intraday order, use the closest/higher triggered level for longs.
    reason, level = max(touched, key=lambda x: x[1])
    return level * (1 - cfg.slippage_bps / 10000), reason


def _close_trade(pos: Position, exit_date: pd.Timestamp, exit_price: float, exit_reason: str, cfg: BacktestConfig) -> Trade:
    pnl = (exit_price - pos.entry_price) * pos.shares - cfg.commission_per_trade
    pnl_pct = (exit_price / pos.entry_price - 1) if pos.entry_price else np.nan
    r_mult = (exit_price - pos.entry_price) / pos.risk_per_share if pos.risk_per_share > 0 else np.nan
    mae = (pos.min_low - pos.entry_price) / pos.risk_per_share if pos.risk_per_share > 0 else np.nan
    mfe = (pos.max_high - pos.entry_price) / pos.risk_per_share if pos.risk_per_share > 0 else np.nan
    holding_days = max(0, int((pd.Timestamp(exit_date) - pd.Timestamp(pos.entry_date)).days))
    return Trade(
        strategy=pos.strategy,
        ticker=pos.ticker,
        entry_date=pd.Timestamp(pos.entry_date).strftime("%Y-%m-%d"),
        entry_price=round(pos.entry_price, 6),
        initial_stop=round(pos.initial_stop, 6),
        risk_per_share=round(pos.risk_per_share, 6),
        exit_date=pd.Timestamp(exit_date).strftime("%Y-%m-%d"),
        exit_price=round(exit_price, 6),
        exit_reason=exit_reason,
        shares=pos.shares,
        position_size=round(pos.position_size, 2),
        pnl=round(pnl, 2),
        pnl_pct=round(pnl_pct, 6),
        r_multiple=round(r_mult, 6) if pd.notna(r_mult) else np.nan,
        mae=round(mae, 6) if pd.notna(mae) else np.nan,
        mfe=round(mfe, 6) if pd.notna(mfe) else np.nan,
        holding_days=holding_days,
        rs_rank_at_entry=pos.rs_rank_at_entry,
        signal_details=pos.signal_details,
    )


def _mark_to_market_equity(cash_realized: float, positions: list[Position], day: pd.DataFrame) -> float:
    equity = cash_realized
    for pos in positions:
        if pos.ticker in day.index:
            close = float(day.loc[pos.ticker, "close"])
            equity += (close - pos.entry_price) * pos.shares
    return float(equity)


def performance_report(trades: pd.DataFrame, equity: pd.DataFrame, cfg: BacktestConfig) -> dict:
    report: dict = {
        "initial_capital": cfg.initial_capital,
        "position_pct": cfg.position_pct,
        "rs_threshold": cfg.rs_threshold,
        "exit_mode": cfg.exit_mode,
        "trade_count": int(len(trades)),
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
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    trades.to_csv(out / "trades.csv", index=False)
    equity.to_csv(out / "equity_curve.csv", index=False)
    rs90_recent.to_csv(out / "rs90_daily_recent.csv", index=False)
    with (out / "performance_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    try:
        import matplotlib.pyplot as plt
        if not equity.empty:
            ax = equity.assign(date=pd.to_datetime(equity["date"])).plot(x="date", y="equity", legend=False, figsize=(10, 5))
            ax.set_title("Equity Curve")
            ax.set_xlabel("Date")
            ax.set_ylabel("Equity")
            fig = ax.get_figure()
            fig.tight_layout()
            fig.savefig(out / "equity_curve.png", dpi=150)
            plt.close(fig)
    except Exception as exc:
        print(f"Could not generate equity curve plot: {exc}")
