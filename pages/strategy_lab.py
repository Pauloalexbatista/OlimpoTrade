"""
OlimpoTrade — Strategy Lab
UI de trader profissional com cockpit de análise, bot autónomo e hall of fame.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
import asyncio
import logging
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import ta

from lab_engine import (
    LabDatabase, LabBot, fetch_ohlcv, run_backtest_sync,
    score_result, build_config,
)

# ─────────────────────────────────────────────
# CONFIG DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Strategy Lab | OlimpoTrade",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# CSS — TEMA ESCURO PROFISSIONAL
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #07080f !important;
    color: #c9d1e0 !important;
    font-family: 'Inter', sans-serif;
}
[data-testid="stSidebar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }

/* Header */
.lab-header {
    background: linear-gradient(135deg, #0d0e1a 0%, #111327 100%);
    border-bottom: 1px solid #1e2240;
    padding: 18px 28px 14px;
    margin: -1rem -1rem 0;
    display: flex;
    align-items: center;
    gap: 20px;
}
.lab-logo { font-size: 26px; }
.lab-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 22px;
    font-weight: 700;
    color: #e8eaf6;
    letter-spacing: 1px;
}
.lab-subtitle { font-size: 12px; color: #5c6080; letter-spacing: 2px; text-transform: uppercase; }

/* Metric cards */
.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0; }
.metric-card {
    background: #0d0e1a;
    border: 1px solid #1a1d30;
    border-radius: 8px;
    padding: 14px 16px;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
}
.metric-card.green::before { background: #00e676; }
.metric-card.red::before   { background: #ff5252; }
.metric-card.blue::before  { background: #448aff; }
.metric-card.gold::before  { background: #ffd740; }
.metric-label { font-size: 10px; color: #5c6080; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 6px; }
.metric-value { font-family: 'JetBrains Mono', monospace; font-size: 22px; font-weight: 700; }
.metric-value.green { color: #00e676; }
.metric-value.red   { color: #ff5252; }
.metric-value.blue  { color: #448aff; }
.metric-value.gold  { color: #ffd740; }
.metric-sub { font-size: 11px; color: #5c6080; margin-top: 4px; }

/* Metric row for 6+ items */
.metric-row { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0; }
.metric-chip {
    background: #0d0e1a;
    border: 1px solid #1a1d30;
    border-radius: 6px;
    padding: 8px 14px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
}
.chip-label { font-size: 10px; color: #5c6080; text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 2px; }

/* Panel */
.panel {
    background: #0d0e1a;
    border: 1px solid #1a1d30;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 10px;
}
.panel-title {
    font-size: 11px;
    color: #448aff;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 12px;
    font-weight: 600;
}

/* Bot status */
.bot-status {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    background: #0d0e1a;
    border: 1px solid #1a1d30;
    border-radius: 8px;
    margin-bottom: 12px;
}
.dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.dot.green { background: #00e676; box-shadow: 0 0 8px #00e676; animation: pulse 1.4s infinite; }
.dot.red   { background: #ff5252; }
.dot.grey  { background: #3a3d52; }
@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }

/* Hall of Fame table */
.hof-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.hof-table th {
    background: #0d0e1a;
    border-bottom: 2px solid #1e2240;
    padding: 10px 12px;
    text-align: left;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #448aff;
}
.hof-table td {
    border-bottom: 1px solid #11131f;
    padding: 9px 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: #c9d1e0;
}
.hof-table tr:hover td { background: #0f1020; }
.rank-badge {
    width: 24px; height: 24px; border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700;
}
.rank-1 { background: #ffd740; color: #0a0a0f; }
.rank-2 { background: #b0bec5; color: #0a0a0f; }
.rank-3 { background: #c88b3a; color: #0a0a0f; }
.rank-n { background: #1a1d30; color: #6b7190; }

/* Tabs */
[data-testid="stTabs"] [role="tablist"] {
    background: #0d0e1a;
    border-bottom: 1px solid #1a1d30;
    padding: 0 16px;
    gap: 0;
}
[data-testid="stTabs"] [role="tab"] {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    color: #5c6080 !important;
    padding: 12px 20px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    letter-spacing: 0.5px !important;
    margin-bottom: -1px !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    border-bottom-color: #448aff !important;
    color: #e8eaf6 !important;
}

/* ══ STREAMLIT WIDGET OVERRIDES — TEMA ESCURO COMPLETO ══ */

/* Fundo geral das páginas e conteúdo */
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section.main > div,
.block-container {
    background: #07080f !important;
    color: #c9d1e0 !important;
}

/* Labels de todos os widgets */
label, .stSelectbox label, .stMultiSelect label,
.stSlider label, .stNumberInput label,
.stCheckbox label, .stRadio label,
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] span {
    color: #8a91b0 !important;
    font-size: 12px !important;
}

/* Selectbox — caixa principal */
div[data-testid="stSelectbox"] > div > div,
div[data-testid="stSelectbox"] > div > div > div {
    background: #0d0e1a !important;
    border: 1px solid #1e2240 !important;
    border-radius: 6px !important;
    color: #c9d1e0 !important;
}
div[data-testid="stSelectbox"] > div > div > div > div,
div[data-testid="stSelectbox"] span {
    color: #c9d1e0 !important;
}
/* Dropdown popup (lista de opções) */
div[data-baseweb="popover"],
div[data-baseweb="menu"],
ul[data-testid="stSelectboxVirtualDropdown"],
[data-testid="stSelectboxVirtualDropdown"] {
    background: #0f1020 !important;
    border: 1px solid #1e2240 !important;
    border-radius: 6px !important;
}
[data-testid="stSelectboxVirtualDropdown"] li,
div[data-baseweb="menu"] li,
div[role="option"] {
    background: #0f1020 !important;
    color: #c9d1e0 !important;
}
[data-testid="stSelectboxVirtualDropdown"] li:hover,
div[role="option"]:hover,
div[role="option"][aria-selected="true"] {
    background: #1a1d30 !important;
    color: #ffffff !important;
}

/* Multiselect */
div[data-testid="stMultiSelect"] > div > div {
    background: #0d0e1a !important;
    border: 1px solid #1e2240 !important;
    color: #c9d1e0 !important;
}
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
    background: #1a237e !important;
    color: #90caf9 !important;
}

/* Number input */
.stNumberInput input,
.stTextInput input,
input[type="number"],
input[type="text"] {
    background: #0d0e1a !important;
    border: 1px solid #1e2240 !important;
    border-radius: 6px !important;
    color: #c9d1e0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
}
.stNumberInput input:focus,
.stTextInput input:focus {
    border-color: #448aff !important;
    outline: none !important;
    box-shadow: 0 0 0 2px rgba(68,138,255,0.2) !important;
}

/* Slider */
.stSlider [data-testid="stThumbValue"],
.stSlider div[data-testid="stTickBarMin"],
.stSlider div[data-testid="stTickBarMax"] {
    color: #8a91b0 !important;
    font-size: 11px !important;
}
.stSlider [data-baseweb="slider"] div[role="slider"] {
    background: #448aff !important;
    border-color: #448aff !important;
}

/* Checkbox */
.stCheckbox label p,
.stCheckbox label span {
    color: #c9d1e0 !important;
}
.stCheckbox input[type="checkbox"] + div {
    background: #0d0e1a !important;
    border-color: #1e2240 !important;
}
.stCheckbox input[type="checkbox"]:checked + div {
    background: #448aff !important;
    border-color: #448aff !important;
}

/* Radio */
.stRadio label p { color: #c9d1e0 !important; }
div[data-testid="stRadio"] div[role="radiogroup"] label {
    color: #c9d1e0 !important;
}

/* Expander */
details summary p,
[data-testid="stExpander"] summary p {
    color: #8a91b0 !important;
}
[data-testid="stExpander"] {
    background: #0d0e1a !important;
    border: 1px solid #1a1d30 !important;
    border-radius: 6px !important;
}

/* Progress bar */
[data-testid="stProgress"] > div > div {
    background: #1a1d30 !important;
}
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, #2962ff, #00b0ff) !important;
}

/* Success / Warning / Error messages */
[data-testid="stAlert"] {
    background: #0d0e1a !important;
    border-radius: 6px !important;
    color: #c9d1e0 !important;
}

/* Buttons */
button[kind="primary"], .stButton button[kind="primary"] {
    background: linear-gradient(135deg, #2962ff, #1565c0) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    border-radius: 6px !important;
}
button[kind="secondary"], .stButton button[kind="secondary"] {
    background: #0d0e1a !important;
    border: 1px solid #1e2240 !important;
    color: #c9d1e0 !important;
    border-radius: 6px !important;
}
button[kind="secondary"]:hover {
    border-color: #448aff !important;
    color: #ffffff !important;
}

/* Divider */
hr { border-color: #1a1d30 !important; }

/* Tabs */
[data-testid="stTabs"] [role="tablist"] {
    background: #0d0e1a;
    border-bottom: 1px solid #1a1d30;
    padding: 0 16px;
    gap: 0;
}
[data-testid="stTabs"] [role="tab"] {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    color: #5c6080 !important;
    padding: 12px 20px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    letter-spacing: 0.5px !important;
    margin-bottom: -1px !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    border-bottom-color: #448aff !important;
    color: #e8eaf6 !important;
}
[data-testid="stTabsContent"] {
    background: #07080f !important;
    padding-top: 16px !important;
}

/* Spinner */
.stSpinner p { color: #8a91b0 !important; }

/* Dataframe / Table */
[data-testid="stDataFrame"] {
    background: #0d0e1a !important;
}
[data-testid="stDataFrame"] th {
    background: #0a0b14 !important;
    color: #448aff !important;
}
[data-testid="stDataFrame"] td {
    background: #0d0e1a !important;
    color: #c9d1e0 !important;
}

/* Texto genérico */
p, span, div, li {
    color: inherit;
}
h1, h2, h3, h4 { color: #e8eaf6 !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "lab_db" not in st.session_state:
    st.session_state.lab_db = LabDatabase()
if "lab_bot" not in st.session_state:
    st.session_state.lab_bot = LabBot(st.session_state.lab_db)
if "cockpit_result" not in st.session_state:
    st.session_state.cockpit_result = None
if "cockpit_df" not in st.session_state:
    st.session_state.cockpit_df = None
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0

db: LabDatabase = st.session_state.lab_db
bot: LabBot = st.session_state.lab_bot


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

STRATEGY_LABELS = {
    "SMA_CROSSOVER":    "SMA Crossover — Cruzamento de Médias Simples",
    "EMA_CROSSOVER":    "EMA Crossover — Cruzamento de Médias Exponenciais",
    "PAULO_GOLD":       "⭐ Paulo Gold — Breakout por Cruzamento de Linha",
    "MULTIPOINT_VECTOR":"Vetor 5 Pontos — Alinhamento de 4-5 Médias",
    "QUANTUM_CONSENSUS":"Quantum Consensus — DNA de Consenso Estatístico",
}
STRATEGY_LABELS_SHORT = {
    "SMA_CROSSOVER":    "SMA Crossover",
    "EMA_CROSSOVER":    "EMA Crossover",
    "PAULO_GOLD":       "Paulo Gold",
    "MULTIPOINT_VECTOR":"Vetor 5 Pontos",
    "QUANTUM_CONSENSUS":"Quantum Consensus",
}

PAIRS = ["BTC/USDT","ETH/USDT","BNB/USDT","SOL/USDT","XRP/USDT",
         "ADA/USDT","AVAX/USDT","DOGE/USDT","MATIC/USDT","DOT/USDT"]
TIMEFRAMES = ["15m","30m","1h","2h","4h","8h","1d"]
PERIODS = {"1 Mês": 30, "3 Meses": 90, "6 Meses": 180,
           "1 Ano": 365, "2 Anos": 730}


def fmt_pct(v, decimals=2):
    if v is None: return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.{decimals}f}%"

def fmt_num(v, decimals=2):
    if v is None: return "—"
    return f"{v:.{decimals}f}"

def color_class(v, good_positive=True):
    if v is None or v == 0: return "blue"
    return ("green" if v > 0 else "red") if good_positive else ("red" if v > 0 else "green")


def add_indicators(fig, df, strategy_type, params, row=1):
    """Adiciona indicadores ao gráfico conforme a estratégia."""
    colors = ["#448aff", "#ff9100", "#00e676", "#e040fb", "#ffd740"]

    if strategy_type in ("SMA_CROSSOVER", "PAULO_GOLD"):
        sw = params.get("short_window", 9)
        lw = params.get("long_window", 21)
        s1 = ta.trend.sma_indicator(df["close"], window=sw)
        s2 = ta.trend.sma_indicator(df["close"], window=lw)
        fig.add_trace(go.Scatter(x=df.index, y=s1, name=f"SMA{sw}", line=dict(color=colors[0], width=1.4), hoverinfo="skip"), row=row, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=s2, name=f"SMA{lw}", line=dict(color=colors[1], width=1.4), hoverinfo="skip"), row=row, col=1)

    elif strategy_type == "EMA_CROSSOVER":
        sw = params.get("short_window", 9)
        lw = params.get("long_window", 21)
        e1 = ta.trend.ema_indicator(df["close"], window=sw)
        e2 = ta.trend.ema_indicator(df["close"], window=lw)
        fig.add_trace(go.Scatter(x=df.index, y=e1, name=f"EMA{sw}", line=dict(color=colors[0], width=1.4), hoverinfo="skip"), row=row, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=e2, name=f"EMA{lw}", line=dict(color=colors[1], width=1.4), hoverinfo="skip"), row=row, col=1)

    elif strategy_type == "MULTIPOINT_VECTOR":
        windows = [
            params.get("p2_window", 9),
            params.get("p3_window", 21),
            params.get("p4_window", 50),
            params.get("p5_window", 200),
        ]
        labels = ["P2", "P3", "P4", "P5"]
        for i, (w, lbl) in enumerate(zip(windows, labels)):
            s = ta.trend.sma_indicator(df["close"], window=w)
            fig.add_trace(go.Scatter(x=df.index, y=s, name=f"{lbl}({w})", line=dict(color=colors[i], width=1.2), hoverinfo="skip"), row=row, col=1)

    elif strategy_type == "QUANTUM_CONSENSUS":
        for i, w in enumerate([5, 13, 21, 55, 144]):
            s = ta.trend.sma_indicator(df["close"], window=w)
            fig.add_trace(go.Scatter(x=df.index, y=s, name=f"S{w}", line=dict(color=colors[i % 5], width=1.1), hoverinfo="skip"), row=row, col=1)


def build_chart(df, trades, cap_hist, strategy_type, params):
    """Gráfico profissional: candlestick + indicadores + trades + volume + equity."""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.58, 0.14, 0.28],
        vertical_spacing=0.025,
        subplot_titles=["", "", ""],
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="Preço",
        increasing_line_color="#00e676", increasing_fillcolor="#00c853",
        decreasing_line_color="#ff5252", decreasing_fillcolor="#c62828",
        line=dict(width=1),
    ), row=1, col=1)

    # Indicadores
    add_indicators(fig, df, strategy_type, params, row=1)

    # Marcadores de trades
    if trades:
        buy_x = [t["entry_timestamp"] for t in trades]
        buy_y = [t["entry_price"] * 0.998 for t in trades]
        sell_x = [t["exit_timestamp"] for t in trades]
        sell_y = [t["exit_price"] * 1.002 for t in trades]

        fig.add_trace(go.Scatter(
            x=buy_x, y=buy_y, mode="markers", name="Compra",
            marker=dict(symbol="triangle-up", color="#00e676", size=10,
                        line=dict(width=1, color="#007700")),
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=sell_x, y=sell_y, mode="markers", name="Venda",
            marker=dict(symbol="triangle-down", color="#ff5252", size=10,
                        line=dict(width=1, color="#770000")),
        ), row=1, col=1)

    # Volume
    vol_colors = ["#00c853" if c >= o else "#c62828"
                  for c, o in zip(df["close"], df["open"])]
    fig.add_trace(go.Bar(
        x=df.index, y=df["volume"], name="Volume",
        marker_color=vol_colors, opacity=0.6, showlegend=False,
    ), row=2, col=1)

    # Equity curve
    if cap_hist and len(cap_hist) > 1:
        initial = cap_hist[0]
        eq_colors = ["#00e676" if v >= initial else "#ff5252" for v in cap_hist]
        fig.add_trace(go.Scatter(
            x=df.index[:len(cap_hist)], y=cap_hist,
            name="Equity",
            line=dict(color="#448aff", width=1.8),
            fill="tonexty",
            fillcolor="rgba(68,138,255,0.06)",
        ), row=3, col=1)
        # Linha base
        fig.add_hline(y=initial, line=dict(color="#3a3d52", width=1, dash="dot"), row=3, col=1)

    # Layout escuro
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#07080f",
        plot_bgcolor="#0a0b14",
        margin=dict(l=0, r=0, t=8, b=0),
        height=620,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            bgcolor="rgba(0,0,0,0)", font=dict(size=11, color="#8a91b0"),
        ),
        xaxis_rangeslider_visible=False,
        font=dict(family="JetBrains Mono", color="#6b7190", size=11),
    )
    for i in range(1, 4):
        fig.update_xaxes(
            gridcolor="#0f1020", zerolinecolor="#1a1d30",
            showgrid=True, row=i, col=1,
        )
        fig.update_yaxes(
            gridcolor="#0f1020", zerolinecolor="#1a1d30",
            showgrid=True, row=i, col=1,
        )

    return fig


def metrics_html(metrics, buy_hold_return=None):
    ret = metrics["total_return_pct"]
    dd  = metrics["max_drawdown_pct"]
    wr  = metrics["win_rate"] * 100
    sh  = metrics.get("sharpe_ratio", 0.0)
    pf  = metrics.get("profit_factor", 1.0)
    n   = metrics["num_trades"]
    fc  = metrics["final_capital"]
    ic  = metrics["initial_capital"]

    ret_cls = "green" if ret > 0 else "red"
    dd_cls  = "red"
    sh_cls  = "green" if sh > 1 else ("gold" if sh > 0 else "red")
    wr_cls  = "green" if wr >= 50 else "red"

    bh_html = ""
    if buy_hold_return is not None:
        edge = ret - buy_hold_return
        edge_cls = "green" if edge > 0 else "red"
        bh_html = f"""
        <div class="metric-card {edge_cls}">
            <div class="metric-label">Edge vs B&H</div>
            <div class="metric-value {edge_cls}">{fmt_pct(edge)}</div>
            <div class="metric-sub">B&H: {fmt_pct(buy_hold_return)}</div>
        </div>"""

    return f"""
<div class="metric-grid">
    <div class="metric-card {ret_cls}">
        <div class="metric-label">Retorno Total</div>
        <div class="metric-value {ret_cls}">{fmt_pct(ret)}</div>
        <div class="metric-sub">{fmt_num(ic)} → {fmt_num(fc)} USDT</div>
    </div>
    <div class="metric-card {dd_cls}">
        <div class="metric-label">Max Drawdown</div>
        <div class="metric-value {dd_cls}">{fmt_pct(dd)}</div>
        <div class="metric-sub">{n} trades</div>
    </div>
    <div class="metric-card {sh_cls}">
        <div class="metric-label">Sharpe Ratio</div>
        <div class="metric-value {sh_cls}">{fmt_num(sh)}</div>
        <div class="metric-sub">Sortino: {fmt_num(metrics.get('sortino_ratio', 0.0))}</div>
    </div>
    <div class="metric-card {wr_cls}">
        <div class="metric-label">Win Rate</div>
        <div class="metric-value {wr_cls}">{fmt_pct(wr, 1)}</div>
        <div class="metric-sub">Profit Factor: {fmt_num(pf)}</div>
    </div>
    {bh_html}
</div>"""


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class="lab-header">
    <div class="lab-logo">🔬</div>
    <div>
        <div class="lab-title">STRATEGY LAB</div>
        <div class="lab-subtitle">OlimpoTrade · Optimização de Estratégias</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab_cockpit, tab_bot, tab_hof = st.tabs([
    "⚡ Cockpit — Análise Manual",
    "🤖 Bot Autónomo — Optimização",
    "🏆 Hall of Fame — Melhores Resultados",
])


# ═══════════════════════════════════════════════
# TAB 1 — COCKPIT
# ═══════════════════════════════════════════════
with tab_cockpit:
    col_cfg, col_chart = st.columns([1, 3], gap="medium")

    with col_cfg:
        st.markdown('<div class="panel-title">⚙ Configuração</div>', unsafe_allow_html=True)

        symbol_c   = st.selectbox("Par", PAIRS, key="c_symbol")
        tf_c       = st.selectbox("Timeframe", TIMEFRAMES, index=2, key="c_tf")
        period_lbl = st.selectbox("Período", list(PERIODS.keys()), index=2, key="c_period")
        period_c   = PERIODS[period_lbl]

        st.divider()
        st.markdown('<div class="panel-title">📐 Estratégia</div>', unsafe_allow_html=True)

        strategy_c = st.selectbox(
            "Estratégia",
            list(STRATEGY_LABELS.keys()),
            format_func=lambda k: STRATEGY_LABELS[k],
            key="c_strategy",
        )

        params_c = {}
        if strategy_c in ("SMA_CROSSOVER", "EMA_CROSSOVER", "PAULO_GOLD"):
            params_c["short_window"] = st.slider("Média Rápida", 3, 50, 9, key="c_sw")
            params_c["long_window"]  = st.slider("Média Lenta",  10, 200, 21, key="c_lw")
            if strategy_c == "PAULO_GOLD":
                params_c["trend_filter"] = st.checkbox("Filtro de Tendência", value=False, key="c_tf2")

        elif strategy_c == "MULTIPOINT_VECTOR":
            params_c["p2_window"] = st.slider("P2 (Rápida)", 3, 30, 9, key="c_p2")
            params_c["p3_window"] = st.slider("P3 (Curta)",  10, 60, 21, key="c_p3")
            params_c["p4_window"] = st.slider("P4 (Média)",  30, 150, 50, key="c_p4")
            params_c["p5_window"] = st.slider("P5 (Longa)",  100, 300, 200, key="c_p5")
            params_c["multipoint_mode"] = st.radio("Modo", ["AGILE","CONSERVATIVE"], horizontal=True, key="c_mode")

        st.divider()
        st.markdown('<div class="panel-title">🛡 Gestão de Risco</div>', unsafe_allow_html=True)

        params_c["stop_loss_pct"]   = st.slider("Stop Loss (%)", 0.5, 10.0, 2.0, 0.5, key="c_sl")
        params_c["take_profit_pct"] = st.slider("Take Profit (%)", 1.0, 30.0, 5.0, 0.5, key="c_tp")
        params_c["risk_pct"]        = st.slider("Risco/Trade (%)", 1.0, 50.0, 10.0, 1.0, key="c_rsk")
        params_c["trailing_stop"]   = st.checkbox("Trailing Stop", value=False, key="c_ts")

        st.divider()
        st.markdown('<div class="panel-title">💰 Capital & Custos</div>', unsafe_allow_html=True)

        initial_cap_c = st.number_input("Capital Inicial (USDT)", 100.0, 1_000_000.0, 1000.0, 100.0, key="c_cap")
        fee_c         = st.number_input("Fee (%)", 0.0, 1.0, 0.04, 0.01, key="c_fee",
                                        format="%.3f", help="Binance Futures: 0.04%")
        slip_c        = st.number_input("Slippage (%)", 0.0, 1.0, 0.05, 0.01, key="c_slip",
                                        format="%.3f")

        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("▶  CORRER BACKTEST", type="primary", use_container_width=True, key="c_run")

    with col_chart:
        if run_btn:
            with st.spinner("A carregar dados e a correr análise..."):
                try:
                    df_raw = fetch_ohlcv(symbol_c, tf_c, days=period_c)
                    if df_raw is None or df_raw.empty:
                        st.error("Não foi possível obter dados. Verifica a ligação.")
                    else:
                        _, trades_c, cap_hist_c, metrics_c = run_backtest_sync(
                            strategy_c, params_c, df_raw, symbol_c, tf_c,
                            fee_c, slip_c, initial_cap_c,
                        )
                        bh_return = (df_raw["close"].iloc[-1] / df_raw["close"].iloc[0] - 1) * 100
                        st.session_state.cockpit_result = {
                            "df": df_raw, "trades": trades_c,
                            "cap_hist": cap_hist_c, "metrics": metrics_c,
                            "bh_return": bh_return,
                            "strategy_type": strategy_c, "params": params_c,
                        }
                except Exception as e:
                    st.error(f"Erro: {e}")

        res = st.session_state.cockpit_result

        if res is None:
            st.markdown("""
<div style="display:flex; flex-direction:column; align-items:center; justify-content:center;
            height:500px; color:#3a3d52; text-align:center;">
    <div style="font-size:60px; margin-bottom:16px;">📊</div>
    <div style="font-size:18px; font-weight:600; margin-bottom:8px; color:#4a4f6a;">
        Configura e corre o backtest
    </div>
    <div style="font-size:13px; color:#2d3148;">
        Define a estratégia no painel esquerdo e clica em CORRER BACKTEST
    </div>
</div>""", unsafe_allow_html=True)
        else:
            # Métricas
            st.markdown(
                metrics_html(res["metrics"], res.get("bh_return")),
                unsafe_allow_html=True,
            )

            # Score
            s = score_result(res["metrics"])
            score_color = "#00e676" if s > 20 else ("#ffd740" if s > 0 else "#ff5252")
            st.markdown(
                f'<div style="text-align:right; font-family:\'JetBrains Mono\'; font-size:12px; color:{score_color}; margin:-6px 0 8px;">SCORE: {s}</div>',
                unsafe_allow_html=True,
            )

            # Gráfico
            fig = build_chart(
                res["df"], res["trades"], res["cap_hist"],
                res["strategy_type"], res["params"],
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            # Tabela de trades
            if res["trades"]:
                with st.expander(f"📋 Tabela de Trades ({len(res['trades'])} operações)"):
                    df_trades = pd.DataFrame(res["trades"])
                    cols = ["entry_timestamp","exit_timestamp","entry_price","exit_price","pnl","pnl_pct","reason"]
                    cols = [c for c in cols if c in df_trades.columns]
                    df_show = df_trades[cols].copy()
                    df_show.columns = ["Entrada","Saída","Preço Entrada","Preço Saída","PnL","PnL%","Motivo"]

                    def style_pnl(v):
                        if isinstance(v, (int, float)):
                            return "color: #00e676" if v > 0 else "color: #ff5252"
                        return ""

                    styled = df_show.style.applymap(style_pnl, subset=["PnL", "PnL%"])
                    st.dataframe(styled, use_container_width=True, hide_index=True)

            # Botão salvar
            s_val = score_result(res["metrics"])
            if s_val > 0:
                if st.button("💾  Guardar no Hall of Fame", key="c_save"):
                    db.save_result({
                        "strategy":         res["strategy_type"],
                        "params":           res["params"],
                        "symbol":           symbol_c,
                        "timeframe":        tf_c,
                        "period_days":      period_c,
                        "score":            s_val,
                        "total_return_pct": res["metrics"]["total_return_pct"],
                        "max_drawdown_pct": res["metrics"]["max_drawdown_pct"],
                        "sharpe_ratio":     res["metrics"].get("sharpe_ratio", 0.0),
                        "sortino_ratio":    res["metrics"].get("sortino_ratio", 0.0),
                        "win_rate":         res["metrics"]["win_rate"],
                        "num_trades":       res["metrics"]["num_trades"],
                        "profit_factor":    res["metrics"].get("profit_factor", 1.0),
                        "initial_capital":  initial_cap_c,
                        "final_capital":    res["metrics"]["final_capital"],
                        "fee_pct":          fee_c,
                        "slippage_pct":     slip_c,
                    })
                    st.success("Guardado no Hall of Fame!")


# ═══════════════════════════════════════════════
# TAB 2 — BOT AUTÓNOMO
# ═══════════════════════════════════════════════
with tab_bot:
    col_b1, col_b2 = st.columns([1, 2], gap="medium")

    with col_b1:
        st.markdown('<div class="panel-title">🤖 Configuração do Bot</div>', unsafe_allow_html=True)

        b_symbol    = st.selectbox("Par", PAIRS, key="b_sym")
        b_tf        = st.selectbox("Timeframe", TIMEFRAMES, index=2, key="b_tf")
        b_period_lbl= st.selectbox("Período de Dados", list(PERIODS.keys()), index=2, key="b_period")
        b_period    = PERIODS[b_period_lbl]

        st.markdown("**Estratégias a Testar**")
        b_strats = []
        for k, lbl in STRATEGY_LABELS.items():
            if k == "QUANTUM_CONSENSUS":
                continue
            if st.checkbox(lbl, value=(k in ["SMA_CROSSOVER","PAULO_GOLD"]), key=f"bs_{k}"):
                b_strats.append(k)

        st.divider()
        b_cap     = st.number_input("Capital (USDT)", 100.0, 100_000.0, 1000.0, 100.0, key="b_cap")
        b_fee     = st.number_input("Fee (%)", 0.0, 1.0, 0.04, 0.01, format="%.3f", key="b_fee")
        b_slip    = st.number_input("Slippage (%)", 0.0, 1.0, 0.05, 0.01, format="%.3f", key="b_slip")
        b_minscore= st.slider("Score Mínimo para Guardar", -50, 100, 5, key="b_minscore",
                              help="Só guarda resultados acima deste score")

        st.markdown("<br>", unsafe_allow_html=True)

        running = bot.is_running()
        if not running:
            if st.button("▶  INICIAR BOT", type="primary", use_container_width=True, key="b_start"):
                if not b_strats:
                    st.warning("Selecciona pelo menos uma estratégia.")
                else:
                    bot.start(b_strats, b_symbol, b_tf, b_period,
                              b_fee, b_slip, b_cap, b_minscore)
                    st.rerun()
        else:
            if st.button("⏹  PARAR BOT", type="secondary", use_container_width=True, key="b_stop"):
                bot.stop()
                st.rerun()

    with col_b2:
        p = bot.progress
        running = bot.is_running()

        # Status
        dot_cls = "green" if running else ("red" if p["done"] > 0 else "grey")
        status_txt = "A CORRER" if running else ("CONCLUÍDO" if p["done"] > 0 else "INACTIVO")
        st.markdown(f"""
<div class="bot-status">
    <div class="dot {dot_cls}"></div>
    <div>
        <strong style="color:#e8eaf6; font-size:14px;">{status_txt}</strong>
        {"<br><small style='color:#5c6080; font-size:11px;'>Par: " + p.get("current_strategy","") + " | " + str(p.get("current_params","")) + "</small>" if running else ""}
    </div>
</div>""", unsafe_allow_html=True)

        # Progress bar
        total = p["total"] or 1
        done  = p["done"]
        pct   = done / total
        st.progress(pct, text=f"{done}/{total} testes  ·  {pct*100:.1f}%")

        # Stats row
        eta_txt = ""
        if running and p.get("eta_secs"):
            m, s2 = divmod(p["eta_secs"], 60)
            eta_txt = f"  ·  ETA {m}m {s2}s"

        elapsed = ""
        if p.get("start_time"):
            e = int(time.time() - p["start_time"])
            em, es = divmod(e, 60)
            elapsed = f"{em}m {es}s"

        st.markdown(f"""
<div class="metric-row">
    <div class="metric-chip"><span class="chip-label">Guardados</span><span style="color:#00e676;">{p['saved']}</span></div>
    <div class="metric-chip"><span class="chip-label">Erros</span><span style="color:#ff5252;">{p['errors']}</span></div>
    <div class="metric-chip"><span class="chip-label">Melhor Score</span><span style="color:#ffd740;">{p['best_score'] if p['best_score'] > -900 else '—'}</span></div>
    <div class="metric-chip"><span class="chip-label">Tempo</span><span style="color:#448aff;">{elapsed or '—'}</span></div>
</div>""", unsafe_allow_html=True)

        # Melhor resultado encontrado
        if p["best_result"]:
            br = p["best_result"]
            ret_cls = "green" if br["total_return_pct"] > 0 else "red"
            st.markdown(f"""
<div class="panel" style="border-color:#ffd740; margin-top:12px;">
    <div class="panel-title" style="color:#ffd740;">🥇 Melhor Resultado Até Agora</div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-family:'JetBrains Mono'; font-size:13px;">
        <div><span style="color:#5c6080;">Estratégia</span><br><strong>{STRATEGY_LABELS_SHORT.get(br['strategy'], br['strategy'])}</strong></div>
        <div><span style="color:#5c6080;">Score</span><br><strong style="color:#ffd740; font-size:18px;">{br['score']}</strong></div>
        <div><span style="color:#5c6080;">Retorno</span><br><strong style="color:{'#00e676' if br['total_return_pct']>0 else '#ff5252'};">{fmt_pct(br['total_return_pct'])}</strong></div>
        <div><span style="color:#5c6080;">Drawdown</span><br><strong style="color:#ff5252;">{fmt_pct(br['max_drawdown_pct'])}</strong></div>
        <div><span style="color:#5c6080;">Sharpe</span><br><strong style="color:#448aff;">{fmt_num(br['sharpe_ratio'])}</strong></div>
        <div><span style="color:#5c6080;">Win Rate</span><br><strong>{fmt_pct(br['win_rate']*100, 1)}</strong></div>
    </div>
    <div style="margin-top:10px; font-size:11px; color:#5c6080;">
        Params: {json.dumps(br['params'], ensure_ascii=False)}
    </div>
</div>""", unsafe_allow_html=True)

        # Último resultado
        if p["last_result"] and running:
            lr = p["last_result"]
            col_lr = "#00e676" if lr["total_return_pct"] > 0 else "#3a3d52"
            st.markdown(f"""
<div style="font-size:11px; color:#5c6080; font-family:'JetBrains Mono'; margin-top:8px;">
    Último: {STRATEGY_LABELS_SHORT.get(lr['strategy'],lr['strategy'])} |
    Ret: <span style="color:{col_lr};">{fmt_pct(lr['total_return_pct'])}</span> |
    Score: {lr['score']} |
    Trades: {lr['num_trades']}
</div>""", unsafe_allow_html=True)

        # Auto-refresh quando bot está a correr
        if running:
            time.sleep(1.5)
            st.rerun()


# ═══════════════════════════════════════════════
# TAB 3 — HALL OF FAME
# ═══════════════════════════════════════════════
with tab_hof:
    total_saved = db.count_results()
    st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
    <div>
        <span style="font-family:'JetBrains Mono'; font-size:20px; color:#ffd740;">🏆 Hall of Fame</span>
        <span style="font-size:12px; color:#5c6080; margin-left:12px;">{total_saved} resultados guardados</span>
    </div>
</div>""", unsafe_allow_html=True)

    # Filtros
    hf_col1, hf_col2, hf_col3, hf_col4 = st.columns([2, 2, 1, 1])
    with hf_col1:
        hf_strat = st.selectbox("Estratégia", ["Todas"] + list(STRATEGY_LABELS.keys()),
                                format_func=lambda k: "Todas" if k == "Todas" else STRATEGY_LABELS_SHORT[k],
                                key="hf_strat")
    with hf_col2:
        hf_sym = st.selectbox("Par", ["Todos"] + PAIRS, key="hf_sym")
    with hf_col3:
        hf_limit = st.selectbox("Mostrar", [25, 50, 100, 200], key="hf_limit")
    with hf_col4:
        st.markdown("<br>", unsafe_allow_html=True)
        hf_refresh = st.button("🔄 Actualizar", use_container_width=True, key="hf_refresh")

    results = db.get_top_results(
        limit=hf_limit,
        strategy=hf_strat if hf_strat != "Todas" else None,
        symbol=hf_sym if hf_sym != "Todos" else None,
    )

    if not results:
        st.markdown("""
<div style="text-align:center; padding:60px; color:#3a3d52;">
    <div style="font-size:48px; margin-bottom:12px;">🏺</div>
    <div style="font-size:16px; color:#4a4f6a;">Ainda não há resultados guardados.</div>
    <div style="font-size:13px; margin-top:6px;">Corre o Bot Autónomo ou guarda resultados do Cockpit.</div>
</div>""", unsafe_allow_html=True)
    else:
        # Cabeçalho tabela
        rows_html = ""
        for i, r in enumerate(results):
            rank = i + 1
            if rank == 1:
                badge = '<span class="rank-badge rank-1">1</span>'
            elif rank == 2:
                badge = '<span class="rank-badge rank-2">2</span>'
            elif rank == 3:
                badge = '<span class="rank-badge rank-3">3</span>'
            else:
                badge = f'<span class="rank-badge rank-n">{rank}</span>'

            ret_color  = "#00e676" if r["total_return_pct"] > 0 else "#ff5252"
            sh_color   = "#00e676" if r["sharpe_ratio"] > 1 else ("#ffd740" if r["sharpe_ratio"] > 0 else "#ff5252")
            score_color= "#ffd740" if r["score"] > 30 else ("#00e676" if r["score"] > 10 else "#c9d1e0")

            try:
                params_obj = json.loads(r["params"]) if isinstance(r["params"], str) else r["params"]
                params_short = ", ".join(f"{k}={v}" for k, v in list(params_obj.items())[:3])
            except Exception:
                params_short = str(r["params"])[:50]

            ts = r["timestamp"][:10] if r.get("timestamp") else "—"

            rows_html += f"""
<tr>
    <td>{badge}</td>
    <td><strong style="color:#e8eaf6;">{STRATEGY_LABELS_SHORT.get(r['strategy'], r['strategy'])}</strong><br>
        <small style="color:#4a4f6a; font-size:10px;">{params_short}</small></td>
    <td>{r['symbol']}</td>
    <td>{r['timeframe']}</td>
    <td style="color:{score_color}; font-weight:700; font-size:15px;">{r['score']}</td>
    <td style="color:{ret_color}; font-weight:600;">{fmt_pct(r['total_return_pct'])}</td>
    <td style="color:#ff5252;">{fmt_pct(r['max_drawdown_pct'])}</td>
    <td style="color:{sh_color};">{fmt_num(r['sharpe_ratio'])}</td>
    <td>{fmt_pct(r['win_rate']*100, 1)}</td>
    <td>{r['num_trades']}</td>
    <td style="color:#5c6080; font-size:11px;">{ts}</td>
</tr>"""

        st.markdown(f"""
<div style="overflow-x:auto;">
<table class="hof-table">
<thead>
<tr>
    <th>#</th><th>Estratégia / Params</th><th>Par</th><th>TF</th>
    <th>Score</th><th>Retorno</th><th>Drawdown</th>
    <th>Sharpe</th><th>Win%</th><th>Trades</th><th>Data</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
</div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Botões de limpeza
        with st.expander("⚙ Gestão de Dados"):
            st.warning("Atenção: estas acções são irreversíveis.")
            if st.button("🗑  Limpar TODOS os Resultados", type="secondary", key="hf_clear"):
                db.clear_all()
                st.success("Base de dados limpa.")
                st.rerun()
