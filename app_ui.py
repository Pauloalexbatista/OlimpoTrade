# my_trading_bot/app_ui.py
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
        "Criptomoeda", "SMA RÃ¡pida", "SMA Lenta", "Stop Loss (%)",
        "Take Profit", "Stop MÃ³vel (Trailing)", "Take Profit Ativo",
        "Retorno Treino (%)", "Retorno Teste (%)", "Trades Treino",
        "Trades Teste", "Win Rate Treino (%)", "Max Drawdown (%)", "Notas"
    ]
    if not os.path.exists(csv_path):
        initial_data = [
            {
                "Criptomoeda": "ETH/USDT",
                "SMA RÃ¡pida": 15,
                "SMA Lenta": 21,
                "Stop Loss (%)": 1.0,
                "Take Profit": "10.0%",
                "Stop MÃ³vel (Trailing)": "NÃ£o",
                "Take Profit Ativo": "Sim",
                "Retorno Treino (%)": 24.08,
                "Retorno Teste (%)": 0.0,
                "Trades Treino": 10,
                "Trades Teste": 0,
                "Win Rate Treino (%)": 30.0,
                "Max Drawdown (%)": 0.0,
                "Notas": "Seguidor de TendÃªncia / Breakout: Lucros brutais nas grandes ondas (+10%) com perdas muito pequenas e controladas (-1%). Ideal para mercados com tendÃªncias fortes e rÃ¡pidas."
            },
            {
                "Criptomoeda": "SOL/USDT",
                "SMA RÃ¡pida": 15,
                "SMA Lenta": 21,
                "Stop Loss (%)": 2.0,
                "Take Profit": "5.0%",
                "Stop MÃ³vel (Trailing)": "NÃ£o",
                "Take Profit Ativo": "Sim",
                "Retorno Treino (%)": 4.53,
                "Retorno Teste (%)": 0.0,
                "Trades Treino": 35,
                "Trades Teste": 0,
                "Win Rate Treino (%)": 51.4,
                "Max Drawdown (%)": -4.10,
                "Notas": "Equilibrado e Consistente: Curva de capital extremamente estÃ¡vel e segura (Drawdown baixÃ­ssimo de 4%). A amplitude curta das mÃ©dias corta perdas muito antes de atingir o Stop Loss."
            },
            {
                "Criptomoeda": "BTC/USDT",
                "SMA RÃ¡pida": 9,
                "SMA Lenta": 21,
                "Stop Loss (%)": 1.0,
                "Take Profit": "3.0%",
                "Stop MÃ³vel (Trailing)": "NÃ£o",
                "Take Profit Ativo": "Sim",
                "Retorno Treino (%)": 8.14,
                "Retorno Teste (%)": -0.26,
                "Trades Treino": 15,
                "Trades Teste": 0,
                "Win Rate Treino (%)": 60.0,
                "Max Drawdown (%)": 0.0,
                "Notas": "Filtro de TendÃªncia EstÃ¡vel: ConfiguraÃ§Ã£o moderada e muito estÃ¡vel. Quase break-even no teste futuro (-0.26%), provando excelente resiliÃªncia contra ruÃ­do e volatilidade rÃ¡pida."
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
        (df["SMA RÃ¡pida"] == recipe["SMA RÃ¡pida"]) &
        (df["SMA Lenta"] == recipe["SMA Lenta"]) &
        (df["Stop Loss (%)"] == recipe["Stop Loss (%)"]) &
        (df["Take Profit"] == recipe["Take Profit"]) &
        (df["Stop MÃ³vel (Trailing)"] == recipe["Stop MÃ³vel (Trailing)"]) &
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

# 1. ConfiguraÃ§Ã£o da PÃ¡gina do Streamlit
st.set_page_config(
    page_title="OlimpoTrade - Algorithmic Trading Lab",
    page_icon="âš¡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. InicializaÃ§Ã£o de Session State para persistÃªncia e ligaÃ§Ã£o dinÃ¢mica de inputs
if "strategy_type_val" not in st.session_state:
    st.session_state.strategy_type_val = "MULTIPOINT_VECTOR"
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
    st.session_state.short_window_val = 12
if "long_window_val" not in st.session_state:
    st.session_state.long_window_val = 26
if "stop_loss_pct_val" not in st.session_state:
    st.session_state.stop_loss_pct_val = 2.0
if "take_profit_pct_val" not in st.session_state:
    st.session_state.take_profit_pct_val = 7.0
if "tp_active_val" not in st.session_state:
    st.session_state.tp_active_val = True
if "trailing_stop_active_val" not in st.session_state:
    st.session_state.trailing_stop_active_val = False

if "backtest_results" not in st.session_state:
    st.session_state.backtest_results = None
if "optimizer_results" not in st.session_state:
    st.session_state.optimizer_results = None

# 3. InjeÃ§Ã£o de CSS Customizado para EstÃ©tica Premium Glassmorphic (Tema Claro / Light Mode)
st.markdown("""
<style>
    /* Importar Fonte Outfit do Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

    /* ConfiguraÃ§Ã£o de Fontes e Fundo Principal */
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

    /* CabeÃ§alho Principal */
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

    /* Cards de MÃ©tricas RÃ¡pidas */
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

    /* Indicador de ConexÃ£o */
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

    /* Estilizar inputs e botÃµes do Streamlit */
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

# 4. CabeÃ§alho da AplicaÃ§Ã£o
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
    strategy_type = st.selectbox(
        "Estratégia Ativa",
        ["SMA_CROSSOVER", "EMA_CROSSOVER", "MULTIPOINT_VECTOR"],
        index=2 if st.session_state.strategy_type_val == "MULTIPOINT_VECTOR" else (1 if st.session_state.strategy_type_val == "EMA_CROSSOVER" else 0),
        format_func=lambda x: "Média Simples (SMA Crossover)" if x == "SMA_CROSSOVER" else ("Média Exponencial (EMA Crossover)" if x == "EMA_CROSSOVER" else "Vetor de 5 Pontos (MultiPoint)"),
        help="Escolha o algoritmo quantitativo de decisão."
    )
with col_ctrl5:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    run_button = st.button("🚀 Executar Simulação Real", use_container_width=True, type="primary")

# ----------------- NOVO PAINEL DE CONFIGURAÃ‡Ã•ES COLAPSÃVEL CENTRAL -----------------
with st.expander("ðŸ› ï¸ Painel Global de ConfiguraÃ§Ã£o do RobÃ´ (Clique para Configurar)", expanded=False):
    st.markdown("""
    <div style='font-size: 0.9rem; color: #64748b; margin-bottom: 1rem;'>
        Configure aqui todos os parÃ¢metros matemÃ¡ticos do algoritmo de trading e as regras estritas de gestÃ£o de risco de banca. 
        Estas definiÃ§Ãµes sÃ£o comuns a todas as abas e afetam o comportamento do robÃ´ instantaneamente!
    </div>
    """, unsafe_allow_html=True)
    
    col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
    
    with col_cfg1:
        st.markdown("##### ðŸ“ˆ Estrutura da EstratÃ©gia")
        if strategy_type == "MULTIPOINT_VECTOR":
            operation_mode = st.selectbox(
                "Modo Operacional da Lagarta",
                ["TREND_FOLLOWING", "MEAN_REVERSION"],
                index=0 if st.session_state.operation_mode_val == "TREND_FOLLOWING" else 1,
                format_func=lambda x: "Seguimento de TendÃªncia (ClÃ¡ssica)" if x == "TREND_FOLLOWING" else "ReversÃ£o Ã  MÃ©dia (Reversa)",
                help="Seguimento de TendÃªncia compra na alta e vende na queda. ReversÃ£o Ã  MÃ©dia compra nos baixos (sobrevenda) e vende nos altos (picos)!"
            )
            entry_mode = st.selectbox(
                "Modo de Entrada (Gatilho)",
                ["3PONTOS", "4PONTOS", "5PONTOS"],
                index=0 if st.session_state.entry_mode_val == "3PONTOS" else (1 if st.session_state.entry_mode_val == "4PONTOS" else 2),
                format_func=lambda x: "Super-Ãgil (3 Pernas: P1 > P2 > P3)" if x == "3PONTOS" else ("Equilibrada (4 Pernas: P1 > P2 > P3 > P4)" if x == "4PONTOS" else "Conservadora (5 Pernas: P1 > P2 > P3 > P4 > P5)"),
                help="Escolha quantas pernas da lagarta devem alinhar para disparar a COMPRA."
            )
            exit_mode = st.selectbox(
                "Modo de SaÃ­da (Suporte)",
                ["P2", "P3", "P4"],
                index=0 if st.session_state.exit_mode_val == "P2" else (1 if st.session_state.exit_mode_val == "P3" else 2),
                format_func=lambda x: "SaÃ­da RÃ¡pida (PreÃ§o < P2/MÃ©dia 9)" if x == "P2" else ("SaÃ­da IntermÃ©dia (PreÃ§o < P3/MÃ©dia 21)" if x == "P3" else "SaÃ­da Lenta (PreÃ§o < P4/MÃ©dia 50)"),
                help="Escolha que suporte a cabeÃ§a da lagarta deve quebrar para disparar a VENDA."
            )
            short_window = 9
            long_window = 21
            multipoint_mode = "AGILE" # Modo dinÃ¢mico controlado por pernas
        else:
            st.info("EstratÃ©gias clÃ¡ssicas de cruzamento nÃ£o possuem sub-modos dinÃ¢micos de pernas.")
            operation_mode = "TREND_FOLLOWING"
            entry_mode = "4PONTOS"
            exit_mode = "P3"
            multipoint_mode = "AGILE"
            
    with col_cfg2:
        st.markdown("##### ðŸ“ Pontos de MediÃ§Ã£o (MÃ©dias)")
        if strategy_type in ["SMA_CROSSOVER", "EMA_CROSSOVER"]:
            short_window = st.number_input(
                "Janela Curta (RÃ¡pida)",
                min_value=2, max_value=100,
                value=st.session_state.short_window_val,
                help="NÃºmero de candles para calcular a mÃ©dia mÃ³vel curta. PadrÃµes profissionais: 9 a 20."
            )
            long_window = st.number_input(
                "Janela Longa (Lenta)",
                min_value=5, max_value=200,
                value=st.session_state.long_window_val,
                help="NÃºmero de candles para calcular a mÃ©dia mÃ³vel lenta. PadrÃµes profissionais: 21 a 50."
            )
            p2_window = 9
            p3_window = 21
            p4_window = 50
            p5_window = 200
            p5_filter_active = False
            exhaustion_filter = False
            exhaustion_threshold = 2.5
        else:
            p2_window = st.number_input(
                "MÃ©dia Muito RÃ¡pida - P2",
                min_value=2, max_value=50,
                value=st.session_state.p2_window_val,
                help="Representa o Ponto 2 (MÃ©dia RÃ¡pida de curto-prazo, ex: 9)."
            )
            p3_window = st.number_input(
                "MÃ©dia Curta/Confirmadora - P3",
                min_value=5, max_value=100,
                value=st.session_state.p3_window_val,
                help="Representa o Ponto 3 (MÃ©dia Curta confirmadora, ex: 21)."
            )
            p4_window = st.number_input(
                "MÃ©dia MÃ©dia - P4",
                min_value=10, max_value=150,
                value=st.session_state.p4_window_val,
                help="Representa o Ponto 4 (MÃ©dia de suporte dinÃ¢mico, ex: 50)."
            )
            p5_window = st.number_input(
                "MÃ©dia Longa/Mestra - P5",
                min_value=50, max_value=500,
                value=st.session_state.p5_window_val,
                help="Representa o Ponto 5 (MÃ©dia Longa da tendÃªncia macro global, ex: 200)."
            )
            p5_filter_active = st.checkbox(
                "Filtro de InclinaÃ§Ã£o P5 (MÃ©dia 200) Ativo",
                value=st.session_state.p5_filter_active_val if "p5_filter_active_val" in st.session_state else True,
                help="Se ativado, bloqueia novas compras se a MÃ©dia 200 estiver inclinada para baixo (macro queda)."
            )
            exhaustion_filter = st.checkbox(
                "Ativar Filtro de ExaustÃ£o",
                value=st.session_state.exhaustion_filter_val,
                help="Se ativado, bloqueia novas compras caso o PreÃ§o Atual (P1) esteja demasiado longe da MÃ©dia RÃ¡pida (P2)."
            )
            if exhaustion_filter:
                exhaustion_threshold = st.slider(
                    "Limite de ExaustÃ£o (%)",
                    0.5, 10.0,
                    value=st.session_state.exhaustion_threshold_val,
                    step=0.1,
                    help="DistÃ¢ncia mÃ¡xima percentual entre o PreÃ§o (P1) e a MÃ©dia RÃ¡pida (P2) para permitir a compra."
                )
            else:
                exhaustion_threshold = 2.5
            short_window = p2_window
            long_window = p3_window
            
    with col_cfg3:
        st.markdown("##### ðŸ›¡ï¸ GestÃ£o de Risco & Banca")
        initial_capital = st.number_input(
            "Capital Inicial (EUR)",
            min_value=100.0, max_value=100000.0,
            value=1000.0,
            step=100.0,
            help="Saldo simulado de Euros com que inicia a sua conta no primeiro dia."
        )
        max_risk_pct = st.slider(
            "Risco por Trade (%)",
            0.1, 5.0, 1.0,
            step=0.1,
            help="A percentagem mÃ¡xima da sua banca total que aceita perder caso a operaÃ§Ã£o atinja o Stop Loss. PadrÃ£o: 1.0%."
        )
        stop_loss_pct = st.slider(
            "Stop Loss (%)",
            0.5, 10.0,
            value=st.session_state.stop_loss_pct_val,
            step=0.1,
            help="Limite de perda automÃ¡tica. Se o preÃ§o cair esta percentagem abaixo da compra, o robÃ´ vende."
        )
        trailing_stop_active = st.checkbox(
            "Acompanhar Lucros (Trailing Stop)",
            value=st.session_state.trailing_stop_active_val,
            help="Se ativado, o seu Stop Loss subirÃ¡ automaticamente acompanhando o preÃ§o para proteger lucros!"
        )
        tp_active = st.checkbox(
            "Take Profit Ativo (Meta de Lucro)",
            value=st.session_state.tp_active_val,
            help="Se ativado, o robÃ´ vende quando atinge a percentagem de ganho definida abaixo."
        )
        if not tp_active:
            take_profit_pct = 999.0
        else:
            take_profit_pct = st.slider(
                "Take Profit (%)",
                1.0, 30.0,
                value=st.session_state.take_profit_pct_val,
                step=0.5,
                help="Alvo de ganho automÃ¡tico. Se o preÃ§o subir esta percentagem, o robÃ´ vende."
            )
        max_daily_loss_pct = st.slider(
            "Limite Perda DiÃ¡ria (%)",
            1.0, 20.0, 5.0,
            step=0.5,
            help="Se a sua conta perder esta percentagem total num Ãºnico dia, o robÃ´ desliga-se automaticamente."
        )
    
    # Adicionar o Guia e DicionÃ¡rio de ParÃ¢metros de forma discreta dentro do Painel de ConfiguraÃ§Ãµes
    with st.expander("ðŸ“š Guia PrÃ¡tico & DicionÃ¡rio de ParÃ¢metros"):
        st.markdown("""
        **Como testar 1 Ano Inteiro (InstantÃ¢neo):**
        1. Defina o **Timeframe** para `1d` (velas diÃ¡rias).
        2. Defina a **Quantidade de Candles** para `365` (1 ano) ou `1000` (quase 3 anos).
        *Isto descarrega instantaneamente dados reais de longo prazo da Binance!*

        ---

        **Conceitos RÃ¡pidos:**
        * **Risco por Trade (%)**: Percentagem da sua banca que aceita perder se o trade correr mal (bater no Stop Loss). Recomenda-se **1%**.
        * **Stop Loss (SL)**: Limite de perda automÃ¡tica. Vende se o ativo cair esta % abaixo do preÃ§o de compra.
        * **Take Profit (TP)**: Alvo de lucro. Vende automaticamente quando o ativo subir esta % para embolsar o ganho.
        * **MÃ©dias MÃ³veis (SMA)**:
          * **Curta (RÃ¡pida)**: MÃ©dia de curto prazo. Reage rÃ¡pido ao preÃ§o (ex: 9 a 20).
          * **Longa (Lenta)**: MÃ©dia de mÃ©dio prazo. Reage devagar (ex: 21 a 50).
        """)

# Sincronizar o estado interno caso o utilizador tenha mexido manualmente nos widgets
st.session_state.strategy_type_val = strategy_type
st.session_state.short_window_val = short_window
st.session_state.long_window_val = long_window
st.session_state.p2_window_val = p2_window
st.session_state.p3_window_val = p3_window
st.session_state.p4_window_val = p4_window
st.session_state.p5_window_val = p5_window
st.session_state.multipoint_mode_val = multipoint_mode
st.session_state.exhaustion_filter_val = exhaustion_filter
st.session_state.exhaustion_threshold_val = exhaustion_threshold
st.session_state.p5_filter_active_val = p5_filter_active
st.session_state.entry_mode_val = entry_mode
st.session_state.exit_mode_val = exit_mode
st.session_state.operation_mode_val = operation_mode

st.session_state.stop_loss_pct_val = stop_loss_pct
st.session_state.tp_active_val = tp_active
st.session_state.trailing_stop_active_val = trailing_stop_active
if tp_active:
    st.session_state.take_profit_pct_val = take_profit_pct

# Carregar configuraÃ§Ãµes e atualizar com a seleÃ§Ã£o da UI
config = load_config()
config.update({
    "INITIAL_CAPITAL": initial_capital,
    "SYMBOL": symbol,
    "TIMEFRAME": timeframe,
    "STRATEGY_TYPE": strategy_type,
    "SHORT_WINDOW": short_window,
    "LONG_WINDOW": long_window,
    "P2_WINDOW": p2_window,
    "P3_WINDOW": p3_window,
    "P4_WINDOW": p4_window,
    "P5_WINDOW": p5_window,
    "MULTIPOINT_MODE": multipoint_mode,
    "EXHAUSTION_FILTER": exhaustion_filter,
    "EXHAUSTION_THRESHOLD": exhaustion_threshold,
    "P5_SLOPE_FILTER_ACTIVE": p5_filter_active,
    "ENTRY_MODE": entry_mode,
    "EXIT_MODE": exit_mode,
    "OPERATION_MODE": operation_mode,
    "MAX_RISK_PER_TRADE_PERCENT": max_risk_pct,
    "STOP_LOSS_PERCENT": stop_loss_pct,
    "TAKE_PROFIT_PERCENT": take_profit_pct,
    "MAX_DAILY_LOSS_PERCENT": max_daily_loss_pct,
    "TRAILING_STOP_ACTIVE": trailing_stop_active
})

# Inicializar logger
logger = setup_logging()

# 7. Abas Principais do LaboratÃ³rio (TABS SIMPLIFICADAS)
tab_backtest, tab_simulator = st.tabs(["ðŸ“ˆ SimulaÃ§Ã£o & GrÃ¡ficos Real", "ðŸ”® LaboratÃ³rio de SimulaÃ§Ã£o & OtimizaÃ§Ã£o"])

# AÃ§Ã£o do BotÃ£o Principal do Backtester
if run_button:
    st.markdown("### â³ Recolhendo dados e processando simulaÃ§Ã£o...")
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

        # Guardar no session state para preservaÃ§Ã£o apÃ³s rerun
        st.session_state.backtest_results = metrics
        st.session_state.backtest_trades = trades
        st.session_state.backtest_capital_history = capital_history
        st.session_state.backtest_df = df_ohlcv
        st.rerun()

# AÃ§Ã£o do BotÃ£o Principal do Backtester
if run_button:
    st.markdown("### â³ Recolhendo dados e processando simulaÃ§Ã£o...")
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

        # Guardar no session state para preservaÃ§Ã£o apÃ³s rerun
        st.session_state.backtest_results = metrics
        st.session_state.backtest_trades = trades
        st.session_state.backtest_capital_history = capital_history
        st.session_state.backtest_df = df_ohlcv
        st.rerun()
with tab_backtest:
    if st.session_state.backtest_results is not None:
        metrics = st.session_state.backtest_results
        trades = st.session_state.backtest_trades
        capital_history = st.session_state.backtest_capital_history
        df_ohlcv = st.session_state.backtest_df


        # Calcular as MÃ©dias no histÃ³rico de acordo com a estratÃ©gia ativa para exibiÃ§Ã£o visual
        df_visualization = df_ohlcv.copy()
        if strategy_type == "SMA_CROSSOVER":
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
            line1_name = f"P2 - MÃ©dia RÃ¡pida ({p2_window})"
            line2_name = f"P3 - MÃ©dia Curta ({p3_window})"
            line3_name = f"P4 - MÃ©dia MÃ©dia ({p4_window})"
            line4_name = f"P5 - MÃ©dia Longa ({p5_window})"
            line1_color = "#0ea5e9"
            line2_color = "#f97316" 

        # --- EXIBIÃ‡ÃƒO DE MÃ‰TRICAS (METRICS CARDS) ---
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="margin-top:0;">ðŸ“Š SumÃ¡rio de Desempenho</h4>', unsafe_allow_html=True)

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
                <div class="metric-label">Taxa de VitÃ³ria</div>
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

        # Outras mÃ©tricas rÃ¡pidas
        st.markdown(
            f"**Total de OperaÃ§Ãµes:** {metrics['num_trades']} | "
            f"**VitÃ³rias:** <span class='text-green'>{metrics['num_wins']}</span> âœ… | "
            f"**Derrotas:** <span class='text-red'>{metrics['num_losses']}</span> âŒ",
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

        # --- GRÃFICOS INTERATIVOS ---

        # 1. Curva de Capital (Equity Curve)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h4>ðŸ“ˆ Curva de Capital (Equity Curve)</h4>', unsafe_allow_html=True)

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

        # PreÃ§o do Ativo de Fundo (Normalizado para Capital Inicial)
        price_normalized = df_ohlcv['close'] / df_ohlcv['close'].iloc[0] * initial_capital
        fig_equity.add_trace(go.Scatter(
            x=dates_chart,
            y=price_normalized,
            mode='lines',
            name=f'EstratÃ©gia Buy & Hold {symbol}',
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

        st.plotly_chart(fig_equity, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # 2. GrÃ¡fico Interativo de Sinais no PreÃ§o do Ativo + MÃ©dias MÃ³veis (SMA)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h4>ðŸŽ¯ JustificaÃ§Ã£o Visual: PreÃ§o & Cruzamento das MÃ©dias MÃ³veis (SMA)</h4>', unsafe_allow_html=True)
        st.markdown(
            "ðŸ’¡ **Por que o robÃ´ entra e sai?** O robÃ´ compra quando a linha azul clara (Curta) cruza **acima** da laranja (Lenta). "
            "Ele vende no cruzamento inverso, ou quando bate no seu Stop Loss automÃ¡tico (limite de seguranÃ§a) ou Take Profit (alvo de lucro)."
        )

        fig_prices = go.Figure()

        # Linha do PreÃ§o Real do Ativo - INTERATIVA (Unified Hover)
        fig_prices.add_trace(go.Scatter(
            x=df_visualization.index,
            y=df_visualization['close'],
            mode='lines',
            name=f'PreÃ§o {symbol}',
            line=dict(color='rgba(71, 85, 105, 0.25)', width=1.5),
            hovertemplate='PreÃ§o: %{y:.2f} EUR<extra></extra>'
        ))

        # Segmentos verde lagarta vibrante (#22c55e) ligando a Entrada Ã  SaÃ­da de cada trade real
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
                    hovertemplate='PreÃ§o Ativo: %{y:.2f} EUR<extra></extra>'
                ))

        # Linhas das mÃ©dias da estratÃ©gia correspondente
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

        # Filtrar e agrupar marcas de BUY e SELL/SL/TP com explicaÃ§Ãµes pedagÃ³gicas completas
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
                
            points_info = f"P1 (PreÃ§o): {p1_val:.2f} EUR<br>P2 (MÃ©dia): {p2_val:.2f} EUR<br>P3 (MÃ©dia): {p3_val:.2f} EUR<br>"
            if strategy_type == "MULTIPOINT_VECTOR":
                points_info = (
                    f"P1 (PreÃ§o): {p1_val:.2f} EUR<br>"
                    f"P2 (MÃ©dia {short_window}): {p2_val:.2f} EUR<br>"
                    f"P3 (MÃ©dia {long_window}): {p3_val:.2f} EUR<br>"
                    f"P4 (MÃ©dia {p4_window if 'p4_window' in locals() else 50}): {p4_val:.2f} EUR<br>"
                )
                if p5_filter_active or entry_mode == "5PONTOS":
                    points_info += f"P5 (MÃ©dia {p5_window if 'p5_window' in locals() else 200}): {p5_val:.2f} EUR<br>"
            
            buy_text.append(
                f"ðŸ“¥ <b>ENTRADA (BUY)</b><br>"
                f"<b>Data</b>: {trade['entry_timestamp'].strftime('%Y-%m-%d %H:%M')}<br>"
                f"<b>PreÃ§o Compra</b>: {trade['entry_price']:.2f} EUR<br>"
                f"<b>Quantidade</b>: {trade['quantity']:.6f}<br>"
                f"<b>Valor Investido</b>: {invested_val:.2f} EUR<br><br>"
                f"<b>Estado dos Pontos de MediÃ§Ã£o:</b><br>{points_info}<br>"
                f"<b>JustificaÃ§Ã£o</b>: Gatilho da estratÃ©gia ativado! ConfirmaÃ§Ã£o de tendÃªncia."
            )

            # SaÃ­da (SELL / STOP LOSS / TAKE PROFIT / TRAILING STOP)
            sell_x.append(trade['exit_timestamp'])
            sell_y.append(trade['exit_price'])
            pnl_sign = "+" if trade['pnl'] >= 0 else ""
            pnl_pct_sign = "+" if trade['pnl_pct'] >= 0 else ""

            if trade['reason'] == "STOP_LOSS":
                justification = f"O preÃ§o caiu abaixo do limite de seguranÃ§a ({stop_loss_pct}%). OperaÃ§Ã£o cortada para proteger o seu capital."
            elif trade['reason'] == "TRAILING_STOP":
                justification = f"O preÃ§o bateu no seu <b>Stop Loss MÃ³vel (Trailing Stop)</b>, que subiu acompanhando a alta para proteger os lucros da banca antes da queda!"
            elif trade['reason'] == "TAKE_PROFIT":
                justification = f"O preÃ§o subiu e atingiu o seu alvo de ganho ideal. Lucro embolsado com sucesso."
            elif trade['reason'] == "STRATEGY_SELL":
                justification = f"SaÃ­da executada por: {trade.get('reason', 'Gatilho de saÃ­da da estratÃ©gia.')}"
            else:
                justification = "Fim do perÃ­odo de testes. PosiÃ§Ã£o fechada de forma virtual ao preÃ§o final de mercado para fins de cÃ¡lculo."

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
                
            points_exit_info = f"P1 (PreÃ§o): {p1_exit:.2f} EUR<br>P2 (MÃ©dia): {p2_exit:.2f} EUR<br>P3 (MÃ©dia): {p3_exit:.2f} EUR<br>"
            if strategy_type == "MULTIPOINT_VECTOR":
                points_exit_info = (
                    f"P1 (PreÃ§o): {p1_exit:.2f} EUR<br>"
                    f"P2 (MÃ©dia {short_window}): {p2_exit:.2f} EUR<br>"
                    f"P3 (MÃ©dia {long_window}): {p3_exit:.2f} EUR<br>"
                    f"P4 (MÃ©dia {p4_window if 'p4_window' in locals() else 50}): {p4_exit:.2f} EUR<br>"
                )
                if p5_filter_active or entry_mode == "5PONTOS":
                    points_exit_info += f"P5 (MÃ©dia {p5_window if 'p5_window' in locals() else 200}): {p5_exit:.2f} EUR<br>"

            sell_text.append(
                f"âŒ <b>SAÃDA ({trade['reason']})</b><br>"
                f"<b>Data</b>: {trade['exit_timestamp'].strftime('%Y-%m-%d %H:%M')}<br>"
                f"<b>PreÃ§o Venda (P1)</b>: {trade['exit_price']:.2f} EUR<br>"
                f"<b>Resultado</b>: {pnl_sign}{trade['pnl']:.2f} EUR ({pnl_pct_sign}{trade['pnl_pct']:.2f}%)<br><br>"
                f"<b>Estado dos Pontos de MediÃ§Ã£o:</b><br>{points_exit_info}<br>"
                f"<b>JustificaÃ§Ã£o</b>: {justification}"
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
                name='SaÃ­das (SELL/SL/TP)',
                marker=dict(symbol='triangle-down', size=14, color='#ef4444', line=dict(color='#b91c1c', width=1.5)),
                text=sell_text,
                hoverinfo='text'
            ))

        fig_prices.update_layout(
            hovermode='x unified', # Guia vertical unificada com todos os valores das mÃ©dias
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=20, b=0),
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
            xaxis=dict(gridcolor='rgba(0,0,0,0.05)', tickfont=dict(color='#475569')),
            yaxis=dict(gridcolor='rgba(0,0,0,0.05)', tickfont=dict(color='#475569')),
            height=400
        )

        st.plotly_chart(fig_prices, use_container_width=True)
        st.caption("ðŸ’¡ Dica: Passe com o rato por cima de qualquer ponto do grÃ¡fico para ver a guia vertical unificada com o preÃ§o e o valor exato das duas mÃ©dias mÃ³veis!")
        st.markdown('</div>', unsafe_allow_html=True)

        # --- TABELA DE OPERAÃ‡Ã•ES ---
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h4>ðŸ“œ HistÃ³rico de Ordens Efetuadas</h4>', unsafe_allow_html=True)

        if trades:
            trades_df = pd.DataFrame(trades)

            # CÃ¡lculo dinÃ¢mico direto na UI para contornar qualquer bug de cache
            trades_df['position_value'] = trades_df['entry_price'] * trades_df['quantity']
            trades_df['capital_after'] = initial_capital + trades_df['pnl'].cumsum()

            trades_df_display = trades_df[[
                'entry_timestamp', 'exit_timestamp', 'action', 'entry_price', 'exit_price', 'quantity', 'position_value', 'pnl', 'pnl_pct', 'capital_after', 'reason'
            ]].copy()

            trades_df_display.columns = [
                'Entrada', 'SaÃ­da', 'AÃ§Ã£o', 'PreÃ§o Entrada', 'PreÃ§o SaÃ­da', 'Quantidade', 'Valor Investido (EUR)', 'PnL (EUR)', 'Retorno (%)', 'Saldo da Banca (EUR)', 'Motivo Fecho'
            ]

            def color_pnl(val):
                color = '#059669' if val >= 0 else '#e11d48'
                return f'color: {color}; font-weight: bold;'

            st.dataframe(
                trades_df_display.style.map(color_pnl, subset=['PnL (EUR)', 'Retorno (%)'])
                .format({'PreÃ§o Entrada': '{:.2f}', 'PreÃ§o SaÃ­da': '{:.2f}', 'Quantidade': '{:.6f}', 'Valor Investido (EUR)': '{:.2f}', 'PnL (EUR)': '{:+.2f}', 'Retorno (%)': '{:+.2f}%', 'Saldo da Banca (EUR)': '{:.2f}'}),
                use_container_width=True
            )
        else:
            st.info("Nenhuma operaÃ§Ã£o foi efetuada durante esta simulaÃ§Ã£o. Tente ajustar os parÃ¢metros das mÃ©dias mÃ³veis ou selecione um nÃºmero maior de candles.")

        st.markdown('</div>', unsafe_allow_html=True)

    else:
        # Estado Inicial da UI
        st.markdown('<div class="glass-card" style="text-align: center; padding: 50px 20px;">', unsafe_allow_html=True)
        st.markdown('<h3 style="margin-top:0;">ðŸš€ Pronto para ComeÃ§ar!</h3>', unsafe_allow_html=True)
        st.markdown(
            'Configure os parÃ¢metros de estratÃ©gia e gestÃ£o de risco no **painel esquerdo** '
            'e carregue no botÃ£o **"Executar SimulaÃ§Ã£o"** para correr o backtest com dados de mercado reais da Binance.',
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

# --- CONTEÃšDO DA ABA 2: OTIMIZADOR DE PARÃ‚METROS ---
with tab_simulator:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<h3>ðŸ”® LaboratÃ³rio de SimulaÃ§Ã£o & OtimizaÃ§Ã£o Unificado</h3>', unsafe_allow_html=True)
    st.markdown("Este laboratÃ³rio permite-lhe testar teorias, visualizar o comportamento dos 5 pontos (com ou sem ReversÃ£o Ã  MÃ©dia) e executar o **Otimizador de ParÃ¢metros integrado** para encontrar a configuraÃ§Ã£o perfeita para qualquer bioma de mercado.")
    
    col_src1, col_src2 = st.columns([2, 3])
    with col_src1:
        market_source = st.radio(
            "Fonte de Mercado para Testes:",
            ["SINTETICO", "MOEDA_REAL"],
            format_func=lambda x: "ðŸ”® Mercado SintÃ©tico (Passeio AleatÃ³rio / Browniano)" if x == "SINTETICO" else f"ðŸ“ˆ Exemplo de Moeda Real da Barra Lateral ({symbol})",
            help="Escolha se deseja testar as estratÃ©gias num mercado gerado artificialmente ou usar dados histÃ³ricos de uma moeda real."
        )

    sim_df = None
    if market_source == "SINTETICO":
        st.markdown("##### âš™ï¸ VariÃ¡veis para GeraÃ§Ã£o do Mercado SintÃ©tico")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            drift = st.slider("TendÃªncia Geral (Drift %)", -5.0, 5.0, 0.0, step=0.1, help="DireÃ§Ã£o geral: positivo para tendÃªncia de alta, negativo para baixa.")
        with col_s2:
            volatility = st.slider("Volatilidade (Instabilidade %)", 0.5, 10.0, 2.5, step=0.1, help="Instabilidade: valores maiores geram ziguezagues mais violentos.")
        with col_s3:
            sim_steps = st.slider("NÃºmero de Velas (Passos)", 50, 500, 250, step=10, help="Quantidade de velas do grÃ¡fico sintÃ©tico.")
            
        st.button("ðŸ”„ Gerar e Testar em Mercado SintÃ©tico Novo")
        
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
            st.info(f"ðŸ“ˆ Usando dados histÃ³ricos de **{symbol} ({timeframe})** com {len(sim_df)} velas como base de testes!")
        else:
            st.warning("âš ï¸ NÃ£o foram encontrados dados reais na memÃ³ria. Puxando dados rÃ¡pidos da Binance...")
            collector = DataCollector(exchange_id='binance', symbol=symbol, timeframe=timeframe)
            sim_df = collector.get_ohlcv(limit=limit_candles)
            if sim_df is not None and not sim_df.empty:
                st.session_state.backtest_df = sim_df
                st.success("Dados reais carregados com sucesso!")

    if sim_df is not None and not sim_df.empty:
        st.session_state.sim_df_val = sim_df
        
        sim_config = config.copy()
        sim_config["INITIAL_CAPITAL"] = 1000.0
        
        sim_bt = Backtester(sim_config, logger)
        sim_trades, sim_cap_history = asyncio.run(sim_bt.run_backtest(sim_df))
        sim_metrics = sim_bt.get_performance_metrics()
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Retorno SimulaÃ§Ã£o", f"{sim_metrics['total_return_pct']:.2f}%")
        with col_m2:
            st.metric("Trades Executados", f"{sim_metrics['num_trades']}")
        with col_m3:
            st.metric("Win Rate", f"{sim_metrics['win_rate']*100:.1f}%")
        with col_m4:
            st.metric("Max Drawdown", f"{sim_metrics['max_drawdown_pct']:.2f}%")
            
        sim_viz = sim_df.copy()
        if strategy_type == "SMA_CROSSOVER":
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
            
        fig_sim = go.Figure()
        
        fig_sim.add_trace(go.Scatter(
            x=sim_viz.index, 
            y=sim_viz['close'], 
            mode='lines', 
            name='PreÃ§o de Teste', 
            line=dict(color='rgba(100, 116, 139, 0.25)', width=1.5),
            hovertemplate='PreÃ§o: %{y:.2f} EUR<extra></extra>'
        ))
        
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
                    hovertemplate='PreÃ§o Ativo: %{y:.2f} EUR<extra></extra>'
                ))
                
        fig_sim.add_trace(go.Scatter(x=sim_viz.index, y=sim_viz['Line_1'], mode='lines', name=l1_n, line=dict(color='#0ea5e9', width=2), hovertemplate=f'{l1_n}: %{{y:.2f}} EUR<extra></extra>'))
        fig_sim.add_trace(go.Scatter(x=sim_viz.index, y=sim_viz['Line_2'], mode='lines', name=l2_n, line=dict(color='#f97316', width=2), hovertemplate=f'{l2_n}: %{{y:.2f}} EUR<extra></extra>'))
        
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
                    f"ðŸ“¥ <b>ENTRADA COMPRA (BUY)</b><br>"
                    f"<b>Data</b>: {entry_t.strftime('%Y-%m-%d %H:%M') if hasattr(entry_t, 'strftime') else entry_t}<br>"
                    f"<b>PreÃ§o Entrada (P1)</b>: {p1_val:.2f} EUR<br>"
                    f"<b>P2 (MÃ©dia {p2_window})</b>: {p2_val:.2f} EUR<br>"
                    f"<b>P3 (MÃ©dia {p3_window})</b>: {p3_val:.2f} EUR<br>"
                    f"<b>P4 (MÃ©dia {p4_window})</b>: {p4_val:.2f} EUR<br>"
                )
                if p5_filter_active or entry_mode == "5PONTOS":
                    buy_info += f"<b>P5 (MÃ©dia {p5_window})</b>: {p5_val:.2f} EUR<br>"
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
                    f"ðŸ“¤ <b>SAÃDA VENDA ({t_s['reason']})</b><br>"
                    f"<b>Data</b>: {exit_t.strftime('%Y-%m-%d %H:%M') if hasattr(exit_t, 'strftime') else exit_t}<br>"
                    f"<b>PreÃ§o SaÃ­da (P1)</b>: {p1_val:.2f} EUR<br>"
                    f"<b>P2 (MÃ©dia {p2_window})</b>: {p2_val:.2f} EUR<br>"
                    f"<b>P3 (MÃ©dia {p3_window})</b>: {p3_val:.2f} EUR<br>"
                    f"<b>P4 (MÃ©dia {p4_window})</b>: {p4_val:.2f} EUR<br>"
                )
                if p5_filter_active or entry_mode == "5PONTOS":
                    sell_info += f"<b>P5 (MÃ©dia {p5_window})</b>: {p5_val:.2f} EUR<br>"
                sell_info += f"<i>Resultado: {t_s['pnl']:.2f} EUR ({t_s['pnl_pct']:.2f}%)</i>"
                sim_sell_text.append(sell_info)
            except Exception:
                sim_sell_text.append(f"VENDA a {t_s['exit_price']:.2f} ({t_s['reason']})")
                
        fig_sim.add_trace(go.Scatter(x=sim_buy_x, y=sim_buy_y, mode='markers', name='COMPRA', marker=dict(symbol='triangle-up', size=14, color='#10b981', line=dict(width=1.5, color='#047857')), text=sim_buy_text, hoverinfo='text'))
        fig_sim.add_trace(go.Scatter(x=sim_sell_x, y=sim_sell_y, mode='markers', name='VENDA', marker=dict(symbol='triangle-down', size=14, color='#ef4444', line=dict(width=1.5, color='#b91c1c')), text=sim_sell_text, hoverinfo='text'))
        
        fig_sim.update_layout(
            title=f"LaboratÃ³rio Visual - Bioma de Testes ({market_source})", 
            hovermode='x unified', 
            template='plotly_white', 
            height=500, 
            margin=dict(l=10, r=10, t=40, b=10)
        )
        st.plotly_chart(fig_sim, use_container_width=True)

        if strategy_type == "MULTIPOINT_VECTOR":
            import logging
            main_logger = logging.getLogger("TradingBot")
            old_level = main_logger.level
            main_logger.setLevel(logging.WARNING)

            entries = ["3PONTOS", "4PONTOS", "5PONTOS"]
            exits = ["P2", "P3", "P4"]
            
            matrix_data = []
            for ent in entries:
                row_dict = {"Modo de Entrada": "Super-Ãgil (3P)" if ent == "3PONTOS" else ("Equilibrada (4P)" if ent == "4PONTOS" else "Conservadora (5P)")}
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
                        "INITIAL_CAPITAL": 1000.0
                    })
                    bt_mat = Backtester(m_cfg, main_logger)
                    asyncio.run(bt_mat.run_backtest(sim_df))
                    met = bt_mat.get_performance_metrics()
                    
                    cell_label = f"SaÃ­da {ex}"
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
            st.markdown("<h3>ðŸ“Š A Matriz de LÃ³gicas da Lagarta (AnÃ¡lise de 9 LÃ³gicas)</h3>", unsafe_allow_html=True)
            st.markdown("Esta tabela exibe o resultado financeiro de **todas as 9 combinaÃ§Ãµes de Entrada e SaÃ­da** possÃ­veis para a nossa lagarta **neste mesmo mercado ativo**. Descubra instantaneamente qual a melhor forma de se mover perante estas ondas!")
            st.info("ðŸ’¡ **Segredo Quantitativo**: Se os resultados de saÃ­das diferentes (P2, P3, P4) derem o mesmo valor na tabela, significa que a tua **GestÃ£o de Risco (Take Profit ou Stop Loss)** fechou as operaÃ§Ãµes antes de o preÃ§o tocar nos gatilhos de saÃ­da das mÃ©dias! Para veres a diferenÃ§a dinÃ¢mica das saÃ­das da lagarta pura, experimenta desativar o Take Profit ou alargar o Stop Loss!")
            
            best_ret = -999.0
            best_combo = None
            for row in matrix_data:
                for ex in ["P2", "P3", "P4"]:
                    cell = row[f"SaÃ­da {ex}"]
                    if cell["ret"] > best_ret:
                        best_ret = cell["ret"]
                        best_combo = cell
            
            html_table = "<table style='width:100%; border-collapse: collapse; text-align: center; font-family: sans-serif;'>"
            html_table += "<tr style='background-color: #0f172a; color: white;'>"
            html_table += "<th style='padding: 12px; border: 1px solid #1e293b;'>Gatilho de Entrada (Pernas)</th>"
            html_table += "<th style='padding: 12px; border: 1px solid #1e293b;'>âš¡ SaÃ­da RÃ¡pida (P2 / MÃ©dia 9)</th>"
            html_table += "<th style='padding: 12px; border: 1px solid #1e293b;'>âš–ï¸ SaÃ­da IntermÃ©dia (P3 / MÃ©dia 21)</th>"
            html_table += "<th style='padding: 12px; border: 1px solid #1e293b;'>ðŸ¢ SaÃ­da Lenta (P4 / MÃ©dia 50)</th>"
            html_table += "</tr>"
            
            for row in matrix_data:
                html_table += "<tr style='border-bottom: 1px solid #cbd5e1;'>"
                html_table += f"<td style='padding: 15px; font-weight: bold; background-color: #f8fafc; border: 1px solid #cbd5e1;'>{row['Modo de Entrada']}</td>"
                for ex in ["P2", "P3", "P4"]:
                    cell = row[f"SaÃ­da {ex}"]
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
                        html_table += "<div style='margin-top: 6px; padding: 2px 6px; background-color: #3b82f6; color: white; border-radius: 4px; font-size: 0.75rem; font-weight: bold; display: inline-block;'>ðŸ† CampeÃ£</div>"
                    html_table += "</td>"
                html_table += "</tr>"
            html_table += "</table>"
            st.markdown(html_table, unsafe_allow_html=True)
            
            col_l1, col_l2 = st.columns([3, 1])
            with col_l1:
                st.markdown(f"ðŸ’¡ **AnÃ¡lise Quantitativa**: A melhor lÃ³gica para este bioma de mercado foi **Entrada {best_combo['entry']} + SaÃ­da {best_combo['exit']}**, obtendo um retorno de **{best_combo['ret']:+.2f}%**.")
            with col_l2:
                if st.button("ðŸ† Aplicar LÃ³gica CampeÃ£", use_container_width=True):
                    st.session_state.entry_mode_val = best_combo["entry"]
                    st.session_state.exit_mode_val = best_combo["exit"]
                    if best_combo["entry"] == "3PONTOS":
                        st.session_state.p5_filter_active_val = False
                    st.success("LÃ³gica campeÃ£ carregada com sucesso! Re-execute para visualizar.")
                    st.rerun()

        st.markdown("---")
        st.markdown("<h3>âš¡ Otimizador de ParÃ¢metros Integrado</h3>", unsafe_allow_html=True)
        st.markdown("Corra o Otimizador de ParÃ¢metros **sobre este mercado ativo** para varrer o comportamento da estratÃ©gia e encontrar a combinaÃ§Ã£o perfeita de MÃ©dias, Stop Loss e Take Profit.")
        
        if "opt_sim_results" not in st.session_state:
            st.session_state.opt_sim_results = None

        if st.button("âš¡ Executar Varredura de ParÃ¢metros neste Mercado", use_container_width=True):
            with st.spinner("A processar varredura de parÃ¢metros..."):
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
                                        "INITIAL_CAPITAL": 1000.0
                                    })
                                    
                                    bt_sint = Backtester(local_cfg, main_logger)
                                    asyncio.run(bt_sint.run_backtest(sim_df))
                                    metrics_sint = bt_sint.get_performance_metrics()
                                    
                                    results_sint.append({
                                        "P2 (RÃ¡pida)": sw,
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
                    st.success("OtimizaÃ§Ã£o concluÃ­da com sucesso!")
                else:
                    st.warning("Nenhum resultado obtido.")
                    
        if st.session_state.opt_sim_results is not None:
            top_df = pd.DataFrame(st.session_state.opt_sim_results)
            st.markdown("##### ðŸ† Top 5 ConfiguraÃ§Ãµes Vencedoras")
            st.dataframe(top_df.head(5).style.format({
                "Retorno (%)": "{:+.2f}%",
                "Max Drawdown (%)": "{:.2f}%",
                "Win Rate (%)": "{:.1f}%",
                "Stop Loss (%)": "{:.1f}%",
                "Take Profit (%)": "{:.1f}%"
            }), use_container_width=True)
            
            best_row = top_df.iloc[0]
            if st.button("ðŸ† Aplicar Melhor ConfiguraÃ§Ã£o Otimizada (Top 1) no Painel Principal", use_container_width=True):
                st.session_state.p2_window_val = int(best_row["P2 (RÃ¡pida)"])
                st.session_state.p3_window_val = int(best_row["P3 (Confirmadora)"])
                st.session_state.short_window_val = int(best_row["P2 (RÃ¡pida)"])
                st.session_state.long_window_val = int(best_row["P3 (Confirmadora)"])
                st.session_state.stop_loss_pct_val = float(best_row["Stop Loss (%)"])
                st.session_state.take_profit_pct_val = float(best_row["Take Profit (%)"])
                st.session_state.trailing_stop_active_val = bool(best_row["Trailing Stop"])
                st.session_state.p5_filter_active_val = False
                
                st.success("ConfiguraÃ§Ã£o Top 1 aplicada com sucesso no Painel de ConfiguraÃ§Ãµes! Re-execute para visualizar.")
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
