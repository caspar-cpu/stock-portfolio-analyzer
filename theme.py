"""Design tokens and Plotly defaults for the two UI modes.

The categorical slot order is load-bearing: it was validated for adjacent-pair
colour-vision-deficiency separation in both modes (dataviz validate_palette.js).
Don't reorder or restep without re-running the validator against these surfaces.
"""

from __future__ import annotations

DARK = {
    "name": "dark",
    "page_bg": "#0e0c14",
    "surface": "#17141f",
    "surface_2": "#211c2e",
    "border": "rgba(255,255,255,0.09)",
    "text": "#f4f2fa",
    "text_2": "#b7b2c8",
    "muted": "#8b8794",
    "gridline": "#29242f",
    "accent": "#9085e9",
    "accent_soft": "rgba(144,133,233,0.16)",
    "good": "#0ca30c",
    "bad": "#e66767",
    "categorical": [
        "#9085e9", "#d95926", "#199e70", "#c98500",
        "#d55181", "#008300", "#3987e5", "#e66767",
    ],
    "status": {
        "good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b",
    },
}

LIGHT = {
    "name": "light",
    "page_bg": "#f4f3f8",
    "surface": "#fbfbfd",
    "surface_2": "#efedf5",
    "border": "rgba(11,11,11,0.09)",
    "text": "#16131f",
    "text_2": "#52514e",
    "muted": "#898781",
    "gridline": "#e1e0d9",
    "accent": "#4a3aa7",
    "accent_soft": "rgba(74,58,167,0.12)",
    "good": "#006300",
    "bad": "#d03b3b",
    "categorical": [
        "#4a3aa7", "#eb6834", "#1baf7a", "#eda100",
        "#e87ba4", "#008300", "#2a78d6", "#e34948",
    ],
    "status": {
        "good": "#0ca30c", "warning": "#b97f00", "serious": "#c05621", "critical": "#d03b3b",
    },
}

FONT_STACK = "system-ui, -apple-system, 'Segoe UI', sans-serif"


def plot_layout(theme: dict, height: int = 340) -> dict:
    """Base Plotly layout: transparent on the card surface, recessive chrome."""
    axis = {
        "gridcolor": theme["gridline"],
        "zeroline": False,
        "linecolor": theme["gridline"],
        "tickfont": {"color": theme["muted"]},
    }
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": FONT_STACK, "color": theme["text_2"], "size": 12},
        "height": height,
        "margin": {"l": 10, "r": 10, "t": 10, "b": 10},
        "xaxis": axis,
        "yaxis": dict(axis),
        "hoverlabel": {
            "bgcolor": theme["surface_2"],
            "font": {"color": theme["text"], "family": FONT_STACK},
            "bordercolor": theme["border"],
        },
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "x": 0,
            "font": {"color": theme["text_2"]},
        },
    }


def app_css(theme: dict) -> str:
    t = theme
    return f"""
<style>
.stApp {{ background: {t["page_bg"]}; color: {t["text"]}; }}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {{ color: {t["text"]}; letter-spacing: -0.01em; }}
header[data-testid="stHeader"] {{ background: transparent; }}

section[data-testid="stSidebar"] {{
  background: {t["surface"]};
  border-right: 1px solid {t["border"]};
}}
section[data-testid="stSidebar"] * {{ color: {t["text_2"]}; }}
section[data-testid="stSidebar"] hr {{ border-color: {t["border"]}; }}

/* nav radio as a menu — scoped to the keyed nav so the theme toggle is untouched */
.st-key-nav label {{
  padding: 0.45rem 0.7rem; border-radius: 10px; width: 100%;
  transition: background 0.15s ease;
}}
.st-key-nav label:hover {{ background: {t["surface_2"]}; }}
.st-key-nav label:has(input:checked) {{ background: {t["accent_soft"]}; }}
.st-key-nav label:has(input:checked) p {{ color: {t["accent"]}; font-weight: 600; }}
.st-key-nav [role="radiogroup"] {{ gap: 0.15rem; }}
.st-key-nav div[data-testid="stMarkdownContainer"] p {{ font-size: 0.95rem; }}

/* cards */
div[data-testid="stVerticalBlockBorderWrapper"] {{
  background: {t["surface"]};
  border: 1px solid {t["border"]};
  border-radius: 16px;
  padding: 0.35rem 0.45rem;
}}

.stButton > button, .stFormSubmitButton > button {{
  background: {t["accent"]}; color: #ffffff; border: none; border-radius: 10px;
  font-weight: 600;
}}
.stButton > button:hover, .stFormSubmitButton > button:hover {{
  filter: brightness(1.1); color: #ffffff;
}}

.stApp [data-testid="stMetricValue"] {{ color: {t["text"]}; font-weight: 650; }}
.stApp [data-testid="stMetricLabel"] p {{ color: {t["text_2"]}; }}
.stApp [data-testid="stMarkdownContainer"] p, .stApp [data-testid="stCaptionContainer"] p {{
  color: {t["text_2"]};
}}
.stApp [data-testid="stWidgetLabel"] p {{ color: {t["text_2"]}; }}

.stSelectbox div[data-baseweb="select"] > div,
.stTextInput input, .stNumberInput input {{
  background: {t["surface_2"]}; color: {t["text"]}; border-color: {t["border"]};
}}

.stApp [data-testid="stExpander"] {{
  background: {t["surface"]}; border: 1px solid {t["border"]}; border-radius: 12px;
}}

/* custom tables */
table.pc-table {{
  width: 100%; border-collapse: collapse; font-size: 0.88rem;
  font-variant-numeric: tabular-nums;
}}
table.pc-table th {{
  text-align: left; color: {t["muted"]}; font-weight: 500; font-size: 0.74rem;
  text-transform: uppercase; letter-spacing: 0.06em;
  padding: 0.35rem 0.6rem; border-bottom: 1px solid {t["border"]};
}}
table.pc-table td {{
  padding: 0.5rem 0.6rem; border-bottom: 1px solid {t["border"]}; color: {t["text"]};
}}
table.pc-table tr:last-child td {{ border-bottom: none; }}
table.pc-table th.num, table.pc-table td.num {{ text-align: right; }}
table.pc-table td .sub {{ color: {t["muted"]}; font-size: 0.78rem; }}

.pc-chip {{
  display: inline-flex; align-items: center; gap: 0.35rem;
  padding: 0.14rem 0.6rem; border-radius: 999px; font-size: 0.8rem; font-weight: 600;
  white-space: nowrap;
}}
.pc-flag {{
  display: inline-block; padding: 0.2rem 0.65rem; border-radius: 8px;
  font-size: 0.8rem; margin: 0 0.35rem 0.35rem 0;
  background: {t["surface_2"]}; color: {t["text"]}; border: 1px solid {t["border"]};
}}
.pc-brand {{
  font-size: 1.15rem; font-weight: 700; color: {t["text"]}; letter-spacing: -0.01em;
}}
.pc-hero {{ font-size: 2.1rem; font-weight: 700; color: {t["text"]}; line-height: 1.1; }}
.pc-up {{ color: {t["good"]}; }}
.pc-down {{ color: {t["bad"]}; }}
</style>
"""
