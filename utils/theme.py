"""
BioSift Design System
─────────────────────
Single source of truth for colours, typography, components and chart theme.
Every view imports from here so the whole app stays visually consistent.

Direction: light scholarly ledger ("a methods journal on paper").
Palette: warm paper + ink neutrals + ONE accent (deep emerald), with
status hues (blue/amber/red) reserved for state only. Radii stay near
square because printed forms are near square; the pill shape is reserved
for status badges because a pill is a state marker, not decoration.
Flat surfaces: hairline rules carry structure, shadows and glow carry
nothing, so there are none. Typography: Georgia serif display (journal
voice), system sans with tabular numerals for data, mono for machine
strings only. See DESIGN.md for the written reasons.
"""

import plotly.graph_objects as go
import streamlit as st

# ── Design tokens ─────────────────────────────────────────
C = {
    "bg":          "#F4F1E8",   # paper page
    "bg_soft":     "#EDE9DC",   # sidebar, sunken panels
    "card":        "#FBF9F2",   # raised card / panel
    "card_hi":     "#F1ECDE",   # card hover
    "line":        "#D6CFBC",   # hairline
    "line_strong": "#B9B09A",   # rule, table borders
    "text":        "#232019",   # ink
    "text_dim":    "#5C5647",   # body copy on card (6.7:1)
    "text_faint":  "#6E6653",   # small labels on card (5.2:1)
    "accent":      "#136F4E",   # deep emerald, the one accent
    "accent_dim":  "#DCEBE0",   # accent tint surface
    "blue":        "#1D5FA8",   # info / links
    "amber":       "#75530F",   # warn state (5.7:1 on warn tint)
    "red":         "#A2382B",   # fail state
    "violet":      "#6A4B9E",
    "orange":      "#9C5A22",
    "black":       "#232019",
}

# Vivid data colours for maps and chart series (encoded state, not UI
# text): readable on both paper and satellite imagery.
D = {
    "clean":  "#1E7A54",
    "flag":   "#C2402F",
    "sparse": "#C97B23",
    "rich":   "#1E7A54",
    "mid":    "#C9922B",
    "poor":   "#B23A2E",
}

CSS = f"""
<style>
/* Field-ledger direction on paper: no webfont fetch (system stack only),
   tabular numerals, flat ink: nothing glows, nothing gradients. */
html, body, [class*="css"], .stApp {{
    font-family: -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    font-variant-numeric: tabular-nums;
    color: {C['text']};
}}
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
[data-testid="stDecoration"] {{ display: none; }}
[data-testid="stHeader"] {{ background: transparent; }}
.stApp {{ background: {C['bg']}; }}

/* keyboard focus must stay visible (R-34) */
a:focus-visible, button:focus-visible, input:focus-visible,
textarea:focus-visible, [tabindex]:focus-visible {{
    outline: 2px solid {C['accent']}; outline-offset: 2px;
}}

/* ── layout rhythm ── */
.block-container {{ padding-top: 1.2rem; max-width: 1350px; }}
hr {{ border-color: {C['line']}; margin: 1.1rem 0; }}
a {{ color: {C['blue']}; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

/* ── sidebar ── */
[data-testid="stSidebar"] {{
    background: {C['bg_soft']};
    border-right: 1px solid {C['line']};
}}
[data-testid="stSidebar"] * {{ color: {C['text_dim']}; }}
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stNumberInput label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stTextArea label {{ font-size: 0.78rem; }}
[data-testid="stSidebar"] hr {{ margin: 0.8rem 0; }}
.sb-brand {{
    display: flex; align-items: center; gap: 0.6rem;
    padding: 0.4rem 0.2rem 1rem 0.2rem;
}}
.sb-logo {{
    width: 34px; height: 34px; border-radius: 4px;
    background: {C['accent']};
    border: 1px solid #0C5A3F;
    display: flex; align-items: center; justify-content: center;
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 1.15rem; color: #F4F1E8; font-weight: 700;
}}
.sb-name {{
    font-family: Georgia, 'Times New Roman', serif;
    font-weight: 700; font-size: 1.05rem; color: {C['text']} !important;
    letter-spacing: -0.2px;
}}
.sb-tag  {{
    font-size: 0.66rem; color: {C['text_faint']} !important;
    letter-spacing: 1.2px; text-transform: uppercase;
}}

/* ── hero header ── */
.hero {{
    padding: 1.9rem 1.9rem 1.6rem 1.9rem;
    border: 1px solid {C['line']};
    border-top: 3px double {C['line_strong']};
    background: {C['card']};
    border-radius: 4px;
    margin-bottom: 1.4rem;
}}
.hero-kicker {{
    display: block;
    font-family: ui-monospace, Menlo, Consolas, monospace;
    font-size: 0.72rem; font-weight: 600;
    color: {C['text_faint']};
    padding: 0 0 0.9rem 0; margin-bottom: 1.1rem;
    border-bottom: 1px solid {C['line']};
}}
.hero-title {{
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 2.3rem; font-weight: 700; letter-spacing: -0.3px;
    color: {C['text']}; line-height: 1.12; margin: 0 0 0.75rem 0;
    max-width: 24ch;
}}
.hero-sub {{
    font-size: 1.0rem; color: {C['text_dim']}; max-width: 780px;
    line-height: 1.65; margin: 0;
}}
.hero-facts {{
    display: flex; flex-wrap: wrap; gap: 0; margin-top: 1.35rem;
    border-top: 1px solid {C['line']}; padding-top: 0.9rem;
}}
.hero-fact {{
    font-size: 0.8rem; color: {C['text_dim']};
    padding: 0 1.1rem; border-left: 1px solid {C['line']};
    line-height: 1.5;
}}
.hero-fact:first-child {{ padding-left: 0; border-left: none; }}

/* ── page header (inner pages) ── */
.page-head {{ margin: 0.6rem 0 1.4rem 0; }}
/* higher specificity to beat Streamlit's h1 font reset */
.hero .hero-title, .page-head .page-title {{
    font-family: Georgia, 'Times New Roman', serif;
}}
.page-title {{
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 1.8rem; font-weight: 700; letter-spacing: -0.3px;
    color: {C['text']}; margin: 0;
}}
.page-sub {{ font-size: 0.92rem; color: {C['text_dim']}; margin: 0.35rem 0 0 0; }}

/* ── section header ── */
.sec {{
    display: flex; align-items: center; gap: 0.7rem;
    margin: 1.6rem 0 0.85rem 0;
}}
.sec-line {{ flex: 1; height: 1px; background: {C['line_strong']}; }}
.sec-t {{
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.09em;
    text-transform: uppercase; color: {C['text_dim']}; white-space: nowrap;
}}

/* ── cards: flat paper panels, hairline structure, no glow ── */
.card {{
    background: {C['card']};
    border: 1px solid {C['line']};
    border-radius: 4px;
    padding: 1.25rem 1.35rem;
}}
/* lead card = real hierarchy (entry points outrank depth features) */
.card-hi {{ border-color: {C['line_strong']}; border-top: 3px solid {C['accent']}; }}
.card-t {{ font-weight: 700; font-size: 0.98rem; color: {C['text']}; margin-bottom: 0.35rem; }}
.card-d {{ font-size: 0.85rem; color: {C['text_dim']}; line-height: 1.6; }}

/* ── metrics ── */
.metric {{
    background: {C['card']}; border: 1px solid {C['line']};
    border-radius: 4px; padding: 1.05rem 1.15rem;
}}
.metric:hover {{ border-color: {C['line_strong']}; }}
.metric-label {{
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.09em;
    text-transform: uppercase; color: {C['text_faint']};
}}
.metric-value {{
    font-size: 1.6rem; font-weight: 700; color: {C['text']};
    margin-top: 0.3rem; letter-spacing: -0.4px;
}}
.metric-note {{ font-size: 0.76rem; color: {C['text_dim']}; margin-top: 0.2rem; }}

/* ── score hero: the verdict is the focal point of its screen ── */
.score-hero {{
    background: {C['card']}; border: 1px solid {C['line']};
    border-radius: 4px; padding: 1.35rem 1.5rem;
}}
.score-big {{
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 2.5rem; font-weight: 700; letter-spacing: -0.5px;
    line-height: 1.05;
}}
.score-bar {{
    background: {C['bg_soft']}; border: 1px solid {C['line']};
    height: 8px; border-radius: 2px; overflow: hidden; margin-top: 0.85rem;
}}
.score-fill {{ height: 8px; border-radius: 1px; }}
.t-good  {{ color: {C['accent']}; }}
.t-fair  {{ color: {C['amber']}; }}
.t-poor  {{ color: {C['red']}; }}
.f-good  {{ background: {C['accent']}; }}
.f-fair  {{ background: {C['amber']}; }}
.f-poor  {{ background: {C['red']}; }}

/* ── inline svg icons: ink, not accent (accent is reserved) ── */
.ic {{ color: {C['text']}; display: inline-flex; align-items: center; }}

/* ── badges: pill shape reserved for status (a pill marks state) ── */
.badge {{
    display: inline-flex; align-items: center; gap: 0.35rem;
    font-size: 0.72rem; font-weight: 700;
    padding: 0.22rem 0.65rem; border-radius: 999px;
    border: 1px solid {C['line_strong']}; color: {C['text_dim']};
    background: {C['bg_soft']};
}}
.badge-ok    {{ color: {C['accent']}; border-color: {C['accent']}; background: {C['accent_dim']}; }}
.badge-warn  {{ color: {C['amber']};  border-color: {C['amber']};  background: #F3E7C8; }}
.badge-bad   {{ color: {C['red']};    border-color: {C['red']};    background: #F1DAD3; }}
.badge-std {{
    color: {C['violet']}; border-color: {C['violet']}; background: #E9E2F2;
    font-family: ui-monospace, monospace; font-size: 0.66rem;
}}

/* ── alert cards: left edge marks real state (info/success/warn/error) ── */
.alert {{
    border-radius: 4px; padding: 0.85rem 1.05rem;
    font-size: 0.86rem; line-height: 1.6; margin-bottom: 0.6rem;
    border: 1px solid {C['line']}; background: {C['card']};
}}
.alert-t {{ font-weight: 700; color: {C['text']}; margin-bottom: 0.15rem; }}
.alert-m {{ color: {C['text_dim']}; }}
.a-info    {{ border-left: 3px solid {C['blue']}; }}
.a-success {{ border-left: 3px solid {C['accent']}; }}
.a-warn    {{ border-left: 3px solid {C['amber']}; }}
.a-error   {{ border-left: 3px solid {C['red']}; }}

/* ── table tweaks ── */
[data-testid="stDataFrame"] {{
    border: 1px solid {C['line']}; border-radius: 4px; overflow: hidden;
}}

/* ── iucn chip (official IUCN category colours, standard, not palette) ── */
.iucn {{
    font-weight: 800; font-size: 0.74rem; letter-spacing: 0.5px;
    padding: 0.2rem 0.6rem; border-radius: 4px; color: #fff;
}}

/* ── taxonomy strip ── */
.tax {{
    text-align: center; padding: 0.55rem 0.2rem;
    background: {C['card']}; border: 1px solid {C['line']};
    border-radius: 4px;
}}
.tax-r {{
    font-size: 0.62rem; font-weight: 700; letter-spacing: 1.1px;
    text-transform: uppercase; color: {C['text_faint']};
}}
.tax-v {{
    font-size: 0.8rem; color: {C['text']}; font-style: italic;
    margin-top: 0.1rem;
}}

/* ── map legend dots: encode clean/flagged/sparse state on maps ── */
.legend-dot {{
    display:inline-block; width:10px; height:10px;
    border-radius:50%; margin-right:4px; vertical-align:middle;
    border: 1px solid rgba(0,0,0,0.15);
}}
.dot-green  {{ background: {D['clean']}; }}
.dot-red    {{ background: {D['flag']}; }}
.dot-orange {{ background: {D['sparse']}; }}

/* ── field label ── */
.field-label {{
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.09em;
    text-transform: uppercase; color: {C['text_faint']};
    margin: 0.4rem 0 0.2rem 0;
}}

/* ── footer ── */
.foot {{
    margin-top: 3rem; padding-top: 1.2rem; border-top: 1px solid {C['line_strong']};
    font-size: 0.76rem; color: {C['text_faint']};
    display: flex; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;
}}

/* ── streamlit control restyle ── */
.stButton > button {{
    border-radius: 4px; font-weight: 600; letter-spacing: 0.01em;
    border: 1px solid {C['line_strong']};
    background: {C['card']}; color: {C['text']};
    transition: border-color 120ms ease, background 120ms ease;
}}
.stButton > button:hover {{ border-color: {C['text_dim']}; background: {C['card_hi']}; }}
.stButton > button[kind="primary"] {{
    background: {C['accent']};
    border: 1px solid #0C5A3F; color: #F4F1E8;
}}
.stButton > button[kind="primary"]:hover {{
    background: #106144; color: #F4F1E8;
}}
.stDownloadButton > button {{
    border-radius: 4px; font-weight: 600;
    border: 1px solid {C['accent']};
    background: {C['accent_dim']}; color: {C['accent']};
}}
.stDownloadButton > button:hover {{ background: #CCE3D4; }}
.stTabs [data-baseweb="tab-list"] {{
    gap: 1.2rem; border-bottom: 1px solid {C['line_strong']};
}}
.stTabs [data-baseweb="tab"] {{
    padding: 0.45rem 0.1rem;
    color: {C['text_faint']}; font-weight: 600; font-size: 0.88rem;
}}
.stTabs [aria-selected="true"] {{
    background: transparent; color: {C['text']};
    border: none; border-bottom: 2px solid {C['accent']};
}}
.stTabs [data-baseweb="tab-highlight"] {{ display: none; }}
.stTabs [data-baseweb="tab-border"] {{ display: none; }}
div[data-testid="stExpander"] {{
    border: 1px solid {C['line']} !important; border-radius: 4px !important;
    background: {C['card']};
}}
input, textarea, [data-baseweb="select"] > div {{
    background: {C['card']} !important;
    border-radius: 4px !important;
}}
[data-testid="stTextInputRootElement"] input,
textarea {{
    color: {C['text']} !important;
}}
.stAlert {{
    border-radius: 4px; border: 1px solid {C['line']};
}}

/* ── responsive ── */
@media (max-width: 768px) {{
    .hero {{ padding: 1.5rem 1.2rem; }}
    .hero-title {{ font-size: 1.75rem; }}
    .hero-fact {{ padding: 0.25rem 0.9rem; border-left: none; }}
    .metric-value {{ font-size: 1.3rem; }}
    .score-big {{ font-size: 1.9rem; }}
    .page-title {{ font-size: 1.45rem; }}
}}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


# ── components ────────────────────────────────────────────
def page_head(title, subtitle=""):
    sub = f'<p class="page-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="page-head"><h1 class="page-title">{title}</h1>{sub}</div>',
        unsafe_allow_html=True,
    )


def section(title):
    st.markdown(
        f'<div class="sec"><span class="sec-t">{title}</span>'
        f'<span class="sec-line"></span></div>',
        unsafe_allow_html=True,
    )


def metric_card(label, value, note="", col=None):
    """Custom metric. Pass col=st column to render inside it."""
    note_html = f'<div class="metric-note">{note}</div>' if note else ""
    html = (
        f'<div class="metric"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>{note_html}</div>'
    )
    if col is not None:
        col.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown(html, unsafe_allow_html=True)


def score_hero(label, score, col=None):
    cls = "good" if score >= 80 else ("fair" if score >= 50 else "poor")
    label_txt = "Good" if score >= 80 else ("Fair" if score >= 50 else "Poor")
    html = (
        f'<div class="score-hero">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="score-big t-{cls}">{score}%'
        f' <span style="font-size:0.95rem;font-weight:600;'
        f'color:{C["text_dim"]}">{label_txt}</span></div>'
        f'<div class="score-bar"><div class="score-fill f-{cls}" '
        f'style="width:{min(score, 100)}%"></div></div>'
        f'</div>'
    )
    if col is not None:
        col.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown(html, unsafe_allow_html=True)


def badge(text, tone="", mono=False):
    cls = "badge-std" if mono else (f"badge-{tone}" if tone else "badge")
    return f'<span class="{cls}">{text}</span>'


def alert(kind, title, message):
    st.markdown(
        f'<div class="alert a-{kind}"><div class="alert-t">{title}</div>'
        f'<div class="alert-m">{message}</div></div>',
        unsafe_allow_html=True,
    )


def footer():
    st.markdown(
        f'<div class="foot"><span>BioSift, biodiversity data intelligence · '
        f'aligned with TDWG BDQ &amp; Darwin Core standards</span>'
        f'<span>Data: <a href="https://www.gbif.org" target="_blank">GBIF.org</a> '
        f'· CC-BY 4.0 sources</span></div>',
        unsafe_allow_html=True,
    )


# ── plotly theming (light paper, hairline grid) ───────────
def style_fig(fig, height=380, legend=True):
    """Apply BioSift look to any plotly figure and return it."""
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="-apple-system, Segoe UI, Roboto, sans-serif",
            size=12, color=C["text_dim"],
        ),
        margin=dict(l=10, r=10, t=36, b=10),
        height=height,
        showlegend=legend,
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=C["line"],
            font=dict(size=11),
        ),
        title=dict(font=dict(size=14, color=C["text"]), x=0.01),
    )
    fig.update_xaxes(gridcolor=C["line"], zerolinecolor=C["line_strong"])
    fig.update_yaxes(gridcolor=C["line"], zerolinecolor=C["line_strong"])
    return fig


def bar_fig(labels, values, title="", color=None, horizontal=False,
            height=380, text_auto=True):
    color = color or C["accent"]
    fig = go.Figure(
        go.Bar(
            x=values if horizontal else labels,
            y=labels if horizontal else values,
            orientation="h" if horizontal else "v",
            marker=dict(
                color=values if horizontal else [color] * len(values),
                colorscale=[[0, C["accent_dim"]], [1, C["accent"]]]
                if horizontal else None,
                line=dict(width=0),
            ),
            text=[f"{v:,}" for v in values] if text_auto else None,
            textposition="outside",
            textfont=dict(size=10, color=C["text_dim"]),
        )
    )
    fig.update_layout(title=title)
    return style_fig(fig, height=height, legend=False)
