from theme import DARK
from ui.format import md_escape, money_gbp, money_usd, pct, signed_class, stance_chip


def test_md_escape_neutralises_dollar_and_tilde():
    note = "cut ~35% (~$1bn+), insiders sold ~$83m"
    assert md_escape(note) == r"cut \~35% (\~\$1bn+), insiders sold \~\$83m"


def test_md_escape_covers_emphasis_code_and_links():
    assert md_escape("use *bold* _em_ `code` [link]") == (
        r"use \*bold\* \_em\_ \`code\` \[link\]"
    )


def test_md_escape_escapes_backslash_first():
    assert md_escape(r"a\b") == r"a\\b"


def test_md_escape_leaves_plain_text_untouched():
    assert md_escape("volume falling at last research pass") == (
        "volume falling at last research pass"
    )


def test_money_and_pct_formatting():
    assert money_gbp(224417.71) == "£224,418"
    assert money_usd(None) == "—"
    assert money_usd(229.9) == "$229.90"
    assert pct(None) == "—"
    assert pct(19.6, sign=True) == "+19.6%"
    assert pct(-2.5) == "-2.5%"


def test_signed_class_direction():
    assert signed_class(1.0) == "pc-up"
    assert signed_class(-1.0) == "pc-down"
    assert signed_class(0.0) == ""
    assert signed_class(None) == ""


def test_stance_chip_uses_status_colour():
    chip = stance_chip("Accumulate", DARK)
    assert DARK["status"]["good"] in chip
    assert "Accumulate" in chip
