"""Market data snapshots.

The app never fetches implicitly: every read comes from the snapshot last saved
to disk, and refresh_snapshot() — wired to the Refresh button — is the only
network call. This keeps the app usable offline and off Yahoo's rate limits.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

BENCHMARK = "^GSPC"
FX_PAIR = "GBPUSD=X"
HISTORY_PERIOD = "1y"


def wilder_rsi(closes: pd.Series, periods: int = 14) -> float | None:
    if len(closes) <= periods:
        return None
    delta = closes.diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_gain = gains.ewm(alpha=1 / periods, min_periods=periods).mean().iloc[-1]
    avg_loss = losses.ewm(alpha=1 / periods, min_periods=periods).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - 100 / (1 + rs))


def compute_indicators(closes: pd.Series, volumes: pd.Series | None) -> dict:
    """Technical readings derived from a daily close series (most recent last)."""
    price = float(closes.iloc[-1])
    out: dict = {"price": price}

    out["day_change_pct"] = (
        (price / float(closes.iloc[-2]) - 1) * 100 if len(closes) >= 2 else None
    )
    out["ma50"] = float(closes.tail(50).mean()) if len(closes) >= 50 else None
    out["ma200"] = float(closes.tail(200).mean()) if len(closes) >= 200 else None
    out["rsi14"] = wilder_rsi(closes)
    out["pct_off_52w_high"] = (price / float(closes.max()) - 1) * 100

    out["volume_ratio_10d_3m"] = None
    if volumes is not None and len(volumes) >= 63:
        avg_3m = float(volumes.tail(63).mean())
        if avg_3m > 0:
            out["volume_ratio_10d_3m"] = float(volumes.tail(10).mean()) / avg_3m

    return {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in out.items()}


def _field_series(raw: pd.DataFrame, symbol: str, field: str) -> pd.Series | None:
    """Extract one field for one symbol from a multi-ticker yf.download frame.

    With group_by="ticker", yfinance returns a (ticker, field) MultiIndex and
    fills failed symbols with all-NaN columns rather than omitting them.
    """
    try:
        series = raw[symbol][field]
    except KeyError:
        return None
    series = series.dropna()
    return series if not series.empty else None


def refresh_snapshot(tickers: list[str], path: Path) -> tuple[dict, list[str]]:
    """Fetch 1y of daily data for all tickers plus FX and benchmark, persist to path.

    Returns the snapshot and the tickers that could not be fetched.
    """
    symbols = sorted(set(tickers)) + [BENCHMARK, FX_PAIR]
    raw = yf.download(
        symbols,
        period=HISTORY_PERIOD,
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="ticker",
    )

    snapshot: dict = {
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "usd_per_gbp": None,
        "benchmark": None,
        "tickers": {},
    }
    failed: list[str] = []

    fx = _field_series(raw, FX_PAIR, "Close")
    if fx is not None:
        snapshot["usd_per_gbp"] = round(float(fx.iloc[-1]), 6)

    bench = _field_series(raw, BENCHMARK, "Close")
    if bench is not None:
        snapshot["benchmark"] = {
            "symbol": BENCHMARK,
            "dates": [d.strftime("%Y-%m-%d") for d in bench.index],
            "close": [round(float(v), 4) for v in bench],
        }

    for ticker in sorted(set(tickers)):
        closes = _field_series(raw, ticker, "Close")
        if closes is None:
            failed.append(ticker)
            continue
        volumes = _field_series(raw, ticker, "Volume")
        snapshot["tickers"][ticker] = {
            "dates": [d.strftime("%Y-%m-%d") for d in closes.index],
            "close": [round(float(v), 4) for v in closes],
            **compute_indicators(closes, volumes),
        }

    save_snapshot(snapshot, path)
    return snapshot, failed


def save_snapshot(snapshot: dict, path: Path) -> None:
    path.write_text(json.dumps(snapshot))


def load_snapshot(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def close_series(entry: dict) -> pd.Series:
    """Rehydrate a snapshot ticker entry into a date-indexed close series."""
    return pd.Series(entry["close"], index=pd.to_datetime(entry["dates"]))
