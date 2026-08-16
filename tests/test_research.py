from datetime import date
from pathlib import Path

from core.research import load_research, upcoming_catalysts

RESEARCH = {
    "catalysts": [
        {"sort_date": "2026-08-17", "label": "17 Aug", "tickers": ["HIVE"], "event": "Earnings"},
        {"sort_date": "2026-08-10", "label": "10 Aug", "tickers": ["MU"], "event": "Past event"},
        {
            "sort_date": "2026-09-15",
            "label": "Sep 2026",
            "tickers": ["MSFT"],
            "event": "Chip reveal",
            "approx": True,
        },
    ]
}

TODAY = date(2026, 8, 16)


def test_upcoming_excludes_past_and_sorts():
    events = upcoming_catalysts(RESEARCH, TODAY)
    assert [c.event for c in events] == ["Earnings", "Chip reveal"]


def test_upcoming_filters_by_ticker():
    events = upcoming_catalysts(RESEARCH, TODAY, ticker="MSFT")
    assert len(events) == 1
    assert events[0].event == "Chip reveal"


def test_days_until_exact_vs_approximate():
    events = upcoming_catalysts(RESEARCH, TODAY)
    assert events[0].days_until(TODAY) == 1
    assert events[1].days_until(TODAY) is None  # approximate date: no false precision


def test_bundled_research_file_parses():
    research = load_research(Path(__file__).parent.parent / "data" / "research.json")
    assert set(research["themes"]) == set(research["tickers"])
    assert upcoming_catalysts(research, TODAY)
