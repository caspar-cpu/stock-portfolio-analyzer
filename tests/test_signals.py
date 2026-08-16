from core.signals import Component, score_position

STRONG_INDICATORS = {
    "price": 110.0,
    "ma50": 100.0,
    "ma200": 90.0,
    "rsi14": 55.0,
    "volume_ratio_10d_3m": 1.1,
}

STRONG_RESEARCH = {
    "consensus": "strong_buy",
    "avg_target_upside_pct": 35.0,
    "peg": 0.9,
    "volume_trend": "rising",
}


def score(research=None, indicators=None, **kwargs):
    defaults = {
        "ticker": "TST",
        "research": STRONG_RESEARCH if research is None else research,
        "indicators": STRONG_INDICATORS if indicators is None else indicators,
        "weight_pct": 5.0,
        "theme": "Test theme",
        "theme_weight_pct": 10.0,
        "days_to_event": None,
        "event_label": None,
    }
    defaults.update(kwargs)
    return score_position(**defaults)


def test_perfect_setup_scores_100_and_accumulates():
    result = score()
    assert result.total == 100.0
    assert result.stance == "Accumulate"
    assert result.flags == ()


def test_weak_setup_lands_in_review():
    result = score(
        research={
            "consensus": "hold",
            "avg_target_upside_pct": 3.0,
            "peg": 6.0,
            "volume_trend": "collapsed",
            "short_interest_pct": 25.0,
        },
        indicators={"price": 80.0, "ma50": 100.0, "ma200": 90.0, "rsi14": 85.0},
    )
    assert result.stance == "Review"


def test_no_research_coverage_returns_none():
    assert score(research={"consensus": "buy"}) is not None
    assert score_position(
        ticker="NEW",
        research=None,
        indicators=STRONG_INDICATORS,
        weight_pct=0.0,
        theme=None,
        theme_weight_pct=None,
        days_to_event=None,
        event_label=None,
    ) is None


def test_unrecognised_consensus_is_neutral_and_surfaced():
    result = score(research={**STRONG_RESEARCH, "consensus": "mega_buy"})
    street = next(c for c in result.components if c.name == "Street view")
    assert street.score == 50.0
    assert "mega_buy" in street.detail


def test_unrecognised_volume_trend_is_surfaced_without_drag():
    result = score(research={**STRONG_RESEARCH, "volume_trend": "sideways"})
    risk = next(c for c in result.components if c.name == "Risk drag")
    assert risk.score == 100.0
    assert "sideways" in risk.detail


def test_valuation_clamps_to_100():
    result = score()
    valuation = next(c for c in result.components if c.name == "Valuation headroom")
    assert valuation.score == 100.0  # 100 for upside + 10 PEG bonus, clamped


def test_risk_never_goes_negative():
    result = score(
        research={
            **STRONG_RESEARCH,
            "short_interest_pct": 30.0,
            "volume_trend": "collapsed",
        },
        indicators={**STRONG_INDICATORS, "volume_ratio_10d_3m": 0.3},
    )
    risk = next(c for c in result.components if c.name == "Risk drag")
    assert risk.score == 0.0


def test_concentration_and_theme_flags():
    result = score(weight_pct=15.9, theme="AI infra", theme_weight_pct=27.0)
    assert any("Concentration" in f for f in result.flags)
    assert any("Theme crowding" in f for f in result.flags)


def test_event_flag_only_within_window():
    near = score(days_to_event=5, event_label="Q3 earnings")
    far = score(days_to_event=45, event_label="Q3 earnings")
    past = score(days_to_event=-2, event_label="Q3 earnings")
    assert any("Event in 5d" in f for f in near.flags)
    assert not far.flags
    assert not past.flags


def test_battleground_short_interest_flag():
    result = score(research={**STRONG_RESEARCH, "short_interest_pct": 26.3})
    assert any("Battleground" in f for f in result.flags)


def test_missing_moving_averages_score_neutral():
    result = score(indicators={"price": 100.0, "rsi14": 55.0})
    trend = next(c for c in result.components if c.name == "Trend")
    assert trend.score == 50.0
    assert "unavailable" in trend.detail


def test_component_weights_sum_to_one():
    result = score()
    assert isinstance(result.components[0], Component)
    assert abs(sum(c.weight for c in result.components) - 1.0) < 1e-9
