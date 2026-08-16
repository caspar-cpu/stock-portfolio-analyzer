"""The four screens: Dashboard, Positions, Research desk, Calendar.

Each view is a pure render function of already-computed data + the active theme.
Data loading, scoring and caching happen in app.py; nothing here touches the
network or disk.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from core.research import Catalyst, upcoming_catalysts
from core.signals import PositionScore
from ui import charts
from ui.format import md_escape, money_gbp, money_usd, pct, signed_class, stance_chip


def _table(headers: list[tuple[str, bool]], rows: list[list[str]]) -> str:
    """Build a styled HTML table. headers is (label, is_numeric); rows are raw
    HTML cells already aligned to the header order."""
    head = "".join(f'<th class="{"num" if num else ""}">{label}</th>' for label, num in headers)
    body = ""
    for row in rows:
        cells = "".join(
            f'<td class="{"num" if num else ""}">{cell}</td>'
            for cell, (_, num) in zip(row, headers, strict=True)
        )
        body += f"<tr>{cells}</tr>"
    return f'<table class="pc-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def dashboard(
    valued: pd.DataFrame,
    themes: pd.DataFrame,
    scores: dict[str, PositionScore],
    history_gbp: pd.Series | None,
    benchmark: pd.Series | None,
    theme: dict,
    today: date,
    research: dict,
) -> None:
    total = valued["value_gbp"].sum()
    live = valued[valued["priced_live"]]
    day_delta = (
        (live["value_gbp"] * live["day_change_pct"] / 100).sum() if not live.empty else 0.0
    )
    day_pct = (day_delta / total * 100) if total else 0.0

    top = valued.iloc[0]
    stances = pd.Series([s.stance for s in scores.values()])
    flagged = sum(1 for s in scores.values() if s.flags)

    c1, c2, c3, c4 = st.columns(4)
    with c1, st.container(border=True):
        st.caption("Total holdings")
        st.markdown(f'<div class="pc-hero">{money_gbp(total)}</div>', unsafe_allow_html=True)
        cls = signed_class(day_pct)
        st.markdown(
            f'<span class="{cls}">{money_gbp(day_delta)} ({pct(day_pct, sign=True)}) today</span>',
            unsafe_allow_html=True,
        )
    with c2, st.container(border=True):
        st.caption("Positions")
        st.markdown(f'<div class="pc-hero">{len(valued)}</div>', unsafe_allow_html=True)
        st.markdown(
            f"across {valued['account'].nunique()} accounts", unsafe_allow_html=True
        )
    with c3, st.container(border=True):
        st.caption("Largest position")
        st.markdown(f'<div class="pc-hero">{top["ticker"]}</div>', unsafe_allow_html=True)
        st.markdown(f"{top['weight_pct']:.1f}% of portfolio", unsafe_allow_html=True)
    with c4, st.container(border=True):
        st.caption("Risk flags")
        st.markdown(f'<div class="pc-hero">{flagged}</div>', unsafe_allow_html=True)
        st.markdown("positions with active flags", unsafe_allow_html=True)

    left, right = st.columns([1.6, 1])
    with left, st.container(border=True):
        st.markdown("#### Portfolio performance")
        if history_gbp is not None:
            st.caption("Indexed to 100 at window start · current shares held throughout")
            st.plotly_chart(
                charts.performance_area(history_gbp, benchmark, theme),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        else:
            st.info("Refresh market data to chart performance.")
    with right, st.container(border=True):
        st.markdown("#### Allocation by theme")
        st.plotly_chart(
            charts.allocation_bar(themes, theme),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    b1, b2 = st.columns(2)
    with b1, st.container(border=True):
        st.markdown("#### Stance summary")
        order = ["Accumulate", "Hold", "Watch", "Review"]
        counts = stances.value_counts()
        rows = [
            [stance_chip(s, theme), str(int(counts.get(s, 0)))]
            for s in order
        ]
        st.markdown(
            _table([("Stance", False), ("Positions", True)], rows), unsafe_allow_html=True
        )
        st.caption("Rules-based. Decision support, not financial advice.")
    with b2, st.container(border=True):
        st.markdown("#### Next catalysts")
        events = upcoming_catalysts(research, today)[:5]
        if events:
            rows = [
                [", ".join(c.tickers), c.event, c.label]
                for c in events
            ]
            st.markdown(
                _table(
                    [("Ticker", False), ("Event", False), ("When", False)], rows
                ),
                unsafe_allow_html=True,
            )
        else:
            st.caption("No upcoming catalysts in the research log.")


def positions(
    valued: pd.DataFrame,
    scores: dict[str, PositionScore],
    themes_map: dict[str, str],
    theme: dict,
) -> None:
    with st.container(border=True):
        st.markdown("#### Positions & stance")
        accounts = ["All accounts", *sorted(valued["account"].unique())]
        f1, f2 = st.columns([1, 1])
        account = f1.selectbox("Account", accounts, label_visibility="collapsed")
        sort_by = f2.selectbox(
            "Sort by", ["Value", "Weight", "Score", "Day change"], label_visibility="collapsed"
        )

        view = valued if account == "All accounts" else valued[valued["account"] == account]
        sort_key = {
            "Value": ("value_gbp", False),
            "Weight": ("weight_pct", False),
            "Day change": ("day_change_pct", False),
        }
        if sort_by == "Score":
            view = view.assign(
                _score=view["ticker"].map(lambda t: scores[t].total if t in scores else -1)
            ).sort_values("_score", ascending=False)
        else:
            col, asc = sort_key[sort_by]
            view = view.sort_values(col, ascending=asc, na_position="last")

        headers = [
            ("Ticker", False), ("Theme", False), ("Value", True), ("Weight", True),
            ("Day", True), ("Score", True), ("Stance", False),
        ]
        rows = []
        for row in view.itertuples(index=False):
            score = scores.get(row.ticker)
            day_cls = signed_class(row.day_change_pct)
            live_mark = "" if row.priced_live else ' <span class="sub">· file price</span>'
            rows.append(
                [
                    f'<strong>{row.ticker}</strong>{live_mark}'
                    f'<br><span class="sub">{row.name}</span>',
                    themes_map.get(row.ticker, "—"),
                    f"{money_gbp(row.value_gbp)}"
                    f"<br><span class='sub'>{money_usd(row.price_usd)}</span>",
                    f"{row.weight_pct:.1f}%",
                    f'<span class="{day_cls}">{pct(row.day_change_pct, sign=True)}</span>',
                    f"{score.total:.0f}" if score else "—",
                    stance_chip(score.stance, theme) if score else "—",
                ]
            )
        st.markdown(_table(headers, rows), unsafe_allow_html=True)
        st.caption(
            "Score 0–100 blends trend, momentum, street view, valuation headroom and risk drag. "
            "Positions without research coverage show no score."
        )


def research_desk(
    valued: pd.DataFrame,
    scores: dict[str, PositionScore],
    research: dict,
    snapshot: dict | None,
    theme: dict,
    today: date,
) -> None:
    tickers = valued["ticker"].tolist()
    with st.container(border=True):
        c1, c2 = st.columns([1, 3])
        ticker = c1.selectbox("Position", tickers)
        row = valued[valued["ticker"] == ticker].iloc[0]
        c2.markdown(
            f"### {row['name']} ({ticker})\n"
            f"{money_gbp(row['value_gbp'])} · {row['weight_pct']:.1f}% of portfolio · "
            f"{row['account']}"
        )

    score = scores.get(ticker)
    ticker_research = research["tickers"].get(ticker, {})
    entry = (snapshot or {}).get("tickers", {}).get(ticker)

    left, right = st.columns([1, 1])
    with left, st.container(border=True):
        st.markdown("#### Decision score")
        if score is not None:
            st.markdown(
                f'<div class="pc-hero">{score.total:.0f}'
                f'<span style="font-size:1rem;color:{theme["muted"]}">/100</span></div>'
                f'{stance_chip(score.stance, theme)}',
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                charts.score_breakdown_bar(score.components, theme),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            for comp in score.components:
                st.markdown(f"**{comp.name}** · {md_escape(comp.detail)}")
        else:
            st.info("No research coverage for this position yet.")
    with right, st.container(border=True):
        st.markdown("#### Market read")
        if entry is not None:
            m1, m2, m3 = st.columns(3)
            m1.metric("Price", money_usd(entry["price"]), pct(entry["day_change_pct"], sign=True))
            m2.metric("RSI (14)", f"{entry['rsi14']:.0f}" if entry["rsi14"] else "—")
            m3.metric("Off 52w high", pct(entry["pct_off_52w_high"]))
            st.plotly_chart(
                charts.price_with_ma(entry, theme),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        else:
            st.info("Refresh market data to see live technicals.")

    if score is not None and score.flags:
        with st.container(border=True):
            st.markdown("#### Flags")
            st.markdown(
                "".join(f'<span class="pc-flag">⚑ {f}</span>' for f in score.flags),
                unsafe_allow_html=True,
            )

    with st.container(border=True):
        st.markdown("#### Research log")
        if ticker_research:
            cols = st.columns(4)
            fields = [
                ("Consensus", ticker_research.get("consensus", "—").replace("_", " ")),
                ("Avg target", pct(ticker_research.get("avg_target_upside_pct"), sign=True)),
                ("Target range", ticker_research.get("target_range", "—")),
                ("Short interest", pct(ticker_research.get("short_interest_pct"), digits=0)),
            ]
            for col, (label, value) in zip(cols, fields, strict=True):
                col.metric(label, value)
            if ticker_research.get("note"):
                st.markdown(f"> {md_escape(ticker_research['note'])}")
        else:
            st.caption("No research notes for this ticker.")

        events = upcoming_catalysts(research, today, ticker=ticker)
        if events:
            st.markdown("**Upcoming catalysts**")
            rows = [[c.event, c.label] for c in events]
            st.markdown(
                _table([("Event", False), ("When", False)], rows), unsafe_allow_html=True
            )


def calendar(research: dict, theme: dict, today: date) -> None:
    with st.container(border=True):
        st.markdown("#### Catalyst calendar")
        st.caption("Dated events from the research log, nearest first.")
        events = upcoming_catalysts(research, today)
        if not events:
            st.info("No upcoming catalysts.")
            return
        rows = []
        for c in events:
            countdown = _countdown(c, today)
            rows.append([c.label, ", ".join(c.tickers), c.event, countdown])
        st.markdown(
            _table(
                [("When", False), ("Ticker", False), ("Event", False), ("Countdown", True)],
                rows,
            ),
            unsafe_allow_html=True,
        )


def _countdown(catalyst: Catalyst, today: date) -> str:
    days = catalyst.days_until(today)
    if days is None:
        return '<span class="sub">approx</span>'
    if days == 0:
        return "today"
    return f"{days}d"
