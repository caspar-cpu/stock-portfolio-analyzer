"""Plotly figure builders. Every figure takes the active theme so colours,
gridlines and hover styling follow the light/dark toggle."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from core.market import close_series
from theme import plot_layout


def _hex_to_rgba(hex_colour: str, alpha: float) -> str:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def performance_area(
    portfolio: pd.Series, benchmark: pd.Series | None, theme: dict
) -> go.Figure:
    """Portfolio value over time, indexed to 100 at the window start, with the
    benchmark on the same axis so the comparison is honest (one scale)."""
    fig = go.Figure()
    base = portfolio / portfolio.iloc[0] * 100
    accent = theme["accent"]
    fig.add_trace(
        go.Scatter(
            x=base.index,
            y=base.values,
            name="Portfolio",
            mode="lines",
            line={"color": accent, "width": 2},
            fill="tozeroy",
            fillcolor=_hex_to_rgba(accent, 0.14),
            hovertemplate="%{x|%d %b %Y}<br>Portfolio %{y:.1f}<extra></extra>",
        )
    )
    if benchmark is not None and not benchmark.empty:
        aligned = benchmark.reindex(portfolio.index).ffill()
        bench_base = aligned / aligned.iloc[0] * 100
        fig.add_trace(
            go.Scatter(
                x=bench_base.index,
                y=bench_base.values,
                name="S&P 500",
                mode="lines",
                line={"color": theme["muted"], "width": 1.5, "dash": "dot"},
                hovertemplate="%{x|%d %b %Y}<br>S&P 500 %{y:.1f}<extra></extra>",
            )
        )
    layout = plot_layout(theme, height=360)
    layout["yaxis"]["ticksuffix"] = ""
    layout["hovermode"] = "x unified"
    fig.update_layout(**layout)
    return fig


def allocation_bar(themes: pd.DataFrame, theme: dict) -> go.Figure:
    """Portfolio weight by theme. Horizontal bars, one hue per theme in slot
    order, 4px rounded ends, sorted so the largest concentration reads first."""
    ordered = themes.sort_values("weight_pct")
    colours = theme["categorical"]
    bar_colours = [colours[i % len(colours)] for i in range(len(ordered))]
    fig = go.Figure(
        go.Bar(
            x=ordered["weight_pct"],
            y=ordered["theme"],
            orientation="h",
            marker={"color": bar_colours, "cornerradius": 4},
            customdata=ordered[["value_gbp", "positions"]],
            hovertemplate=(
                "%{y}<br>%{x:.1f}% of portfolio<br>"
                "£%{customdata[0]:,.0f} · %{customdata[1]} positions<extra></extra>"
            ),
        )
    )
    layout = plot_layout(theme, height=260)
    layout["xaxis"]["ticksuffix"] = "%"
    layout["yaxis"]["gridcolor"] = "rgba(0,0,0,0)"
    fig.update_layout(**layout)
    return fig


def score_breakdown_bar(components, theme: dict) -> go.Figure:
    """Weighted contribution of each scoring component to a position's total."""
    contributions = [c.score * c.weight for c in components]
    names = [c.name for c in components]
    fig = go.Figure(
        go.Bar(
            x=contributions,
            y=names,
            orientation="h",
            marker={"color": theme["accent"], "cornerradius": 4},
            customdata=[[c.score, c.weight * 100] for c in components],
            hovertemplate=(
                "%{y}<br>raw %{customdata[0]:.0f}/100 × %{customdata[1]:.0f}%"
                " = %{x:.1f} pts<extra></extra>"
            ),
        )
    )
    layout = plot_layout(theme, height=230)
    layout["yaxis"]["gridcolor"] = "rgba(0,0,0,0)"
    layout["yaxis"]["autorange"] = "reversed"
    fig.update_layout(**layout)
    return fig


def price_with_ma(entry: dict, theme: dict) -> go.Figure:
    """Close price with 50/200-day moving averages over the snapshot window."""
    close = close_series(entry)
    dates = close.index
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=close.values,
            name="Close",
            mode="lines",
            line={"color": theme["accent"], "width": 2},
            hovertemplate="%{x|%d %b %Y}<br>$%{y:.2f}<extra></extra>",
        )
    )
    for window, colour in ((50, theme["categorical"][2]), (200, theme["categorical"][1])):
        if len(close) >= window:
            ma = close.rolling(window).mean()
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=ma.values,
                    name=f"{window}DMA",
                    mode="lines",
                    line={"color": colour, "width": 1.5},
                    hovertemplate=f"%{{x|%d %b %Y}}<br>{window}DMA $%{{y:.2f}}<extra></extra>",
                )
            )
    layout = plot_layout(theme, height=340)
    layout["hovermode"] = "x unified"
    fig.update_layout(**layout)
    return fig
