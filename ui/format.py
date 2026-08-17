"""Value formatting and stance/status colour mapping shared across views."""

from __future__ import annotations

STANCE_STATUS = {
    "Accumulate": "good",
    "Hold": "warning",
    "Watch": "serious",
    "Review": "critical",
}


# Inline markdown metacharacters that appear in free-text research notes and would
# otherwise be interpreted: $ (LaTeX), ~ (strikethrough), * _ (emphasis), ` (code),
# [ ] (links). Backslash is escaped first so we don't double-escape our own escapes.
_MD_SPECIAL = "\\`*_~$[]"


def md_escape(text: str) -> str:
    """Escape inline markdown so a research note renders as written — e.g. a
    price figure ('$1bn') isn't read as LaTeX and a stray '~' pair isn't read
    as a strikethrough. Markdown consumes the backslashes, so nothing shows."""
    for char in _MD_SPECIAL:
        text = text.replace(char, "\\" + char)
    return text


def money_gbp(value: float) -> str:
    return f"£{value:,.0f}"


def money_usd(value: float | None) -> str:
    return "—" if value is None else f"${value:,.2f}"


def pct(value: float | None, digits: int = 1, sign: bool = False) -> str:
    if value is None:
        return "—"
    return f"{value:+.{digits}f}%" if sign else f"{value:.{digits}f}%"


def signed_class(value: float | None) -> str:
    if value is None or value == 0:
        return ""
    return "pc-up" if value > 0 else "pc-down"


def stance_chip(stance: str, theme: dict) -> str:
    status_key = STANCE_STATUS.get(stance, "warning")
    colour = theme["status"][status_key]
    return (
        f'<span class="pc-chip" style="background:{colour}22;color:{colour};'
        f'border:1px solid {colour}55;">{stance}</span>'
    )


def stat_label(text: str) -> str:
    """A short, uppercase, letter-spaced title above a hero number — distinct
    from st.caption(), which stays sentence-case for explainer prose."""
    return f'<div class="pc-label">{text}</div>'
