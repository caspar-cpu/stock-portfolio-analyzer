"""Remote holdings persistence for deployments without a durable filesystem.

Streamlit Community Cloud's containers are ephemeral — anything written to
disk through the app's own UI (Manage holdings) is lost on the next restart.
This backs the private holdings file with a GitHub Gist instead, so edits
made through a deployed instance survive. Local dev never touches this: it
only activates when both HOLDINGS_GIST_ID and HOLDINGS_GIST_TOKEN are set.
"""

from __future__ import annotations

import io

import pandas as pd
import requests

GIST_API = "https://api.github.com/gists/{gist_id}"
HOLDINGS_FILENAME = "holdings.csv"
TIMEOUT_SECONDS = 10


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def load_holdings_gist(gist_id: str, token: str) -> pd.DataFrame | None:
    """None if the gist has no holdings file yet (a brand-new empty gist)."""
    url = GIST_API.format(gist_id=gist_id)
    resp = requests.get(url, headers=_headers(token), timeout=TIMEOUT_SECONDS)
    resp.raise_for_status()
    files = resp.json()["files"]
    if HOLDINGS_FILENAME not in files:
        return None
    return pd.read_csv(io.StringIO(files[HOLDINGS_FILENAME]["content"]))


def save_holdings_gist(holdings: pd.DataFrame, gist_id: str, token: str) -> None:
    buf = io.StringIO()
    holdings.to_csv(buf, index=False)
    resp = requests.patch(
        GIST_API.format(gist_id=gist_id),
        headers=_headers(token),
        json={"files": {HOLDINGS_FILENAME: {"content": buf.getvalue()}}},
        timeout=TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
