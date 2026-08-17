import pandas as pd
import pytest

from core.portfolio import (
    load_holdings,
    portfolio_history_usd,
    save_holdings,
    theme_weights,
    value_positions,
)

HOLDINGS = pd.DataFrame(
    {
        "account": ["ISA", "Invest"],
        "ticker": ["AAA", "BBB"],
        "name": ["Alpha Corp", "Beta Corp"],
        "shares": [10.0, 20.0],
        "value_gbp_snapshot": [1000.0, 2000.0],
    }
)

SNAPSHOT = {
    "usd_per_gbp": 1.25,
    "tickers": {
        "AAA": {
            "price": 150.0,
            "day_change_pct": 2.0,
            "dates": ["2026-08-12", "2026-08-13", "2026-08-14"],
            "close": [140.0, 145.0, 150.0],
        }
    },
}


def test_load_holdings_rejects_missing_columns(tmp_path):
    path = tmp_path / "holdings.csv"
    path.write_text("account,ticker\nISA,AAA\n")
    with pytest.raises(ValueError, match="shares"):
        load_holdings(path)


def test_load_holdings_normalises_tickers(tmp_path):
    path = tmp_path / "holdings.csv"
    path.write_text(
        "account,ticker,name,shares,value_gbp_snapshot\nISA, aaa ,Alpha,10,1000\n"
    )
    assert load_holdings(path)["ticker"].tolist() == ["AAA"]


def test_value_positions_prices_from_snapshot_with_fallback():
    valued = value_positions(HOLDINGS, SNAPSHOT, usd_per_gbp=1.25)
    aaa = valued[valued["ticker"] == "AAA"].iloc[0]
    bbb = valued[valued["ticker"] == "BBB"].iloc[0]
    assert aaa["value_gbp"] == pytest.approx(10 * 150 / 1.25)  # 1200
    assert aaa["priced_live"]
    assert bbb["value_gbp"] == 2000.0  # falls back to the holdings file value
    assert not bbb["priced_live"]
    assert valued["weight_pct"].sum() == pytest.approx(100.0)


def test_value_positions_without_snapshot_uses_file_values():
    valued = value_positions(HOLDINGS, None, usd_per_gbp=1.25)
    assert valued["value_gbp"].tolist() == [2000.0, 1000.0]  # sorted by value
    assert not valued["priced_live"].any()


def test_theme_weights_groups_and_labels_unknown():
    valued = value_positions(HOLDINGS, None, usd_per_gbp=1.25)
    themes = theme_weights(valued, {"AAA": "Tech"})
    assert themes["weight_pct"].sum() == pytest.approx(100.0)
    assert set(themes["theme"]) == {"Tech", "Unclassified"}


def test_portfolio_history_sums_covered_tickers():
    history = portfolio_history_usd(HOLDINGS, SNAPSHOT)
    # only AAA is covered: 10 shares × closes
    assert history.tolist() == [1400.0, 1450.0, 1500.0]


def test_portfolio_history_none_without_snapshot():
    assert portfolio_history_usd(HOLDINGS, None) is None


def test_save_holdings_round_trips_through_load(tmp_path):
    path = tmp_path / "holdings.csv"
    save_holdings(HOLDINGS, path)
    reloaded = load_holdings(path)
    pd.testing.assert_frame_equal(reloaded, HOLDINGS)


def test_save_holdings_writes_only_required_columns(tmp_path):
    path = tmp_path / "holdings.csv"
    extra = HOLDINGS.assign(scratch_column="drop me")
    save_holdings(extra, path)
    assert list(pd.read_csv(path).columns) == [
        "account", "ticker", "name", "shares", "value_gbp_snapshot",
    ]
