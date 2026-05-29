# my_trading_bot/app_ui.py
import json
import datetime
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import asyncio
import ta
import logging
from data_collector import DataCollector
from backtester import Backtester
from config import load_config
from logger import setup_logging
import os

def load_recipes_db():
    csv_path = r"c:\Users\paulo\.gemini\antigravity\playground\core-omega\PRJT_OlimpoTrade\registro_otimizacao_moedas.csv"
    columns = [
        "Criptomoeda", "SMA Rápida", "SMA Lenta", "Stop Loss (%)",
        "Take Profit", "Stop Móvel (Trailing)", "Take Profit Ativo",
        "Retorno Treino (%)", "Retorno Teste (%)", "Trades Treino",
        "Trades Teste", "Win Rate Treino (%)", "Max Drawdown (%)", "Notas"
    ]
    if not os.path.exists(csv_path):
        initial_data = [
            {
                "Criptomoeda": "ETH/USDT",
                "SMA Rápida": 15,
                "SMA Lenta": 21,
                "Stop Loss (%)": 1.0,
                "Take Profit": "10.0%",
                "Stop Móvel (Trailing)": "Não",
                "Take Profit Ativo": "Sim",
                "Retorno Treino (%)": 24.08,
                "Retorno Teste (%)": 0.0,
                "Trades Treino": 10,
                "Trades Teste": 0,
                "Win Rate Treino (%)": 30.0,
                "Max Drawdown (%)": 0.0,
                "Notas": "Seguidor de Tendência / Breakout: Lucros brutais nas grandes ondas (+10%) com perdas muito pequenas e controladas (-1%). Ideal para mercados com tendências fortes e rápidas."
            },
            {
                "Criptomoeda": "SOL/USDT",
                "SMA Rápida": 15,
                "SMA Lenta": 21,
                "Stop Loss (%)": 2.0,
                "Take Profit": "5.0%",
                "Stop Móvel (Trailing)": "Não",
                "Take Profit Ativo": "Sim",
                "Retorno Treino (%)": 4.53,
                "Retorno Teste (%)": 0.0,
                "Trades Treino": 35,
                "Trades Teste": 0,
                "Win Rate Treino (%)": 51.4,
                "Max Drawdown (%)": -4.10,
                "Notas": "Equilibrado e Consistente: Curva de capital extremamente estável e segura (Drawdown baixíssimo de 4%). A amplitude curta das médias corta perdas muito antes de atingir o Stop Loss."
            },
            {
                "Criptomoeda": "BTC/USDT",
                "SMA Rápida": 9,
                "SMA Lenta": 21,
                "Stop Loss (%)": 1.0,
                "Take Profit": "3.0%",
                "Stop Móvel (Trailing)": "Não",
                "Take Profit Ativo": "Sim",
                "Retorno Treino (%)": 8.14,
                "Retorno Teste (%)": -0.26,
                "Trades Treino": 15,
                "Trades Teste": 0,
                "Win Rate Treino (%)": 60.0,
                "Max Drawdown (%)": 0.0,
                "Notas": "Filtro de Tendência Estável: Configuração moderada e muito estável. Quase break-even no teste futuro (-0.26%), provando excelente resiliência contra ruído e volatilidade rápida."
            }
        ]
        df = pd.DataFrame(initial_data, columns=columns)
        df.to_csv(csv_path, index=False, encoding="utf-8")
        return df
    else:
        try:
            return pd.read_csv(csv_path, encoding="utf-8")
        except Exception:
            return pd.read_csv(csv_path, encoding="latin-1")

def save_recipe(recipe):
    csv_path = r"c:\Users\paulo\.gemini\antigravity\playground\core-omega\PRJT_OlimpoTrade\registro_otimizacao_moedas.csv"
    df = load_recipes_db()

    # Check if duplicate exists to avoid cluttering
    duplicate_mask = (
        (df["Criptomoeda"] == recipe["Criptomoeda"]) &
        (df["SMA Rápida"] == recipe["SMA Rápida"]) &
        (df["SMA Lenta"] == recipe["SMA Lenta"]) &
        (df["Stop Loss (%)"] == recipe["Stop Loss (%)"]) &
        (df["Take Profit"] == recipe["Take Profit"]) &
        (df["Stop Móvel (Trailing)"] == recipe["Stop Móvel (Trailing)"]) &
        (df["Take Profit Ativo"] == recipe["Take Profit Ativo"])
    )
    if duplicate_mask.any():
        idx = df[duplicate_mask].index[0]
        df.at[idx, "Retorno Treino (%)"] = recipe["Retorno Treino (%)"]
        df.at[idx, "Retorno Teste (%)"] = recipe["Retorno Teste (%)"]
        df.at[idx, "Trades Treino"] = recipe["Trades Treino"]
        df.at[idx, "Trades Teste"] = recipe["Trades Teste"]
        df.at[idx, "Win Rate Treino (%)"] = recipe["Win Rate Treino (%)"]
        df.at[idx, "Max Drawdown (%)"] = recipe["Max Drawdown (%)"]
        df.at[idx, "Notas"] = recipe["Notas"]
    else:
        new_row = pd.DataFrame([recipe])
        df = pd.concat([df, new_row], ignore_index=True)

    df.to_csv(csv_path, index=False, encoding="utf-8")

# 1. Configuração da Página do Streamlit
st.set_page_config(
    page_title="OlimpoTrade - Algorithmic Trading Lab",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Inicialização de Session State para persistência e ligação dinâmica de inputs
if "strategy_type_val" not in st.session_state:
    st.session_state.strategy_type_val = "PAULO_GOLD"
if "p2_window_val" not in st.session_state:
    st.session_state.p2_window_val = 9
if "p3_window_val" not in st.session_state:
    st.session_state.p3_window_val = 21
if "p4_window_val" not in st.session_state:
    st.session_state.p4_window_val = 50
if "p5_window_val" not in st.session_state:
    st.session_state.p5_window_val = 200
if "multipoint_mode_val" not in st.session_state:
    st.session_state.multipoint_mode_val = "AGILE"
if "exhaustion_filter_val" not in st.session_state:
    st.session_state.exhaustion_filter_val = True
if "exhaustion_threshold_val" not in st.session_state:
    st.session_state.exhaustion_threshold_val = 2.5
if "p5_filter_active_val" not in st.session_state:
    st.session_state.p5_filter_active_val = True
if "entry_mode_val" not in st.session_state:
    st.session_state.entry_mode_val = "4PONTOS"
if "exit_mode_val" not in st.session_state:
    st.session_state.exit_mode_val = "P3" 
if "operation_mode_val" not in st.session_state:
    st.session_state.operation_mode_val = "TREND_FOLLOWING" 

if "short_window_val" not in st.session_state:
    st.session_state.short_window_val = 9
if "long_window_val" not in st.session_state:
    st.session_state.long_window_val = 21
if "stop_loss_pct_val" not in st.session_state:
    st.session_state.stop_loss_pct_val = 2.0
if "sl_active_val" not in st.session_state:
    st.session_state.sl_active_val = True
if "take_profit_pct_val" not in st.session_state:
    st.session_state.take_profit_pct_val = 7.0
if "tp_active_val" not in st.session_state:
    st.session_state.tp_active_val = False
if "trailing_stop_active_val" not in st.session_state:
    st.session_state.trailing_stop_active_val = False
if "emergency_exit_price_cross_val" not in st.session_state:
    st.session_state.emergency_exit_price_cross_val = "ANY"
if "allow_reentry_val" not in st.session_state:
    st.session_state.allow_reentry_val = True

# ─── CARREGAMENTO AUTOMATICO DE LAGARTAS ESPECIALISTAS DO DISCO ───────────────
_CATERPILLARS_FILE = os.path.join(os.path.dirname(__file__), "caterpillars.json")
if "game_trained_caterpillars" not in st.session_state:
    if os.path.exists(_CATERPILLARS_FILE):
        try:
            with open(_CATERPILLARS_FILE, "r", encoding="utf-8") as _f:
                st.session_state.game_trained_caterpillars = json.load(_f)
        except Exception:
            st.session_state.game_trained_caterpillars = {}
    else:
        st.session_state.game_trained_caterpillars = {}
# ─────────────────────────────────────────────────────────────────────────────
if "paulo_gold_trend_filter_val" not in st.session_state:
    st.session_state.paulo_gold_trend_filter_val = False
if "paulo_gold_min_dist_pct_val" not in st.session_state:
    st.session_state.paulo_gold_min_dist_pct_val = 0.0

if "fee_pct_val" not in st.session_state:
    st.session_state.fee_pct_val = 0.1
if "tax_pct_val" not in st.session_state:
    st.session_state.tax_pct_val = 28.0
if "slippage_pct_val" not in st.session_state:
    st.session_state.slippage_pct_val = 0.05

if "backtest_results" not in st.session_state:
    st.session_state.backtest_results = None
if "optimizer_results" not in st.session_state:
    st.session_state.optimizer_results = None

# 3. Injeção de CSS Customizado para Estética Premium Glassmorphic (Tema Claro / Light Mode)
st.markdown("""
<style>
    /* Importar Fonte Outfit do Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

    /* Configuração de Fontes e Fundo Principal */
    html, body, [class*="css"], .stApp {
        font-family: 'Outfit', sans-serif;
        background-color: #f1f5f9;
        color: #0f172a;
    }

    /* Efeito de Fundo Gradiente Suave Claro */
    .stApp {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
    }

    /* Estilo do Menu Lateral (Sidebar) com alto contraste */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid rgba(0, 0, 0, 0.08);
        box-shadow: 4px 0 16px rgba(0, 0, 0, 0.02);
    }

    /* Cabeçalho Principal */
    .main-title {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #0284c7 0%, #7c3aed 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.2rem;
        letter-spacing: -1px;
    }

    .sub-title {
        font-size: 1.1rem;
        font-weight: 400;
        color: #475569;
        text-align: center;
        margin-bottom: 2rem;
    }

    /* Cards Glassmorphic Light Premium */
    .glass-card {
        background: rgba(255, 255, 255, 0.75);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.6);
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.04);
        transition: transform 0.3s ease, border 0.3s ease;
        color: #0f172a;
    }

    .glass-card:hover {
        border: 1px solid rgba(2, 132, 199, 0.2);
        transform: translateY(-2px);
    }

    /* Cards de Métricas Rápidas */
    .metric-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 15px;
        margin-bottom: 25px;
    }

    .metric-card {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 12px;
        border: 1px solid rgba(0, 0, 0, 0.05);
        padding: 18px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.01);
        transition: all 0.2s ease;
    }

    .metric-card:hover {
        border-color: rgba(124, 58, 237, 0.2);
        box-shadow: 0 4px 15px rgba(124, 58, 237, 0.06);
    }

    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        margin-top: 5px;
    }

    .metric-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Cores de Alto Contraste */
    .text-green { color: #059669; font-weight: bold; }
    .text-red { color: #e11d48; font-weight: bold; }
    .text-cyan { color: #0369a1; font-weight: bold; }
    .text-purple { color: #6d28d9; font-weight: bold; }
    .text-orange { color: #c2410c; font-weight: bold; }

    /* Indicador de Conexão */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 20px;
    }
    .status-active {
        background-color: rgba(5, 150, 105, 0.1);
        color: #059669;
        border: 1px solid rgba(5, 150, 105, 0.25);
    }

    /* Estilizar inputs e botões do Streamlit */
    div.stButton > button {
        background: linear-gradient(135deg, #0284c7 0%, #7c3aed 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        padding: 10px 24px !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 15px rgba(124, 58, 237, 0.25) !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }
    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(124, 58, 237, 0.4) !important;
    }
</style>
""", unsafe_allow_html=True)

# 4. Cabeçalho da Aplicação - Compacto & Premium
st.markdown("""
<style>
    /* Reduzir paddings e margens padrão do Streamlit para maximizar espaço vertical */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    /* Espaçador entre elementos do Streamlit */
    div[data-testid="stVerticalBlock"] > div {
        padding-bottom: 0.35rem !important;
        padding-top: 0.35rem !important;
    }
    /* Reduzir margens dos selectboxes e sliders */
    .stSelectbox, .stSlider, .stButton {
        margin-bottom: 0px !important;
    }
    /* Tornar cabeçalhos dos expanders mais compactos */
    .streamlit-expanderHeader {
        font-size: 0.88rem !important;
        padding: 0.35rem 0.7rem !important;
        background-color: rgba(255, 255, 255, 0.5) !important;
        border-radius: 8px !important;
    }
</style>

<div style="display: flex; align-items: center; justify-content: space-between; background: rgba(255,255,255,0.75); padding: 6px 14px; border-radius: 12px; border: 1px solid rgba(0,0,0,0.06); gap: 15px; margin-bottom: 8px; flex-wrap: wrap;">
    <div style="display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 1.5rem; font-weight: 800; background: linear-gradient(135deg, #0284c7 0%, #7c3aed 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -1px; line-height: 1;">OLIMPOTRADE</span>
        <span style="background-color: rgba(5, 150, 105, 0.1); color: #059669; border: 1px solid rgba(5, 150, 105, 0.25); padding: 2px 8px; border-radius: 9999px; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.5px; display: inline-flex; align-items: center; gap: 4px;">🤖 SIMULADOR ATIVO</span>
    </div>
    <div style="font-size: 0.8rem; font-weight: 600; color: #64748b; letter-spacing: 0.5px;">Algorithmic Trading & Analytics Lab</div>
</div>
""", unsafe_allow_html=True)

# 1. LINHA HORIZONTAL COMPACTA DE CONTROLES E BOTÃO (SEM BARRA LATERAL!)
col_ctrl1, col_ctrl2, col_ctrl3, col_ctrl4, col_ctrl5 = st.columns([1.5, 1.2, 2.2, 2.8, 2.3])

with col_ctrl1:
    symbol = st.selectbox(
        "Par de Trading",
        ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"],
        index=0,
        help="Par de moedas a transacionar. Todos os cálculos de banca e lucro são exibidos na sua moeda local (EUR)."
    )
with col_ctrl2:
    timeframe = st.selectbox(
        "Timeframe",
        ["15m", "1h", "4h", "1d"],
        index=1,
        help="Escala de tempo de cada candle (vela). Timeframes maiores (1h, 1d) filtram ruído e mostram tendências mais fortes."
    )
with col_ctrl3:
    limit_candles = st.slider(
        "Quantidade de Candles",
        100, 1000, 500,
        step=50,
        help="Quantidade de velas a obter do histórico. Dica: Para simular 1 ano instantaneamente, use timeframe '1d' e 365 candles."
    )
with col_ctrl4:
    # Construir lista de estrategias incluindo lagartas graduadas da Universidade
    if "game_trained_caterpillars" not in st.session_state:
        st.session_state.game_trained_caterpillars = {}
    
    _base_strategies = ["SMA_CROSSOVER", "EMA_CROSSOVER", "MULTIPOINT_VECTOR", "PAULO_GOLD"]
    _caterpillar_keys = ["🎓 " + k for k in st.session_state.game_trained_caterpillars.keys()]
    _all_strategies = _base_strategies + _caterpillar_keys
    
    def _fmt_strategy(x):
        if x == "SMA_CROSSOVER":      return "Media Simples (SMA Crossover)"
        if x == "EMA_CROSSOVER":      return "Media Exponencial (EMA Crossover)"
        if x == "MULTIPOINT_VECTOR":  return "Vetor de 5 Pontos (MultiPoint)"
        if x == "PAULO_GOLD":         return "✨ Estrategia Exclusiva PAULO_GOLD"
        return x  # Lagartas graduadas mostram o proprio nome com emoji
    
    _current = st.session_state.strategy_type_val if st.session_state.strategy_type_val in _all_strategies else "PAULO_GOLD"
    _current_idx = _all_strategies.index(_current) if _current in _all_strategies else 3
    
    strategy_type = st.selectbox(
        "Estrategia Ativa",
        _all_strategies,
        index=_current_idx,
        format_func=_fmt_strategy,
        help="Escolha o algoritmo de decisao. As lagartas 🎓 sao especialistas treinadas na Universidade IA!"
    )
    
    # Se for uma lagarta graduada, injetar o seu DNA nos parametros da sessao
    _active_caterpillar_dna = None
    if strategy_type.startswith("🎓 "):
        _caterpillar_name = strategy_type[2:].strip()
        if _caterpillar_name in st.session_state.game_trained_caterpillars:
            _active_caterpillar_dna = st.session_state.game_trained_caterpillars[_caterpillar_name]
            st.session_state.stop_loss_pct_val = float(round(_active_caterpillar_dna["stop_loss_pct"], 1))
            st.session_state.sl_active_val = True
        # Mantém a strategy_type com o nome original da lagarta para que a StrategyFactory a apanhe
        st.session_state.strategy_type_val = strategy_type
with col_ctrl5:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    run_button = st.button("🚀 Executar Simulação Real", width='stretch', type="primary")

# ----------------- NOVO PAINEL DE CONFIGURAÇÕES COLAPSÁVEL CENTRAL -----------------
if '_active_caterpillar_dna' not in dir():
    _active_caterpillar_dna = None

config = load_config()

with st.expander("🔧 Painel Global de Configuração do Robô & Central de Variáveis (Clique para Configurar)", expanded=False):
    st.markdown("""
    <div style='font-size: 0.9rem; color: #64748b; margin-bottom: 1.5rem; text-align:center;'>
        💡 <b>Comando Central:</b> Configure aqui todas as variáveis quantitativas, médias de Fibonacci, limites de risco e fricções de mercado.
        As alterações propagam-se instantaneamente para todas as abas e simulações da app!
    </div>
    """, unsafe_allow_html=True)
    
    import variables_registry
    variables_registry.render_variables_dashboard(compact=True)
    
    config.update({
        "ENV": "development",
        "EXCHANGE_NAME": "binance",
        "SYMBOL": symbol,
        "TIMEFRAME": timeframe,
        "TRADING_INTERVAL_SECONDS": 300,
        "LOG_LEVEL": "INFO",
        "LOG_FILE": "trading_bot.log",
        "INITIAL_CAPITAL": 100.0,
        "SHORT_WINDOW": st.session_state.get('short_window_val', 9),
        "LONG_WINDOW": st.session_state.get('long_window_val', 21),
        "P2_WINDOW": st.session_state.get('tg_p2', 5),
        "P3_WINDOW": st.session_state.get('tg_p3', 13),
        "P4_WINDOW": st.session_state.get('tg_p4', 21),
        "P5_WINDOW": st.session_state.get('tg_p5', 55),
        "P6_WINDOW": st.session_state.get('tg_p6', 144),
        "STOP_LOSS_ACTIVE": st.session_state.get('tg_sl_pct_active', True),
        "STOP_LOSS_PERCENT": st.session_state.get('tg_sl_pct', 2.0),
        "TAKE_PROFIT_ACTIVE": st.session_state.get('tg_tp_pct_active', False),
        "TAKE_PROFIT_PERCENT": st.session_state.get('tg_tp_pct', 7.0),
        "TRAILING_STOP_ACTIVE": st.session_state.get('tg_ts_pct_active', False),
        "TRAILING_STOP_PERCENT": st.session_state.get('tg_ts_pct', 1.5),
        "ALLOW_REENTRY": st.session_state.get('allow_reentry_val', True),
        "PAULO_GOLD_TREND_FILTER": st.session_state.get('paulo_gold_trend_filter_val', False),
        "PAULO_GOLD_MIN_DIST_PCT": st.session_state.get('paulo_gold_min_dist_pct_val', 0.0),
        "FEE_PCT": st.session_state.get('fee_pct_val', 0.1),
        "TAX_PCT": st.session_state.get('tax_pct_val', 28.0),
        "SLIPPAGE_PCT": st.session_state.get('slippage_pct_val', 0.05)
    })

# Mapear variáveis locais a partir do estado para compatibilidade global
short_window = st.session_state.get('short_window_val', 9)
long_window = st.session_state.get('long_window_val', 21)
operation_mode = st.session_state.get('operation_mode_val', 'TREND_FOLLOWING')
entry_mode = st.session_state.get('entry_mode_val', '4PONTOS')
exit_mode = st.session_state.get('exit_mode_val', 'P3')
multipoint_mode = st.session_state.get('multipoint_mode_val', 'AGILE')
allow_reentry = st.session_state.get('allow_reentry_val', True)
paulo_gold_trend_filter = st.session_state.get('paulo_gold_trend_filter_val', False)
paulo_gold_min_dist_pct = st.session_state.get('paulo_gold_min_dist_pct_val', 0.0)
max_risk_pct = 1.0
stop_loss_pct = st.session_state.get('tg_sl_pct', 2.0)
take_profit_pct = st.session_state.get('tg_tp_pct', 7.0)
trailing_stop_pct = st.session_state.get('tg_ts_pct', 1.5)
fee_pct = st.session_state.get('fee_pct_val', 0.1)
tax_pct = st.session_state.get('tax_pct_val', 28.0)
slippage_pct = st.session_state.get('slippage_pct_val', 0.05)

# Inicializar logger
logger = setup_logging()

# 7. Abas Principais do Laboratório (TABS SIMPLIFICADAS)
tab_backtest, tab_simulator, tab_math_lab, tab_trader_game, tab_bot_brain = st.tabs([
    "📈 Simulação & Gráficos Real",
    "🔬 Laboratório de Simulação & Otimização",
    "🎛️ Laboratório Matemático & Regimes",
    "🎮 Arena de Jogo & Auto-Treino",
    "🧠 Cérebro do Bot (DNA)"
])

# Ação do Botão Principal do Backtester
if run_button:
    st.markdown("### 🚀 Recolhendo dados e processando simulação...")
    progress_bar = st.progress(0)

    # Obter dados da Binance
    collector = DataCollector(exchange_id='binance', symbol=symbol, timeframe=timeframe)
    progress_bar.progress(30)

    df_ohlcv = collector.get_ohlcv(limit=limit_candles)
    progress_bar.progress(60)

    if df_ohlcv is not None and not df_ohlcv.empty:
        # Criar backtester
        backtester = Backtester(config, logger)

        # Correr backtest
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        trades, capital_history = loop.run_until_complete(backtester.run_backtest(df_ohlcv))
        metrics = backtester.get_performance_metrics()

        progress_bar.progress(100)
        progress_bar.empty()

        # Guardar no session state para preservação
        st.session_state.backtest_results = metrics
        st.session_state.backtest_trades = trades
        st.session_state.backtest_capital_history = capital_history
        st.session_state.backtest_df = df_ohlcv
        # st.rerun() removido para evitar loop infinito de re-execução em Streamlit pós-2025

# ─── CLASSIFICADOR DE TIPO DE MERCADO (usando precos reais da Binance) ──────────
def classify_market_type(prices_list):
    """
    Analisa uma lista de precos de fecho e classifica o tipo de mercado.
    Usa as N velas disponiveis (todas as que foram carregadas da Binance).
    Retorna dict com: type, type_pt, emoji, confidence, slope_pct, volatility_pct, range_pct
    """
    import numpy as np
    if len(prices_list) < 10:
        return {"type": "DESCONHECIDO", "type_pt": "Desconhecido", "emoji": "❓", "confidence": 0,
                "slope_pct": 0, "volatility_pct": 0, "range_pct": 0}

    prices_arr = np.array(prices_list, dtype=float)

    # 1. Tendencia linear: inclinacao percentual total
    p_start = float(np.mean(prices_arr[:max(1, len(prices_arr)//10)]))  # media dos primeiros 10%
    p_end   = float(np.mean(prices_arr[-max(1, len(prices_arr)//10):]))  # media dos ultimos 10%
    slope_pct = ((p_end - p_start) / p_start) * 100.0

    # 2. Volatilidade: desvio padrao dos retornos diarios
    returns = np.diff(prices_arr) / prices_arr[:-1]
    volatility_pct = float(np.std(returns)) * 100.0

    # 3. Range: amplitude total relativa
    range_pct = float((np.max(prices_arr) - np.min(prices_arr)) / np.min(prices_arr)) * 100.0

    # 4. Classificacao por regras
    if volatility_pct > 4.0:
        mtype = "CAOTICO"
        mtype_pt = "Caótico / Hiper-Volátil"
        emoji = "💥"
        confidence = min(99, int(volatility_pct / 4.0 * 70))
    elif slope_pct > 5.0:
        mtype = "BULL"
        mtype_pt = "Tendência de Alta (Bull)"
        emoji = "🐂"
        confidence = min(99, int(min(slope_pct, 30) / 30 * 100))
    elif slope_pct < -5.0:
        mtype = "BEAR"
        mtype_pt = "Tendência de Baixa (Bear)"
        emoji = "🐻"
        confidence = min(99, int(min(abs(slope_pct), 30) / 30 * 100))
    else:
        mtype = "LATERAL"
        mtype_pt = "Mercado Lateral / Range"
        emoji = "↔️"
        confidence = min(99, int((1 - abs(slope_pct) / 5.0) * 100))

    return {
        "type": mtype,
        "type_pt": mtype_pt,
        "emoji": emoji,
        "confidence": confidence,
        "slope_pct": round(slope_pct, 2),
        "volatility_pct": round(volatility_pct, 3),
        "range_pct": round(range_pct, 2),
        "n_candles": len(prices_list)
    }
# ─────────────────────────────────────────────────────────────────────────────

with tab_backtest:
    if st.session_state.backtest_results is not None:
        metrics = st.session_state.backtest_results
        trades = st.session_state.backtest_trades
        capital_history = st.session_state.backtest_capital_history
        df_ohlcv = st.session_state.backtest_df

        # ─── BANNER: DETEÇÃO AUTOMÁTICA DO TIPO DE MERCADO ──────────────────────────
        _real_prices = df_ohlcv["close"].tolist()
        _mkt = classify_market_type(_real_prices)

        # Encontrar lagartas recomendadas para este tipo de mercado
        _habitat_map = {
            "BULL":    ["Alta", "Bull"],
            "BEAR":    ["Baixa", "Bear"],
            "LATERAL": ["Lateral", "Range"],
            "CAOTICO": ["Caótico", "Chaos"]
        }
        _matching_caterpillars = []
        for _cn, _cdna in st.session_state.game_trained_caterpillars.items():
            _habitat = _cdna.get("market_habitat", "")
            _keywords = _habitat_map.get(_mkt["type"], [])
            if any(kw in _habitat for kw in _keywords):
                _matching_caterpillars.append(_cn)

        # Cores por tipo de mercado
        _mkt_colors = {
            "BULL":    ("#16a34a", "#dcfce7"),  # verde
            "BEAR":    ("#dc2626", "#fee2e2"),  # vermelho
            "LATERAL": ("#2563eb", "#dbeafe"),  # azul
            "CAOTICO": ("#9333ea", "#f3e8ff"),  # roxo
        }
        _c_border, _c_bg = _mkt_colors.get(_mkt["type"], ("#6b7280", "#f9fafb"))

        st.markdown(f"""
        <div style="border-left: 5px solid {_c_border}; background: {_c_bg}; padding: 12px 18px;
                    border-radius: 8px; margin-bottom: 16px;">
            <div style="font-size: 1.1rem; font-weight: 700; color: {_c_border};">
                {_mkt['emoji']} Mercado Detetado: {_mkt['type_pt']}
                <span style="font-size:0.85rem; font-weight:400; margin-left:12px;">
                    Confiança: {_mkt['confidence']}% · {_mkt['n_candles']} velas analisadas
                </span>
            </div>
            <div style="font-size: 0.85rem; margin-top: 4px; color: #374151;">
                📈 Inclinação: <b>{_mkt['slope_pct']:+.2f}%</b> &nbsp;|&nbsp;
                📊 Volatilidade: <b>{_mkt['volatility_pct']:.3f}%/vela</b> &nbsp;|&nbsp;
                📏 Amplitude: <b>{_mkt['range_pct']:.1f}%</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Mostrar lagartas recomendadas (se existirem)
        if _matching_caterpillars:
            _rec_col1, _rec_col2 = st.columns([3, 1])
            with _rec_col1:
                _names_str = ", ".join([f"🎓 {n}" for n in _matching_caterpillars])
                st.info(f"**Especialistas disponíveis para este mercado:** {_names_str}")
            with _rec_col2:
                if len(_matching_caterpillars) == 1 and st.button(
                    f"⚡ Ativar '{_matching_caterpillars[0]}'",
                    key="auto_activate_caterpillar",
                    type="primary",
                    width='stretch'
                ):
                    st.session_state.strategy_type_val = f"🎓 {_matching_caterpillars[0]}"
                    st.rerun()
        # ─────────────────────────────────────────────────────────────────────────────

        # Calcular as Médias no histórico de acordo com a estratégia ativa para exibição visual
        df_visualization = df_ohlcv.copy()
        if strategy_type.startswith("🎓"):
            # Para a lagarta, mostramos as médias dos seus sensores IA
            import ta
            df_visualization['Line_1'] = ta.trend.sma_indicator(df_visualization['close'], window=5)
            df_visualization['Line_2'] = ta.trend.sma_indicator(df_visualization['close'], window=12)
            df_visualization['Line_3'] = ta.trend.sma_indicator(df_visualization['close'], window=20)
            line1_name = "MA Rápida (5)"
            line2_name = "MA Lenta (12)"
            line3_name = "MA Chão (200)"
            line1_color = "#10b981"
            line2_color = "#3b82f6"
            line3_color = "#f59e0b"
        elif strategy_type == "PAULO_GOLD":
            df_visualization['Line_1'] = ta.trend.sma_indicator(df_visualization['close'], window=short_window)
            df_visualization['Line_2'] = ta.trend.sma_indicator(df_visualization['close'], window=long_window)
            line1_name = f"MǸdia Curta ({short_window})"
            line2_name = f"MǸdia Lenta ({long_window})"
            line1_color = "#0ea5e9"
            line2_color = "#f97316"
        elif strategy_type == "SMA_CROSSOVER":
            df_visualization['Line_1'] = ta.trend.sma_indicator(df_visualization['close'], window=short_window)
            df_visualization['Line_2'] = ta.trend.sma_indicator(df_visualization['close'], window=long_window)
            line1_name = f"SMA Curta ({short_window})"
            line2_name = f"SMA Lenta ({long_window})"
            line1_color = "#0ea5e9"
            line2_color = "#f97316"
        elif strategy_type == "EMA_CROSSOVER":
            df_visualization['Line_1'] = ta.trend.ema_indicator(df_visualization['close'], window=short_window)
            df_visualization['Line_2'] = ta.trend.ema_indicator(df_visualization['close'], window=long_window)
            line1_name = f"EMA Curta ({short_window})"
            line2_name = f"EMA Lenta ({long_window})"
            line1_color = "#3b82f6"
            line2_color = "#ec4899"
        else:
            # MULTIPOINT_VECTOR
            df_visualization['Line_1'] = ta.trend.sma_indicator(df_visualization['close'], window=p2_window)
            df_visualization['Line_2'] = ta.trend.sma_indicator(df_visualization['close'], window=p3_window)
            df_visualization['Line_3'] = ta.trend.sma_indicator(df_visualization['close'], window=p4_window)
            df_visualization['Line_4'] = ta.trend.sma_indicator(df_visualization['close'], window=p5_window)
            line1_name = f"P2 - Média Rápida ({p2_window})"
            line2_name = f"P3 - Média Curta ({p3_window})"
            line3_name = f"P4 - Média Média ({p4_window})"
            line4_name = f"P5 - Média Longa ({p5_window})"
            line1_color = "#0ea5e9"
            line2_color = "#f97316" 

        # Calcular a primeira linha média que o preço encontra (a mais próxima)
        if strategy_type in ["SMA_CROSSOVER", "EMA_CROSSOVER", "PAULO_GOLD"]:
            df_visualization['First_Line'] = df_visualization.apply(
                lambda row: max(row['Line_1'], row['Line_2']) if (pd.notna(row['Line_1']) and pd.notna(row['Line_2']) and row['close'] >= max(row['Line_1'], row['Line_2'])) else row['close'],
                axis=1
            )

        # --- EXIBIÇÃO DE MÉTRICAS (METRICS CARDS) ---
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="margin-top:0;">📊 Sumário de Desempenho</h4>', unsafe_allow_html=True)

        total_pnl = metrics["total_pnl"]
        pnl_class = "text-green" if total_pnl >= 0 else "text-red"
        pnl_sign = "+" if total_pnl >= 0 else ""

        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-card">
                <div class="metric-label">Capital Final</div>
                <div class="metric-value text-cyan">{metrics['final_capital']:.2f} EUR</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Retorno Total</div>
                <div class="metric-value {pnl_class}">{pnl_sign}{total_pnl:.2f} EUR ({pnl_sign}{metrics['total_return_pct']:.2f}%)</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Taxa de Vitória</div>
                <div class="metric-value text-purple">{metrics['win_rate']*100:.1f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Max Drawdown</div>
                <div class="metric-value text-red">{metrics['max_drawdown_pct']:.2f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Sharpe / Sortino</div>
                <div class="metric-value text-orange">{metrics['sharpe_ratio']:.2f} / {metrics['sortino_ratio']:.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Fator de Lucro</div>
                <div class="metric-value text-cyan">{metrics['profit_factor']:.2f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Outras métricas rápidas
        st.markdown(
            f"**Total de Operações:** {metrics['num_trades']} | "
            f"**Vitórias:** <span class='text-green'>{metrics['num_wins']}</span> ✅ | "
            f"**Derrotas:** <span class='text-red'>{metrics['num_losses']}</span> ❌",
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

        # --- GRÁFICOS INTERATIVOS ---

        # 1. Curva de Capital (Equity Curve)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h4>📈 Curva de Capital (Equity Curve)</h4>', unsafe_allow_html=True)

        dates_chart = df_ohlcv.index
        capital_padded = capital_history[:len(dates_chart)]
        while len(capital_padded) < len(dates_chart):
            capital_padded.append(capital_padded[-1])

        fig_equity = go.Figure()

        # Equity Curve
        fig_equity.add_trace(go.Scatter(
            x=dates_chart,
            y=capital_padded,
            mode='lines',
            name='Capital (EUR)',
            line=dict(color='#0284c7', width=3),
            fill='tozeroy',
            fillcolor='rgba(2, 132, 199, 0.04)'
        ))

        # Preço do Ativo de Fundo (Normalizado para Capital Inicial)
        price_normalized = df_ohlcv['close'] / df_ohlcv['close'].iloc[0] * initial_capital
        fig_equity.add_trace(go.Scatter(
            x=dates_chart,
            y=price_normalized,
            mode='lines',
            name=f'Estratégia Buy & Hold {symbol}',
            line=dict(color='rgba(71, 85, 105, 0.4)', width=1.5, dash='dash')
        ))

        fig_equity.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=20, b=0),
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
            xaxis=dict(gridcolor='rgba(0,0,0,0.05)', tickfont=dict(color='#475569')),
            yaxis=dict(gridcolor='rgba(0,0,0,0.05)', tickfont=dict(color='#475569')),
            height=350
        )

        st.plotly_chart(fig_equity, width='stretch')
        st.markdown('</div>', unsafe_allow_html=True)

        # 2. Gráfico Interativo de Sinais no Preço do Ativo + Médias Móveis (SMA)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h4>🎯 Justificação Visual: Preço & Cruzamento das Médias Móveis (SMA)</h4>', unsafe_allow_html=True)
        st.markdown(
            "💡 **Por que o robô entra e sai?** O robô compra quando a linha azul clara (Curta) cruza **acima** da laranja (Lenta). "
            "Ele vende no cruzamento inverso, ou quando bate no seu Stop Loss automático (limite de segurança) ou Take Profit (alvo de lucro)."
        )

        fig_prices = go.Figure()
        if strategy_type in ["SMA_CROSSOVER", "EMA_CROSSOVER", "PAULO_GOLD"]:
            fig_prices.add_trace(go.Scatter(
                x=df_visualization.index,
                y=df_visualization['First_Line'],
                mode='lines',
                line=dict(color='rgba(0,0,0,0)', width=0),
                showlegend=False,
                hoverinfo='skip'
            ))

        # Linha do Preço Real do Ativo - INTERATIVA (Unified Hover)
        fig_prices.add_trace(go.Scatter(
            x=df_visualization.index,
            y=df_visualization['close'],
            mode='lines',
            name=f'Preço {symbol}',
            line=dict(color='rgba(71, 85, 105, 0.25)', width=1.5),
            fill='tonexty' if strategy_type in ["SMA_CROSSOVER", "EMA_CROSSOVER", "PAULO_GOLD"] else None,
            fillcolor='rgba(14, 165, 233, 0.06)' if strategy_type in ["SMA_CROSSOVER", "EMA_CROSSOVER", "PAULO_GOLD"] else None,
            hovertemplate='Preço: %{y:.2f} EUR<extra></extra>'
        ))

        # Segmentos verde lagarta vibrante (#22c55e) ligando a Entrada à Saída de cada trade real
        for idx_tr, trade in enumerate(trades):
            trade_mask = (df_visualization.index >= trade['entry_timestamp']) & (df_visualization.index <= trade['exit_timestamp'])
            trade_segment = df_visualization[trade_mask]
            if not trade_segment.empty:
                show_legend = (idx_tr == 0)
                fig_prices.add_trace(go.Scatter(
                    x=trade_segment.index,
                    y=trade_segment['close'],
                    mode='lines',
                    name='Lagarta Ativa (Trade Open)',
                    line=dict(color='#22c55e', width=3.5),
                    showlegend=show_legend,
                    hovertemplate='Preço Ativo: %{y:.2f} EUR<extra></extra>'
                ))

        # Linhas das médias da estratégia correspondente
        fig_prices.add_trace(go.Scatter(
            x=df_visualization.index,
            y=df_visualization['Line_1'],
            mode='lines',
            name=line1_name,
            line=dict(color=line1_color if strategy_type != "MULTIPOINT_VECTOR" else "#0ea5e9", width=2),
            hovertemplate=f'{line1_name}: %{{y:.2f}} EUR<extra></extra>'
        ))

        fig_prices.add_trace(go.Scatter(
            x=df_visualization.index,
            y=df_visualization['Line_2'],
            mode='lines',
            name=line2_name,
            line=dict(color=line2_color if strategy_type != "MULTIPOINT_VECTOR" else "#f97316", width=2),
            hovertemplate=f'{line2_name}: %{{y:.2f}} EUR<extra></extra>'
        ))
        
        if strategy_type == "MULTIPOINT_VECTOR":
            fig_prices.add_trace(go.Scatter(
                x=df_visualization.index,
                y=df_visualization['Line_3'],
                mode='lines',
                name=line3_name,
                line=dict(color='#10b981', width=1.5),
                hovertemplate=f'{line3_name}: %{{y:.2f}} EUR<extra></extra>'
            ))
            fig_prices.add_trace(go.Scatter(
                x=df_visualization.index,
                y=df_visualization['Line_4'],
                mode='lines',
                name=line4_name,
                line=dict(color='#8b5cf6', width=1.5),
                hovertemplate=f'{line4_name}: %{{y:.2f}} EUR<extra></extra>'
            ))

        # Filtrar e agrupar marcas de BUY e SELL/SL/TP com explicações pedagógicas completas
        buy_x, buy_y, buy_text = [], [], []
        sell_x, sell_y, sell_text = [], [], []

        for trade in trades:
            # Entrada (BUY)
            buy_x.append(trade['entry_timestamp'])
            buy_y.append(trade['entry_price'])
            invested_val = trade['entry_price'] * trade['quantity']
            
            # Obter os valores dos pontos no instante da compra
            p1_val = trade['entry_price']
            p2_val = p3_val = p4_val = p5_val = 0
            try:
                row_val = df_visualization.loc[trade['entry_timestamp']]
                p2_val = row_val['Line_1'] if 'Line_1' in row_val and not pd.isna(row_val['Line_1']) else 0
                p3_val = row_val['Line_2'] if 'Line_2' in row_val and not pd.isna(row_val['Line_2']) else 0
                p4_val = row_val['Line_3'] if 'Line_3' in row_val and not pd.isna(row_val['Line_3']) else 0
                p5_val = row_val['Line_4'] if 'Line_4' in row_val and not pd.isna(row_val['Line_4']) else 0
            except Exception:
                pass
                
            points_info = f"P1 (Preço): {p1_val:.2f} EUR<br>P2 (Média): {p2_val:.2f} EUR<br>P3 (Média): {p3_val:.2f} EUR<br>"
            if strategy_type == "MULTIPOINT_VECTOR":
                points_info = (
                    f"P1 (Preço): {p1_val:.2f} EUR<br>"
                    f"P2 (Média {short_window}): {p2_val:.2f} EUR<br>"
                    f"P3 (Média {long_window}): {p3_val:.2f} EUR<br>"
                    f"P4 (Média {p4_window if 'p4_window' in locals() else 50}): {p4_val:.2f} EUR<br>"
                )
                if p5_filter_active or entry_mode == "5PONTOS":
                    points_info += f"P5 (Média {p5_window if 'p5_window' in locals() else 200}): {p5_val:.2f} EUR<br>"
            
            buy_text.append(
                f"📥 <b>ENTRADA (BUY)</b><br>"
                f"<b>Data</b>: {trade['entry_timestamp'].strftime('%Y-%m-%d %H:%M')}<br>"
                f"<b>Preço Compra</b>: {trade['entry_price']:.2f} EUR<br>"
                f"<b>Quantidade</b>: {trade['quantity']:.6f}<br>"
                f"<b>Valor Investido</b>: {invested_val:.2f} EUR<br><br>"
                f"<b>Estado dos Pontos de Medição:</b><br>{points_info}<br>"
                f"<b>Justificação</b>: Gatilho da estratégia ativado! Confirmação de tendência."
            )

            # Saída (SELL / STOP LOSS / TAKE PROFIT / TRAILING STOP)
            sell_x.append(trade['exit_timestamp'])
            sell_y.append(trade['exit_price'])
            pnl_sign = "+" if trade['pnl'] >= 0 else ""
            pnl_pct_sign = "+" if trade['pnl_pct'] >= 0 else ""

            if trade['reason'] == "STOP_LOSS":
                justification = f"O preço caiu abaixo do limite de segurança ({stop_loss_pct}%). Operação cortada para proteger o seu capital."
            elif trade['reason'] == "TRAILING_STOP":
                justification = f"O preço bateu no seu <b>Stop Loss Móvel (Trailing Stop)</b>, que subiu acompanhando a alta para proteger os lucros da banca antes da queda!"
            elif trade['reason'] == "TAKE_PROFIT":
                justification = f"O preço subiu e atingiu o seu alvo de ganho ideal. Lucro embolsado com sucesso."
            elif trade['reason'] == "STRATEGY_SELL":
                justification = f"Saída executada por: {trade.get('reason', 'Gatilho de saída da estratégia.')}"
            else:
                justification = "Fim do período de testes. Posição fechada de forma virtual ao preço final de mercado para fins de cálculo."

            # Obter os valores dos pontos no instante da venda
            p1_exit = trade['exit_price']
            p2_exit = p3_exit = p4_exit = p5_exit = 0
            try:
                row_exit = df_visualization.loc[trade['exit_timestamp']]
                p2_exit = row_exit['Line_1'] if 'Line_1' in row_exit and not pd.isna(row_exit['Line_1']) else 0
                p3_exit = row_exit['Line_2'] if 'Line_2' in row_exit and not pd.isna(row_exit['Line_2']) else 0
                p4_exit = row_exit['Line_3'] if 'Line_3' in row_exit and not pd.isna(row_exit['Line_3']) else 0
                p5_exit = row_exit['Line_4'] if 'Line_4' in row_exit and not pd.isna(row_exit['Line_4']) else 0
            except Exception:
                pass
                
            points_exit_info = f"P1 (Preço): {p1_exit:.2f} EUR<br>P2 (Média): {p2_exit:.2f} EUR<br>P3 (Média): {p3_exit:.2f} EUR<br>"
            if strategy_type == "MULTIPOINT_VECTOR":
                points_exit_info = (
                    f"P1 (Preço): {p1_exit:.2f} EUR<br>"
                    f"P2 (Média {short_window}): {p2_exit:.2f} EUR<br>"
                    f"P3 (Média {long_window}): {p3_exit:.2f} EUR<br>"
                    f"P4 (Média {p4_window if 'p4_window' in locals() else 50}): {p4_exit:.2f} EUR<br>"
                )
                if p5_filter_active or entry_mode == "5PONTOS":
                    points_exit_info += f"P5 (Média {p5_window if 'p5_window' in locals() else 200}): {p5_exit:.2f} EUR<br>"

            sell_text.append(
                f"❌ <b>SAÍDA ({trade['reason']})</b><br>"
                f"<b>Data</b>: {trade['exit_timestamp'].strftime('%Y-%m-%d %H:%M')}<br>"
                f"<b>Preço Venda (P1)</b>: {trade['exit_price']:.2f} EUR<br>"
                f"<b>Resultado</b>: {pnl_sign}{trade['pnl']:.2f} EUR ({pnl_pct_sign}{trade['pnl_pct']:.2f}%)<br><br>"
                f"<b>Estado dos Pontos de Medição:</b><br>{points_exit_info}<br>"
                f"<b>Justificação</b>: {justification}"
            )

        # Adicionar marcadores verdes de compra
        if buy_x:
            fig_prices.add_trace(go.Scatter(
                x=buy_x,
                y=buy_y,
                mode='markers',
                name='Entradas (BUY)',
                marker=dict(symbol='triangle-up', size=14, color='#10b981', line=dict(color='#047857', width=1.5)),
                text=buy_text,
                hoverinfo='text'
            ))

        # Adicionar marcadores vermelhos de venda
        if sell_x:
            fig_prices.add_trace(go.Scatter(
                x=sell_x,
                y=sell_y,
                mode='markers',
                name='Saídas (SELL/SL/TP)',
                marker=dict(symbol='triangle-down', size=14, color='#ef4444', line=dict(color='#b91c1c', width=1.5)),
                text=sell_text,
                hoverinfo='text'
            ))

        fig_prices.update_layout(
            hovermode='x unified', # Guia vertical unificada com todos os valores das médias
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=20, b=0),
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
            xaxis=dict(gridcolor='rgba(0,0,0,0.05)', tickfont=dict(color='#475569')),
            yaxis=dict(gridcolor='rgba(0,0,0,0.05)', tickfont=dict(color='#475569')),
            height=400
        )

        st.plotly_chart(fig_prices, width='stretch')
        st.caption("💡 Dica: Passe com o rato por cima de qualquer ponto do gráfico para ver a guia vertical unificada com o preço e o valor exato das duas médias móveis!")
        st.markdown('</div>', unsafe_allow_html=True)

        # --- TABELA DE OPERAÇÕES ---
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h4>📜 Histórico de Ordens Efetuadas</h4>', unsafe_allow_html=True)

        if trades:
            trades_df = pd.DataFrame(trades)

            # Cálculo dinâmico direto na UI para contornar qualquer bug de cache
            trades_df['position_value'] = trades_df['entry_price'] * trades_df['quantity']
            trades_df['capital_after'] = initial_capital + trades_df['pnl'].cumsum()

            trades_df_display = trades_df[[
                'entry_timestamp', 'exit_timestamp', 'action', 'entry_price', 'exit_price', 'quantity', 'position_value', 'pnl', 'pnl_pct', 'capital_after', 'reason'
            ]].copy()

            trades_df_display.columns = [
                'Entrada', 'Saída', 'Ação', 'Preço Entrada', 'Preço Saída', 'Quantidade', 'Valor Investido (EUR)', 'PnL (EUR)', 'Retorno (%)', 'Saldo da Banca (EUR)', 'Motivo Fecho'
            ]

            def color_pnl(val):
                color = '#059669' if val >= 0 else '#e11d48'
                return f'color: {color}; font-weight: bold;'

            st.dataframe(
                trades_df_display.style.map(color_pnl, subset=['PnL (EUR)', 'Retorno (%)'])
                .format({'Preço Entrada': '{:.2f}', 'Preço Saída': '{:.2f}', 'Quantidade': '{:.6f}', 'Valor Investido (EUR)': '{:.2f}', 'PnL (EUR)': '{:+.2f}', 'Retorno (%)': '{:+.2f}%', 'Saldo da Banca (EUR)': '{:.2f}'}),
                width='stretch'
            )
        else:
            st.info("Nenhuma operação foi efetuada durante esta simulação. Tente ajustar os parâmetros das médias móveis ou selecione um número maior de candles.")

        st.markdown('</div>', unsafe_allow_html=True)

    else:
        # Estado Inicial da UI
        st.markdown('<div class="glass-card" style="text-align: center; padding: 50px 20px;">', unsafe_allow_html=True)
        st.markdown('<h3 style="margin-top:0;">🚀 Pronto para Começar!</h3>', unsafe_allow_html=True)
        st.markdown(
            'Configure os parâmetros de estratégia e gestão de risco no **painel esquerdo** '
            'e carregue no botão **"Executar Simulação"** para correr o backtest com dados de mercado reais da Binance.',
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

# --- CONTEÚDO DA ABA 2: OTIMIZADOR DE PARÂMETROS ---
with tab_simulator:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<h3>🔮 Laboratório de Simulação & Otimização Unificado</h3>', unsafe_allow_html=True)
    st.markdown("Este laboratório permite-lhe testar teorias, visualizar o comportamento dos 5 pontos (com ou sem Reversão à Média) e executar o **Otimizador de Parâmetros integrado** para encontrar a configuração perfeita para qualquer bioma de mercado.")
    
    col_src1, col_src2 = st.columns([2, 3])
    with col_src1:
        market_source = st.radio(
            "Fonte de Mercado para Testes:",
            ["SINTETICO", "MOEDA_REAL"],
            format_func=lambda x: "🔮 Mercado Sintético (Passeio Aleatório / Browniano)" if x == "SINTETICO" else f"📈 Exemplo de Moeda Real da Barra Lateral ({symbol})",
            help="Escolha se deseja testar as estratégias num mercado gerado artificialmente ou usar dados históricos de uma moeda real."
        )

    sim_df = None
    if market_source == "SINTETICO":
        st.markdown("##### ⚙️ Configuração do Bioma de Teste Sintético")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            market_type_sim = st.selectbox(
                "Tipo de Mercado Simulado",
                ["Tendência de Alta Forte (Bull Market)", "Tendência de Baixa Forte (Bear Market)", "Mercado Lateral / Range (Consolidação)", "Hiper-Volátil Caótico (Chaos Market)"]
            )
        with col_s2:
            sim_steps = st.slider("Número de Velas (Passos)", 50, 500, 250, step=10, help="Quantidade de velas do gráfico sintético.")
            
        if "Alta" in market_type_sim or "Bull" in market_type_sim:
            drift = 0.5; volatility = 2.0
        elif "Baixa" in market_type_sim or "Bear" in market_type_sim:
            drift = -0.5; volatility = 2.0
        elif "Lateral" in market_type_sim:
            drift = 0.0; volatility = 1.0
        else:
            drift = 0.0; volatility = 6.0
            
        st.button("🔄 Gerar e Testar em Mercado Sintético Novo")
        
        np.random.seed(int(drift * 100 + volatility * 1000 + sim_steps))
        dt = 0.1
        prices = [100.0]
        for _ in range(sim_steps - 1):
            change = prices[-1] * (drift / 100.0 * dt + volatility / 100.0 * np.sqrt(dt) * np.random.normal())
            prices.append(max(5.0, prices[-1] + change))
            
        dates = pd.date_range(start="2026-01-01", periods=sim_steps, freq="4h")
        sim_df = pd.DataFrame({
            'open': prices,
            'high': [p * (1 + np.abs(np.random.normal(0, 0.002))) for p in prices],
            'low': [p * (1 - np.abs(np.random.normal(0, 0.002))) for p in prices],
            'close': prices,
            'volume': [1000] * sim_steps
        }, index=dates)
        
        sim_df['high'] = sim_df[['open', 'close', 'high']].max(axis=1)
        sim_df['low'] = sim_df[['open', 'close', 'low']].min(axis=1)
        
    else:
        if 'backtest_df' in st.session_state and st.session_state.backtest_df is not None:
            sim_df = st.session_state.backtest_df.copy()
            st.info(f"📈 Usando dados históricos de **{symbol} ({timeframe})** com {len(sim_df)} velas como base de testes!")
        else:
            st.warning("⚠️ Não foram encontrados dados reais na memória. Puxando dados rápidos da Binance...")
            collector = DataCollector(exchange_id='binance', symbol=symbol, timeframe=timeframe)
            sim_df = collector.get_ohlcv(limit=limit_candles)
            if sim_df is not None and not sim_df.empty:
                st.session_state.backtest_df = sim_df
                st.success("Dados reais carregados com sucesso!")

    if sim_df is not None and not sim_df.empty:
        st.session_state.sim_df_val = sim_df
        
        # Caching inteligente do backtest para evitar execução em loop nas atualizações de página
        run_sim = True
        current_config_hash = hash(str(config))
        if "sim_metrics" in st.session_state and st.session_state.get("sim_config_hash") == current_config_hash:
            run_sim = False
            
        if run_sim:
            sim_config = config.copy()
            sim_config["INITIAL_CAPITAL"] = 100.0
            
            sim_bt = Backtester(sim_config, logger)
            sim_trades, sim_cap_history = asyncio.run(sim_bt.run_backtest(sim_df))
            sim_metrics = sim_bt.get_performance_metrics()
            
            st.session_state.sim_metrics = sim_metrics
            st.session_state.sim_trades = sim_trades
            st.session_state.sim_cap_history = sim_cap_history
            st.session_state.sim_config_hash = current_config_hash
        else:
            sim_metrics = st.session_state.sim_metrics
            sim_trades = st.session_state.sim_trades
            sim_cap_history = st.session_state.sim_cap_history
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Retorno Simulação", f"{sim_metrics['total_return_pct']:.2f}%")
        with col_m2:
            st.metric("Trades Executados", f"{sim_metrics['num_trades']}")
        with col_m3:
            st.metric("Win Rate", f"{sim_metrics['win_rate']*100:.1f}%")
        with col_m4:
            st.metric("Max Drawdown", f"{sim_metrics['max_drawdown_pct']:.2f}%")
            
        sim_viz = sim_df.copy()
        if strategy_type == "PAULO_GOLD":
            sim_viz['Line_1'] = ta.trend.sma_indicator(sim_viz['close'], window=short_window)
            sim_viz['Line_2'] = ta.trend.sma_indicator(sim_viz['close'], window=long_window)
            l1_n, l2_n = f"MǸdia {short_window}", f"MǸdia {long_window}"
        elif strategy_type == "SMA_CROSSOVER":
            sim_viz['Line_1'] = ta.trend.sma_indicator(sim_viz['close'], window=short_window)
            sim_viz['Line_2'] = ta.trend.sma_indicator(sim_viz['close'], window=long_window)
            l1_n, l2_n = f"SMA {short_window}", f"SMA {long_window}"
        elif strategy_type == "EMA_CROSSOVER":
            sim_viz['Line_1'] = ta.trend.ema_indicator(sim_viz['close'], window=short_window)
            sim_viz['Line_2'] = ta.trend.ema_indicator(sim_viz['close'], window=long_window)
            l1_n, l2_n = f"EMA {short_window}", f"EMA {long_window}"
        else:
            sim_viz['Line_1'] = ta.trend.sma_indicator(sim_viz['close'], window=p2_window)
            sim_viz['Line_2'] = ta.trend.sma_indicator(sim_viz['close'], window=p3_window)
            sim_viz['Line_3'] = ta.trend.sma_indicator(sim_viz['close'], window=p4_window)
            if p5_filter_active or entry_mode == "5PONTOS":
                sim_viz['Line_4'] = ta.trend.sma_indicator(sim_viz['close'], window=p5_window)
            l1_n, l2_n, l3_n = f"P2 ({p2_window})", f"P3 ({p3_window})", f"P4 ({p4_window})"
            l4_n = f"P5 ({p5_window})" if (p5_filter_active or entry_mode == "5PONTOS") else None
            
        # Calcular a primeira linha média que o preço encontra (a mais próxima)
        if strategy_type in ["SMA_CROSSOVER", "EMA_CROSSOVER", "PAULO_GOLD"]:
            sim_viz['First_Line'] = sim_viz.apply(
                lambda row: max(row['Line_1'], row['Line_2']) if (pd.notna(row['Line_1']) and pd.notna(row['Line_2']) and row['close'] >= max(row['Line_1'], row['Line_2'])) else row['close'],
                axis=1
            )

        fig_sim = go.Figure()
        if strategy_type in ["SMA_CROSSOVER", "EMA_CROSSOVER", "PAULO_GOLD"]:
            fig_sim.add_trace(go.Scatter(
                x=sim_viz.index,
                y=sim_viz['First_Line'],
                mode='lines',
                line=dict(color='rgba(0,0,0,0)', width=0),
                showlegend=False,
                hoverinfo='skip'
            ))
        
        # Gerar OHLC pseudo-realista se faltar open, high, low
        if 'open' not in sim_viz.columns:
            import numpy as np
            np.random.seed(42)
            sim_viz['open'] = sim_viz['close'] - np.random.normal(0, 0.2, len(sim_viz))
            sim_viz['high'] = np.maximum(sim_viz['open'], sim_viz['close']) + np.abs(np.random.normal(0, 0.2, len(sim_viz)))
            sim_viz['low'] = np.minimum(sim_viz['open'], sim_viz['close']) - np.abs(np.random.normal(0, 0.2, len(sim_viz)))

        fig_sim.add_trace(go.Candlestick(
            x=sim_viz.index,
            open=sim_viz['open'],
            high=sim_viz['high'],
            low=sim_viz['low'],
            close=sim_viz['close'],
            name='Velas',
            increasing_line_color='#22c55e',
            decreasing_line_color='#ef4444'
        ))
        fig_sim.update_layout(xaxis_rangeslider_visible=False)
        
        for idx_s, t_s in enumerate(sim_trades):
            trade_mask = (sim_viz.index >= t_s['entry_timestamp']) & (sim_viz.index <= t_s['exit_timestamp'])
            trade_segment = sim_viz[trade_mask]
            if not trade_segment.empty:
                show_legend_s = (idx_s == 0)
                fig_sim.add_trace(go.Scatter(
                    x=trade_segment.index,
                    y=trade_segment['close'],
                    mode='lines',
                    name='Lagarta Ativa (Trade Open)',
                    line=dict(color='#22c55e', width=3.5),
                    showlegend=show_legend_s,
                    hovertemplate='Preço Ativo: %{y:.2f} EUR<extra></extra>'
                ))
                
        fig_sim.add_trace(go.Scatter(x=sim_viz.index, y=sim_viz['Line_1'], mode='lines', name=l1_n, line=dict(color='#0ea5e9', width=2), hovertemplate=f'{l1_n}: %{{y:.2f}} EUR<extra></extra>'))
        fig_sim.add_trace(go.Scatter(x=sim_viz.index, y=sim_viz['Line_2'], mode='lines', name=l2_n, line=dict(color=locals().get('line2_color', '#f97316'), width=2), hovertemplate=f'{l2_n}: %{{y:.2f}} EUR<extra></extra>'))
        
        if strategy_type.startswith("🎓"):
            fig_sim.add_trace(go.Scatter(x=sim_viz.index, y=sim_viz['Line_3'], mode='lines', name=locals().get('line3_name', 'Line_3'), line=dict(color=locals().get('line3_color', '#f59e0b'), width=1.5), hovertemplate=f'{locals().get("line3_name", "Line_3")}: %{{y:.2f}} EUR<extra></extra>'))
            
        if strategy_type == "MULTIPOINT_VECTOR":
            fig_sim.add_trace(go.Scatter(x=sim_viz.index, y=sim_viz['Line_3'], mode='lines', name=l3_n, line=dict(color='#10b981', width=1.5), hovertemplate=f'{l3_n}: %{{y:.2f}} EUR<extra></extra>'))
            if (p5_filter_active or entry_mode == "5PONTOS") and 'Line_4' in sim_viz:
                fig_sim.add_trace(go.Scatter(x=sim_viz.index, y=sim_viz['Line_4'], mode='lines', name=l4_n, line=dict(color='#8b5cf6', width=1.5), hovertemplate=f'{l4_n}: %{{y:.2f}} EUR<extra></extra>'))
                
        sim_buy_x, sim_buy_y, sim_buy_text = [], [], []
        sim_sell_x, sim_sell_y, sim_sell_text = [], [], []
        for t_s in sim_trades:
            entry_t = t_s['entry_timestamp']
            exit_t = t_s['exit_timestamp']
            
            sim_buy_x.append(entry_t)
            sim_buy_y.append(t_s['entry_price'])
            
            try:
                entry_row = sim_viz.loc[entry_t]
                p1_val = t_s['entry_price']
                p2_val = entry_row['Line_1'] if 'Line_1' in entry_row and not pd.isna(entry_row['Line_1']) else 0
                p3_val = entry_row['Line_2'] if 'Line_2' in entry_row and not pd.isna(entry_row['Line_2']) else 0
                p4_val = entry_row['Line_3'] if 'Line_3' in entry_row and not pd.isna(entry_row['Line_3']) else 0
                p5_val = entry_row['Line_4'] if 'Line_4' in entry_row and 'Line_4' in sim_viz and not pd.isna(entry_row['Line_4']) else 0
                
                buy_info = (
                    f"📥 <b>ENTRADA COMPRA (BUY)</b><br>"
                    f"<b>Data</b>: {entry_t.strftime('%Y-%m-%d %H:%M') if hasattr(entry_t, 'strftime') else entry_t}<br>"
                    f"<b>Preço Entrada (P1)</b>: {p1_val:.2f} EUR<br>"
                    f"<b>P2 (Média {p2_window})</b>: {p2_val:.2f} EUR<br>"
                    f"<b>P3 (Média {p3_window})</b>: {p3_val:.2f} EUR<br>"
                    f"<b>P4 (Média {p4_window})</b>: {p4_val:.2f} EUR<br>"
                )
                if p5_filter_active or entry_mode == "5PONTOS":
                    buy_info += f"<b>P5 (Média {p5_window})</b>: {p5_val:.2f} EUR<br>"
                buy_info += f"<i>Gatilho: Entrada {entry_mode}!</i>"
                sim_buy_text.append(buy_info)
            except Exception:
                sim_buy_text.append(f"COMPRA a {t_s['entry_price']:.2f}")

            sim_sell_x.append(exit_t)
            sim_sell_y.append(t_s['exit_price'])
            
            try:
                exit_row = sim_viz.loc[exit_t]
                p1_val = t_s['exit_price']
                p2_val = exit_row['Line_1'] if 'Line_1' in exit_row and not pd.isna(exit_row['Line_1']) else 0
                p3_val = exit_row['Line_2'] if 'Line_2' in exit_row and not pd.isna(exit_row['Line_2']) else 0
                p4_val = exit_row['Line_3'] if 'Line_3' in exit_row and not pd.isna(exit_row['Line_3']) else 0
                p5_val = exit_row['Line_4'] if 'Line_4' in exit_row and 'Line_4' in sim_viz and not pd.isna(exit_row['Line_4']) else 0
                
                sell_info = (
                    f"📤 <b>SAÍDA VENDA ({t_s['reason']})</b><br>"
                    f"<b>Data</b>: {exit_t.strftime('%Y-%m-%d %H:%M') if hasattr(exit_t, 'strftime') else exit_t}<br>"
                    f"<b>Preço Saída (P1)</b>: {p1_val:.2f} EUR<br>"
                    f"<b>P2 (Média {p2_window})</b>: {p2_val:.2f} EUR<br>"
                    f"<b>P3 (Média {p3_window})</b>: {p3_val:.2f} EUR<br>"
                    f"<b>P4 (Média {p4_window})</b>: {p4_val:.2f} EUR<br>"
                )
                if p5_filter_active or entry_mode == "5PONTOS":
                    sell_info += f"<b>P5 (Média {p5_window})</b>: {p5_val:.2f} EUR<br>"
                sell_info += f"<i>Resultado: {t_s['pnl']:.2f} EUR ({t_s['pnl_pct']:.2f}%)</i>"
                sim_sell_text.append(sell_info)
            except Exception:
                sim_sell_text.append(f"VENDA a {t_s['exit_price']:.2f} ({t_s['reason']})")
                
        fig_sim.add_trace(go.Scatter(x=sim_buy_x, y=sim_buy_y, mode='markers', name='COMPRA', marker=dict(symbol='triangle-up', size=14, color='#10b981', line=dict(width=1.5, color='#047857')), text=sim_buy_text, hoverinfo='text'))
        fig_sim.add_trace(go.Scatter(x=sim_sell_x, y=sim_sell_y, mode='markers', name='VENDA', marker=dict(symbol='triangle-down', size=14, color='#ef4444', line=dict(width=1.5, color='#b91c1c')), text=sim_sell_text, hoverinfo='text'))
        
        fig_sim.update_layout(
            title=f"Laboratório Visual - Bioma de Testes ({market_source})", 
            hovermode='x unified', 
            template='plotly_white', 
            height=500, 
            margin=dict(l=10, r=10, t=40, b=10)
        )
        st.plotly_chart(fig_sim, width='stretch')

        if strategy_type == "MULTIPOINT_VECTOR":
            import logging
            main_logger = logging.getLogger("TradingBot")
            old_level = main_logger.level
            main_logger.setLevel(logging.WARNING)

            entries = ["3PONTOS", "4PONTOS", "5PONTOS"]
            exits = ["P2", "P3", "P4"]
            
            matrix_data = []
            for ent in entries:
                row_dict = {"Modo de Entrada": "Super-Ágil (3P)" if ent == "3PONTOS" else ("Equilibrada (4P)" if ent == "4PONTOS" else "Conservadora (5P)")}
                for ex in exits:
                    m_cfg = config.copy()
                    m_cfg.update({
                        "STRATEGY_TYPE": "MULTIPOINT_VECTOR",
                        "ENTRY_MODE": ent,
                        "EXIT_MODE": ex,
                        "P2_WINDOW": p2_window,
                        "P3_WINDOW": p3_window,
                        "P4_WINDOW": p4_window,
                        "P5_WINDOW": p5_window,
                        "P5_SLOPE_FILTER_ACTIVE": False if ent == "3PONTOS" else p5_filter_active,
                        "INITIAL_CAPITAL": 100.0
                    })
                    bt_mat = Backtester(m_cfg, main_logger)
                    asyncio.run(bt_mat.run_backtest(sim_df))
                    met = bt_mat.get_performance_metrics()
                    
                    cell_label = f"Saída {ex}"
                    row_dict[cell_label] = {
                        "ret": met["total_return_pct"],
                        "dd": met["max_drawdown_pct"],
                        "trades": met["num_trades"],
                        "entry": ent,
                        "exit": ex
                    }
                matrix_data.append(row_dict)
            
            main_logger.setLevel(old_level)
            
            st.markdown("---")
            st.markdown("<h3>📊 A Matriz de Lógicas da Lagarta (Análise de 9 Lógicas)</h3>", unsafe_allow_html=True)
            st.markdown("Esta tabela exibe o resultado financeiro de **todas as 9 combinações de Entrada e Saída** possíveis para a nossa lagarta **neste mesmo mercado ativo**. Descubra instantaneamente qual a melhor forma de se mover perante estas ondas!")
            st.info("💡 **Segredo Quantitativo**: Se os resultados de saídas diferentes (P2, P3, P4) derem o mesmo valor na tabela, significa que a tua **Gestão de Risco (Take Profit ou Stop Loss)** fechou as operações antes de o preço tocar nos gatilhos de saída das médias! Para veres a diferença dinâmica das saídas da lagarta pura, experimenta desativar o Take Profit ou alargar o Stop Loss!")
            
            best_ret = -999.0
            best_combo = None
            for row in matrix_data:
                for ex in ["P2", "P3", "P4"]:
                    cell = row[f"Saída {ex}"]
                    if cell["ret"] > best_ret:
                        best_ret = cell["ret"]
                        best_combo = cell
            
            html_table = "<table style='width:100%; border-collapse: collapse; text-align: center; font-family: sans-serif;'>"
            html_table += "<tr style='background-color: #0f172a; color: white;'>"
            html_table += "<th style='padding: 12px; border: 1px solid #1e293b;'>Gatilho de Entrada (Pernas)</th>"
            html_table += "<th style='padding: 12px; border: 1px solid #1e293b;'>⚡ Saída Rápida (P2 / Média 9)</th>"
            html_table += "<th style='padding: 12px; border: 1px solid #1e293b;'>⚖️ Saída Intermédia (P3 / Média 21)</th>"
            html_table += "<th style='padding: 12px; border: 1px solid #1e293b;'>🐢 Saída Lenta (P4 / Média 50)</th>"
            html_table += "</tr>"
            
            for row in matrix_data:
                html_table += "<tr style='border-bottom: 1px solid #cbd5e1;'>"
                html_table += f"<td style='padding: 15px; font-weight: bold; background-color: #f8fafc; border: 1px solid #cbd5e1;'>{row['Modo de Entrada']}</td>"
                for ex in ["P2", "P3", "P4"]:
                    cell = row[f"Saída {ex}"]
                    ret = cell["ret"]
                    dd = cell["dd"]
                    num_t = cell["trades"]
                    
                    is_champion = (cell == best_combo)
                    bg_color = "rgba(16, 185, 129, 0.15)" if ret > 0 else "rgba(239, 68, 68, 0.08)"
                    border_style = "border: 2px solid #3b82f6;" if is_champion else "border: 1px solid #cbd5e1;"
                    
                    html_table += f"<td style='padding: 12px; background-color: {bg_color}; {border_style}'>"
                    html_table += f"<div style='font-size: 1.1rem; font-weight: bold; color: {'#10b981' if ret > 0 else '#ef4444'};'>{ret:+.2f}%</div>"
                    html_table += f"<div style='font-size: 0.8rem; color: #64748b;'>(Drawdown: {dd:.2f}%)</div>"
                    html_table += f"<div style='font-size: 0.8rem; color: #475569;'>{num_t} Trades</div>"
                    if is_champion:
                        html_table += "<div style='margin-top: 6px; padding: 2px 6px; background-color: #3b82f6; color: white; border-radius: 4px; font-size: 0.75rem; font-weight: bold; display: inline-block;'>🏆 Campeã</div>"
                    html_table += "</td>"
                html_table += "</tr>"
            html_table += "</table>"
            st.markdown(html_table, unsafe_allow_html=True)
            
            col_l1, col_l2 = st.columns([3, 1])
            with col_l1:
                st.markdown(f"💡 **Análise Quantitativa**: A melhor lógica para este bioma de mercado foi **Entrada {best_combo['entry']} + Saída {best_combo['exit']}**, obtendo um retorno de **{best_combo['ret']:+.2f}%**.")
            with col_l2:
                if st.button("🏆 Aplicar Lógica Campeã", width='stretch'):
                    st.session_state.entry_mode_val = best_combo["entry"]
                    st.session_state.exit_mode_val = best_combo["exit"]
                    if best_combo["entry"] == "3PONTOS":
                        st.session_state.p5_filter_active_val = False
                    st.success("Lógica campeã carregada com sucesso! Re-execute para visualizar.")
                    st.rerun()

        st.markdown("---")
        st.markdown("<h3>⚡ Otimizador de Parâmetros Integrado</h3>", unsafe_allow_html=True)
        st.markdown("Corra o Otimizador de Parâmetros **sobre este mercado ativo** para varrer o comportamento da estratégia e encontrar a combinação perfeita de Médias, Stop Loss e Take Profit.")
        
        if "opt_sim_results" not in st.session_state:
            st.session_state.opt_sim_results = None

        if st.button("⚡ Executar Varredura de Parâmetros neste Mercado", width='stretch'):
            with st.spinner("A processar varredura de parâmetros..."):
                main_logger = logging.getLogger("TradingBot")
                old_level = main_logger.level
                main_logger.setLevel(logging.WARNING)

                sw_range = [5, 9, 12]
                lw_range = [21, 26, 50]
                sl_range = [1.5, 2.5]
                tp_range = [5.0, 10.0]
                ts_range = [False, True]
                
                results_sint = []
                for sw in sw_range:
                    for lw in lw_range:
                        if sw >= lw:
                            continue
                        for sl in sl_range:
                            for tp in tp_range:
                                for ts in ts_range:
                                    local_cfg = config.copy()
                                    local_cfg.update({
                                        "SHORT_WINDOW": sw,
                                        "LONG_WINDOW": lw,
                                        "P2_WINDOW": sw,
                                        "P3_WINDOW": lw,
                                        "P4_WINDOW": 50,
                                        "P5_WINDOW": 200,
                                        "P5_SLOPE_FILTER_ACTIVE": False,
                                        "STOP_LOSS_PERCENT": sl,
                                        "TAKE_PROFIT_PERCENT": tp,
                                        "TRAILING_STOP_ACTIVE": ts,
                                        "INITIAL_CAPITAL": 100.0
                                    })
                                    
                                    bt_sint = Backtester(local_cfg, main_logger)
                                    asyncio.run(bt_sint.run_backtest(sim_df))
                                    metrics_sint = bt_sint.get_performance_metrics()
                                    
                                    results_sint.append({
                                        "P2 (Rápida)": sw,
                                        "P3 (Confirmadora)": lw,
                                        "Stop Loss (%)": sl,
                                        "Take Profit (%)": tp,
                                        "Trailing Stop": ts,
                                        "Retorno (%)": metrics_sint["total_return_pct"],
                                        "Max Drawdown (%)": metrics_sint["max_drawdown_pct"],
                                        "Trades Executados": metrics_sint["num_trades"],
                                        "Win Rate (%)": metrics_sint["win_rate"] * 100
                                    })
                                    
                main_logger.setLevel(old_level)
                if results_sint:
                    st.session_state.opt_sim_results = sorted(results_sint, key=lambda x: x["Retorno (%)"], reverse=True)
                    st.success("Otimização concluída com sucesso!")
                else:
                    st.warning("Nenhum resultado obtido.")
                    
        if st.session_state.opt_sim_results is not None:
            top_df = pd.DataFrame(st.session_state.opt_sim_results)
            st.markdown("##### 🏆 Top 5 Configurações Vencedoras")
            st.dataframe(top_df.head(5).style.format({
                "Retorno (%)": "{:+.2f}%",
                "Max Drawdown (%)": "{:.2f}%",
                "Win Rate (%)": "{:.1f}%",
                "Stop Loss (%)": "{:.1f}%",
                "Take Profit (%)": "{:.1f}%"
            }), width='stretch')
            
            best_row = top_df.iloc[0]
            if st.button("🏆 Aplicar Melhor Configuração Otimizada (Top 1) no Painel Principal", width='stretch'):
                st.session_state.p2_window_val = int(best_row["P2 (Rápida)"])
                st.session_state.p3_window_val = int(best_row["P3 (Confirmadora)"])
                st.session_state.short_window_val = int(best_row["P2 (Rápida)"])
                st.session_state.long_window_val = int(best_row["P3 (Confirmadora)"])
                st.session_state.stop_loss_pct_val = float(best_row["Stop Loss (%)"])
                st.session_state.take_profit_pct_val = float(best_row["Take Profit (%)"])
                st.session_state.trailing_stop_active_val = bool(best_row["Trailing Stop"])
                st.session_state.p5_filter_active_val = False
                
                st.success("Configuração Top 1 aplicada com sucesso no Painel de Configurações! Re-execute para visualizar.")
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# --- CONTEÚDO DA ABA 4: O CENTRO DE TREINAMENTO DA LAGARTA IA (VERSÃO 3.0) ---
with tab_math_lab:
    import tab_math_lab
    tab_math_lab.render()
# =========================================================================
# SEPARADOR 5: JOGO DO TRADER QUANTITATIVO (ARENA BLIND TRADER)
# =========================================================================
with tab_trader_game:
    import variables_registry
    variables_registry.initialize_variables_registry()

    # =========================================================================
    # SEPARADOR 5: JOGO DO TRADER QUANTITATIVO (ARENA BLIND TRADER)
    # =========================================================================
    with tab_trader_game:
        import os, json, time
        import numpy as np
        import pandas as pd
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        highscores_file = "trader_highscores.json"

        # --- ESTADO DO JOGO ---
        if "tg_active" not in st.session_state: st.session_state.tg_active = False
        if "tg_step" not in st.session_state: st.session_state.tg_step = 144
        if "tg_capital" not in st.session_state: st.session_state.tg_capital = 100.0
        if "tg_position" not in st.session_state: st.session_state.tg_position = "NONE"
        if "tg_entry_price" not in st.session_state: st.session_state.tg_entry_price = 0.0
        if "tg_entry_step" not in st.session_state: st.session_state.tg_entry_step = 0
        if "tg_trades" not in st.session_state: st.session_state.tg_trades = []
        if "tg_data" not in st.session_state: st.session_state.tg_data = None
        if "tg_trader_name" not in st.session_state: st.session_state.tg_trader_name = "Trader Anon"
        if "tg_running" not in st.session_state: st.session_state.tg_running = False
        if "tg_game_finished" not in st.session_state: st.session_state.tg_game_finished = False
        if "tg_strategy_type" not in st.session_state: st.session_state.tg_strategy_type = "Default"

        # Carregar ultimo jogo persistido caso o estado ativo seja None e existam dados salvos
        if "tg_data" not in st.session_state or st.session_state.tg_data is None:
            if os.path.exists("last_game_data.csv") and os.path.exists("last_game_state.json"):
                try:
                    st.session_state.tg_data = pd.read_csv("last_game_data.csv", index_col=0, parse_dates=True)
                    with open("last_game_state.json", "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    st.session_state.tg_capital = meta.get("capital", 100.0)
                    st.session_state.tg_trades = meta.get("trades", [])
                    st.session_state.tg_trader_name = meta.get("trader_name", "Trader Anon")
                    st.session_state.tg_p2 = meta.get("p2", 5)
                    st.session_state.tg_p3 = meta.get("p3", 13)
                    st.session_state.tg_p4 = meta.get("p4", 21)
                    st.session_state.tg_p5 = meta.get("p5", 55)
                    st.session_state.tg_p6 = meta.get("p6", 144)
                    st.session_state.tg_game_finished = True
                    st.session_state.tg_active = False
                except Exception:
                    st.session_state.tg_data = None
            else:
                st.session_state.tg_data = None

        # Periodos das medias
        if "tg_p2" not in st.session_state: st.session_state.tg_p2 = 5
        if "tg_p3" not in st.session_state: st.session_state.tg_p3 = 13
        if "tg_p4" not in st.session_state: st.session_state.tg_p4 = 21
        if "tg_p5" not in st.session_state: st.session_state.tg_p5 = 55
        if "tg_p6" not in st.session_state: st.session_state.tg_p6 = 144

        # Visibilidade persistente entre batimentos

        # Gestao de risco
        if "tg_sl_active" not in st.session_state: st.session_state.tg_sl_active = True
        if "tg_sl_pct" not in st.session_state: st.session_state.tg_sl_pct = 2.0
        if "tg_tp_active" not in st.session_state: st.session_state.tg_tp_active = False
        if "tg_tp_pct" not in st.session_state: st.session_state.tg_tp_pct = 4.0
        if "tg_ts_active" not in st.session_state: st.session_state.tg_ts_active = False
        if "tg_ts_pct" not in st.session_state: st.session_state.tg_ts_pct = 1.5
        if "tg_highest_price" not in st.session_state: st.session_state.tg_highest_price = 0.0
        if "tg_lowest_price" not in st.session_state: st.session_state.tg_lowest_price = 999999.0

        # Visibilidade das linhas — persiste entre batimentos via session_state
        if "tg_vis_price" not in st.session_state: st.session_state.tg_vis_price = True
        if "tg_vis_canal" not in st.session_state: st.session_state.tg_vis_canal = True
        if "tg_vis_vector" not in st.session_state: st.session_state.tg_vis_vector = True
        if "tg_vis_sma5" not in st.session_state: st.session_state.tg_vis_sma5 = True
        if "tg_vis_sma13" not in st.session_state: st.session_state.tg_vis_sma13 = True
        if "tg_vis_sma21" not in st.session_state: st.session_state.tg_vis_sma21 = True
        if "tg_vis_sma55" not in st.session_state: st.session_state.tg_vis_sma55 = True
        if "tg_vis_sma144" not in st.session_state: st.session_state.tg_vis_sma144 = True

        # Bot co-piloto / autonomo
        if "tg_bot_mode" not in st.session_state: st.session_state.tg_bot_mode = "Manual"
        if "tg_bot_compress_thresh" not in st.session_state: st.session_state.tg_bot_compress_thresh = 2.0
        if "tg_bot_vel_thresh" not in st.session_state: st.session_state.tg_bot_vel_thresh = 0.03

        def _build_chart(sub_df, df_full, title_str, show_full_range=False):
            """Constroi o grafico Plotly. Reutilizavel para modo jogo e modo revisao."""
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.82, 0.18], vertical_spacing=0.03)

            upper_band = sub_df['avg_sma'] + 1.0 * sub_df['sma_std']
            lower_band = sub_df['avg_sma'] - 1.0 * sub_df['sma_std']
            fig.add_trace(go.Scatter(
                x=sub_df.index.tolist() + sub_df.index.tolist()[::-1],
                y=upper_band.tolist() + lower_band.tolist()[::-1],
                fill='toself', fillcolor='rgba(148,163,184,0.12)',
                line=dict(color='rgba(255,255,255,0)'), hoverinfo="skip",
                name='Canal Desvio Padrao', visible=True
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=sub_df.index, y=sub_df['avg_sma'], name='Media do Vetor',
                line=dict(color='#94a3b8', width=1.5, dash='dash'), visible=True
            ), row=1, col=1)
            fig.add_trace(go.Scatter(x=sub_df.index, y=sub_df['sma_5'], name=f'SMA {st.session_state.tg_p2} (Rapida)', line=dict(color='#00E676', width=2), visible=True), row=1, col=1)
            fig.add_trace(go.Scatter(x=sub_df.index, y=sub_df['sma_13'], name=f'SMA {st.session_state.tg_p3}', line=dict(color='#00B0FF', width=2), visible=True), row=1, col=1)
            fig.add_trace(go.Scatter(x=sub_df.index, y=sub_df['sma_21'], name=f'SMA {st.session_state.tg_p4}', line=dict(color='#FF9100', width=2), visible=True), row=1, col=1)
            fig.add_trace(go.Scatter(x=sub_df.index, y=sub_df['sma_55'], name=f'SMA {st.session_state.tg_p5}', line=dict(color='#D500F9', width=2), visible=True), row=1, col=1)
            fig.add_trace(go.Scatter(x=sub_df.index, y=sub_df['sma_144'], name=f'SMA {st.session_state.tg_p6} (Lenta)', line=dict(color='#FF1744', width=2), visible=True), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=sub_df.index, y=sub_df['close'], name='Preco Real',
                line=dict(color='#1e293b', width=3), visible=True
            ), row=1, col=1)

            # Marcadores de trades sobre a janela visivel
            game_buy_x, game_buy_y, game_sell_x, game_sell_y = [], [], [], []
            for tr in st.session_state.tg_trades:
                if "entry_step" in tr and "exit_step" in tr:
                    entry_time = df_full.index[tr['entry_step']]
                    exit_time = df_full.index[tr['exit_step']]
                    if tr['type'] == "LONG":
                        if entry_time in sub_df.index: game_buy_x.append(entry_time); game_buy_y.append(tr['entry_price'])
                        if exit_time in sub_df.index: game_sell_x.append(exit_time); game_sell_y.append(tr['exit_price'])
                    else:
                        if entry_time in sub_df.index: game_sell_x.append(entry_time); game_sell_y.append(tr['entry_price'])
                        if exit_time in sub_df.index: game_buy_x.append(exit_time); game_buy_y.append(tr['exit_price'])
            if game_buy_x:
                fig.add_trace(go.Scatter(x=game_buy_x, y=game_buy_y, mode='markers', name='Compra / Fecho Short', marker=dict(symbol='triangle-up', size=14, color='#10b981')), row=1, col=1)
            if game_sell_x:
                fig.add_trace(go.Scatter(x=game_sell_x, y=game_sell_y, mode='markers', name='Venda / Fecho Long', marker=dict(symbol='triangle-down', size=14, color='#ef4444')), row=1, col=1)

            vel_dir = sub_df['velocity'].apply(lambda x: 1.0 if x > 0 else (-1.0 if x < 0 else 0.0)).tolist()
            acc_dir = sub_df['acceleration'].apply(lambda x: 1.0 if x > 0 else (-1.0 if x < 0 else 0.0)).tolist()
            fig.add_trace(go.Heatmap(
                x=sub_df.index, y=['Forca (Acel.)', 'Direcao (Vel.)'], z=[acc_dir, vel_dir],
                colorscale=[[0.0,'#e74c3c'],[0.5,'#cbd5e1'],[1.0,'#2ecc71']],
                showscale=False, hovertemplate='%{x}<br>%{y}: %{z}<extra></extra>'
            ), row=2, col=1)

            chart_height = 520 if show_full_range else 500
            fig.update_layout(
                title=title_str,
                hovermode='x unified', template='plotly_white', height=chart_height,
                margin=dict(l=10, r=10, t=40, b=160),
                uirevision='game_chart',
                legend=dict(
                    orientation="h", yanchor="top", y=-0.35,
                    xanchor="center", x=0.5,
                    font=dict(size=11),
                    bgcolor="rgba(255,255,255,0.85)",
                    bordercolor="rgba(0,0,0,0.1)", borderwidth=1
                )
            )
            fig.update_xaxes(showgrid=True, gridcolor='#e2e8f0', row=1, col=1)
            fig.update_yaxes(showgrid=True, gridcolor='#e2e8f0', row=1, col=1)
            return fig

        def generate_game_market():
            np.random.seed(int(time.time() * 100) % 100000)
            steps = 260
            drift = np.random.choice([0.08, -0.04, 0.0, 0.12])
            volatility = np.random.uniform(1.3, 3.2)
            dt = 0.1
            prices = [100.0]
            for _ in range(steps - 1):
                change = prices[-1] * (drift / 100.0 * dt + volatility / 100.0 * np.sqrt(dt) * np.random.normal())
                prices.append(max(10.0, prices[-1] + change))
            dates = pd.date_range(start="2026-01-01", periods=steps, freq="1h")
            df = pd.DataFrame({
                'close': prices,
                'open': [p - np.random.normal(0, 0.1) for p in prices],
                'high': [p + abs(np.random.normal(0, 0.15)) for p in prices],
                'low': [p - abs(np.random.normal(0, 0.15)) for p in prices],
                'volume': [1000] * steps
            }, index=dates)
            df['sma_5'] = df['close'].rolling(window=st.session_state.tg_p2).mean()
            df['sma_13'] = df['close'].rolling(window=st.session_state.tg_p3).mean()
            df['sma_21'] = df['close'].rolling(window=st.session_state.tg_p4).mean()
            df['sma_55'] = df['close'].rolling(window=st.session_state.tg_p5).mean()
            df['sma_144'] = df['close'].rolling(window=st.session_state.tg_p6).mean()
            smas = ['sma_5','sma_13','sma_21','sma_55','sma_144']
            df['avg_sma'] = df[smas].mean(axis=1)
            df['sma_std'] = df[smas].std(axis=1)
            df['stretching'] = df[smas].sub(df['avg_sma'], axis=0).abs().mean(axis=1).div(df['avg_sma']).mul(100)
            df['velocity'] = df['sma_5'].diff(periods=2)
            df['acceleration'] = df['velocity'].diff(periods=2)
            df['volatility'] = df['close'].rolling(window=20, min_periods=1).std()
            
            def classify_regime_row(row):
                p = row['close']
                s2 = row['sma_5']
                s3 = row['sma_13']
                s4 = row['sma_21']
                s5 = row['sma_55']
                s6 = row['sma_144']
                v = row['velocity']
                vol = row['volatility']
                stretch = row['stretching']
                if pd.isna(s6) or pd.isna(v) or pd.isna(vol) or pd.isna(stretch):
                    return "LATERAL"
                is_bull_trend = (s2 > s3) and (s3 > s4) and (s4 > s5) and (v > 0)
                is_bear_trend = (s2 < s3) and (s3 < s4) and (s4 < s5) and (v < 0)
                if stretch < 0.6:
                    return "LATERAL"
                elif is_bull_trend:
                    return "BULL"
                elif is_bear_trend:
                    return "BEAR"
                elif vol > p * 0.012:
                    return "CAOTICO"
                else:
                    return "LATERAL"
            
            df['regime'] = df.apply(classify_regime_row, axis=1)
            df['disp_pct'] = (df['sma_5'] - df['sma_144']) / df['sma_144'] * 100
            smas_col = ['sma_5','sma_13','sma_21','sma_55','sma_144']
            df['mola_pct'] = df[smas_col].std(axis=1) / df[smas_col].mean(axis=1) * 100
            df['infil_bull'] = (df['sma_5'] > df['sma_13']) & (df['sma_13'] > df['sma_21']) & (df['sma_55'] < df['sma_144'])
            df['infil_bear'] = (df['sma_5'] < df['sma_13']) & (df['sma_13'] < df['sma_21']) & (df['sma_55'] > df['sma_144'])
            df['reteste_val'] = ((df['close'] - df['sma_55']).abs() / df['sma_55'] * 100 < 0.8) | ((df['close'] - df['sma_144']).abs() / df['sma_144'] * 100 < 0.8)
            
            # 4 novos indicadores dinâmicos para a Arena
            delta_t = df['close'].diff()
            gain_t = delta_t.clip(lower=0).rolling(window=14).mean()
            loss_t = (-delta_t.clip(upper=0)).rolling(window=14).mean()
            rs_t = gain_t / (loss_t + 1e-9)
            df['rsi_14'] = 100 - (100 / (1 + rs_t))

            bb_std_t = df['close'].rolling(window=20).std()
            bb_mid_t = df['close'].rolling(window=20).mean()
            df['bb_dist'] = ((df['close'] - (bb_mid_t - 2 * bb_std_t)) / (4 * bb_std_t + 1e-9)) * 100

            macd_line_t = df['close'].ewm(span=12, adjust=False).mean() - df['close'].ewm(span=26, adjust=False).mean()
            macd_signal_t = macd_line_t.ewm(span=9, adjust=False).mean()
            df['macd_hist'] = macd_line_t - macd_signal_t

            if 'high' in df.columns and 'low' in df.columns:
                tr_t = np.maximum(df['high'] - df['low'], np.maximum((df['high'] - df['close'].shift()).abs(), (df['low'] - df['close'].shift()).abs()))
            else:
                tr_t = df['close'].diff().abs()
            df['atr_14'] = tr_t.rolling(window=14).mean()
            
            df.bfill(inplace=True)
            return df

        def recalculate_indicators():
            if st.session_state.tg_data is not None:
                df = st.session_state.tg_data
                df['sma_5'] = df['close'].rolling(window=st.session_state.tg_p2).mean()
                df['sma_13'] = df['close'].rolling(window=st.session_state.tg_p3).mean()
                df['sma_21'] = df['close'].rolling(window=st.session_state.tg_p4).mean()
                df['sma_55'] = df['close'].rolling(window=st.session_state.tg_p5).mean()
                df['sma_144'] = df['close'].rolling(window=st.session_state.tg_p6).mean()
                smas = ['sma_5','sma_13','sma_21','sma_55','sma_144']
                df['avg_sma'] = df[smas].mean(axis=1)
                df['sma_std'] = df[smas].std(axis=1)
                df['stretching'] = df[smas].sub(df['avg_sma'], axis=0).abs().mean(axis=1).div(df['avg_sma']).mul(100)
                df['velocity'] = df['sma_5'].diff(periods=2)
                df['acceleration'] = df['velocity'].diff(periods=2)
                df['volatility'] = df['close'].rolling(window=20, min_periods=1).std()
                
                def classify_regime_row(row):
                    p = row['close']
                    s2 = row['sma_5']
                    s3 = row['sma_13']
                    s4 = row['sma_21']
                    s5 = row['sma_55']
                    s6 = row['sma_144']
                    v = row['velocity']
                    vol = row['volatility']
                    stretch = row['stretching']
                    if pd.isna(s6) or pd.isna(v) or pd.isna(vol) or pd.isna(stretch):
                        return "LATERAL"
                    is_bull_trend = (s2 > s3) and (s3 > s4) and (s4 > s5) and (v > 0)
                    is_bear_trend = (s2 < s3) and (s3 < s4) and (s4 < s5) and (v < 0)
                    if stretch < 0.6:
                        return "LATERAL"
                    elif is_bull_trend:
                        return "BULL"
                    elif is_bear_trend:
                        return "BEAR"
                    elif vol > p * 0.012:
                        return "CAOTICO"
                    else:
                        return "LATERAL"
                
                df['regime'] = df.apply(classify_regime_row, axis=1)
                df['disp_pct'] = (df['sma_5'] - df['sma_144']) / df['sma_144'] * 100
                smas_col = ['sma_5','sma_13','sma_21','sma_55','sma_144']
                df['mola_pct'] = df[smas_col].std(axis=1) / df[smas_col].mean(axis=1) * 100
                df['infil_bull'] = (df['sma_5'] > df['sma_13']) & (df['sma_13'] > df['sma_21']) & (df['sma_55'] < df['sma_144'])
                df['infil_bear'] = (df['sma_5'] < df['sma_13']) & (df['sma_13'] < df['sma_21']) & (df['sma_55'] > df['sma_144'])
                df['reteste_val'] = ((df['close'] - df['sma_55']).abs() / df['sma_55'] * 100 < 0.8) | ((df['close'] - df['sma_144']).abs() / df['sma_144'] * 100 < 0.8)
                
                # 4 novos indicadores dinâmicos para a Arena
                delta_t = df['close'].diff()
                gain_t = delta_t.clip(lower=0).rolling(window=14).mean()
                loss_t = (-delta_t.clip(upper=0)).rolling(window=14).mean()
                rs_t = gain_t / (loss_t + 1e-9)
                df['rsi_14'] = 100 - (100 / (1 + rs_t))

                bb_std_t = df['close'].rolling(window=20).std()
                bb_mid_t = df['close'].rolling(window=20).mean()
                df['bb_dist'] = ((df['close'] - (bb_mid_t - 2 * bb_std_t)) / (4 * bb_std_t + 1e-9)) * 100

                macd_line_t = df['close'].ewm(span=12, adjust=False).mean() - df['close'].ewm(span=26, adjust=False).mean()
                macd_signal_t = macd_line_t.ewm(span=9, adjust=False).mean()
                df['macd_hist'] = macd_line_t - macd_signal_t

                if 'high' in df.columns and 'low' in df.columns:
                    tr_t = np.maximum(df['high'] - df['low'], np.maximum((df['high'] - df['close'].shift()).abs(), (df['low'] - df['close'].shift()).abs()))
                else:
                    tr_t = df['close'].diff().abs()
                df['atr_14'] = tr_t.rolling(window=14).mean()
                
                df.bfill(inplace=True)
                st.session_state.tg_data = df

        # Sincronização automática se as médias mudaram
        current_smas = (st.session_state.tg_p2, st.session_state.tg_p3, st.session_state.tg_p4, st.session_state.tg_p5, st.session_state.tg_p6)
        if st.session_state.get('tg_last_calculated_smas') != current_smas:
            recalculate_indicators()
            st.session_state.tg_last_calculated_smas = current_smas

        def compute_bot_signal(df, step):
            """Calcula sinal do bot: LONG / SHORT / HOLD com confianca 0-100%."""
            if step < 10:
                return "HOLD", 0.0, {}
                
            # Verificar se a estratégia ativa é o Cérebro de Consenso DNA
            if st.session_state.get("tg_strategy_type", "Default") == "Cérebro de Consenso (Lab)" and os.path.exists("bot_consensus_dna.json"):
                try:
                    with open("bot_consensus_dna.json", "r", encoding="utf-8") as f:
                        dna = json.load(f)
                    reg = df['regime'].iloc[step]
                    reg_rules = dna["regimes"].get(reg, {})
                    
                    if reg_rules and reg_rules.get("active", False):
                        stretch = df['stretching'].iloc[step]
                        mola_pct = df['mola_pct'].iloc[step]
                        disp_pct = df['disp_pct'].iloc[step]
                        acc = df['acceleration'].iloc[step]
                        velocity = df['velocity'].iloc[step]
                        volatility = df['volatility'].iloc[step]
                        
                        rsi = df['rsi_14'].iloc[step] if 'rsi_14' in df.columns and not pd.isna(df['rsi_14'].iloc[step]) else 50.0
                        bb = df['bb_dist'].iloc[step] if 'bb_dist' in df.columns and not pd.isna(df['bb_dist'].iloc[step]) else 50.0
                        macd = df['macd_hist'].iloc[step] if 'macd_hist' in df.columns and not pd.isna(df['macd_hist'].iloc[step]) else 0.0
                        atr = df['atr_14'].iloc[step] if 'atr_14' in df.columns and not pd.isna(df['atr_14'].iloc[step]) else 1.0
                        
                        # --- CONDIÇÕES DE COMPRA (LONG) ---
                        opp_rules = reg_rules.get("buy_rules", {})
                        cond_long = {}
                        
                        mola_mean = opp_rules.get("mola", {}).get("mean", 2.0)
                        cond_long["Compressão Mola (Coesão)"] = (mola_pct <= mola_mean * 1.3) if mola_mean > 0 else True
                        
                        strt_mean = opp_rules.get("stretching", {}).get("mean", 1.5)
                        cond_long["Estiramento Mola (Stretching)"] = (stretch <= strt_mean * 1.3) if strt_mean > 0 else True
                        
                        disp_mean = opp_rules.get("disp", {}).get("mean", 0.0)
                        cond_long["Dispersão Vetorial"] = (disp_pct >= disp_mean - 1.5)
                        
                        vel_mean = opp_rules.get("velocity", {}).get("mean", 0.0)
                        cond_long["Velocidade Tendência"] = (velocity >= 0) if vel_mean >= 0 else (velocity < 0)
                        
                        acc_mean = opp_rules.get("acceleration", {}).get("mean", 0.0)
                        cond_long["Aceleração Reversão"] = (acc >= 0) if acc_mean >= 0 else (acc < 0)
                        
                        vol_mean = opp_rules.get("volatility", {}).get("mean", 10.0)
                        cond_long["Volatilidade Controlada"] = (volatility <= vol_mean * 1.5) if vol_mean > 0 else True
                        
                        cond_long["Infiltração Bull (Regime)"] = bool(df['infil_bull'].iloc[step])
                        cond_long["Reteste Fibonacci"] = bool(df['reteste_val'].iloc[step])
                        
                        rsi_mean = opp_rules.get("rsi", {}).get("mean", 50.0)
                        cond_long["Momentum Força (RSI)"] = (abs(rsi - rsi_mean) <= 20.0)
                        
                        bb_mean = opp_rules.get("bb", {}).get("mean", 50.0)
                        cond_long["Fronteira Est. (Bollinger)"] = (abs(bb - bb_mean) <= 30.0)
                        
                        macd_mean = opp_rules.get("macd", {}).get("mean", 0.0)
                        cond_long["Aceleração Macro (MACD)"] = (macd >= 0) if macd_mean >= 0 else (macd < 0)
                        
                        atr_mean = opp_rules.get("atr", {}).get("mean", 1.0)
                        cond_long["Respiração Mercado (ATR)"] = (atr <= atr_mean * 1.5) if atr_mean > 0 else True

                        # --- CONDIÇÕES DE VENDA (SHORT) ---
                        thr_rules = reg_rules.get("sell_rules", {})
                        cond_short = {}
                        
                        mola_mean = thr_rules.get("mola", {}).get("mean", 2.0)
                        cond_short["Compressão Mola (Coesão)"] = (mola_pct <= mola_mean * 1.3) if mola_mean > 0 else True
                        
                        strt_mean = thr_rules.get("stretching", {}).get("mean", 1.5)
                        cond_short["Estiramento Mola (Stretching)"] = (stretch <= strt_mean * 1.3) if strt_mean > 0 else True
                        
                        disp_mean = thr_rules.get("disp", {}).get("mean", 0.0)
                        cond_short["Dispersão Vetorial"] = (disp_pct <= disp_mean + 1.5)
                        
                        vel_mean = thr_rules.get("velocity", {}).get("mean", 0.0)
                        cond_short["Velocidade Tendência"] = (velocity <= 0) if vel_mean <= 0 else (velocity > 0)
                        
                        acc_mean = thr_rules.get("acceleration", {}).get("mean", 0.0)
                        cond_short["Aceleração Reversão"] = (acc <= 0) if acc_mean <= 0 else (acc > 0)
                        
                        vol_mean = thr_rules.get("volatility", {}).get("mean", 10.0)
                        cond_short["Volatilidade Controlada"] = (volatility <= vol_mean * 1.5) if vol_mean > 0 else True
                        
                        cond_short["Infiltração Bear (Regime)"] = bool(df['infil_bear'].iloc[step])
                        cond_short["Reteste Fibonacci"] = bool(df['reteste_val'].iloc[step])
                        
                        rsi_mean = thr_rules.get("rsi", {}).get("mean", 50.0)
                        cond_short["Momentum Força (RSI)"] = (abs(rsi - rsi_mean) <= 20.0)
                        
                        bb_mean = thr_rules.get("bb", {}).get("mean", 50.0)
                        cond_short["Fronteira Est. (Bollinger)"] = (abs(bb - bb_mean) <= 30.0)
                        
                        macd_mean = thr_rules.get("macd", {}).get("mean", 0.0)
                        cond_short["Aceleração Macro (MACD)"] = (macd <= 0) if macd_mean <= 0 else (macd > 0)
                        
                        atr_mean = thr_rules.get("atr", {}).get("mean", 1.0)
                        cond_short["Respiração Mercado (ATR)"] = (atr <= atr_mean * 1.5) if atr_mean > 0 else True

                        long_score = sum(cond_long.values()) / len(cond_long) if cond_long else 0.0
                        short_score = sum(cond_short.values()) / len(cond_short) if cond_short else 0.0
                        
                        if long_score > short_score and long_score >= (st.session_state.get('tg_min_confidence_pct', 80.0) / 100.0):
                            return "LONG", round(long_score * 100), cond_long
                        elif short_score > long_score and short_score >= (st.session_state.get('tg_min_confidence_pct', 80.0) / 100.0):
                            return "SHORT", round(short_score * 100), cond_short
                        else:
                            return "HOLD", round(max(long_score, short_score) * 100), cond_long if long_score >= short_score else cond_short
                except Exception:
                    pass
                    
            # Fallback para regras padrão do jogo
            vel = df['velocity'].iloc[step]
            acc = df['acceleration'].iloc[step]
            stretch = df['stretching'].iloc[step]
            
            rsi = df['rsi_14'].iloc[step] if 'rsi_14' in df.columns and not pd.isna(df['rsi_14'].iloc[step]) else 50.0
            bb = df['bb_dist'].iloc[step] if 'bb_dist' in df.columns and not pd.isna(df['bb_dist'].iloc[step]) else 50.0
            macd = df['macd_hist'].iloc[step] if 'macd_hist' in df.columns and not pd.isna(df['macd_hist'].iloc[step]) else 0.0
            atr = df['atr_14'].iloc[step] if 'atr_14' in df.columns and not pd.isna(df['atr_14'].iloc[step]) else 1.0
            
            cond_long = {
                "Compressão Mola (<2.5)": bool(df['mola_pct'].iloc[step] <= 2.5),
                "Estiramento Mola (Média)": bool(stretch <= 2.0),
                "Dispersão Vetorial (>0)": bool(df['disp_pct'].iloc[step] >= 0),
                "Velocidade Tendência (+)": bool(vel > 0),
                "Aceleração Reversão (+)": bool(acc > 0),
                "Volatilidade Saudável": bool(df['volatility'].iloc[step] <= 5.0),
                "Infiltração Bull": bool(df['infil_bull'].iloc[step]),
                "Reteste Fibonacci": bool(df['reteste_val'].iloc[step]),
                "Momentum Força (RSI < 70)": bool(rsi <= 70.0),
                "Fronteira Est. (Bollinger < 80)": bool(bb <= 80.0),
                "Aceleração Macro (MACD > 0)": bool(macd >= 0),
                "Respiração Mercado (ATR)": bool(atr <= 1.5)
            }
            
            cond_short = {
                "Compressão Mola (<2.5)": bool(df['mola_pct'].iloc[step] <= 2.5),
                "Estiramento Mola (Média)": bool(stretch <= 2.0),
                "Dispersão Vetorial (<0)": bool(df['disp_pct'].iloc[step] <= 0),
                "Velocidade Tendência (-)": bool(vel < 0),
                "Aceleração Reversão (-)": bool(acc < 0),
                "Volatilidade Saudável": bool(df['volatility'].iloc[step] <= 5.0),
                "Infiltração Bear": bool(df['infil_bear'].iloc[step]),
                "Reteste Fibonacci": bool(df['reteste_val'].iloc[step]),
                "Momentum Força (RSI > 30)": bool(rsi >= 30.0),
                "Fronteira Est. (Bollinger > 20)": bool(bb >= 20.0),
                "Aceleração Macro (MACD < 0)": bool(macd <= 0),
                "Respiração Mercado (ATR)": bool(atr <= 1.5)
            }

            long_score  = sum(cond_long.values())  / len(cond_long)
            short_score = sum(cond_short.values()) / len(cond_short)

            if long_score > short_score and long_score >= 0.6:
                return "LONG", round(long_score * 100), cond_long
            elif short_score > long_score and short_score >= 0.6:
                return "SHORT", round(short_score * 100), cond_short
            else:
                return "HOLD", round(max(long_score, short_score) * 100), cond_long if long_score >= short_score else cond_short
        
        def start_new_game():
            st.session_state.tg_data = generate_game_market()
            st.session_state.tg_step = 144
            st.session_state.tg_capital = 100.0
            st.session_state.tg_position = "NONE"
            st.session_state.tg_entry_price = 0.0
            st.session_state.tg_entry_step = 0
            st.session_state.tg_trades = []
            st.session_state.tg_active = True
            st.session_state.tg_game_finished = False
            st.session_state.tg_running = False
            st.session_state.tg_highest_price = 0.0
            st.session_state.tg_lowest_price = 999999.0

        def load_highscores():
            if os.path.exists(highscores_file):
                try:
                    with open(highscores_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    return []
            return []

        def save_highscore(name, final_capital, trades_count):
            scores = load_highscores()
            config_desc = (f"Medias:[{st.session_state.tg_p2},{st.session_state.tg_p3},{st.session_state.tg_p4},{st.session_state.tg_p5},{st.session_state.tg_p6}] "
                           f"SL={st.session_state.tg_sl_pct if st.session_state.tg_sl_active else 'OFF'}% "
                           f"TP={st.session_state.tg_tp_pct if st.session_state.tg_tp_active else 'OFF'}% "
                           f"TS={st.session_state.tg_ts_pct if st.session_state.tg_ts_active else 'OFF'}%")
            scores.append({
                "name": name, "capital": float(final_capital),
                "return": float(final_capital - 100.0), "trades": int(trades_count),
                "config": config_desc, "date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
            })
            scores = sorted(scores, key=lambda x: x["capital"], reverse=True)[:5]
            try:
                with open(highscores_file, "w", encoding="utf-8") as f:
                    json.dump(scores, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        def save_last_game_persistent(df):
            try:
                df.to_csv("last_game_data.csv", index=True)
                game_meta = {
                    "capital": st.session_state.tg_capital,
                    "trades": st.session_state.tg_trades,
                    "trader_name": st.session_state.tg_trader_name,
                    "p2": st.session_state.tg_p2,
                    "p3": st.session_state.tg_p3,
                    "p4": st.session_state.tg_p4,
                    "p5": st.session_state.tg_p5,
                    "p6": st.session_state.tg_p6,
                }
                with open("last_game_state.json", "w", encoding="utf-8") as f:
                    json.dump(game_meta, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        # CSS dos botoes casino - ARCADE LED STYLE
        st.markdown("""
        <style>
        div[data-testid="column"]:has(div.game-control-anchor) {
            background: linear-gradient(160deg, rgba(15,23,42,0.95) 0%, rgba(30,41,59,0.98) 100%) !important;
            backdrop-filter: blur(20px) !important;
            border-radius: 18px !important;
            border: 1px solid rgba(124,58,237,0.35) !important;
            padding: 16px !important;
            box-shadow: 0 0 0 1px rgba(124,58,237,0.15), 0 8px 32px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.06) !important;
        }
        @keyframes pulse-green-led {
            0%   { box-shadow: 0 0 10px 3px #10b981, 0 0 28px 8px rgba(16,185,129,0.5), inset 0 0 16px rgba(16,185,129,0.25); }
            50%  { box-shadow: 0 0 22px 9px #10b981, 0 0 55px 18px rgba(16,185,129,0.8), inset 0 0 28px rgba(16,185,129,0.55); }
            100% { box-shadow: 0 0 10px 3px #10b981, 0 0 28px 8px rgba(16,185,129,0.5), inset 0 0 16px rgba(16,185,129,0.25); }
        }
        @keyframes pulse-red-led {
            0%   { box-shadow: 0 0 10px 3px #ef4444, 0 0 28px 8px rgba(239,68,68,0.5), inset 0 0 16px rgba(239,68,68,0.25); }
            50%  { box-shadow: 0 0 22px 9px #ef4444, 0 0 55px 18px rgba(239,68,68,0.8), inset 0 0 28px rgba(239,68,68,0.55); }
            100% { box-shadow: 0 0 10px 3px #ef4444, 0 0 28px 8px rgba(239,68,68,0.5), inset 0 0 16px rgba(239,68,68,0.25); }
        }
        .casino-long-active button, .casino-long-inactive button,
        .casino-short-active button, .casino-short-inactive button,
        .casino-blocked button {
            border-radius: 16px !important;
            font-weight: 900 !important;
            font-size: 13px !important;
            letter-spacing: 0.5px !important;
            text-transform: uppercase !important;
            transition: all 0.15s ease !important;
            height: 72px !important;
            min-height: 72px !important;
        }
        .casino-long-active button {
            background: linear-gradient(180deg, #34d399 0%, #10b981 35%, #059669 70%, #064e3b 100%) !important;
            color: #ffffff !important;
            border: 3px solid #6ee7b7 !important;
            outline: 3px solid rgba(16,185,129,0.5) !important; outline-offset: 2px !important;
            text-shadow: 0 0 10px rgba(255,255,255,0.9), 0 1px 2px rgba(0,0,0,0.6) !important;
            animation: pulse-green-led 1.4s ease-in-out infinite !important;
        }
        .casino-long-active button:hover { filter: brightness(1.15) !important; transform: scale(1.02) !important; }
        .casino-long-inactive button {
            background: linear-gradient(180deg, #052e16 0%, #064e3b 40%, #065f46 100%) !important;
            color: #6ee7b7 !important;
            border: 3px solid #134e4a !important;
            outline: 3px solid rgba(16,185,129,0.08) !important; outline-offset: 2px !important;
            text-shadow: 0 0 6px rgba(110,231,183,0.35) !important;
            box-shadow: 0 0 5px rgba(16,185,129,0.1), inset 0 2px 5px rgba(0,0,0,0.5) !important;
        }
        .casino-long-inactive button:hover {
            background: linear-gradient(180deg, #065f46 0%, #059669 40%, #10b981 100%) !important;
            color: #fff !important;
            box-shadow: 0 0 20px rgba(16,185,129,0.55), inset 0 0 14px rgba(16,185,129,0.2) !important;
            transform: scale(1.01) !important;
        }
        .casino-short-active button {
            background: linear-gradient(180deg, #fca5a5 0%, #ef4444 35%, #dc2626 70%, #7f1d1d 100%) !important;
            color: #ffffff !important;
            border: 3px solid #fca5a5 !important;
            outline: 3px solid rgba(239,68,68,0.5) !important; outline-offset: 2px !important;
            text-shadow: 0 0 10px rgba(255,255,255,0.9), 0 1px 2px rgba(0,0,0,0.6) !important;
            animation: pulse-red-led 1.4s ease-in-out infinite !important;
        }
        .casino-short-active button:hover { filter: brightness(1.15) !important; transform: scale(1.02) !important; }
        .casino-short-inactive button {
            background: linear-gradient(180deg, #450a0a 0%, #7f1d1d 40%, #991b1b 100%) !important;
            color: #fca5a5 !important;
            border: 3px solid #7f1d1d !important;
            outline: 3px solid rgba(239,68,68,0.08) !important; outline-offset: 2px !important;
            text-shadow: 0 0 6px rgba(252,165,165,0.35) !important;
            box-shadow: 0 0 5px rgba(239,68,68,0.1), inset 0 2px 5px rgba(0,0,0,0.5) !important;
        }
        .casino-short-inactive button:hover {
            background: linear-gradient(180deg, #991b1b 0%, #dc2626 40%, #ef4444 100%) !important;
            color: #fff !important;
            box-shadow: 0 0 20px rgba(239,68,68,0.55), inset 0 0 14px rgba(239,68,68,0.2) !important;
            transform: scale(1.01) !important;
        }
        .casino-blocked button {
            background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%) !important;
            color: #334155 !important;
            border: 3px solid #1e293b !important;
            opacity: 0.4 !important;
            cursor: not-allowed !important;
        }
        .review-banner {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            border-radius: 14px; padding: 18px 24px; margin-bottom: 14px;
            border: 1px solid rgba(99,102,241,0.4);
            box-shadow: 0 0 40px rgba(99,102,241,0.15);
        }
        .review-stat {
            text-align: center; padding: 8px 12px;
            background: rgba(255,255,255,0.05); border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.08);
        }
        </style>
        """, unsafe_allow_html=True)

        # --- COCKPIT DE CONFIGURACOES ---
        with st.expander("Configuração: Períodos das Médias & Risco", expanded=not st.session_state.tg_active and not st.session_state.tg_game_finished):
            col_c1, col_c2, col_c3 = st.columns([0.8, 1.8, 1.0])
            with col_c1:
                st.markdown("##### Jogador")
                name_input = st.text_input("Nome:", value=st.session_state.tg_trader_name, key="tg_name_wdg")
                if name_input: st.session_state.tg_trader_name = name_input
                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
                if st.button("Iniciar / Novo Jogo", type="primary", width='stretch'):
                    start_new_game()
                    st.rerun()
            with col_c2:
                st.markdown("##### 📏 Médias Ativas no Jogo")
                # Exibir as médias como badges premium estilizados
                st.markdown(f"""
                <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px;">
                    <div style="background: rgba(14, 165, 233, 0.1); border: 1px solid rgba(14, 165, 233, 0.3); border-radius: 6px; padding: 6px 12px; text-align: center; flex: 1; min-width: 60px;">
                        <div style="font-size: 10px; color: #0ea5e9; text-transform: uppercase; font-weight: bold;">Rápida (P2)</div>
                        <div style="font-size: 18px; font-weight: 900; color: var(--text-color);">{st.session_state.tg_p2}</div>
                    </div>
                    <div style="background: rgba(249, 115, 22, 0.1); border: 1px solid rgba(249, 115, 22, 0.3); border-radius: 6px; padding: 6px 12px; text-align: center; flex: 1; min-width: 60px;">
                        <div style="font-size: 10px; color: #f97316; text-transform: uppercase; font-weight: bold;">Confirm (P3)</div>
                        <div style="font-size: 18px; font-weight: 900; color: var(--text-color);">{st.session_state.tg_p3}</div>
                    </div>
                    <div style="background: rgba(168, 85, 247, 0.1); border: 1px solid rgba(168, 85, 247, 0.3); border-radius: 6px; padding: 6px 12px; text-align: center; flex: 1; min-width: 60px;">
                        <div style="font-size: 10px; color: #a855f7; text-transform: uppercase; font-weight: bold;">Média (P4)</div>
                        <div style="font-size: 18px; font-weight: 900; color: var(--text-color);">{st.session_state.tg_p4}</div>
                    </div>
                    <div style="background: rgba(236, 72, 153, 0.1); border: 1px solid rgba(236, 72, 153, 0.3); border-radius: 6px; padding: 6px 12px; text-align: center; flex: 1; min-width: 60px;">
                        <div style="font-size: 10px; color: #ec4899; text-transform: uppercase; font-weight: bold;">Longa (P5)</div>
                        <div style="font-size: 18px; font-weight: 900; color: var(--text-color);">{st.session_state.tg_p5}</div>
                    </div>
                    <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 6px; padding: 6px 12px; text-align: center; flex: 1; min-width: 60px;">
                        <div style="font-size: 10px; color: #10b981; text-transform: uppercase; font-weight: bold;">Mestra (P6)</div>
                        <div style="font-size: 18px; font-weight: 900; color: var(--text-color);">{st.session_state.tg_p6}</div>
                    </div>
                </div>
                <div style="font-size: 11px; color: #64748b; margin-top: 10px; font-style: italic; text-align: center;">
                    💡 Altere os períodos das médias móveis na Central de Variáveis no topo da página.
                </div>
                """, unsafe_allow_html=True)
            with col_c3:
                st.markdown("##### Estratégia do Robô")
                strat_choice = st.selectbox(
                    "Modelo de Decisão:", ["Default (Fórmula do Jogo)", "Cérebro de Consenso (Lab)"],
                    index=0 if st.session_state.tg_strategy_type == "Default" else 1,
                    key="tg_strategy_type_select"
                )
                if strat_choice != st.session_state.tg_strategy_type:
                    st.session_state.tg_strategy_type = strat_choice
                    if "Cérebro" in strat_choice:
                        if os.path.exists("bot_consensus_dna.json"):
                            try:
                                with open("bot_consensus_dna.json", "r", encoding="utf-8") as f:
                                    dna = json.load(f)
                                smas = dna.get("smas", [5, 13, 21, 55, 144])
                                st.session_state.tg_p2 = smas[0]
                                st.session_state.tg_p3 = smas[1]
                                st.session_state.tg_p4 = smas[2]
                                st.session_state.tg_p5 = smas[3]
                                st.session_state.tg_p6 = smas[4]
                                recalculate_indicators()
                                st.toast("Médias sincronizadas com o Cérebro de Consenso!")
                            except Exception:
                                pass
                    st.rerun()
                
                st.markdown("##### 🛡️ Gestão de Risco Ativa")
                sl_status = f"<span style='color:#10b981; font-weight:bold;'>LIGADO ({st.session_state.tg_sl_pct:.1f}%)</span>" if st.session_state.tg_sl_active else "<span style='color:#64748b; font-style:italic;'>Desativado</span>"
                tp_status = f"<span style='color:#10b981; font-weight:bold;'>LIGADO ({st.session_state.tg_tp_pct:.1f}%)</span>" if st.session_state.tg_tp_active else "<span style='color:#64748b; font-style:italic;'>Desativado</span>"
                ts_status = f"<span style='color:#10b981; font-weight:bold;'>LIGADO ({st.session_state.tg_ts_pct:.1f}%)</span>" if st.session_state.tg_ts_active else "<span style='color:#64748b; font-style:italic;'>Desativado</span>"
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding: 10px; font-size: 13px; margin-top: 5px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom: 6px;">
                        <span style="color:#94a3b8;">Stop Loss (SL):</span>
                        <span>{sl_status}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-bottom: 6px;">
                        <span style="color:#94a3b8;">Take Profit (TP):</span>
                        <span>{tp_status}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between;">
                        <span style="color:#94a3b8;">Trailing Stop (TS):</span>
                        <span>{ts_status}</span>
                    </div>
                </div>
                <div style="font-size: 11px; color: #64748b; margin-top: 10px; font-style: italic; text-align: center;">
                    💡 Ajuste os parâmetros de risco na Central de Variáveis no topo.
                </div>
                """, unsafe_allow_html=True)
        # --- NOVO EXPANDER: AUTO-TREINO (MACHINE LEARNING AUTÓNOMO) ---
        with st.expander("🧠 Otimizador de Auto-Treino (Machine Learning Autónomo)", expanded=False):
            col_t1, col_t2 = st.columns([1, 1])
            with col_t1:
                training_source = st.selectbox(
                    "Fonte de Aprendizagem:",
                    ["Sintético (Aleatório)", "Real Binance (BTC/USDT)", "Real Binance (ETH/USDT)"],
                    key="tg_train_source"
                )
                training_candles = st.number_input(
                    "Volume de Treino (Velas):",
                    min_value=100, max_value=20000, value=1000, step=100,
                    key="tg_train_candles"
                )
            with col_t2:
                st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
                if st.button("🚀 Iniciar Auto-Treino Estatístico", width='stretch', type="primary", key="tg_btn_train"):
                    st.toast("A inicializar motor de aprendizagem...")
                    
                    # 1. Obter dados
                    df_train = None
                    if "Sintético" in training_source:
                        st.toast("A gerar mercado didático...")
                        np.random.seed(int(time.time() * 100) % 100000)
                        drift = np.random.choice([0.08, -0.04, 0.0, 0.12])
                        volatility = np.random.uniform(1.3, 3.2)
                        dt = 0.1
                        prices = [100.0]
                        for _ in range(int(training_candles) - 1):
                            change = prices[-1] * (drift / 100.0 * dt + volatility / 100.0 * np.sqrt(dt) * np.random.normal())
                            prices.append(max(10.0, prices[-1] + change))
                        dates = pd.date_range(start="2026-01-01", periods=int(training_candles), freq="1h")
                        df_train = pd.DataFrame({
                            'close': prices,
                            'open': [p - np.random.normal(0, 0.1) for p in prices],
                            'high': [p + abs(np.random.normal(0, 0.15)) for p in prices],
                            'low': [p - abs(np.random.normal(0, 0.15)) for p in prices],
                            'volume': [1000] * int(training_candles)
                        }, index=dates)
                    else:
                        st.toast("A descarregar dados históricos da Binance...")
                        from data_collector import DataCollector
                        symbol = "BTC/USDT" if "BTC" in training_source else "ETH/USDT"
                        try:
                            collector = DataCollector(exchange_id='binance', symbol=symbol, timeframe='1h')
                            df_train = collector.get_ohlcv(limit=int(training_candles))
                        except Exception as e:
                            st.error(f"Erro ao descarregar da Binance: {e}")
                            
                    if df_train is not None and not df_train.empty:
                        st.toast("A calcular feixe de médias de Fibonacci...")
                        p2_t = st.session_state.get('tg_p2', 5)
                        p3_t = st.session_state.get('tg_p3', 13)
                        p4_t = st.session_state.get('tg_p4', 21)
                        p5_t = st.session_state.get('tg_p5', 55)
                        p6_t = st.session_state.get('tg_p6', 144)
                        
                        df_train['sma_5'] = df_train['close'].rolling(window=p2_t).mean()
                        df_train['sma_13'] = df_train['close'].rolling(window=p3_t).mean()
                        df_train['sma_21'] = df_train['close'].rolling(window=p4_t).mean()
                        df_train['sma_55'] = df_train['close'].rolling(window=p5_t).mean()
                        df_train['sma_144'] = df_train['close'].rolling(window=p6_t).mean()
                        smas_t = ['sma_5','sma_13','sma_21','sma_55','sma_144']
                        df_train['avg_sma'] = df_train[smas_t].mean(axis=1)
                        df_train['sma_std'] = df_train[smas_t].std(axis=1)
                        df_train['stretching'] = df_train[smas_t].sub(df_train['avg_sma'], axis=0).abs().mean(axis=1).div(df_train['avg_sma']).mul(100)
                        df_train['velocity'] = df_train['sma_5'].diff(periods=2)
                        df_train['acceleration'] = df_train['velocity'].diff(periods=2)
                        df_train['volatility'] = df_train['close'].rolling(window=20, min_periods=1).std()

                        # 4 novos indicadores dinâmicos
                        delta_t = df_train['close'].diff()
                        gain_t = delta_t.clip(lower=0).rolling(window=14).mean()
                        loss_t = (-delta_t.clip(upper=0)).rolling(window=14).mean()
                        rs_t = gain_t / (loss_t + 1e-9)
                        df_train['rsi_14'] = 100 - (100 / (1 + rs_t))

                        bb_std_t = df_train['close'].rolling(window=20).std()
                        bb_mid_t = df_train['close'].rolling(window=20).mean()
                        df_train['bb_dist'] = ((df_train['close'] - (bb_mid_t - 2 * bb_std_t)) / (4 * bb_std_t + 1e-9)) * 100

                        macd_line_t = df_train['close'].ewm(span=12, adjust=False).mean() - df_train['close'].ewm(span=26, adjust=False).mean()
                        macd_signal_t = macd_line_t.ewm(span=9, adjust=False).mean()
                        df_train['macd_hist'] = macd_line_t - macd_signal_t

                        if 'high' in df_train.columns and 'low' in df_train.columns:
                            tr_t = np.maximum(df_train['high'] - df_train['low'], np.maximum((df_train['high'] - df_train['close'].shift()).abs(), (df_train['low'] - df_train['close'].shift()).abs()))
                        else:
                            tr_t = df_train['close'].diff().abs()
                        df_train['atr_14'] = tr_t.rolling(window=14).mean()
                        
                        def classify_regime_row_t(row):
                            p = row['close']
                            s2 = row['sma_5']
                            s3 = row['sma_13']
                            s4 = row['sma_21']
                            s5 = row['sma_55']
                            s6 = row['sma_144']
                            v = row['velocity']
                            vol = row['volatility']
                            stretch = row['stretching']
                            if pd.isna(s6) or pd.isna(v) or pd.isna(vol) or pd.isna(stretch):
                                return "LATERAL"
                            is_bull_trend = (s2 > s3) and (s3 > s4) and (s4 > s5) and (v > 0)
                            is_bear_trend = (s2 < s3) and (s3 < s4) and (s4 < s5) and (v < 0)
                            if stretch < 0.6:
                                return "LATERAL"
                            elif is_bull_trend:
                                return "BULL"
                            elif is_bear_trend:
                                return "BEAR"
                            elif vol > p * 0.012:
                                return "CAOTICO"
                            else:
                                return "LATERAL"
                        
                        df_train['regime'] = df_train.apply(classify_regime_row_t, axis=1)
                        df_train['disp_pct'] = (df_train['sma_5'] - df_train['sma_144']) / df_train['sma_144'] * 100
                        df_train['mola_pct'] = df_train[smas_t].std(axis=1) / df_train[smas_t].mean(axis=1) * 100
                        df_train['infil_bull'] = (df_train['sma_5'] > df_train['sma_13']) & (df_train['sma_13'] > df_train['sma_21']) & (df_train['sma_55'] < df_train['sma_144'])
                        df_train['infil_bear'] = (df_train['sma_5'] < df_train['sma_13']) & (df_train['sma_13'] < df_train['sma_21']) & (df_train['sma_55'] > df_train['sma_144'])
                        df_train['reteste_val'] = ((df_train['close'] - df_train['sma_55']).abs() / df_train['sma_55'] * 100 < 0.8) | ((df_train['close'] - df_train['sma_144']).abs() / df_train['sma_144'] * 100 < 0.8)
                        df_train.bfill(inplace=True)
                        
                        st.toast("A processar treino massivo...")
                        pos_t = "NONE"
                        ent_p_t = 0.0
                        ent_step_t = 0
                        trades_t = []
                        
                        dna_t = {"smas": [p2_t, p3_t, p4_t, p5_t, p6_t], "regimes": {}}
                        if os.path.exists("bot_consensus_dna.json"):
                            try:
                                with open("bot_consensus_dna.json", "r", encoding="utf-8") as f:
                                    dna_t = json.load(f)
                            except Exception:
                                pass
                                
                        for step_t in range(p6_t + 10, len(df_train)):
                            price_now_t = df_train['close'].iloc[step_t]
                            
                            if pos_t == "LONG":
                                pnl_pct_t = (price_now_t - ent_p_t) / ent_p_t * 100
                                if pnl_pct_t <= -st.session_state.get('tg_sl_pct', 2.0):
                                    trades_t.append({
                                        "type": "LONG", "entry_price": ent_p_t, "exit_price": price_now_t, "pnl_pct": pnl_pct_t,
                                        "regime": df_train['regime'].iloc[ent_step_t], "mola": df_train['mola_pct'].iloc[ent_step_t],
                                        "stretch": df_train['stretching'].iloc[ent_step_t], "acc": df_train['acceleration'].iloc[ent_step_t],
                                        "disp": df_train['disp_pct'].iloc[ent_step_t],
                                        "vol": df_train['volatility'].iloc[ent_step_t],
                                        "vel": df_train['velocity'].iloc[ent_step_t],
                                        "infil": bool(df_train['infil_bull'].iloc[ent_step_t]),
                                        "reteste": bool(df_train['reteste_val'].iloc[ent_step_t]),
                                        "rsi": float(df_train['rsi_14'].iloc[ent_step_t]) if not pd.isna(df_train['rsi_14'].iloc[ent_step_t]) else 50.0,
                                        "bb": float(df_train['bb_dist'].iloc[ent_step_t]) if not pd.isna(df_train['bb_dist'].iloc[ent_step_t]) else 50.0,
                                        "macd": float(df_train['macd_hist'].iloc[ent_step_t]) if not pd.isna(df_train['macd_hist'].iloc[ent_step_t]) else 0.0,
                                        "atr": float(df_train['atr_14'].iloc[ent_step_t]) if not pd.isna(df_train['atr_14'].iloc[ent_step_t]) else 0.0,
                                        # Exits
                                        "mola_exit": df_train['mola_pct'].iloc[step_t],
                                        "stretch_exit": df_train['stretching'].iloc[step_t],
                                        "acc_exit": df_train['acceleration'].iloc[step_t],
                                        "disp_exit": df_train['disp_pct'].iloc[step_t],
                                        "vol_exit": df_train['volatility'].iloc[step_t],
                                        "vel_exit": df_train['velocity'].iloc[step_t],
                                        "infil_exit": bool(df_train['infil_bull'].iloc[step_t]),
                                        "reteste_exit": bool(df_train['reteste_val'].iloc[step_t]),
                                        "rsi_exit": float(df_train['rsi_14'].iloc[step_t]) if not pd.isna(df_train['rsi_14'].iloc[step_t]) else 50.0,
                                        "bb_exit": float(df_train['bb_dist'].iloc[step_t]) if not pd.isna(df_train['bb_dist'].iloc[step_t]) else 50.0,
                                        "macd_exit": float(df_train['macd_hist'].iloc[step_t]) if not pd.isna(df_train['macd_hist'].iloc[step_t]) else 0.0,
                                        "atr_exit": float(df_train['atr_14'].iloc[step_t]) if not pd.isna(df_train['atr_14'].iloc[step_t]) else 0.0
                                    })
                                    pos_t = "NONE"
                                    continue
                            elif pos_t == "SHORT":
                                pnl_pct_t = (ent_p_t - price_now_t) / ent_p_t * 100
                                if pnl_pct_t <= -st.session_state.get('tg_sl_pct', 2.0):
                                    trades_t.append({
                                        "type": "SHORT", "entry_price": ent_p_t, "exit_price": price_now_t, "pnl_pct": pnl_pct_t,
                                        "regime": df_train['regime'].iloc[ent_step_t], "mola": df_train['mola_pct'].iloc[ent_step_t],
                                        "stretch": df_train['stretching'].iloc[ent_step_t], "acc": df_train['acceleration'].iloc[ent_step_t],
                                        "disp": df_train['disp_pct'].iloc[ent_step_t],
                                        "vol": df_train['volatility'].iloc[ent_step_t],
                                        "vel": df_train['velocity'].iloc[ent_step_t],
                                        "infil": bool(df_train['infil_bear'].iloc[ent_step_t]),
                                        "reteste": bool(df_train['reteste_val'].iloc[ent_step_t]),
                                        "rsi": float(df_train['rsi_14'].iloc[ent_step_t]) if not pd.isna(df_train['rsi_14'].iloc[ent_step_t]) else 50.0,
                                        "bb": float(df_train['bb_dist'].iloc[ent_step_t]) if not pd.isna(df_train['bb_dist'].iloc[ent_step_t]) else 50.0,
                                        "macd": float(df_train['macd_hist'].iloc[ent_step_t]) if not pd.isna(df_train['macd_hist'].iloc[ent_step_t]) else 0.0,
                                        "atr": float(df_train['atr_14'].iloc[ent_step_t]) if not pd.isna(df_train['atr_14'].iloc[ent_step_t]) else 0.0,
                                        # Exits
                                        "mola_exit": df_train['mola_pct'].iloc[step_t],
                                        "stretch_exit": df_train['stretching'].iloc[step_t],
                                        "acc_exit": df_train['acceleration'].iloc[step_t],
                                        "disp_exit": df_train['disp_pct'].iloc[step_t],
                                        "vol_exit": df_train['volatility'].iloc[step_t],
                                        "vel_exit": df_train['velocity'].iloc[step_t],
                                        "infil_exit": bool(df_train['infil_bear'].iloc[step_t]),
                                        "reteste_exit": bool(df_train['reteste_val'].iloc[step_t]),
                                        "rsi_exit": float(df_train['rsi_14'].iloc[step_t]) if not pd.isna(df_train['rsi_14'].iloc[step_t]) else 50.0,
                                        "bb_exit": float(df_train['bb_dist'].iloc[step_t]) if not pd.isna(df_train['bb_dist'].iloc[step_t]) else 50.0,
                                        "macd_exit": float(df_train['macd_hist'].iloc[step_t]) if not pd.isna(df_train['macd_hist'].iloc[step_t]) else 0.0,
                                        "atr_exit": float(df_train['atr_14'].iloc[step_t]) if not pd.isna(df_train['atr_14'].iloc[step_t]) else 0.0
                                    })
                                    pos_t = "NONE"
                                    continue
                                    
                            sig_t, conf_t, _ = compute_bot_signal(df_train, step_t)
                            min_conf_t = st.session_state.get('tg_min_confidence_pct', 80.0)
                            
                            if pos_t == "NONE":
                                if sig_t == "LONG" and conf_t >= min_conf_t:
                                    pos_t = "LONG"
                                    ent_p_t = price_now_t
                                    ent_step_t = step_t
                                elif sig_t == "SHORT" and conf_t >= min_conf_t:
                                    pos_t = "SHORT"
                                    ent_p_t = price_now_t
                                    ent_step_t = step_t
                            else:
                                if pos_t == "LONG" and (sig_t == "SHORT" or (sig_t == "HOLD" and conf_t >= min_conf_t)):
                                    pnl_pct_t = (price_now_t - ent_p_t) / ent_p_t * 100
                                    trades_t.append({
                                        "type": "LONG", "entry_price": ent_p_t, "exit_price": price_now_t, "pnl_pct": pnl_pct_t,
                                        "regime": df_train['regime'].iloc[ent_step_t], "mola": df_train['mola_pct'].iloc[ent_step_t],
                                        "stretch": df_train['stretching'].iloc[ent_step_t], "acc": df_train['acceleration'].iloc[ent_step_t],
                                        "disp": df_train['disp_pct'].iloc[ent_step_t],
                                        "vol": df_train['volatility'].iloc[ent_step_t],
                                        "vel": df_train['velocity'].iloc[ent_step_t],
                                        "infil": bool(df_train['infil_bull'].iloc[ent_step_t]),
                                        "reteste": bool(df_train['reteste_val'].iloc[ent_step_t]),
                                        "rsi": float(df_train['rsi_14'].iloc[ent_step_t]) if not pd.isna(df_train['rsi_14'].iloc[ent_step_t]) else 50.0,
                                        "bb": float(df_train['bb_dist'].iloc[ent_step_t]) if not pd.isna(df_train['bb_dist'].iloc[ent_step_t]) else 50.0,
                                        "macd": float(df_train['macd_hist'].iloc[ent_step_t]) if not pd.isna(df_train['macd_hist'].iloc[ent_step_t]) else 0.0,
                                        "atr": float(df_train['atr_14'].iloc[ent_step_t]) if not pd.isna(df_train['atr_14'].iloc[ent_step_t]) else 0.0,
                                        # Exits
                                        "mola_exit": df_train['mola_pct'].iloc[step_t],
                                        "stretch_exit": df_train['stretching'].iloc[step_t],
                                        "acc_exit": df_train['acceleration'].iloc[step_t],
                                        "disp_exit": df_train['disp_pct'].iloc[step_t],
                                        "vol_exit": df_train['volatility'].iloc[step_t],
                                        "vel_exit": df_train['velocity'].iloc[step_t],
                                        "infil_exit": bool(df_train['infil_bull'].iloc[step_t]),
                                        "reteste_exit": bool(df_train['reteste_val'].iloc[step_t]),
                                        "rsi_exit": float(df_train['rsi_14'].iloc[step_t]) if not pd.isna(df_train['rsi_14'].iloc[step_t]) else 50.0,
                                        "bb_exit": float(df_train['bb_dist'].iloc[step_t]) if not pd.isna(df_train['bb_dist'].iloc[step_t]) else 50.0,
                                        "macd_exit": float(df_train['macd_hist'].iloc[step_t]) if not pd.isna(df_train['macd_hist'].iloc[step_t]) else 0.0,
                                        "atr_exit": float(df_train['atr_14'].iloc[step_t]) if not pd.isna(df_train['atr_14'].iloc[step_t]) else 0.0
                                    })
                                    pos_t = "NONE"
                                elif pos_t == "SHORT" and (sig_t == "LONG" or (sig_t == "HOLD" and conf_t >= min_conf_t)):
                                    pnl_pct_t = (ent_p_t - price_now_t) / ent_p_t * 100
                                    trades_t.append({
                                        "type": "SHORT", "entry_price": ent_p_t, "exit_price": price_now_t, "pnl_pct": pnl_pct_t,
                                        "regime": df_train['regime'].iloc[ent_step_t], "mola": df_train['mola_pct'].iloc[ent_step_t],
                                        "stretch": df_train['stretching'].iloc[ent_step_t], "acc": df_train['acceleration'].iloc[ent_step_t],
                                        "disp": df_train['disp_pct'].iloc[ent_step_t],
                                        "vol": df_train['volatility'].iloc[ent_step_t],
                                        "vel": df_train['velocity'].iloc[ent_step_t],
                                        "infil": bool(df_train['infil_bear'].iloc[ent_step_t]),
                                        "reteste": bool(df_train['reteste_val'].iloc[ent_step_t]),
                                        "rsi": float(df_train['rsi_14'].iloc[ent_step_t]) if not pd.isna(df_train['rsi_14'].iloc[ent_step_t]) else 50.0,
                                        "bb": float(df_train['bb_dist'].iloc[ent_step_t]) if not pd.isna(df_train['bb_dist'].iloc[ent_step_t]) else 50.0,
                                        "macd": float(df_train['macd_hist'].iloc[ent_step_t]) if not pd.isna(df_train['macd_hist'].iloc[ent_step_t]) else 0.0,
                                        "atr": float(df_train['atr_14'].iloc[ent_step_t]) if not pd.isna(df_train['atr_14'].iloc[ent_step_t]) else 0.0,
                                        # Exits
                                        "mola_exit": df_train['mola_pct'].iloc[step_t],
                                        "stretch_exit": df_train['stretching'].iloc[step_t],
                                        "acc_exit": df_train['acceleration'].iloc[step_t],
                                        "disp_exit": df_train['disp_pct'].iloc[step_t],
                                        "vol_exit": df_train['volatility'].iloc[step_t],
                                        "vel_exit": df_train['velocity'].iloc[step_t],
                                        "infil_exit": bool(df_train['infil_bear'].iloc[step_t]),
                                        "reteste_exit": bool(df_train['reteste_val'].iloc[step_t]),
                                        "rsi_exit": float(df_train['rsi_14'].iloc[step_t]) if not pd.isna(df_train['rsi_14'].iloc[step_t]) else 50.0,
                                        "bb_exit": float(df_train['bb_dist'].iloc[step_t]) if not pd.isna(df_train['bb_dist'].iloc[step_t]) else 50.0,
                                        "macd_exit": float(df_train['macd_hist'].iloc[step_t]) if not pd.isna(df_train['macd_hist'].iloc[step_t]) else 0.0,
                                        "atr_exit": float(df_train['atr_14'].iloc[step_t]) if not pd.isna(df_train['atr_14'].iloc[step_t]) else 0.0
                                    })
                                    pos_t = "NONE"
                                    
                        winning_t = [t for t in trades_t if t["pnl_pct"] > 0]
                        
                        if winning_t:
                            import numpy as np
                            import variables_registry
                            
                            knowledge_filepath = "bot_knowledge_base.json"
                            
                            knowledge = {}
                            if os.path.exists(knowledge_filepath):
                                try:
                                    with open(knowledge_filepath, "r", encoding="utf-8") as f:
                                        knowledge = json.load(f)
                                except Exception:
                                    pass
                                    
                            test_name = f"Auto-Treino {training_source} ({pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')})"
                            
                            test_data = {
                                "test_name": test_name,
                                "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                                "smas": [p2_t, p3_t, p4_t, p5_t, p6_t],
                                "regimes": {}
                            }
                            
                            for r_val in ["BULL", "BEAR", "LATERAL", "CAOTICO"]:
                                subset_long = [t for t in winning_t if t["regime"] == r_val and t["type"] == "LONG"]
                                subset_short = [t for t in winning_t if t["regime"] == r_val and t["type"] == "SHORT"]
                                
                                reg_data = {
                                    "opp_count": len(subset_long),
                                    "thr_count": len(subset_short),
                                    "opp_stats": {},
                                    "thr_stats": {}
                                }
                                
                                if subset_long:
                                    avg_mola = float(np.mean([t["mola"] for t in subset_long]))
                                    avg_stretch = float(np.mean([t["stretch"] for t in subset_long]))
                                    avg_acc = float(np.mean([t["acc"] for t in subset_long]))
                                    avg_disp = float(np.mean([t["disp"] for t in subset_long]))
                                    avg_vol = float(np.mean([t["vol"] for t in subset_long])) if "vol" in subset_long[0] else 0.0
                                    avg_vel = float(np.mean([t["vel"] for t in subset_long])) if "vel" in subset_long[0] else 0.0
                                    infil_rate = float(np.mean([100.0 if t["infil"] else 0.0 for t in subset_long])) if "infil" in subset_long[0] else 80.0
                                    reteste_rate = float(np.mean([100.0 if t["reteste"] else 0.0 for t in subset_long])) if "reteste" in subset_long[0] else 70.0
                                    avg_rsi = float(np.mean([t["rsi"] for t in subset_long])) if "rsi" in subset_long[0] else 50.0
                                    avg_bb = float(np.mean([t["bb"] for t in subset_long])) if "bb" in subset_long[0] else 50.0
                                    avg_macd = float(np.mean([t["macd"] for t in subset_long])) if "macd" in subset_long[0] else 0.0
                                    avg_atr = float(np.mean([t["atr"] for t in subset_long])) if "atr" in subset_long[0] else 0.0
                                    
                                    avg_mola_exit = float(np.mean([t["mola_exit"] for t in subset_long])) if "mola_exit" in subset_long[0] else avg_mola
                                    avg_stretch_exit = float(np.mean([t["stretch_exit"] for t in subset_long])) if "stretch_exit" in subset_long[0] else avg_stretch
                                    avg_acc_exit = float(np.mean([t["acc_exit"] for t in subset_long])) if "acc_exit" in subset_long[0] else avg_acc
                                    avg_disp_exit = float(np.mean([t["disp_exit"] for t in subset_long])) if "disp_exit" in subset_long[0] else avg_disp
                                    avg_vol_exit = float(np.mean([t["vol_exit"] for t in subset_long])) if "vol_exit" in subset_long[0] else avg_vol
                                    avg_vel_exit = float(np.mean([t["vel_exit"] for t in subset_long])) if "vel_exit" in subset_long[0] else avg_vel
                                    infil_exit_rate = float(np.mean([100.0 if t["infil_exit"] else 0.0 for t in subset_long])) if "infil_exit" in subset_long[0] else 80.0
                                    reteste_exit_rate = float(np.mean([100.0 if t["reteste_exit"] else 0.0 for t in subset_long])) if "reteste_exit" in subset_long[0] else 70.0
                                    avg_rsi_exit = float(np.mean([t["rsi_exit"] for t in subset_long])) if "rsi_exit" in subset_long[0] else avg_rsi
                                    avg_bb_exit = float(np.mean([t["bb_exit"] for t in subset_long])) if "bb_exit" in subset_long[0] else avg_bb
                                    avg_macd_exit = float(np.mean([t["macd_exit"] for t in subset_long])) if "macd_exit" in subset_long[0] else avg_macd
                                    avg_atr_exit = float(np.mean([t["atr_exit"] for t in subset_long])) if "atr_exit" in subset_long[0] else avg_atr
                                    
                                    reg_data["opp_stats"] = {
                                        "acc_mean": avg_acc,
                                        "acc_std": float(np.std([t["acc"] for t in subset_long])) if len(subset_long) > 1 else 0.0,
                                        "strt_mean": avg_stretch,
                                        "strt_std": float(np.std([t["stretch"] for t in subset_long])) if len(subset_long) > 1 else 0.0,
                                        "mola_mean": avg_mola,
                                        "disp_mean": avg_disp,
                                        "vel_mean": avg_vel,
                                        "vol_mean": avg_vol,
                                        "infil_rate": infil_rate,
                                        "reteste_rate": reteste_rate,
                                        "rsi_mean": avg_rsi,
                                        "bb_dist_mean": avg_bb,
                                        "macd_mean": avg_macd,
                                        "atr_mean": avg_atr,
                                        # Exits
                                        "acc_exit_mean": avg_acc_exit,
                                        "strt_exit_mean": avg_stretch_exit,
                                        "mola_exit_mean": avg_mola_exit,
                                        "disp_exit_mean": avg_disp_exit,
                                        "vel_exit_mean": avg_vel_exit,
                                        "vol_exit_mean": avg_vol_exit,
                                        "infil_exit_rate": infil_exit_rate,
                                        "reteste_exit_rate": reteste_exit_rate,
                                        "rsi_exit_mean": avg_rsi_exit,
                                        "bb_dist_exit_mean": avg_bb_exit,
                                        "macd_exit_mean": avg_macd_exit,
                                        "atr_exit_mean": avg_atr_exit
                                    }
                                    
                                if subset_short:
                                    avg_mola = float(np.mean([t["mola"] for t in subset_short]))
                                    avg_stretch = float(np.mean([t["stretch"] for t in subset_short]))
                                    avg_acc = float(np.mean([t["acc"] for t in subset_short]))
                                    avg_disp = float(np.mean([t["disp"] for t in subset_short]))
                                    avg_vol = float(np.mean([t["vol"] for t in subset_short])) if "vol" in subset_short[0] else 0.0
                                    avg_vel = float(np.mean([t["vel"] for t in subset_short])) if "vel" in subset_short[0] else 0.0
                                    infil_rate = float(np.mean([100.0 if t["infil"] else 0.0 for t in subset_short])) if "infil" in subset_short[0] else 80.0
                                    reteste_rate = float(np.mean([100.0 if t["reteste"] else 0.0 for t in subset_short])) if "reteste" in subset_short[0] else 70.0
                                    avg_rsi = float(np.mean([t["rsi"] for t in subset_short])) if "rsi" in subset_short[0] else 50.0
                                    avg_bb = float(np.mean([t["bb"] for t in subset_short])) if "bb" in subset_short[0] else 50.0
                                    avg_macd = float(np.mean([t["macd"] for t in subset_short])) if "macd" in subset_short[0] else 0.0
                                    avg_atr = float(np.mean([t["atr"] for t in subset_short])) if "atr" in subset_short[0] else 0.0
                                    
                                    avg_mola_exit = float(np.mean([t["mola_exit"] for t in subset_short])) if "mola_exit" in subset_short[0] else avg_mola
                                    avg_stretch_exit = float(np.mean([t["stretch_exit"] for t in subset_short])) if "stretch_exit" in subset_short[0] else avg_stretch
                                    avg_acc_exit = float(np.mean([t["acc_exit"] for t in subset_short])) if "acc_exit" in subset_short[0] else avg_acc
                                    avg_disp_exit = float(np.mean([t["disp_exit"] for t in subset_short])) if "disp_exit" in subset_short[0] else avg_disp
                                    avg_vol_exit = float(np.mean([t["vol_exit"] for t in subset_short])) if "vol_exit" in subset_short[0] else avg_vol
                                    avg_vel_exit = float(np.mean([t["vel_exit"] for t in subset_short])) if "vel_exit" in subset_short[0] else avg_vel
                                    infil_exit_rate = float(np.mean([100.0 if t["infil_exit"] else 0.0 for t in subset_short])) if "infil_exit" in subset_short[0] else 80.0
                                    reteste_exit_rate = float(np.mean([100.0 if t["reteste_exit"] else 0.0 for t in subset_short])) if "reteste_exit" in subset_short[0] else 70.0
                                    avg_rsi_exit = float(np.mean([t["rsi_exit"] for t in subset_short])) if "rsi_exit" in subset_short[0] else avg_rsi
                                    avg_bb_exit = float(np.mean([t["bb_exit"] for t in subset_short])) if "bb_exit" in subset_short[0] else avg_bb
                                    avg_macd_exit = float(np.mean([t["macd_exit"] for t in subset_short])) if "macd_exit" in subset_short[0] else avg_macd
                                    avg_atr_exit = float(np.mean([t["atr_exit"] for t in subset_short])) if "atr_exit" in subset_short[0] else avg_atr
                                    
                                    reg_data["thr_stats"] = {
                                        "acc_mean": avg_acc,
                                        "acc_std": float(np.std([t["acc"] for t in subset_short])) if len(subset_short) > 1 else 0.0,
                                        "strt_mean": avg_stretch,
                                        "strt_std": float(np.std([t["stretch"] for t in subset_short])) if len(subset_short) > 1 else 0.0,
                                        "mola_mean": avg_mola,
                                        "disp_mean": avg_disp,
                                        "vel_mean": avg_vel,
                                        "vol_mean": avg_vol,
                                        "infil_rate": infil_rate,
                                        "reteste_rate": reteste_rate,
                                        "rsi_mean": avg_rsi,
                                        "bb_dist_mean": avg_bb,
                                        "macd_mean": avg_macd,
                                        "atr_mean": avg_atr,
                                        # Exits
                                        "acc_exit_mean": avg_acc_exit,
                                        "strt_exit_mean": avg_stretch_exit,
                                        "mola_exit_mean": avg_mola_exit,
                                        "disp_exit_mean": avg_disp_exit,
                                        "vel_exit_mean": avg_vel_exit,
                                        "vol_exit_mean": avg_vol_exit,
                                        "infil_exit_rate": infil_exit_rate,
                                        "reteste_exit_rate": reteste_exit_rate,
                                        "rsi_exit_mean": avg_rsi_exit,
                                        "bb_dist_exit_mean": avg_bb_exit,
                                        "macd_exit_mean": avg_macd_exit,
                                        "atr_exit_mean": avg_atr_exit
                                    }
                                    
                                test_data["regimes"][r_val] = reg_data
                                
                            knowledge[test_name] = test_data
                            
                            with open(knowledge_filepath, "w", encoding="utf-8") as f:
                                json.dump(knowledge, f, indent=2, ensure_ascii=False)
                                
                            variables_registry.rebuild_consensus_dna()
                            
                            st.success(f"🧠 **Auto-Treino Integrado com Sucesso!** Gravámos as conclusões na base de conhecimento e o cérebro consolidado do Bot evoluiu automaticamente em background com {len(winning_t)} operações lucrativas.")
                        else:
                            st.warning(f"Treino concluído mas nenhuma operação obteve lucro positivo (Total de trades: {len(trades_t)}). Tente aumentar o volume ou mudar a fonte.")
                    else:
                        st.error("Erro ao obter dados para o treino!")

        # =========================================================================
        # MODO REVISAO: gráfico completo apos o fim do jogo
        # =========================================================================
        if st.session_state.tg_game_finished and st.session_state.tg_data is not None:
            df = st.session_state.tg_data
            
            # Calcular eficácia LONG/SHORT
            long_trades = [t for t in st.session_state.tg_trades if t.get('type') == 'LONG']
            short_trades = [t for t in st.session_state.tg_trades if t.get('type') == 'SHORT']
            long_len = len(long_trades)
            short_len = len(short_trades)
            long_wr = (sum(1 for t in long_trades if t.get('pnl_pct', 0) > 0) / max(long_len, 1) * 100) if long_len > 0 else 0.0
            short_wr = (sum(1 for t in short_trades if t.get('pnl_pct', 0) > 0) / max(short_len, 1) * 100) if short_len > 0 else 0.0
            ret_pct = st.session_state.tg_capital - 100.0
            ret_color = "#10B981" if ret_pct >= 0 else "#EF4444"
            emoji_result = "🏆" if ret_pct > 0 else ("😐" if ret_pct == 0 else "💀")

            st.markdown(f"""
            <div class="review-banner">
                <div style="color:#94a3b8; font-size:13px; margin-bottom:12px; letter-spacing:2px; text-transform:uppercase;">
                    {emoji_result} Sessao concluida — {st.session_state.tg_trader_name} &nbsp;&nbsp;•&nbsp;&nbsp; Grafico completo disponivel para consulta
                </div>
                <div style="display:flex; gap:16px; flex-wrap:wrap;">
                    <div class="review-stat" style="flex:1;">
                        <div style="color:#64748b; font-size:11px; text-transform:uppercase;">Banca Final</div>
                        <div style="color:#10B981; font-size:22px; font-weight:900; font-family:monospace;">{st.session_state.tg_capital:.2f} EUR</div>
                    </div>
                    <div class="review-stat" style="flex:1;">
                        <div style="color:#64748b; font-size:11px; text-transform:uppercase;">Retorno Total</div>
                        <div style="color:{ret_color}; font-size:22px; font-weight:900; font-family:monospace;">{ret_pct:+.2f}%</div>
                    </div>
                    <div class="review-stat" style="flex:1;">
                        <div style="color:#64748b; font-size:11px; text-transform:uppercase;">Operacoes</div>
                        <div style="color: var(--text-color); font-size:22px; font-weight:900; font-family:monospace;">{len(st.session_state.tg_trades)}</div>
                    </div>
                    <div class="review-stat" style="flex:1;">
                        <div style="color:#64748b; font-size:11px; text-transform:uppercase;">Win Rate LONG</div>
                        <div style="color:#10B981; font-size:22px; font-weight:900; font-family:monospace;">
                            {long_wr:.0f}% <span style='font-size:11px; color:#64748b;'>({long_len})</span>
                        </div>
                    </div>
                    <div class="review-stat" style="flex:1;">
                        <div style="color:#64748b; font-size:11px; text-transform:uppercase;">Win Rate SHORT</div>
                        <div style="color:#EF4444; font-size:22px; font-weight:900; font-family:monospace;">
                            {short_wr:.0f}% <span style='font-size:11px; color:#64748b;'>({short_len})</span>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_rev_chart, col_rev_ctrl = st.columns([7, 3])

            with col_rev_ctrl:
                st.markdown('<div class="game-control-anchor"></div>', unsafe_allow_html=True)
                st.markdown("##### Ordens Fechadas")
                if st.session_state.tg_trades:
                    for i, tr in enumerate(st.session_state.tg_trades, 1):
                        clr = "#10B981" if tr.get('pnl_pct',0) >= 0 else "#EF4444"
                        st.markdown(f"<div style='font-size:12px; padding:4px 0; border-bottom:1px solid #f1f5f9;'>"
                                    f"<b style='color:{clr};'>#{i} {tr['type']}</b>  "
                                    f"<span style='color:#64748b;'>{tr.get('entry_price',0):.2f}→{tr.get('exit_price',0):.2f}</span>  "
                                    f"<b style='color:{clr};'>{tr.get('pnl_pct',0):+.2f}%</b></div>", unsafe_allow_html=True)
                st.markdown("<hr style='margin:8px 0;'>", unsafe_allow_html=True)
                if st.button("Novo Jogo", type="primary", width='stretch', key="rv_new_game"):
                    start_new_game()
                    st.rerun()

            with col_rev_chart:
                # Grafico completo: das 100 velas jogadas (step 144 a 244)
                full_game_df = df.iloc[144:245]
                # Checkboxes cinzentas redundantes removidas. Controlo feito diretamente por clique na legenda do Plotly!

                fig_review = _build_chart(
                    full_game_df, df,
                    title_str=f"Revisao Completa — {st.session_state.tg_trader_name} | 100 Velas Jogadas",
                    show_full_range=True
                )
                st.plotly_chart(fig_review, width='stretch')

        # =========================================================================
        # MODO JOGO ATIVO
        # =========================================================================
        elif st.session_state.tg_active and st.session_state.tg_data is not None:
            df = st.session_state.tg_data
            current_step = st.session_state.tg_step
            progress_candles = current_step - 144
            price_now = df['close'].iloc[current_step]

            # Gatilhos de seguranca
            if st.session_state.tg_position != "NONE":
                entry_p = st.session_state.tg_entry_price
                triggered = False
                trigger_reason = ""
                executed_price = price_now
                if st.session_state.tg_position == "LONG":
                    st.session_state.tg_highest_price = max(st.session_state.tg_highest_price, price_now)
                    if st.session_state.tg_sl_active and price_now <= entry_p * (1 - st.session_state.tg_sl_pct/100.0):
                        triggered, trigger_reason = True, "STOP LOSS"
                        executed_price = entry_p * (1 - st.session_state.tg_sl_pct/100.0)
                    elif st.session_state.tg_tp_active and price_now >= entry_p * (1 + st.session_state.tg_tp_pct/100.0):
                        triggered, trigger_reason = True, "TAKE PROFIT"
                        executed_price = entry_p * (1 + st.session_state.tg_tp_pct/100.0)
                    elif st.session_state.tg_ts_active and price_now <= st.session_state.tg_highest_price * (1 - st.session_state.tg_ts_pct/100.0):
                        triggered, trigger_reason = True, "TRAILING STOP"
                        executed_price = st.session_state.tg_highest_price * (1 - st.session_state.tg_ts_pct/100.0)
                elif st.session_state.tg_position == "SHORT":
                    st.session_state.tg_lowest_price = min(st.session_state.tg_lowest_price, price_now)
                    if st.session_state.tg_sl_active and price_now >= entry_p * (1 + st.session_state.tg_sl_pct/100.0):
                        triggered, trigger_reason = True, "STOP LOSS"
                        executed_price = entry_p * (1 + st.session_state.tg_sl_pct/100.0)
                    elif st.session_state.tg_tp_active and price_now <= entry_p * (1 - st.session_state.tg_tp_pct/100.0):
                        triggered, trigger_reason = True, "TAKE PROFIT"
                        executed_price = entry_p * (1 - st.session_state.tg_tp_pct/100.0)
                    elif st.session_state.tg_ts_active and price_now >= st.session_state.tg_lowest_price * (1 + st.session_state.tg_ts_pct/100.0):
                        triggered, trigger_reason = True, "TRAILING STOP"
                        executed_price = st.session_state.tg_lowest_price * (1 + st.session_state.tg_ts_pct/100.0)
                if triggered:
                    commissions = st.session_state.tg_capital * 0.0005
                    if st.session_state.tg_position == "LONG":
                        trade_pnl_pct = (executed_price - entry_p) / entry_p * 100
                    else:
                        trade_pnl_pct = (entry_p - executed_price) / entry_p * 100
                    net_pnl = st.session_state.tg_capital * (trade_pnl_pct / 100.0) - commissions
                    st.session_state.tg_capital += net_pnl
                    st.session_state.tg_trades.append({
                        "type": st.session_state.tg_position, "entry_price": entry_p, "exit_price": executed_price,
                        "pnl_pct": trade_pnl_pct, "pnl_eur": net_pnl,
                        "candles": current_step - st.session_state.tg_entry_step,
                        "reason": trigger_reason, "entry_step": st.session_state.tg_entry_step, "exit_step": current_step
                    })
                    old_pos = st.session_state.tg_position
                    st.session_state.tg_position = "NONE"
                    st.toast(f"{trigger_reason} ativado! Posicao {old_pos} liquidada a {executed_price:.2f}")
                    st.rerun()

            # Fim do desafio (100 velas jogadas)
            if progress_candles >= 100:
                # Fechar posicao aberta
                if st.session_state.tg_position != "NONE":
                    entry_p = st.session_state.tg_entry_price
                    commissions = st.session_state.tg_capital * 0.0005
                    trade_pnl_pct = (price_now - entry_p)/entry_p*100 if st.session_state.tg_position == "LONG" else (entry_p - price_now)/entry_p*100
                    net_pnl = st.session_state.tg_capital * (trade_pnl_pct/100.0) - commissions
                    st.session_state.tg_capital += net_pnl
                    st.session_state.tg_trades.append({
                        "type": st.session_state.tg_position, "entry_price": entry_p, "exit_price": price_now,
                        "pnl_pct": trade_pnl_pct, "pnl_eur": net_pnl,
                        "candles": current_step - st.session_state.tg_entry_step,
                        "reason": "Fim do Jogo", "entry_step": st.session_state.tg_entry_step, "exit_step": current_step
                    })
                    st.session_state.tg_position = "NONE"
                save_highscore(st.session_state.tg_trader_name, st.session_state.tg_capital, len(st.session_state.tg_trades))
                save_last_game_persistent(df)
                # Transicao para modo revisao (nao apaga os dados!)
                st.session_state.tg_active = False
                st.session_state.tg_game_finished = True
                st.session_state.tg_running = False
                st.balloons()
                st.rerun()

            pos_str = "FORA"
            pos_color = "#94a3b8"
            if st.session_state.tg_position == "LONG":
                pos_str = f"LONG ({st.session_state.tg_entry_price:.2f})"
                pos_color = "#10B981"
            elif st.session_state.tg_position == "SHORT":
                pos_str = f"SHORT ({st.session_state.tg_entry_price:.2f})"
                pos_color = "#EF4444"

            ret_pct = st.session_state.tg_capital - 100.0
            ret_color = "#10B981" if ret_pct >= 0 else "#EF4444"

            # --- Calcular eficacia para o header ---
            _all_trades = st.session_state.get("tg_trades", [])
            _l_trades = [t for t in _all_trades if t["type"] == "LONG"]
            _s_trades = [t for t in _all_trades if t["type"] == "SHORT"]
            _l_wins = sum(1 for t in _l_trades if t.get("pnl_pct", 0) > 0)
            _s_wins = sum(1 for t in _s_trades if t.get("pnl_pct", 0) > 0)
            _l_eff = (_l_wins / len(_l_trades) * 100) if _l_trades else 0.0
            _s_eff = (_s_wins / len(_s_trades) * 100) if _s_trades else 0.0

            # =========================================================
            # BARRA DE ESTADO TOPO - dark header bar
            # =========================================================
            st.markdown(f"""
            <div style="background:linear-gradient(90deg,#0f172a,#1e293b,#0f172a);
                        border-radius:12px; padding:14px 24px; margin-bottom:14px;
                        display:flex; justify-content:space-between; align-items:center;
                        border:1px solid rgba(124,58,237,0.3);
                        box-shadow:0 4px 24px rgba(0,0,0,0.4);">
                <div style="text-align:center;">
                    <div style="color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:3px;">Banca Final</div>
                    <div style="color:#10B981;font-size:20px;font-weight:900;font-family:monospace;">{st.session_state.tg_capital:.2f} EUR</div>
                </div>
                <div style="text-align:center;">
                    <div style="color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:3px;">Retorno Total</div>
                    <div style="color:{ret_color};font-size:20px;font-weight:900;font-family:monospace;">{ret_pct:+.2f}%</div>
                </div>
                <div style="text-align:center;">
                    <div style="color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:3px;">Eficiencia de Sessao</div>
                    <div style="font-size:13px;font-weight:700;font-family:monospace;">
                        <span style="color:#10B981;">LONG {_l_eff:.0f}% ({_l_wins}/{len(_l_trades)})</span>
                        &nbsp;&nbsp;|&nbsp;&nbsp;
                        <span style="color:#EF4444;">SHORT {_s_eff:.0f}% ({_s_wins}/{len(_s_trades)})</span>
                    </div>
                </div>
                <div style="text-align:center;">
                    <div style="color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:3px;">Posicao</div>
                    <div style="color:{pos_color};font-size:16px;font-weight:900;font-family:monospace;">{pos_str}</div>
                </div>
                <div style="text-align:center;">
                    <div style="color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:3px;">Progresso</div>
                    <div style="color:#e2e8f0;font-size:18px;font-weight:900;font-family:monospace;">{progress_candles} <span style="font-size:11px;color:#64748b;">/ 100</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # =========================================================
            # LAYOUT PRINCIPAL: 3 colunas
            # col_chart | col_ctrl | col_advisor
            # =========================================================
            col_chart, col_ctrl, col_advisor = st.columns([5, 2.5, 3.5])

            # =========================================================
            # COL CHART - Grafico
            # =========================================================
            with col_chart:
                start_idx_c = max(50, current_step - 49)
                sub_df = df.iloc[start_idx_c:current_step+1]
                fig = _build_chart(
                    sub_df, df,
                    title_str=f"Arena Real \U0001f4c8 Batimento {progress_candles} / 100 Velas (ultimas {len(sub_df)})"
                )
                st.plotly_chart(fig, width="stretch")

            # =========================================================
            # COL CTRL - Controlo de fluxo + Botoes casino
            # =========================================================
            with col_ctrl:
                st.markdown("<div class='game-control-anchor'></div>", unsafe_allow_html=True)

                # --- Fluxo ---
                col_flow1, col_flow2 = st.columns([1, 1])
                with col_flow1:
                    if st.button("Avancar", width="stretch", key="tg_step_btn"):
                        st.session_state.tg_step += 1
                        st.rerun()
                with col_flow2:
                    btn_label = "Pausar" if st.session_state.tg_running else "Auto"
                    if st.button(btn_label, width="stretch", key="tg_loop_btn"):
                        st.session_state.tg_running = not st.session_state.tg_running
                        st.rerun()
                tg_speed_select = st.selectbox(
                    "Velocidade:", ["Lento (1.0s)", "Medio (0.3s)", "Rapido (0.05s)"],
                    index=1, label_visibility="collapsed", key="tg_speed_widget"
                )
                tg_delay = 1.0 if "Lento" in tg_speed_select else (0.3 if "Medio" in tg_speed_select else 0.05)

                st.markdown("<hr style='margin:8px 0;border:0;border-top:1px solid rgba(255,255,255,0.08);'>", unsafe_allow_html=True)

                # --- Co-piloto radio ---
                col_bl, col_br = st.columns([1.2, 2.8])
                with col_bl:
                    st.markdown("<h6 style='margin-top:6px;font-weight:bold;color:#a78bfa;'>Co-piloto:</h6>", unsafe_allow_html=True)
                with col_br:
                    bot_mode_choice = st.radio(
                        "Modo:", ["Manual", "Co-piloto", "Bot Autonomo"],
                        horizontal=True,
                        index=["Manual","Co-piloto","Bot Autonomo"].index(st.session_state.tg_bot_mode) if st.session_state.tg_bot_mode in ["Manual","Co-piloto","Bot Autonomo"] else 0,
                        key="tg_bot_mode_radio", label_visibility="collapsed"
                    )
                if bot_mode_choice != st.session_state.tg_bot_mode:
                    st.session_state.tg_bot_mode = bot_mode_choice

                st.markdown("<hr style='margin:8px 0;border:0;border-top:1px solid rgba(255,255,255,0.08);'>", unsafe_allow_html=True)

                # --- Compute signal ---
                _bot_signal, _bot_conf, _bot_conds = compute_bot_signal(df, current_step)
                _sig_color = {"LONG": "#10B981", "SHORT": "#EF4444", "HOLD": "#94a3b8"}[_bot_signal]

                # --- BOT AUTONOMO ---
                if st.session_state.tg_bot_mode == "Bot Autonomo":
                    _pos = st.session_state.tg_position
                    if _pos == "NONE" and _bot_signal == "LONG" and _bot_conf >= st.session_state.get("tg_min_confidence_pct", 80.0):
                        st.session_state.tg_position = "LONG"
                        st.session_state.tg_entry_price = price_now
                        st.session_state.tg_entry_step = current_step
                        st.session_state.tg_highest_price = price_now
                        st.toast(f"Bot entrou LONG a {price_now:.2f}")
                    elif _pos == "NONE" and _bot_signal == "SHORT" and _bot_conf >= st.session_state.get("tg_min_confidence_pct", 80.0):
                        st.session_state.tg_position = "SHORT"
                        st.session_state.tg_entry_price = price_now
                        st.session_state.tg_entry_step = current_step
                        st.session_state.tg_lowest_price = price_now
                        st.toast(f"Bot entrou SHORT a {price_now:.2f}")
                    elif _pos == "LONG" and (_bot_signal == "SHORT" or (_bot_signal == "HOLD" and _bot_conf >= st.session_state.get("tg_min_confidence_pct", 80.0))):
                        entry_p = st.session_state.tg_entry_price
                        commissions = st.session_state.tg_capital * 0.0005
                        pnl_pct = (price_now - entry_p) / entry_p * 100
                        net_pnl = st.session_state.tg_capital * (pnl_pct/100.0) - commissions
                        st.session_state.tg_capital += net_pnl
                        st.session_state.tg_trades.append({
                            "type": "LONG", "entry_price": entry_p, "exit_price": price_now,
                            "pnl_pct": pnl_pct, "pnl_eur": net_pnl,
                            "candles": current_step - st.session_state.tg_entry_step,
                            "reason": f"Bot Exit ({_bot_signal})", "entry_step": st.session_state.tg_entry_step, "exit_step": current_step
                        })
                        st.session_state.tg_position = "NONE"
                        st.toast(f"Bot saiu LONG a {price_now:.2f} ({pnl_pct:+.2f}%)")
                    elif _pos == "SHORT" and (_bot_signal == "LONG" or (_bot_signal == "HOLD" and _bot_conf >= st.session_state.get("tg_min_confidence_pct", 80.0))):
                        entry_p = st.session_state.tg_entry_price
                        commissions = st.session_state.tg_capital * 0.0005
                        pnl_pct = (entry_p - price_now) / entry_p * 100
                        net_pnl = st.session_state.tg_capital * (pnl_pct/100.0) - commissions
                        st.session_state.tg_capital += net_pnl
                        st.session_state.tg_trades.append({
                            "type": "SHORT", "entry_price": entry_p, "exit_price": price_now,
                            "pnl_pct": pnl_pct, "pnl_eur": net_pnl,
                            "candles": current_step - st.session_state.tg_entry_step,
                            "reason": f"Bot Exit ({_bot_signal})", "entry_step": st.session_state.tg_entry_step, "exit_step": current_step
                        })
                        st.session_state.tg_position = "NONE"
                        st.toast(f"Bot saiu SHORT a {price_now:.2f} ({pnl_pct:+.2f}%)")

                # --- CASINO BUTTONS ---
                _long_on  = st.session_state.tg_position == "LONG"
                _short_on = st.session_state.tg_position == "SHORT"
                _led_ld = "background:#10b981;box-shadow:0 0 8px 3px #10b981;" if _long_on else "background:#052e16;border:1px solid #134e4a;"
                _led_sd = "background:#ef4444;box-shadow:0 0 8px 3px #ef4444;" if _short_on else "background:#450a0a;border:1px solid #991b1b;"
                _ll = "ON &#9679; ACESO" if _long_on else "OFF &#9675; APAGADO"
                _sl = "ON &#9679; ACESO" if _short_on else "OFF &#9675; APAGADO"
                _lc = "#10b981" if _long_on else "#334155"
                _sc = "#ef4444" if _short_on else "#334155"
                st.markdown(
                    f'<div style="display:flex;gap:0;margin-bottom:6px;">'
                    f'<div style="flex:1;text-align:center;font-size:10px;font-weight:bold;letter-spacing:1px;color:{_lc};text-transform:uppercase;">'
                    f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;{_led_ld}margin-right:4px;vertical-align:middle;"></span>'
                    f'LONG &nbsp; {_ll}</div>'
                    f'<div style="flex:1;text-align:center;font-size:10px;font-weight:bold;letter-spacing:1px;color:{_sc};text-transform:uppercase;">'
                    f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;{_led_sd}margin-right:4px;vertical-align:middle;"></span>'
                    f'SHORT &nbsp; {_sl}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                col_btn_long, col_btn_short = st.columns(2)

                with col_btn_long:
                    if st.session_state.tg_position == "LONG":
                        long_pnl = (price_now - st.session_state.tg_entry_price)/st.session_state.tg_entry_price*100
                        st.markdown('<div class="casino-long-active">', unsafe_allow_html=True)
                        if st.button(f"LONG ATIVO  {long_pnl:+.2f}%", width="stretch", key="tg_btn_long_act"):
                            entry_p = st.session_state.tg_entry_price
                            commissions = st.session_state.tg_capital * 0.0005
                            trade_pnl_pct = (price_now - entry_p)/entry_p*100
                            net_pnl = st.session_state.tg_capital * (trade_pnl_pct/100.0) - commissions
                            st.session_state.tg_capital += net_pnl
                            st.session_state.tg_trades.append({
                                "type": "LONG", "entry_price": entry_p, "exit_price": price_now,
                                "pnl_pct": trade_pnl_pct, "pnl_eur": net_pnl,
                                "candles": current_step - st.session_state.tg_entry_step,
                                "reason": "Manual Exit", "entry_step": st.session_state.tg_entry_step, "exit_step": current_step
                            })
                            st.session_state.tg_position = "NONE"
                            save_last_game_persistent(df)
                            st.toast(f"LONG fechado a {price_now:.2f}")
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                    elif st.session_state.tg_position == "NONE":
                        st.markdown('<div class="casino-long-inactive">', unsafe_allow_html=True)
                        if st.button("ENTRAR LONG  [OFF]", width="stretch", key="tg_btn_long_inact"):
                            st.session_state.tg_position = "LONG"
                            st.session_state.tg_entry_price = price_now
                            st.session_state.tg_entry_step = current_step
                            st.session_state.tg_highest_price = price_now
                            st.toast(f"LONG ativado a {price_now:.2f}")
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="casino-blocked">', unsafe_allow_html=True)
                        st.button("LONG BLOQUEADO", disabled=True, width="stretch", key="tg_btn_long_blk")
                        st.markdown("</div>", unsafe_allow_html=True)

                with col_btn_short:
                    if st.session_state.tg_position == "SHORT":
                        short_pnl = (st.session_state.tg_entry_price - price_now)/st.session_state.tg_entry_price*100
                        st.markdown('<div class="casino-short-active">', unsafe_allow_html=True)
                        if st.button(f"SHORT ATIVO  {short_pnl:+.2f}%", width="stretch", key="tg_btn_short_act"):
                            entry_p = st.session_state.tg_entry_price
                            commissions = st.session_state.tg_capital * 0.0005
                            trade_pnl_pct = (entry_p - price_now)/entry_p*100
                            net_pnl = st.session_state.tg_capital * (trade_pnl_pct/100.0) - commissions
                            st.session_state.tg_capital += net_pnl
                            st.session_state.tg_trades.append({
                                "type": "SHORT", "entry_price": entry_p, "exit_price": price_now,
                                "pnl_pct": trade_pnl_pct, "pnl_eur": net_pnl,
                                "candles": current_step - st.session_state.tg_entry_step,
                                "reason": "Manual Exit", "entry_step": st.session_state.tg_entry_step, "exit_step": current_step
                            })
                            st.session_state.tg_position = "NONE"
                            save_last_game_persistent(df)
                            st.toast(f"SHORT fechado a {price_now:.2f}")
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                    elif st.session_state.tg_position == "NONE":
                        st.markdown('<div class="casino-short-inactive">', unsafe_allow_html=True)
                        if st.button("ENTRAR SHORT  [OFF]", width="stretch", key="tg_btn_short_inact"):
                            st.session_state.tg_position = "SHORT"
                            st.session_state.tg_entry_price = price_now
                            st.session_state.tg_entry_step = current_step
                            st.session_state.tg_lowest_price = price_now
                            st.toast(f"SHORT ativado a {price_now:.2f}")
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="casino-short-inactive">', unsafe_allow_html=True)
                        st.button("SHORT BLOQUEADO", disabled=True, width="stretch", key="tg_btn_short_blk")
                        st.markdown("</div>", unsafe_allow_html=True)

            # =========================================================
            # COL ADVISOR - Sinal do co-piloto + 12 variaveis
            # =========================================================
            with col_advisor:
                dna_active = st.session_state.get("tg_strategy_type", "Default") == "Cerebro de Consenso (Lab)"
                regime_label = ""
                if dna_active:
                    regime_name = df["regime"].iloc[current_step]
                    regime_emoji = {"BULL": "BULL", "BEAR": "BEAR", "LATERAL": "LATERAL", "CAOTICO": "CAOTICO"}.get(regime_name, regime_name)
                    regime_color = {"BULL": "#10B981", "BEAR": "#EF4444", "LATERAL": "#F59E0B", "CAOTICO": "#8B5CF6"}.get(regime_name, "#94a3b8")
                    regime_label = f'<div style="font-size:11px;margin-bottom:6px;font-weight:bold;color:#7c3aed;">DNA ATIVO | REGIME DETETADO: <span style="color:{regime_color};">{regime_emoji}</span></div>'

                _sig_emoji = {"LONG": "GREEN", "SHORT": "RED", "HOLD": "GREY"}[_bot_signal]
                _cg = "#10B981"
                _cr = "#EF4444"
                _conds_parts = []
                for _ck, _cv in _bot_conds.items():
                    _ccolor = _cg if _cv else _cr
                    _cmark = "OK" if _cv else "X"
                    _conds_parts.append(f"<div><span style='color:{_ccolor};'>{_cmark}</span> <span style='color:#cbd5e1;'>{_ck}</span></div>")
                _conds_html = "".join(_conds_parts)
                st.markdown(f"""
                <div style="background:rgba(15,23,42,0.9);border-radius:12px;padding:12px 16px;
                     border-left:4px solid {_sig_color};border:1px solid rgba(124,58,237,0.2);
                     box-shadow:0 4px 20px rgba(0,0,0,0.3);">
                    {regime_label}
                    <div style="font-size:22px;font-weight:900;color:{_sig_color};margin-bottom:6px;">
                        {_bot_signal} <span style="font-size:13px;color:#64748b;">confianca {_bot_conf}%</span>
                    </div>
                    <div style="font-size:11px;line-height:1.8;">
                        {_conds_html}
                    </div>
                    <div style="margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.06);font-size:11px;">
                        <b style="color:#94a3b8;">Eficiencia:</b><br>
                        <span style="color:#10B981;">LONG: {_l_eff:.1f}% ({_l_wins}/{len(_l_trades)})</span> &nbsp;|&nbsp;
                        <span style="color:#EF4444;">SHORT: {_s_eff:.1f}% ({_s_wins}/{len(_s_trades)})</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)


# Loop automatico
            if st.session_state.tg_running and st.session_state.tg_active:
                time.sleep(tg_delay)
                if (st.session_state.tg_step - 144) < 100:
                    st.session_state.tg_step += 1
                    st.rerun()
                else:
                    st.session_state.tg_running = False
                    st.rerun()

        # Historico e leaderboard (sempre visiveis se houver dados)
        if st.session_state.tg_data is not None or st.session_state.tg_trades:
            st.markdown("---")
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                st.markdown("#### Historico de Ordens")
                if st.session_state.tg_trades:
                    th_df = pd.DataFrame(st.session_state.tg_trades)
                    display_cols = {c: c for c in th_df.columns if c in ["type","entry_price","exit_price","pnl_pct","pnl_eur","candles","reason"]}
                    st.dataframe(th_df[list(display_cols.keys())].rename(columns={
                        "type":"Operacao","entry_price":"Entrada","exit_price":"Saida",
                        "pnl_pct":"PnL (%)","pnl_eur":"Retorno","candles":"Duracao","reason":"Motivo"
                    }), width='stretch')
                else:
                    st.info("Nenhuma ordem fechada.")
            with col_h2:
                st.markdown("#### Top 5 Recordes")
                scores = load_highscores()
                if scores:
                    st.dataframe(pd.DataFrame(scores).rename(columns={
                        "name":"Nome","capital":"Banca Final","return":"Lucro",
                        "trades":"Trades","config":"Config","date":"Data"
                    }), width='stretch')
                else:
                    st.info("Ainda nao ha recordes!")

# =========================================================================
# SEPARADOR 6: CENTRAL DE VARIÁVEIS
# =========================================================================

# =========================================================================
# SEPARADOR 7: CÉREBRO DO BOT (DNA) - CONTA TABULAR
# =========================================================================
with tab_bot_brain:
    import variables_registry
    import json
    
    st.markdown("<h3 style='text-align: center; color: #7c3aed; margin-bottom:5px;'>🧠 Cérebro Consolidado do Bot</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b; font-size:13px; margin-bottom:20px; text-align: center;'>Cockpit estatístico cumulativo que unifica 100% das lições de treino do robô de forma automática.</p>", unsafe_allow_html=True)
    
    knowledge_path = "bot_knowledge_base.json"
    dna_path = "bot_consensus_dna.json"
    
    has_knowledge = os.path.exists(knowledge_path)
    knowledge = {}
    if has_knowledge:
        try:
            with open(knowledge_path, "r", encoding="utf-8") as f:
                knowledge = json.load(f)
        except Exception:
            pass
            
    has_dna = os.path.exists(dna_path)
    dna = {}
    if has_dna:
        try:
            with open(dna_path, "r", encoding="utf-8") as f:
                dna = json.load(f)
        except Exception:
            pass
            
    tests_list = list(knowledge.keys())
    opp_total = 0
    thr_total = 0
    has_conflict = False
    
    for t_name, t_data in knowledge.items():
        for reg in ["BULL", "BEAR", "LATERAL", "CAOTICO"]:
            reg_data = t_data.get("regimes", {}).get(reg, {})
            opp_total += reg_data.get("opp_count", 0)
            thr_total += reg_data.get("thr_count", 0)
            
    if has_dna:
        for reg, r_data in dna.get("regimes", {}).items():
            for action in ["buy_rules", "sell_rules"]:
                for var, v_data in r_data.get(action, {}).items():
                    if isinstance(v_data, dict) and not v_data.get("stable", True):
                        has_conflict = True
                        
    state_desc = "🟢 Consistente"
    if has_conflict:
        state_desc = "⚠️ Contradição Detetada"
    elif not tests_list:
        state_desc = "⚪ Sem Treinos"
        
    last_up = dna.get("last_updated", "Nunca")
    
    # Cartões Compactos de Métrica
    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    with col_c1:
        st.metric("Estado do Cérebro", state_desc, help="Identifica se existem contradições entre as lições")
    with col_c2:
        st.metric("Sessões Integradas", f"{len(tests_list)} Treinos", help="Lições na base de conhecimento")
    with col_c3:
        st.metric("Amostras Estudadas", f"{opp_total + thr_total} Padrões", help="Total de fundos (BUY) e topos (SELL) estudados")
    with col_c4:
        st.metric("Última Sincronização", last_up, help="Data e hora do último recálculo cumulativo")
        
    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    variables_registry.render_bot_brain_table()
    
    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    col_h1, col_h2 = st.columns([3, 1])
    
    with col_h1:
        st.markdown("##### 📚 Lições Guardadas na Base de Conhecimento")
        if tests_list:
            records = []
            for t_name, t_data in knowledge.items():
                smas_str = ", ".join(map(str, t_data.get("smas", [])))
                opp_cnt = sum(t_data.get("regimes", {}).get(r, {}).get("opp_count", 0) for r in ["BULL","BEAR","LATERAL","CAOTICO"])
                thr_cnt = sum(t_data.get("regimes", {}).get(r, {}).get("thr_count", 0) for r in ["BULL","BEAR","LATERAL","CAOTICO"])
                records.append({
                    "Identificação do Exame": t_name,
                    "Data/Hora": t_data.get("timestamp", "Desconhecido"),
                    "Médias Aplicadas": smas_str,
                    "Total Oportunidades (Fundos)": opp_cnt,
                    "Total Ameaças (Topos)": thr_cnt
                })
            df_hist = pd.DataFrame(records)
            st.dataframe(df_hist, width='stretch', hide_index=True, height=350)
        else:
            st.info("ℹ️ Nenhuma lição de treino ativa na memória do Bot. Execute simulações para treinar.")
            
    with col_h2:
        st.markdown("##### ⚙️ Gestão de Memória")
        st.markdown("<p style='font-size:11px; color:#64748b; margin-top:5px;'>O cérebro acumula lições infinitamente. Se desejar começar um ciclo do zero, faça reset.</p>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        
        if st.button("🗑️ Limpar Todo o Cérebro", type="secondary", width='stretch', key="btn_clear_entire_brain"):
            for path in [knowledge_path, dna_path]:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
            st.toast("🧠 Cérebro limpo e redefinido com sucesso!")
            st.rerun()
