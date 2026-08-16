"""Stock Portfolio Analyzer — a Streamlit decision-support tool.

Reads a holdings CSV and a research log, prices positions against a market
snapshot on disk, and scores each position with a transparent rules engine.
Market data is refreshed explicitly via the Refresh button — never implicitly —
so the app stays fast, offline-capable, and off Yahoo's rate limits.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import streamlit as st

from core.market import BENCHMARK, close_series, load_snapshot, refresh_snapshot
from core.portfolio import (
    load_holdings,
    portfolio_history_usd,
    theme_weights,
    value_positions,
)
from core.research import load_research, upcoming_catalysts
from core.signals import score_position
from theme import DARK, LIGHT, app_css
from ui import views

DATA_DIR = Path(__file__).parent / "data"
SNAPSHOT_PATH = DATA_DIR / "snapshot.json"
FX_FALLBACK = 1.348

st.set_page_config(page_title="Portfolio Analyzer", page_icon="📈", layout="wide")


def resolve_holdings_path() -> Path:
    """Prefer the user's private holdings.csv; fall back to the shipped sample."""
    private = DATA_DIR / "holdings.csv"
    return private if private.exists() else DATA_DIR / "holdings.sample.csv"


@st.cache_data(show_spinner=False)
def cached_holdings(path: str, mtime: float):
    return load_holdings(Path(path))


@st.cache_data(show_spinner=False)
def cached_research(path: str, mtime: float):
    return load_research(Path(path))


@st.cache_data(show_spinner=False)
def cached_snapshot(path: str, mtime: float | None):
    return load_snapshot(Path(path))


def score_all(valued, research, snapshot, themes_df, today) -> dict:
    """Score every position that has research coverage."""
    entries = (snapshot or {}).get("tickers", {})
    theme_weight = dict(zip(themes_df["theme"], themes_df["weight_pct"], strict=True))
    theme_of = research["themes"]

    scores = {}
    for row in valued.itertuples(index=False):
        ticker_research = research["tickers"].get(row.ticker)
        indicators = entries.get(row.ticker, {})
        theme_name = theme_of.get(row.ticker)
        events = upcoming_catalysts(research, today, ticker=row.ticker)
        next_event = events[0] if events else None
        result = score_position(
            ticker=row.ticker,
            research=ticker_research,
            indicators=indicators,
            weight_pct=row.weight_pct,
            theme=theme_name,
            theme_weight_pct=theme_weight.get(theme_name),
            days_to_event=next_event.days_until(today) if next_event else None,
            event_label=next_event.event if next_event else None,
        )
        if result is not None:
            scores[row.ticker] = result
    return scores


def sidebar(holdings_path: Path, snapshot: dict | None) -> tuple[str, dict]:
    with st.sidebar:
        st.markdown('<div class="pc-brand">📈 Portfolio Analyzer</div>', unsafe_allow_html=True)
        st.caption("Decision support · not financial advice")
        st.divider()

        page = st.radio(
            "Navigate",
            ["Dashboard", "Positions", "Research desk", "Calendar"],
            label_visibility="collapsed",
            key="nav",
        )
        st.divider()

        st.markdown("**Market data**")
        if snapshot and snapshot.get("fetched_at"):
            fetched = datetime.fromisoformat(snapshot["fetched_at"])
            st.caption(f"Snapshot: {fetched:%d %b %Y, %H:%M} UTC")
        else:
            st.caption("No snapshot yet — refresh to price live.")

        if st.button("↻ Refresh market data", use_container_width=True):
            _run_refresh(holdings_path)

        st.divider()
        mode = st.radio("Theme", ["Dark", "Light"], horizontal=True)
        st.caption(f"Holdings: `{holdings_path.name}`")

    return page, (DARK if mode == "Dark" else LIGHT)


def _run_refresh(holdings_path: Path) -> None:
    holdings = load_holdings(holdings_path)
    with st.spinner("Fetching latest prices from Yahoo Finance…"):
        try:
            _, failed = refresh_snapshot(holdings["ticker"].tolist(), SNAPSHOT_PATH)
        except Exception as exc:  # noqa: BLE001 — surface any network/parse failure to the user
            st.sidebar.error(f"Refresh failed: {exc}")
            return
    cached_snapshot.clear()
    if failed:
        st.sidebar.warning(f"Priced all but: {', '.join(failed)} (kept file values).")
    else:
        st.sidebar.success("Market data refreshed.")
    st.rerun()


def main() -> None:
    today = date.today()
    holdings_path = resolve_holdings_path()

    holdings = cached_holdings(str(holdings_path), holdings_path.stat().st_mtime)
    research_path = DATA_DIR / "research.json"
    research = cached_research(str(research_path), research_path.stat().st_mtime)
    snapshot = cached_snapshot(
        str(SNAPSHOT_PATH), SNAPSHOT_PATH.stat().st_mtime if SNAPSHOT_PATH.exists() else None
    )

    page, theme = sidebar(holdings_path, snapshot)
    st.markdown(app_css(theme), unsafe_allow_html=True)

    if holdings.empty:
        st.warning(f"`{holdings_path.name}` has no positions. Add rows to see your portfolio.")
        return

    usd_per_gbp = (snapshot or {}).get("usd_per_gbp") or FX_FALLBACK
    valued = value_positions(holdings, snapshot, usd_per_gbp)
    themes_df = theme_weights(valued, research["themes"])
    scores = score_all(valued, research, snapshot, themes_df, today)

    if page == "Dashboard":
        history_usd = portfolio_history_usd(holdings, snapshot)
        history_gbp = history_usd / usd_per_gbp if history_usd is not None else None
        benchmark = None
        if snapshot and snapshot.get("benchmark"):
            benchmark = close_series(snapshot["benchmark"])
        views.dashboard(
            valued, themes_df, scores, history_gbp, benchmark, theme, today, research
        )
    elif page == "Positions":
        views.positions(valued, scores, research["themes"], theme)
    elif page == "Research desk":
        views.research_desk(valued, scores, research, snapshot, theme, today)
    else:
        views.calendar(research, theme, today)

    st.caption(
        f"Benchmark {BENCHMARK} · FX {usd_per_gbp:.4f} USD/GBP · "
        "Prices via Yahoo Finance on refresh. Not financial advice."
    )


if __name__ == "__main__":
    main()
