"""Access to the research log (data/research.json): analyst consensus, themes,
standing observations, and the dated catalyst calendar."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class Catalyst:
    sort_date: date
    label: str
    tickers: tuple[str, ...]
    event: str
    approx: bool

    def days_until(self, today: date) -> int | None:
        """None for approximate dates — a day count would imply precision the source lacks."""
        return None if self.approx else (self.sort_date - today).days


def load_research(path: Path) -> dict:
    return json.loads(path.read_text())


def catalysts(research: dict) -> list[Catalyst]:
    return [
        Catalyst(
            sort_date=datetime.strptime(c["sort_date"], "%Y-%m-%d").date(),
            label=c["label"],
            tickers=tuple(c["tickers"]),
            event=c["event"],
            approx=c.get("approx", False),
        )
        for c in research["catalysts"]
    ]


def upcoming_catalysts(research: dict, today: date, ticker: str | None = None) -> list[Catalyst]:
    items = [c for c in catalysts(research) if c.sort_date >= today]
    if ticker is not None:
        items = [c for c in items if ticker in c.tickers]
    return sorted(items, key=lambda c: c.sort_date)
