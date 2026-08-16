"""Holdings loading and valuation against a market snapshot."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.market import close_series

REQUIRED_COLUMNS = ("account", "ticker", "name", "shares", "value_gbp_snapshot")


def load_holdings(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Holdings file '{path.name}' is missing columns: {', '.join(missing)}")
    df["ticker"] = df["ticker"].str.upper().str.strip()
    return df


def value_positions(
    holdings: pd.DataFrame, snapshot: dict | None, usd_per_gbp: float
) -> pd.DataFrame:
    """Price each position from the snapshot; positions the snapshot doesn't cover
    fall back to the value recorded in the holdings file (priced_live=False)."""
    entries = (snapshot or {}).get("tickers", {})
    rows = []
    for row in holdings.itertuples(index=False):
        entry = entries.get(row.ticker)
        if entry is not None:
            value_gbp = row.shares * entry["price"] / usd_per_gbp
            rows.append(
                {
                    "account": row.account,
                    "ticker": row.ticker,
                    "name": row.name,
                    "shares": row.shares,
                    "price_usd": entry["price"],
                    "value_gbp": value_gbp,
                    "day_change_pct": entry["day_change_pct"],
                    "priced_live": True,
                }
            )
        else:
            rows.append(
                {
                    "account": row.account,
                    "ticker": row.ticker,
                    "name": row.name,
                    "shares": row.shares,
                    "price_usd": None,
                    "value_gbp": row.value_gbp_snapshot,
                    "day_change_pct": None,
                    "priced_live": False,
                }
            )
    valued = pd.DataFrame(rows)
    valued["weight_pct"] = valued["value_gbp"] / valued["value_gbp"].sum() * 100
    return valued.sort_values("value_gbp", ascending=False).reset_index(drop=True)


def theme_weights(valued: pd.DataFrame, themes: dict[str, str]) -> pd.DataFrame:
    df = valued.assign(theme=valued["ticker"].map(lambda t: themes.get(t, "Unclassified")))
    grouped = df.groupby("theme", as_index=False).agg(
        value_gbp=("value_gbp", "sum"), positions=("ticker", "count")
    )
    grouped["weight_pct"] = grouped["value_gbp"] / grouped["value_gbp"].sum() * 100
    return grouped.sort_values("weight_pct", ascending=False).reset_index(drop=True)


def portfolio_history_usd(holdings: pd.DataFrame, snapshot: dict | None) -> pd.Series | None:
    """Daily portfolio value in USD, assuming current share counts held throughout.

    Starts at the first date on which every snapshot-covered ticker has a close,
    so early gaps (e.g. a mid-window listing) don't understate the total.
    """
    entries = (snapshot or {}).get("tickers", {})
    parts = [
        close_series(entries[row.ticker]) * row.shares
        for row in holdings.itertuples(index=False)
        if row.ticker in entries
    ]
    if not parts:
        return None
    combined = pd.concat(parts, axis=1).ffill().dropna()
    if combined.empty:
        return None
    return combined.sum(axis=1)
