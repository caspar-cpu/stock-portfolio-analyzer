"""Regenerate the documentation screenshots in docs/screenshots/.

Dev tool, not part of the app. Drives a running instance of the app with
Playwright and captures each view in dark mode plus the dashboard in light mode.

Usage:
    streamlit run app.py --server.port 8533     # in one terminal, then Refresh once
    python tools/capture_screenshots.py         # in another

Requires: pip install playwright && playwright install chromium
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://localhost:8533/"
OUT = Path(__file__).parent.parent / "docs" / "screenshots"
VIEWPORT = {"width": 1600, "height": 1200}


def settle(page, seconds: float = 1.6) -> None:
    """Let Streamlit finish its rerun and Plotly finish drawing."""
    page.wait_for_load_state("networkidle")
    time.sleep(seconds)


def nav(page, label: str) -> None:
    page.locator('[data-testid="stSidebar"]').get_by_text(label, exact=True).click()
    settle(page)


def capture(page, name: str) -> None:
    path = OUT / name
    page.screenshot(path=str(path), full_page=True)
    print(f"  wrote {path.relative_to(OUT.parent.parent)}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=2)
        try:
            page.goto(URL, wait_until="networkidle")
        except Exception as exc:  # noqa: BLE001 — the app must be running first
            print(f"Could not reach {URL}: {exc}\nStart the app on port 8533 first.")
            return 1
        page.wait_for_selector('[data-testid="stSidebar"]')
        settle(page, 2.5)

        capture(page, "01-dashboard-dark.png")
        nav(page, "Positions")
        capture(page, "02-positions-dark.png")
        nav(page, "Research desk")
        capture(page, "03-research-desk-dark.png")
        nav(page, "Calendar")
        capture(page, "04-calendar-dark.png")

        nav(page, "Dashboard")
        page.locator('[data-testid="stSidebar"]').get_by_text("Light", exact=True).click()
        settle(page, 2.0)
        capture(page, "05-dashboard-light.png")

        browser.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
