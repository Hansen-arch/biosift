"""
BioSift Design System
─────────────────────
Single source of truth for colours, typography, components and chart theme.
Every view imports from here so the whole app stays visually consistent.
"""

import plotly.graph_objects as go
import streamlit as st

# ── Design tokens ─────────────────────────────────────────
C = {
    "bg":          "#0B0F14",   # page
    "bg_soft":     "#0F151C",   # panels
    "card":        "#111823",   # cards
    "card_hi":     "#16202E",   # card hover
    "line":        "#1F2A38",   # hairlines
    "text":        "#E9EFF6",
    "text_dim":    "#8A97A8",
    "text_faint":  "#5C6879",
    "accent":      "#22C58B",   # emerald — primary
    "accent_dim":  "#0E3B2C",
    "blue":        "#4DA3FF",
    "amber":       "#E8B339",
    "red":         "#F2555A",
    "violet":      "#A78BFA",
    "orange":      "#F08A3E",
    "black":       "#000000",
}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Fraunces:opsz,wght@9..144,500;9..144,700&display=swap');

html, body, [class*="css"], .stApp {{
    font-family: 'Inter', 'Segoe UI', sans-serif;
}}
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
[data-testid="stDecoration"] {{ display: none; }}
[data-testid="stHeader"] {{ background: transparent; }}
.stApp {{ background: {C['bg']}; }}

/* ── layout rhythm ── */
.block-container {{ padding-top: 1.2rem; max-width: 1350px; }}
hr {{ border-color: {C['line']}; margin: 1.1rem 0; }}
a {{ color: {C['blue']}; text-decoration: none; }}

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
    width: 34px; height: 34px; border-radius: 9px;
    background: linear-gradient(135deg, {C['accent']} 0%, #0E7A57 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.05rem; color: #04140D; font-weight: 800;
    box-shadow: 0 4px 14px rgba(34,197,139,0.35);
}}
.sb-name {{ font-weight: 700; font-size: 1.05rem; color: {C['text']} !important; letter-spacing: -0.3px; }}
.sb-tag  {{ font-size: 0.68rem; color: {C['text_faint']} !important; letter-spacing: 1.4px; text-transform: uppercase; }}

/* ── hero header ── */
.hero {{
    padding: 2.6rem 2.4rem 2.4rem 2.4rem;
    border-radius: 20px;
    border: 1px solid {C['line']};
    background:
        radial-gradient(1100px 380px at 8% -30%, rgba(34,197,139,0.16), transparent 60%),
        radial-gradient(900px 420px at 95% 0%, rgba(77,163,255,0.10), transparent 55%),
        linear-gradient(180deg, {C['card']} 0%, {C['bg_soft']} 100%);
    margin-bottom: 1.6rem;
}}
.hero-kicker {{
    display: inline-flex; align-items: center; gap: 0.45rem;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 1.6px;
    text-transform: uppercase; color: {C['accent']};
    background: {C['accent_dim']}; border: 1px solid rgba(34,197,139,0.4);
    padding: 0.28rem 0.7rem; border-radius: 999px; margin-bottom: 1.1rem;
}}
.hero-title {{
    font-family: 'Fraunces', Georgia, serif;
    font-size: 2.6rem; font-weight: 700; letter-spacing: -0.8px;
    color: {C['text']}; line-height: 1.08; margin: 0 0 0.7rem 0;
}}
.hero-sub {{ font-size: 1.02rem; color: {C['text_dim']}; max-width: 780px; line-height: 1.65; margin: 0; }}
.hero-actions {{ display: flex; gap: 0.6rem; margin-top: 1.4rem; flex-wrap: wrap; }}
.hero-pill {{
    font-size: 0.8rem; font-weight: 600; color: {C['text_dim']};
    border: 1px solid {C['line']}; background: {C['card']};
    padding: 0.42rem 0.9rem; border-radius: 999px;
}}

/* ── page header (inner pages) ── */
.page-head {{ margin: 0.6rem 0 1.4rem 0; }}
/* higher specificity to beat Streamlit's h1 font reset */
.hero .hero-title, .page-head .page-title {{
    font-family: 'Fraunces', Georgia, serif;
}}
.page-title {{
    font-family: 'Fraunces', Georgia, serif;
    font-size: 1.75rem; font-weight: 700; letter-spacing: -0.4px;
    color: {C['text']}; margin: 0;
}}
.page-sub {{ font-size: 0.9rem; color: {C['text_dim']}; margin: 0.35rem 0 0 0; }}

/* ── section header ── */
.sec {{
    display: flex; align-items: center; gap: 0.7rem;
    margin: 1.5rem 0 0.85rem 0;
}}
.sec-line {{ flex: 1; height: 1px; background: {C['line']}; }}
.sec-t {{
    font-size: 0.74rem; font-weight: 700; letter-spacing: 1.6px;
    text-transform: uppercase; color: {C['text_faint']}; white-space: nowrap;
}}

/* ── cards ── */
.card {{
    background: {C['card']};
    border: 1px solid {C['line']};
    border-radius: 16px;
    padding: 1.25rem 1.35rem;
}}
.card-hi {{ border-color: rgba(34,197,139,0.35); }}
.card-t {{ font-weight: 700; font-size: 0.98rem; color: {C['text']}; margin-bottom: 0.35rem; }}
.card-d {{ font-size: 0.85rem; color: {C['text_dim']}; line-height: 1.55; }}

/* ── metrics ── */
.metric {{
    background: {C['card']}; border: 1px solid {C['line']};
    border-radius: 14px; padding: 1.05rem 1.15rem;
    transition: border-color .18s ease, transform .18s ease;
}}
.metric:hover {{ border-color: rgba(34,197,139,0.45); transform: translateY(-2px); }}
.metric-label {{
    font-size: 0.7rem; font-weight: 600; letter-spacing: 1.2px;
    text-transform: uppercase; color: {C['text_faint']};
}}
.metric-value {{ font-size: 1.65rem; font-weight: 800; color: {C['text']}; margin-top: 0.3rem; letter-spacing: -0.5px; }}
.metric-note {{ font-size: 0.76rem; color: {C['text_dim']}; margin-top: 0.15rem; }}

/* ── score hero ── */
.score-hero {{
    background: {C['card']}; border: 1px solid {C['line']};
    border-radius: 16px; padding: 1.35rem 1.5rem;
}}
.score-big {{ font-size: 2.5rem; font-weight: 800; letter-spacing: -1px; line-height: 1; }}
.score-bar {{ background: {C['line']}; height: 8px; border-radius: 999px; overflow: hidden; margin-top: 0.8rem; }}
.score-fill {{ height: 8px; border-radius: 999px; }}
.t-good  {{ color: {C['accent']}; }}
.t-fair  {{ color: {C['amber']}; }}
.t-poor  {{ color: {C['red']}; }}
.f-good  {{ background: linear-gradient(90deg, #0E7A57, {C['accent']}); }}
.f-fair  {{ background: linear-gradient(90deg, #9C6F1D, {C['amber']}); }}
.f-poor  {{ background: linear-gradient(90deg, #8F2B30, {C['red']}); }}

/* ── inline svg icons ── */
.ic {{ color: {C['accent']}; display: inline-flex; align-items: center; }}
.hero-pill svg, .hero-kicker svg, .metric-label svg {{
    vertical-align: middle; margin-right: 3px;
}}

/* ── badges / pills ── */
.badge {{
    display: inline-flex; align-items: center; gap: 0.35rem;
    font-size: 0.72rem; font-weight: 700;
    padding: 0.22rem 0.65rem; border-radius: 999px;
    border: 1px solid {C['line']}; color: {C['text_dim']};
    background: {C['bg_soft']};
}}
.badge-ok    {{ color: {C['accent']}; border-color: rgba(34,197,139,0.45); background: {C['accent_dim']}; }}
.badge-warn  {{ color: {C['amber']};  border-color: rgba(232,179,57,0.4);  background: #2A2312; }}
.badge-bad   {{ color: {C['red']};    border-color: rgba(242,85,90,0.4);  background: #2A1517; }}
.badge-std   {{ color: {C['violet']}; border-color: rgba(167,139,250,0.4); background: #201A33; font-family: ui-monospace, monospace; font-size: 0.66rem; }}

/* ── alert cards ── */
.alert {{
    border-radius: 12px; padding: 0.85rem 1.05rem;
    font-size: 0.86rem; line-height: 1.55; margin-bottom: 0.6rem;
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
    border: 1px solid {C['line']}; border-radius: 12px; overflow: hidden;
}}

/* ── iucn chip ── */
.iucn {{ font-weight: 800; font-size: 0.74rem; letter-spacing: 0.6px; padding: 0.2rem 0.6rem; border-radius: 6px; color: #fff; }}

/* ── taxonomy strip ── */
.tax {{ text-align: center; padding: 0.55rem 0.2rem; background: {C['card']}; border: 1px solid {C['line']}; border-radius: 12px; }}
.tax-r {{ font-size: 0.62rem; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; color: {C['text_faint']}; }}
.tax-v {{ font-size: 0.8rem; color: {C['text']}; font-style: italic; margin-top: 0.1rem; }}

/* ── map legend dots ── */
.legend-dot {{
    display:inline-block; width:10px; height:10px;
    border-radius:50%; margin-right:4px; vertical-align:middle;
}}
.dot-green  {{ background: {C['accent']}; }}
.dot-red    {{ background: {C['red']}; }}
.dot-orange {{ background: {C['orange']}; }}

/* ── field label ── */
.field-label {{
    font-size: 0.74rem; font-weight: 700; letter-spacing: 1.2px;
    text-transform: uppercase; color: {C['text_faint']};
    margin: 0.4rem 0 0.2rem 0;
}}

/* ── footer ── */
.foot {{
    margin-top: 3rem; padding-top: 1.2rem; border-top: 1px solid {C['line']};
    font-size: 0.76rem; color: {C['text_faint']};
    display: flex; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;
}}

/* ── streamlit control restyle ── */
.stButton > button {{
    border-radius: 10px; font-weight: 600; border: 1px solid {C['line']};
    background: {C['card']}; color: {C['text']};
}}
.stButton > button:hover {{ border-color: {C['accent']}; color: {C['accent']}; }}
.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, #17A673, {C['accent']});
    border: none; color: #04140D;
}}
.stButton > button[kind="primary"]:hover {{
    filter: brightness(1.08); color: #04140D;
}}
.stDownloadButton > button {{
    border-radius: 10px; font-weight: 600;
    border: 1px solid rgba(34,197,139,0.4);
    background: {C['accent_dim']}; color: {C['accent']};
}}
.stDownloadButton > button:hover {{ border-color: {C['accent']}; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {C['line']}; }}
.stTabs [data-baseweb="tab"] {{
    border-radius: 9px 9px 0 0; padding: 0.5rem 1rem;
    color: {C['text_dim']}; font-weight: 600; font-size: 0.88rem;
}}
.stTabs [aria-selected="true"] {{
    background: {C['card']}; color: {C['text']};
    border: 1px solid {C['line']}; border-bottom: none;
}}
.stTabs [data-baseweb="tab-highlight"] {{ display: none; }}
.stTabs [data-baseweb="tab-border"] {{ display: none; }}
div[data-testid="stExpander"] {{
    border: 1px solid {C['line']} !important; border-radius: 12px !important;
    background: {C['card']};
}}
input, textarea, [data-baseweb="select"] > div {{
    background: {C['card']} !important;
}}

/* ── responsive ── */
@media (max-width: 768px) {{
    .hero {{ padding: 1.7rem 1.3rem; }}
    .hero-title {{ font-size: 1.9rem; }}
    .metric-value {{ font-size: 1.3rem; }}
    .score-big {{ font-size: 1.9rem; }}
    .page-title {{ font-size: 1.4rem; }}
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
        f' <span style="font-size:0.95rem;font-weight:600;color:{C["text_dim"]}">'
        f'{label_txt}</span></div>'
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
        f'<div class="foot"><span>BioSift — biodiversity data intelligence · '
        f'aligned with TDWG BDQ &amp; Darwin Core standards</span>'
        f'<span>Data: <a href="https://www.gbif.org" target="_blank">GBIF.org</a> '
        f'· CC-BY 4.0 sources</span></div>',
        unsafe_allow_html=True,
    )


# ── plotly theming ────────────────────────────────────────
def style_fig(fig, height=380, legend=True):
    """Apply BioSift look to any plotly figure and return it."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12, color=C["text_dim"]),
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
    fig.update_xaxes(gridcolor=C["line"], zerolinecolor=C["line"])
    fig.update_yaxes(gridcolor=C["line"], zerolinecolor=C["line"])
    return fig


def bar_fig(labels, values, title="", color=C["accent"], horizontal=False,
            height=380, text_auto=True):
    fig = go.Figure(
        go.Bar(
            x=values if horizontal else labels,
            y=labels if horizontal else values,
            orientation="h" if horizontal else "v",
            marker=dict(
                color=values if horizontal else [color] * len(values),
                colorscale="Viridis" if horizontal else None,
                line=dict(width=0),
            ),
            text=[f"{v:,}" for v in values] if text_auto else None,
            textposition="outside",
            textfont=dict(size=10, color=C["text_dim"]),
        )
    )
    fig.update_layout(title=title)
    return style_fig(fig, height=height, legend=False)
