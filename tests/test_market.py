import pandas as pd
import pytest

from core.market import (
    close_series,
    compute_indicators,
    load_snapshot,
    save_snapshot,
    wilder_rsi,
)


def daily_series(values):
    index = pd.bdate_range(end="2026-08-14", periods=len(values))
    return pd.Series([float(v) for v in values], index=index)


def test_rsi_is_100_for_relentless_rise():
    closes = daily_series(range(1, 61))
    assert wilder_rsi(closes) == 100.0


def test_rsi_requires_more_than_period_points():
    assert wilder_rsi(daily_series(range(1, 15))) is None


def test_rsi_midpoint_for_alternating_equal_moves():
    values, price = [], 100.0
    for i in range(60):
        price += 1.0 if i % 2 == 0 else -1.0
        values.append(price)
    rsi = wilder_rsi(daily_series(values))
    assert rsi == pytest.approx(50.0, abs=5.0)


def test_indicators_on_linear_rise():
    closes = daily_series(range(1, 301))
    volumes = daily_series([1000] * 300)
    ind = compute_indicators(closes, volumes)
    assert ind["price"] == 300.0
    assert ind["day_change_pct"] == pytest.approx((300 / 299 - 1) * 100)
    assert ind["ma50"] == pytest.approx(sum(range(251, 301)) / 50)
    assert ind["ma200"] == pytest.approx(sum(range(101, 301)) / 200)
    assert ind["pct_off_52w_high"] == 0.0
    assert ind["volume_ratio_10d_3m"] == pytest.approx(1.0)


def test_indicators_with_short_history_return_none_not_garbage():
    ind = compute_indicators(daily_series([10, 11]), None)
    assert ind["ma50"] is None
    assert ind["ma200"] is None
    assert ind["rsi14"] is None
    assert ind["volume_ratio_10d_3m"] is None
    assert ind["day_change_pct"] == pytest.approx(10.0)


def test_snapshot_round_trip(tmp_path):
    path = tmp_path / "snap.json"
    snapshot = {"fetched_at": "2026-08-16T10:00:00+00:00", "tickers": {"BE": {"price": 42.5}}}
    save_snapshot(snapshot, path)
    assert load_snapshot(path) == snapshot


def test_load_snapshot_missing_file_returns_none(tmp_path):
    assert load_snapshot(tmp_path / "absent.json") is None


def test_close_series_rehydrates_dates():
    entry = {"dates": ["2026-08-13", "2026-08-14"], "close": [10.0, 11.0]}
    series = close_series(entry)
    assert list(series) == [10.0, 11.0]
    assert series.index[0] == pd.Timestamp("2026-08-13")
