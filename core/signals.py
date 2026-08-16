"""Rules-based scoring that turns snapshot technicals and the research log into
a stance per position.

Decision support, not financial advice: the value of the score is that every
input and threshold is explicit — the full rule table lives in the README and
each band is covered by tests. Composite scores are only produced for tickers
with research coverage; technicals alone would give a false sense of rigour.
"""

from __future__ import annotations

from dataclasses import dataclass

CONSENSUS_SCORES = {
    "strong_buy": 100.0,
    "buy": 75.0,
    "moderate_buy": 55.0,
    "weak_buy": 45.0,
    "hold": 30.0,
    "sell": 10.0,
}

VOLUME_TREND_DRAG = {
    "rising": 0.0,
    "rising_fast": 0.0,
    "falling": 15.0,
    "falling_hard": 30.0,
    "collapsed": 40.0,
}

WEIGHTS = {
    "Trend": 0.25,
    "Momentum": 0.15,
    "Street view": 0.20,
    "Valuation headroom": 0.20,
    "Risk drag": 0.20,
}

# (minimum total, stance)
STANCE_BANDS = ((70.0, "Accumulate"), (55.0, "Hold"), (40.0, "Watch"), (0.0, "Review"))

CONCENTRATION_FLAG_PCT = 12.0
THEME_FLAG_PCT = 25.0
EVENT_WINDOW_DAYS = 14
BATTLEGROUND_SHORT_PCT = 15.0


@dataclass(frozen=True)
class Component:
    name: str
    score: float  # 0–100
    weight: float  # fraction of the composite
    detail: str


@dataclass(frozen=True)
class PositionScore:
    ticker: str
    total: float
    stance: str
    components: tuple[Component, ...]
    flags: tuple[str, ...]


def _trend(indicators: dict) -> Component:
    price = indicators.get("price")
    score, parts = 0.0, []
    for key, label in (("ma50", "50DMA"), ("ma200", "200DMA")):
        ma = indicators.get(key)
        if price is None or ma is None:
            score += 25.0  # neutral when the average can't be computed
            parts.append(f"{label} unavailable")
        elif price > ma:
            score += 50.0
            parts.append(f"above {label}")
        else:
            parts.append(f"below {label}")
    return Component("Trend", score, WEIGHTS["Trend"], ", ".join(parts))


def _momentum(indicators: dict) -> Component:
    rsi = indicators.get("rsi14")
    if rsi is None:
        score, detail = 50.0, "RSI unavailable"
    elif rsi > 80:
        score, detail = 20.0, f"RSI {rsi:.0f} — extremely overbought"
    elif rsi > 70:
        score, detail = 40.0, f"RSI {rsi:.0f} — overbought"
    elif rsi >= 45:
        score, detail = 100.0, f"RSI {rsi:.0f} — constructive"
    elif rsi >= 30:
        score, detail = 55.0, f"RSI {rsi:.0f} — cooling"
    else:
        score, detail = 35.0, f"RSI {rsi:.0f} — oversold"
    return Component("Momentum", score, WEIGHTS["Momentum"], detail)


def _street(research: dict) -> Component:
    label = research.get("consensus")
    score = CONSENSUS_SCORES.get(label)
    if score is None:
        # research.json is hand-edited; surface a bad label instead of guessing
        return Component(
            "Street view", 50.0, WEIGHTS["Street view"], f"unrecognised consensus '{label}'"
        )
    detail = label.replace("_", " ")
    if research.get("consensus_note"):
        detail += f" ({research['consensus_note']})"
    return Component("Street view", score, WEIGHTS["Street view"], detail)


def _valuation(research: dict) -> Component:
    upside = research.get("avg_target_upside_pct")
    if upside is None:
        score, parts = 50.0, ["no target data"]
    elif upside >= 30:
        score, parts = 100.0, [f"+{upside:.0f}% to avg target"]
    elif upside >= 20:
        score, parts = 80.0, [f"+{upside:.0f}% to avg target"]
    elif upside >= 10:
        score, parts = 60.0, [f"+{upside:.0f}% to avg target"]
    elif upside >= 5:
        score, parts = 40.0, [f"+{upside:.0f}% to avg target"]
    else:
        score, parts = 20.0, [f"only +{upside:.1f}% to avg target"]

    peg = research.get("peg")
    if peg is not None:
        if peg <= 1:
            score += 10.0
            parts.append(f"PEG {peg} — cheap growth")
        elif peg >= 5:
            score -= 30.0
            parts.append(f"PEG {peg} — very expensive growth")
        elif peg >= 3:
            score -= 20.0
            parts.append(f"PEG {peg} — expensive growth")
        else:
            parts.append(f"PEG {peg}")
    score = min(100.0, max(0.0, score))
    return Component("Valuation headroom", score, WEIGHTS["Valuation headroom"], ", ".join(parts))


def _risk(research: dict, indicators: dict) -> Component:
    score, parts = 100.0, []

    short = research.get("short_interest_pct")
    if short is not None:
        if short >= 20:
            score -= 50.0
            parts.append(f"short interest {short:.0f}%")
        elif short >= 9:
            score -= 25.0
            parts.append(f"short interest {short:.0f}%")

    trend = research.get("volume_trend")
    drag = VOLUME_TREND_DRAG.get(trend)
    if drag is None:
        parts.append(f"unrecognised volume trend '{trend}'")
    elif drag:
        score -= drag
        parts.append(f"volume {trend.replace('_', ' ')} at last research pass")

    # live confirmation of participation, on top of the (static) research label
    ratio = indicators.get("volume_ratio_10d_3m")
    if ratio is not None and ratio < 0.7:
        score -= 10.0
        parts.append(f"10d volume at {ratio:.0%} of 3m average")

    score = max(0.0, score)
    return Component("Risk drag", score, WEIGHTS["Risk drag"], ", ".join(parts) or "no known drags")


def score_position(
    ticker: str,
    research: dict | None,
    indicators: dict,
    weight_pct: float,
    theme: str | None,
    theme_weight_pct: float | None,
    days_to_event: int | None,
    event_label: str | None,
) -> PositionScore | None:
    if research is None:
        return None

    components = (
        _trend(indicators),
        _momentum(indicators),
        _street(research),
        _valuation(research),
        _risk(research, indicators),
    )
    total = sum(c.score * c.weight for c in components)
    stance = next(stance for minimum, stance in STANCE_BANDS if total >= minimum)

    flags = []
    if weight_pct >= CONCENTRATION_FLAG_PCT:
        flags.append(f"Concentration: {weight_pct:.1f}% of portfolio in one name")
    if theme_weight_pct is not None and theme_weight_pct >= THEME_FLAG_PCT:
        flags.append(f"Theme crowding: '{theme}' is {theme_weight_pct:.0f}% of portfolio")
    if days_to_event is not None and 0 <= days_to_event <= EVENT_WINDOW_DAYS:
        flags.append(f"Event in {days_to_event}d: {event_label}")
    short = research.get("short_interest_pct")
    if short is not None and short >= BATTLEGROUND_SHORT_PCT:
        flags.append(f"Battleground: {short:.0f}% short interest")

    return PositionScore(ticker, round(total, 1), stance, components, tuple(flags))
