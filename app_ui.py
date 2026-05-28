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

with st.expander("🛠️ Painel Global de Configuração do Robô (Clique para Configurar)", expanded=False):
    st.markdown("""
    <div style='font-size: 0.9rem; color: #64748b; margin-bottom: 1rem;'>
        Configure aqui todos os parâmetros matemáticos do algoritmo de trading e as regras estritas de gestão de risco de banca. 
        Estas definições são comuns a todas as abas e afetam o comportamento do robô instantaneamente!
    </div>
    """, unsafe_allow_html=True)
    
    col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
    
    with col_cfg1:
        st.markdown("##### 📈 Estrutura da Estratégia")
        
        # Banner informativo: lagarta selecionada no menu de estrategias principal
        if _active_caterpillar_dna is not None:
            st.success(f"🎓 **Lagarta Especialista Ativa!** | Stop Loss: `{_active_caterpillar_dna['stop_loss_pct']:.2f}%` | Limiar: `{_active_caterpillar_dna['threshold']:.2f}`")

        if strategy_type == "MULTIPOINT_VECTOR":
            operation_mode = st.selectbox(
                "Modo Operacional da Lagarta",
                ["TREND_FOLLOWING", "MEAN_REVERSION"],
                index=0 if st.session_state.operation_mode_val == "TREND_FOLLOWING" else 1,
                format_func=lambda x: "Seguimento de Tendência (Clássica)" if x == "TREND_FOLLOWING" else "Reversão à Média (Reversa)",
                help="Seguimento de Tendência compra na alta e vende na queda. Reversão à Média compra nos baixos (sobrevenda) e vende nos altos (picos)!"
            )
            entry_mode = st.selectbox(
                "Modo de Entrada (Gatilho)",
                ["3PONTOS", "4PONTOS", "5PONTOS"],
                index=0 if st.session_state.entry_mode_val == "3PONTOS" else (1 if st.session_state.entry_mode_val == "4PONTOS" else 2),
                format_func=lambda x: "Super-Ágil (3 Pernas: P1 > P2 > P3)" if x == "3PONTOS" else ("Equilibrada (4 Pernas: P1 > P2 > P3 > P4)" if x == "4PONTOS" else "Conservadora (5 Pernas: P1 > P2 > P3 > P4 > P5)"),
                help="Escolha quantas pernas da lagarta devem alinhar para disparar a COMPRA."
            )
            exit_mode = st.selectbox(
                "Modo de Saída (Suporte)",
                ["P2", "P3", "P4"],
                index=0 if st.session_state.exit_mode_val == "P2" else (1 if st.session_state.exit_mode_val == "P3" else 2),
                format_func=lambda x: "Saída Rápida (Preço < P2/Média 9)" if x == "P2" else ("Saída Intermédia (Preço < P3/Média 21)" if x == "P3" else "Saída Lenta (Preço < P4/Média 50)"),
                help="Escolha que suporte a cabeça da lagarta deve quebrar para disparar a VENDA."
            )
            short_window = 9
            long_window = 21
            multipoint_mode = "AGILE" # Modo dinâmico controlado por pernas
            allow_reentry = True  # Lagarta IA: re-entrada permitida por defeito
        else:
            st.info("Estratégias clássicas de cruzamento não possuem sub-modos dinâmicos de pernas.")
            if strategy_type == "PAULO_GOLD":
                paulo_gold_trend_filter = st.checkbox("Filtro de Tendência Macro (Curta > Lenta)", value=st.session_state.paulo_gold_trend_filter_val, help="Se ativado, o robó só compra se a média rápida estiver acima da lenta. Evita perdas em quedas!")
                if paulo_gold_trend_filter:
                    paulo_gold_min_dist_pct = st.slider(
                        "Distância Mínima das Médias (%)",
                        min_value=0.0, max_value=2.0,
                        value=st.session_state.paulo_gold_min_dist_pct_val,
                        step=0.05,
                        help="O robó só compra se a média curta estiver pelo menos a esta % acima da lenta. Bloqueia ruídos e falsas entradas em mercados horizontais/planos!"
                    )
                else:
                    paulo_gold_min_dist_pct = 0.0
                allow_reentry = True
            else:
                paulo_gold_trend_filter = True
                allow_reentry = st.checkbox(
                "Permitir Re-Entrada em Tendência",
                value=st.session_state.allow_reentry_val,
                help="Se ativado, o robô volta a comprar a meio da subida se o preço recuperar acima da média rápida, mantendo a tendência de alta."
            )
            operation_mode = "TREND_FOLLOWING"
            entry_mode = "4PONTOS"
            exit_mode = "P3"
            multipoint_mode = "AGILE"
            
    with col_cfg2:
        st.markdown("##### 📐 Pontos de Medição (Médias)")
        if strategy_type in ["SMA_CROSSOVER", "EMA_CROSSOVER", "PAULO_GOLD"]:
            short_window = st.number_input(
                "Janela Curta (Rápida)",
                min_value=2, max_value=100,
                value=st.session_state.short_window_val,
                help="Número de candles para calcular a média móvel curta. Padrões profissionais: 9 a 20."
            )
            long_window = st.number_input(
                "Janela Longa (Lenta)",
                min_value=5, max_value=200,
                value=st.session_state.long_window_val,
                help="Número de candles para calcular a média móvel lenta. Padrões profissionais: 21 a 50."
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
                "Média Muito Rápida - P2",
                min_value=2, max_value=50,
                value=st.session_state.p2_window_val,
                help="Representa o Ponto 2 (Média Rápida de curto-prazo, ex: 9)."
            )
            p3_window = st.number_input(
                "Média Curta/Confirmadora - P3",
                min_value=5, max_value=100,
                value=st.session_state.p3_window_val,
                help="Representa o Ponto 3 (Média Curta confirmadora, ex: 21)."
            )
            p4_window = st.number_input(
                "Média Média - P4",
                min_value=10, max_value=150,
                value=st.session_state.p4_window_val,
                help="Representa o Ponto 4 (Média de suporte dinâmico, ex: 50)."
            )
            p5_window = st.number_input(
                "Média Longa/Mestra - P5",
                min_value=50, max_value=500,
                value=st.session_state.p5_window_val,
                help="Representa o Ponto 5 (Média Longa da tendência macro global, ex: 200)."
            )
            p5_filter_active = st.checkbox(
                "Filtro de Inclinação P5 (Média 200) Ativo",
                value=st.session_state.p5_filter_active_val if "p5_filter_active_val" in st.session_state else True,
                help="Se ativado, bloqueia novas compras se a Média 200 estiver inclinada para baixo (macro queda)."
            )
            exhaustion_filter = st.checkbox(
                "Ativar Filtro de Exaustão",
                value=st.session_state.exhaustion_filter_val,
                help="Se ativado, bloqueia novas compras caso o Preço Atual (P1) esteja demasiado longe da Média Rápida (P2)."
            )
            if exhaustion_filter:
                exhaustion_threshold = st.slider(
                    "Limite de Exaustão (%)",
                    0.5, 10.0,
                    value=st.session_state.exhaustion_threshold_val,
                    step=0.1,
                    help="Distância máxima percentual entre o Preço (P1) e a Média Rápida (P2) para permitir a compra."
                )
            else:
                exhaustion_threshold = 2.5
            short_window = p2_window
            long_window = p3_window
            
    with col_cfg3:
        st.markdown("##### 🛡️ Gestão de Risco & Banca")
        initial_capital = st.number_input(
            "Capital Inicial (EUR)",
            min_value=10.0, max_value=100000.0,
            value=100.0,
            step=10.0,
            help="Saldo simulado de Euros com que inicia a sua conta no primeiro dia."
        )
        max_risk_pct = st.slider(
            "Risco por Trade (%)",
            0.1, 5.0, 1.0,
            step=0.1,
            help="A percentagem máxima da sua banca total que aceita perder caso a operação atinja o Stop Loss. Padrão: 1.0%."
        )
        sl_active = st.checkbox(
            "Stop Loss Ativo (Limite de Perda)",
            value=st.session_state.sl_active_val,
            help="Se desativado, o robô só vende quando ocorrer o cruzamento das médias (estratégia pura)."
        )
        if sl_active:
            stop_loss_pct = st.slider(
                "Stop Loss (%)",
                0.5, 10.0,
                value=st.session_state.stop_loss_pct_val,
                step=0.1,
                help="Limite de perda automática. Se o preço cair esta percentagem abaixo da compra, o robô vende."
            )
        else:
            stop_loss_pct = 100.0
        trailing_stop_active = st.checkbox(
            "Acompanhar Lucros (Trailing Stop)",
            value=st.session_state.trailing_stop_active_val,
            help="Se ativado, o seu Stop Loss subirá automaticamente acompanhando o preço para proteger lucros!"
        )
        emergency_exit_price_cross = st.selectbox(
            "Saída de Emergência por Preço",
            ["NONE", "SHORT", "LONG", "ANY"],
            index=["NONE", "SHORT", "LONG", "ANY"].index(st.session_state.emergency_exit_price_cross_val),
            format_func=lambda x: "Desativada" if x == "NONE" else ("Preço < Média Curta" if x == "SHORT" else ("Preço < Média Lenta" if x == "LONG" else "Preço < Qualquer uma")),
            help="Vende a posição imediatamente assim que o preço de fecho atual cruzar abaixo da média selecionada (evita o atraso do cruzamento das médias)."
        )
        
        tp_active = st.checkbox(
            "Take Profit Ativo (Meta de Lucro)",
            value=st.session_state.tp_active_val,
            help="Se ativado, o robô vende quando atinge a percentagem de ganho definida abaixo."
        )
        if not tp_active:
            take_profit_pct = 999.0
        else:
            take_profit_pct = st.slider(
                "Take Profit (%)",
                1.0, 30.0,
                value=st.session_state.take_profit_pct_val,
                step=0.5,
                help="Alvo de ganho automático. Se o preço subir esta percentagem, o robô vende."
            )
        max_daily_loss_pct = st.slider(
            "Limite Perda Diária (%)",
            1.0, 20.0, 5.0,
            step=0.5,
            help="Se a sua conta perder esta percentagem total num único dia, o robô desliga-se automaticamente."
        )
        st.markdown("---")
        st.markdown("##### 💸 Custos & Realismo")
        fee_pct = st.slider(
            "Taxa de Operação da API (%)",
            0.0, 1.0,
            value=st.session_state.fee_pct_val,
            step=0.01,
            help="Comissão cobrada pela exchange por transação. Binance padrão spot é 0.1%."
        )
        tax_pct = st.slider(
            "Imposto sobre Mais-Valias (%)",
            0.0, 50.0,
            value=st.session_state.tax_pct_val,
            step=1.0,
            help="Imposto cobrado sobre o lucro líquido positivo no final do período. Padrão Portugal: 28%."
        )
        slippage_pct = st.slider(
            "Deslizamento / Slippage (%)",
            0.0, 1.0,
            value=st.session_state.slippage_pct_val,
            step=0.01,
            help="Desvio no preço de execução a mercado simulando lag de rede e profundidade."
        )
    
    # Adicionar o Guia e Dicionário de Parâmetros de forma discreta dentro do Painel de Configurações
    with st.expander("📚 Guia Prático & Dicionário de Parâmetros"):
        st.markdown("""
        **Como testar 1 Ano Inteiro (Instantâneo):**
        1. Defina o **Timeframe** para `1d` (velas diárias).
        2. Defina a **Quantidade de Candles** para `365` (1 ano) ou `1000` (quase 3 anos).
        *Isto descarrega instantaneamente dados reais de longo prazo da Binance!*

        ---

        **Conceitos Rápidos:**
        * **Risco por Trade (%)**: Percentagem da sua banca que aceita perder se o trade correr mal (bater no Stop Loss). Recomenda-se **1%**.
        * **Stop Loss (SL)**: Limite de perda automática. Vende se o ativo cair esta % abaixo do preço de compra.
        * **Take Profit (TP)**: Alvo de lucro. Vende automaticamente quando o ativo subir esta % para embolsar o ganho.
        * **Médias Móveis (SMA)**:
          * **Curta (Rápida)**: Média de curto prazo. Reage rápido ao preço (ex: 9 a 20).
          * **Longa (Lenta)**: Média de médio prazo. Reage devagar (ex: 21 a 50).
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

st.session_state.sl_active_val = sl_active
if sl_active:
    st.session_state.stop_loss_pct_val = stop_loss_pct
st.session_state.tp_active_val = tp_active
st.session_state.trailing_stop_active_val = trailing_stop_active
st.session_state.emergency_exit_price_cross_val = emergency_exit_price_cross
st.session_state.allow_reentry_val = allow_reentry
if 'paulo_gold_trend_filter' in locals():
    st.session_state.paulo_gold_trend_filter_val = paulo_gold_trend_filter
if 'paulo_gold_min_dist_pct' in locals():
    st.session_state.paulo_gold_min_dist_pct_val = paulo_gold_min_dist_pct
if tp_active:
    st.session_state.take_profit_pct_val = take_profit_pct

st.session_state.fee_pct_val = fee_pct
st.session_state.tax_pct_val = tax_pct
st.session_state.slippage_pct_val = slippage_pct

# Carregar configurações e atualizar com a seleção da UI
config = load_config()
config.update({
    "INITIAL_CAPITAL": initial_capital,
    "FEE_PERCENT": fee_pct,
    "TAX_PERCENT": tax_pct,
    "SLIPPAGE_PCT": slippage_pct,
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
    "TRAILING_STOP_ACTIVE": trailing_stop_active,
    "EMERGENCY_EXIT_PRICE_CROSS": emergency_exit_price_cross,
    "ALLOW_REENTRY": allow_reentry,
    "PAULO_GOLD_TREND_FILTER": paulo_gold_trend_filter if 'paulo_gold_trend_filter' in locals() else st.session_state.paulo_gold_trend_filter_val,
    "PAULO_GOLD_MIN_DIST_PCT": paulo_gold_min_dist_pct if 'paulo_gold_min_dist_pct' in locals() else st.session_state.paulo_gold_min_dist_pct_val
})

# Inicializar logger
logger = setup_logging()

# 7. Abas Principais do Laboratório (TABS SIMPLIFICADAS)
tab_backtest, tab_simulator, tab_game, tab_math_lab, tab_trader_game = st.tabs(["📊 Simulaçao & Gráficos Real", "🔬 Laboratório de Simulaçao & Otimizaçao", "🎓 Universidade de Lagartas IA", "▵ Laboratório Matemático & Regimes", "🎮 Jogo do Trader Quantitativo"])

# Ação do Botão Principal do Backtester
if run_button:
    st.markdown("### ⏳ Recolhendo dados e processando simulação...")
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

        # Guardar no session state para preservação após rerun
        st.session_state.backtest_results = metrics
        st.session_state.backtest_trades = trades
        st.session_state.backtest_capital_history = capital_history
        st.session_state.backtest_df = df_ohlcv
        st.rerun()

# Ação do Botão Principal do Backtester
if run_button:
    st.markdown("### ⏳ Recolhendo dados e processando simulação...")
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

        # Guardar no session state para preservação após rerun
        st.session_state.backtest_results = metrics
        st.session_state.backtest_trades = trades
        st.session_state.backtest_capital_history = capital_history
        st.session_state.backtest_df = df_ohlcv
        st.rerun()

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

        st.plotly_chart(fig_equity, use_container_width=True)
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

        st.plotly_chart(fig_prices, use_container_width=True)
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
        
        sim_config = config.copy()
        sim_config["INITIAL_CAPITAL"] = 100.0
        
        sim_bt = Backtester(sim_config, logger)
        sim_trades, sim_cap_history = asyncio.run(sim_bt.run_backtest(sim_df))
        sim_metrics = sim_bt.get_performance_metrics()
        
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
                if st.button("🏆 Aplicar Lógica Campeã", use_container_width=True):
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

        if st.button("⚡ Executar Varredura de Parâmetros neste Mercado", use_container_width=True):
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
            }), use_container_width=True)
            
            best_row = top_df.iloc[0]
            if st.button("🏆 Aplicar Melhor Configuração Otimizada (Top 1) no Painel Principal", use_container_width=True):
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
with tab_game:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<h3>🔬 Centro de Treino IA: Especialização & Sobrevivência (Versão 3.0)</h3>', unsafe_allow_html=True)
    st.markdown(
        "Neste centro de investigação quantitativa, a nossa Lagarta aprende a operar **de forma 100% autónoma**."
        " Não és tu quem a ensina — a IA corre terrenos maciços de treino (até 10.000 velas) e evolui o seu DNA "
        "ao longo de gerações darwinianas. Cada trade desconta **comissões** e sofre **slippage** real. "
    )
    
    # 1. PARÂMETROS E CONFIGURAÇÕES DO TREINO
    st.markdown("##### ⚙️ Configurações da Sessão de Treinamento")
    
    col_g1, col_g2, col_g3 = st.columns(3)
    
    with col_g1:
        st.markdown("**1. Selecionar Mercado & Terreno**")
        market_type = st.selectbox(
            "Tipo de Mercado para Treino",
            [
                "Tendência de Alta Forte (Bull Market)",
                "Tendência de Baixa Forte (Bear Market)",
                "Mercado Lateral / Range (Consolidação)",
                "Hiper-Volátil Caótico (Chaos Market)"
            ],
            help="Escolhe o habitat da tua lagarta. Uma especialista BULL aprende a ganhar em altas. Uma BEAR aprende a ganhar em quedas. Lateral aprende a trabalhar em ranges. Caótico é sobrevivência extrema."
        )
        
        dynamic_terrain = st.checkbox(
            "🧬 Terrenos Dinâmicos (Evita Cópia)",
            value=True,
            help="Se ativo, a lagarta enfrenta um gráfico de preços completamente novo a cada nova geração (Epoch). Isto obriga-a a desenvolver regras universais em vez de memorizar o mapa!"
        )
        
    with col_g2:
        st.markdown("**2. Volume de Dados (Dificuldade)**")
        candles_count = st.select_slider(
            "Número de Velas do Terreno de Treino",
            options=[500, 1000, 2000, 5000, 10000],
            value=2000
        )
        
        st.session_state.game_specialist_name = st.text_input(
            "Nome da Lagarta Especialista",
            value=f"Lagarta Especialista {market_type.split()[0]}"
        )
        
    with col_g3:
        st.markdown("**3. Parâmetros Genéticos (Epochs)**")
        generations_count = st.slider(
            "Gerações Evolutivas (Epochs)",
            min_value=5,
            max_value=50,
            value=30,
            step=5
        )
        
        # Recuperar valores da Aba Global
        fee_pct = st.session_state.fee_pct_val
        tax_pct = st.session_state.tax_pct_val
        slippage_pct = st.session_state.slippage_pct_val
        
        st.write(f"💼 Taxa da API (Comissão): **{fee_pct}%**")
        st.write(f"⚡ Slippage Padrão: **{slippage_pct}%**")
        st.write(f"⚖️ Imposto de Mais-Valias: **{tax_pct}%**")
        
    run_training = st.button("🚀 Lançar Treino IA Autónomo", type="primary", use_container_width=True)
    
    # 2. VARIÁVEIS DE ESTADO DA ABA DO JOGO
    if "game_trained_champion" not in st.session_state:
        st.session_state.game_trained_champion = None
    if "game_learning_curve" not in st.session_state:
        st.session_state.game_learning_curve = []
    if "game_prices" not in st.session_state:
        st.session_state.game_prices = []
    if "game_training_history" not in st.session_state:
        st.session_state.game_training_history = []
    if "game_trained_caterpillars" not in st.session_state:
        st.session_state.game_trained_caterpillars = {}
        
    # 3. MOTOR GENÉTICO ULTRA-RÁPIDO EM PYTHON (VERSÃO 3.0)
    if run_training:
        mutation_rate = 5 # Taxa de mutação genética padrão (5%)
        with st.spinner(f"A treinar a população de lagartas sobre {candles_count} velas por {generations_count} gerações..."):
            
            # Função para gerar preços e indicadores dinamicamente com base em seed
            def generate_terrain(seed_val, size_val):
                t_local = np.linspace(0, 15, size_val)
                np.random.seed(seed_val)
                if "Alta" in market_type or "Bull" in market_type:
                    # BULL: tendencia de subida clara com oscilacoes suaves
                    prices = 100.0 + t_local * 4.5 + 12.0 * np.sin(t_local * 1.5) + np.random.normal(0, 0.8, size_val)
                elif "Baixa" in market_type or "Bear" in market_type:
                    # BEAR: tendencia de descida clara — espelho do BULL
                    prices = 100.0 + t_local * (-4.5) + 12.0 * np.sin(t_local * 1.5) + np.random.normal(0, 0.8, size_val)
                elif "Lateral" in market_type:
                    # LATERAL: oscila horizontalmente em torno de 100
                    prices = 100.0 + 15.0 * np.sin(t_local * 2.5) + np.random.normal(0, 0.5, size_val)
                else:
                    # CAOTICO: oscilacoes violentas, tendencia indefinida (sobrevivencia extrema)
                    prices = 100.0 + 8.0 * np.sin(t_local * 0.8) + 20.0 * np.sin(t_local * 5.5) + np.random.normal(0, 3.5, size_val)
                prices = np.clip(prices, 5.0, 100000.0).tolist()
                
                df_local = pd.DataFrame({"close": prices})
                df_local['MA_Fast'] = df_local['close'].rolling(window=5).mean()
                df_local['MA_Slow'] = df_local['close'].rolling(window=12).mean()
                df_local['MA_200'] = df_local['close'].rolling(window=20).mean()
                df_local['Std'] = df_local['close'].rolling(window=8).std()
                
                delta_l = df_local['close'].diff()
                gain_l = (delta_l.where(delta_l > 0, 0)).rolling(window=8).mean()
                loss_l = (-delta_l.where(delta_l < 0, 0)).rolling(window=8).mean()
                rs_l = gain_l / (loss_l + 1e-5)
                df_local['RSI'] = 100 - (100 / (1 + rs_l))
                df_local = df_local.fillna(method='bfill')
                
                return (
                    prices,
                    df_local['close'].values,
                    df_local['MA_Fast'].values,
                    df_local['MA_Slow'].values,
                    df_local['MA_200'].values,
                    df_local['Std'].values,
                    df_local['RSI'].values
                )

            # C. Inicializar 25 lagartas com DNA aleatório (Versão 3.0)
            pop_size = 25
            
            def make_dna():
                return {
                    "w_trend": np.random.uniform(-1.0, 1.0),
                    "w_slope": np.random.uniform(-1.0, 1.0),
                    "w_vol": np.random.uniform(-1.0, 1.0),
                    "w_floor": np.random.uniform(-1.0, 1.0),
                    "w_rsi": np.random.uniform(-1.0, 1.0),
                    "w_stop": np.random.uniform(-0.5, 0.5),
                    "threshold": np.random.uniform(0.1, 1.2),
                    "stop_loss_pct": np.random.uniform(0.5, 6.0),
                    "bank": 100.0,
                    "net_bank": 100.0,
                    "in_trade": False,
                    "entry_price": 0.0,
                    "trade_size": 0.0,
                    "units": 0.0,
                    "alive": True,
                    "trades_count": 0
                }
                
            population = [make_dna() for _ in range(pop_size)]
            learning_curve = []
            
            # Se terrenos dinâmicos estiver ativo, o terreno é gerado a cada época.
            # Caso contrário, geramos um terreno único estático para todo o treino.
            if not dynamic_terrain:
                close_prices, prices_arr, ma_f_arr, ma_s_arr, ma_200_arr, std_arr, rsi_arr = generate_terrain(42, candles_count)
            
            # D. Loop Evolutivo por Gerações
            for gen in range(1, generations_count + 1):
                # Resetar bancos e estados a cada nova geração de vida
                for ind in population:
                    ind["bank"] = 100.0
                    ind["in_trade"] = False
                    ind["alive"] = True
                    ind["trades_count"] = 0
                
                # Regenerar Terreno dinâmico contra cópia se ativado!
                if dynamic_terrain:
                    close_prices, prices_arr, ma_f_arr, ma_s_arr, ma_200_arr, std_arr, rsi_arr = generate_terrain(100 + gen, candles_count)
                    
                # Correr o terreno de velas
                for i in range(20, candles_count):
                    p_c = prices_arr[i]
                    ma_f_c = ma_f_arr[i]
                    ma_s_c = ma_s_arr[i]
                    ma_f_p = ma_f_arr[i-1]
                    ma_200 = ma_200_arr[i]
                    std_val = std_arr[i]
                    rsi_val = rsi_arr[i]
                    
                    # Sensores (Valores binários/trinários rápidos)
                    s1_trend = 1.0 if (p_c > ma_f_c > ma_s_c) else -1.0
                    s2_slope = 1.0 if (ma_f_c > ma_f_p) else -1.0
                    s3_vol = -1.0 if (std_val > 6.0) else 1.0
                    s4_floor = -1.0 if ((p_c - ma_200)/ma_200 > 0.09) else 1.0
                    s5_rsi = 1.0 if (rsi_val < 35) else (-1.0 if rsi_val > 65 else 0.0)
                    
                    for ind in population:
                        if not ind["alive"]:
                            continue
                            
                        # Verificar Stop Loss de Sobrevivência
                        if ind["in_trade"]:
                            pnl_pct_ind = (p_c - ind["entry_price"]) / ind["entry_price"] * 100
                            if pnl_pct_ind < -ind["stop_loss_pct"]:
                                # Stop Loss disparado instantaneamente (Preço piorado pelo slippage)
                                real_exit = p_c * (1 - slippage_pct / 100.0)
                                gross_val = real_exit * ind["units"]
                                en_fee = ind["trade_size"] * (fee_pct / 100.0)
                                ex_fee = gross_val * (fee_pct / 100.0)
                                net_pnl = gross_val - ind["trade_size"] - (en_fee + ex_fee)
                                
                                ind["bank"] += net_pnl
                                ind["trades_count"] += 1
                                ind["in_trade"] = False
                                if ind["bank"] < 10.0:
                                    ind["bank"] = 0.0
                                    ind["alive"] = False
                                continue
                        
                        # Decisão neuronal
                        score = (
                            ind["w_trend"] * s1_trend +
                            ind["w_slope"] * s2_slope +
                            ind["w_vol"] * s3_vol +
                            ind["w_floor"] * s4_floor +
                            ind["w_rsi"] * s5_rsi
                        )
                        
                        w_dec = "entrar" if (score > ind["threshold"]) else "sair"
                        
                        if w_dec == "entrar" and not ind["in_trade"] and ind["bank"] >= 10.0:
                            ind["in_trade"] = True
                            ind["trade_size"] = ind["bank"] * 0.95
                            ind["entry_price"] = p_c * (1 + slippage_pct / 100.0)
                            ind["units"] = ind["trade_size"] / ind["entry_price"]
                        elif w_dec == "sair" and ind["in_trade"]:
                            # Fechar posição (Preço piorado pelo slippage)
                            real_exit = p_c * (1 - slippage_pct / 100.0)
                            gross_val = real_exit * ind["units"]
                            en_fee = ind["trade_size"] * (fee_pct / 100.0)
                            ex_fee = gross_val * (fee_pct / 100.0)
                            net_pnl = gross_val - ind["trade_size"] - (en_fee + ex_fee)
                            
                            ind["bank"] += net_pnl
                            ind["trades_count"] += 1
                            ind["in_trade"] = False
                            if ind["bank"] < 10.0:
                                ind["bank"] = 0.0
                                ind["alive"] = False
                                
                # Avaliação de Fitness líquida de Imposto e penalização por inatividade
                # Se o terreno for bearish (tendência de queda), perdoamos a inatividade (min_trades = 0)
                is_bearish = prices_arr[-1] < prices_arr[0]
                min_trades_required = 0 if is_bearish else max(3, int(candles_count / 1500))
                for ind in population:
                    # Fechar trade virtual pendente na última vela
                    if ind["in_trade"]:
                        p_c = prices_arr[-1]
                        real_exit = p_c * (1 - slippage_pct / 100.0)
                        gross_val = real_exit * ind["units"]
                        en_fee = ind["trade_size"] * (fee_pct / 100.0)
                        ex_fee = gross_val * (fee_pct / 100.0)
                        net_pnl = gross_val - ind["trade_size"] - (en_fee + ex_fee)
                        ind["bank"] += net_pnl
                        ind["trades_count"] += 1
                        ind["in_trade"] = False
                        if ind["bank"] < 0:
                            ind["bank"] = 0.0
                            ind["alive"] = False

                    # Penalização por inatividade comercial
                    if ind["trades_count"] < min_trades_required:
                        ind["bank"] = ind["bank"] * 0.15 # Perde 85% do saldo final
                        
                    gross_profit = ind["bank"] - 100.0
                    if gross_profit > 0:
                        tax_due = gross_profit * (tax_pct / 100.0)
                        ind["net_bank"] = ind["bank"] - tax_due
                    else:
                        ind["net_bank"] = ind["bank"]
                
                # Seleção natural (Ordenar pelo banco líquido final)
                population.sort(key=lambda x: x["net_bank"], reverse=True)
                champ = population[0]
                
                # CORRER SIMULAÇÃO DE REFERÊNCIA FIXA (SEED 42) PARA A CURVA DE CONVERGÊNCIA REAL E ESTÁVEL
                ref_prices, ref_prices_arr, ref_ma_f_arr, ref_ma_s_arr, ref_ma_200_arr, ref_std_arr, ref_rsi_arr = generate_terrain(42, min(2000, candles_count))
                
                ref_bank = 100.0
                ref_in_trade = False
                ref_entry_price = 0.0
                ref_units = 0.0
                ref_trade_size = 0.0
                
                for idx_ref in range(20, len(ref_prices_arr)):
                    p_ref = ref_prices_arr[idx_ref]
                    ma_f_ref = ref_ma_f_arr[idx_ref]
                    ma_s_ref = ref_ma_s_arr[idx_ref]
                    ma_f_p_ref = ref_ma_f_arr[idx_ref-1]
                    ma_200_ref = ref_ma_200_arr[idx_ref]
                    std_ref = ref_std_arr[idx_ref]
                    rsi_ref = ref_rsi_arr[idx_ref]
                    
                    s1_t = 1.0 if (p_ref > ma_f_ref > ma_s_ref) else -1.0
                    s2_s = 1.0 if (ma_f_ref > ma_f_p_ref) else -1.0
                    s3_v = -1.0 if (std_ref > 6.0) else 1.0
                    s4_f = -1.0 if ((p_ref - ma_200_ref)/ma_200_ref > 0.09) else 1.0
                    s5_r = 1.0 if (rsi_ref < 35) else (-1.0 if rsi_ref > 65 else 0.0)
                    
                    if ref_in_trade:
                        pnl_pct_ref = (p_ref - ref_entry_price) / ref_entry_price * 100
                        if pnl_pct_ref < -champ["stop_loss_pct"]:
                            r_exit = p_ref * (1 - slippage_pct / 100.0)
                            g_val = r_exit * ref_units
                            en_f = ref_trade_size * (fee_pct / 100.0)
                            ex_f = g_val * (fee_pct / 100.0)
                            n_pnl = g_val - ref_trade_size - (en_f + ex_f)
                            
                            ref_bank += n_pnl
                            ref_in_trade = False
                            if ref_bank < 10.0:
                                ref_bank = 0.0
                                break
                            continue
                            
                    score_ref = (
                        champ["w_trend"] * s1_t +
                        champ["w_slope"] * s2_s +
                        champ["w_vol"] * s3_v +
                        champ["w_floor"] * s4_f +
                        champ["w_rsi"] * s5_r
                    )
                    
                    w_dec_ref = "entrar" if (score_ref > champ["threshold"]) else "sair"
                    
                    if w_dec_ref == "entrar" and not ref_in_trade and ref_bank >= 10.0:
                        ref_in_trade = True
                        ref_trade_size = ref_bank * 0.95
                        ref_entry_price = p_ref * (1 + slippage_pct / 100.0)
                        ref_units = ref_trade_size / ref_entry_price
                    elif w_dec_ref == "sair" and ref_in_trade:
                        r_exit = p_ref * (1 - slippage_pct / 100.0)
                        g_val = r_exit * ref_units
                        en_f = ref_trade_size * (fee_pct / 100.0)
                        ex_f = g_val * (fee_pct / 100.0)
                        n_pnl = g_val - ref_trade_size - (en_f + ex_f)
                        
                        ref_bank += n_pnl
                        ref_in_trade = False
                        if ref_bank < 10.0:
                            ref_bank = 0.0
                            break
                            
                if ref_in_trade:
                    p_ref = ref_prices_arr[-1]
                    r_exit = p_ref * (1 - slippage_pct / 100.0)
                    g_val = r_exit * ref_units
                    en_f = ref_trade_size * (fee_pct / 100.0)
                    ex_f = g_val * (fee_pct / 100.0)
                    n_pnl = g_val - ref_trade_size - (en_f + ex_f)
                    ref_bank += n_pnl
                    
                g_p_ref = ref_bank - 100.0
                if g_p_ref > 0:
                    net_ref_bank = ref_bank - g_p_ref * (tax_pct / 100.0)
                else:
                    net_ref_bank = ref_bank
                    
                learning_curve.append(net_ref_bank)
                
                # Crossover e Mutação
                parents = population[:5] # Top 20%
                new_pop = [parents[0].copy(), parents[1].copy()] # Elitismo (preserva os 2 melhores)
                
                import random
                while len(new_pop) < pop_size:
                    p1 = random.choice(parents)
                    p2 = random.choice(parents)
                    child = {
                        "w_trend": p1["w_trend"] if random.random() < 0.5 else p2["w_trend"],
                        "w_slope": p1["w_slope"] if random.random() < 0.5 else p2["w_slope"],
                        "w_vol": p1["w_vol"] if random.random() < 0.5 else p2["w_vol"],
                        "w_floor": p1["w_floor"] if random.random() < 0.5 else p2["w_floor"],
                        "w_rsi": p1["w_rsi"] if random.random() < 0.5 else p2["w_rsi"],
                        "w_stop": p1["w_stop"] if random.random() < 0.5 else p2["w_stop"],
                        "threshold": p1["threshold"] if random.random() < 0.5 else p2["threshold"],
                        "stop_loss_pct": p1["stop_loss_pct"] if random.random() < 0.5 else p2["stop_loss_pct"],
                        "bank": 100.0,
                        "net_bank": 100.0,
                        "in_trade": False,
                        "entry_price": 0.0,
                        "trade_size": 0.0,
                        "units": 0.0,
                        "alive": True,
                        "trades_count": 0
                    }
                    # Mutação
                    for gene in ["w_trend", "w_slope", "w_vol", "w_floor", "w_rsi", "w_stop", "threshold", "stop_loss_pct"]:
                        if random.random() < (mutation_rate / 100.0):
                            if gene == "stop_loss_pct":
                                child[gene] = np.clip(child[gene] + np.random.uniform(-0.5, 0.5), 0.5, 10.0)
                            elif gene == "threshold":
                                child[gene] = np.clip(child[gene] + np.random.uniform(-0.1, 0.1), 0.05, 1.5)
                            else:
                                child[gene] = np.clip(child[gene] + np.random.uniform(-0.2, 0.2), -1.0, 1.0)
                    new_pop.append(child)
                population = new_pop
                
            # E. Fim do Treino - Extrair Campeã absoluta sintonizada
            champion = champ.copy()
            st.session_state.game_trained_champion = champion
            st.session_state.game_learning_curve = learning_curve
            
            # PROVA DE FOGO (EXAME CEGO FINAL): 
            # Geramos um terreno final Z completamente novo e cego com TAMANHO IDENTICO ao de treino (candles_count)
            # usando a semente 999
            test_prices, test_prices_arr, test_ma_f_arr, test_ma_s_arr, test_ma_200_arr, test_std_arr, test_rsi_arr = generate_terrain(999, candles_count)
            st.session_state.game_prices = test_prices # Armazenamos o terreno de teste cego para auditoria
            
            # Determinar taxa de sobrevivência no final do treino
            alive_count = sum(1 for ind in population if ind["alive"])
            survival_rate = (alive_count / pop_size) * 100.0
            
            # Salvar no registo persistente da Universidade de Lagartas para o Hermes (Mercado de Trabalho)
            if "game_trained_caterpillars" not in st.session_state:
                st.session_state.game_trained_caterpillars = {}
            # Enriquecer o DNA com metadados de habitat e treino
            champion["market_habitat"] = market_type  # Tipo de mercado em que foi treinada
            champion["trained_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            champion["training_candles"] = candles_count
            champion["training_sessions"] = len([h for h in st.session_state.game_training_history
                                                  if h.get("Lagarta") == st.session_state.game_specialist_name]) + 1

            st.session_state.game_trained_caterpillars[st.session_state.game_specialist_name] = champion

            # Gravar em disco para persistencia entre sessoes e acesso por outros programas
            try:
                with open(_CATERPILLARS_FILE, "w", encoding="utf-8") as _f:
                    json.dump(st.session_state.game_trained_caterpillars, _f, indent=2, ensure_ascii=False)
            except Exception as _e:
                st.warning(f"Aviso: Nao foi possivel gravar lagarta em disco: {_e}")

            # Adicionar ao Histórico
            session_id = len(st.session_state.game_training_history) + 1
            st.session_state.game_training_history.append({
                "Nº Treino": session_id,
                "Lagarta": st.session_state.game_specialist_name,
                "Terreno/Mercado": market_type.split("(")[0].strip(),
                "Velas": candles_count,
                "Banca Final (EUR)": round(champion["net_bank"], 2),
                "w_Trend": round(champion["w_trend"], 2),
                "w_Slope": round(champion["w_slope"], 2),
                "w_Vol": round(champion["w_vol"], 2),
                "w_Chão": round(champion["w_floor"], 2),
                "w_RSI": round(champion["w_rsi"], 2),
                "Sobrevivência (%)": round(survival_rate, 1),
                "SL Aprendido (%)": round(champion["stop_loss_pct"], 2),
                "Gatilho Aprendido": round(champion["threshold"], 2),
                "Resultado": "Sucesso" if champion["net_bank"] > 100 else ("Colapso" if champion["net_bank"] <= 0 else "Sobrevivente Neutral"),
                "Modo": "Dinâmico" if dynamic_terrain else "Estático"
            })
            
            st.success(f"🎉 Sessão de Treino Concluída! Lagarta '{st.session_state.game_specialist_name}' especializada em {market_type.split('(')[0]}!")
            st.rerun()

    # 4. EXIBIÇÃO DA CURVA DE APRENDIZAGEM & HISTÓRICO
    if st.session_state.game_trained_champion is not None:
        st.markdown("---")
        st.markdown("##### 📈 Prova de Aprendizagem (Curva de Evolução & Histórico)")
        
        col_curve, col_table = st.columns([1.2, 1.5])
        
        with col_curve:
            st.markdown("<span style='font-size:0.9rem; font-weight:600;'>Banca da Campeã por Geração (Curva de Aprendizagem)</span>", unsafe_allow_html=True)
            
            # Plotly Line Chart da curva de aprendizado
            fig_curve = go.Figure()
            gens_x = list(range(1, len(st.session_state.game_learning_curve) + 1))
            fig_curve.add_trace(go.Scatter(
                x=gens_x,
                y=st.session_state.game_learning_curve,
                mode='lines+markers',
                name='Banca Líquida (EUR)',
                line=dict(color='#22c55e', width=3),
                marker=dict(size=6, color='#15803d')
            ))
            fig_curve.update_layout(
                height=260,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(title="Geração (Epoch)", showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
                yaxis=dict(title="Banca Líquida (EUR)", showgrid=True, gridcolor='rgba(255,255,255,0.03)')
            )
            st.plotly_chart(fig_curve, use_container_width=True)
            st.info("💡 **Como interpretar:** Se a linha estiver a subir ao longo das Gerações, a lagarta aprendeu a adaptar o seu DNA para evitar perdas e focar em ganhos líquidos reais!")
            
        with col_table:
            st.markdown("<span style='font-size:0.9rem; font-weight:600;'>Histórico de Sessões de Treino</span>", unsafe_allow_html=True)
            df_hist = pd.DataFrame(st.session_state.game_training_history)
            st.dataframe(
                df_hist,
                width='stretch',
                column_config={
                    "Nº Treino": st.column_config.NumberColumn("Nº", width=35),
                    "Lagarta": st.column_config.TextColumn("Nome Lagarta"),
                    "Banca Final (EUR)": st.column_config.NumberColumn("Banca Final", format="%.2f EUR"),
                    "w_Trend": st.column_config.NumberColumn("w_Trend", format="%.2f", width=55),
                    "w_Slope": st.column_config.NumberColumn("w_Slope", format="%.2f", width=55),
                    "w_Vol": st.column_config.NumberColumn("w_Vol", format="%.2f", width=55),
                    "w_Chão": st.column_config.NumberColumn("w_Chão", format="%.2f", width=55),
                    "w_RSI": st.column_config.NumberColumn("w_RSI", format="%.2f", width=55),
                    "Sobrevivência (%)": st.column_config.NumberColumn("Sobrevivência", format="%.1f%%"),
                    "SL Aprendido (%)": st.column_config.NumberColumn("SL (%)", format="%.2f%%"),
                    "Gatilho Aprendido": st.column_config.NumberColumn("Limiar", format="%.2f"),
                    "Modo": st.column_config.TextColumn("Treino", width=70)
                },
                hide_index=True
            )
            
        # 4b. ARQUIVO DE ESPECIALISTAS — Consulta, Gestao e Exportacao
        if st.session_state.game_trained_caterpillars:
            st.markdown("---")
            st.markdown("### 📚 Arquivo de Especialistas Treinadas")
            st.caption("Todas as lagartas listadas estao gravadas em disco (caterpillars.json) e disponiveis no menu principal de Estrategias.")

            _specialist_names = list(st.session_state.game_trained_caterpillars.keys())
            _sel_spec = st.selectbox(
                "🔍 Consultar Especialista",
                _specialist_names,
                key="archive_specialist_selector"
            )

            if _sel_spec:
                _dna = st.session_state.game_trained_caterpillars[_sel_spec]
                st.markdown(f"#### 🧬 DNA da Lagarta: `{_sel_spec}`")

                _col_d1, _col_d2, _col_d3 = st.columns(3)

                with _col_d1:
                    st.markdown("**🧠 Pesos Neuronais (Como Pensa)**")
                    st.metric("w_trend (Tendencia)", f"{_dna.get('w_trend', 0):.3f}", help="Importancia dada a tendencia macro")
                    st.metric("w_slope (Momentum)", f"{_dna.get('w_slope', 0):.3f}", help="Importancia dada ao momentum/velocidade")
                    st.metric("w_vol (Volatilidade)", f"{_dna.get('w_vol', 0):.3f}", help="Importancia dada a volatilidade")
                    st.metric("w_floor (Suporte)", f"{_dna.get('w_floor', 0):.3f}", help="Importancia dada ao suporte da media lenta")
                    st.metric("w_rsi (RSI)", f"{_dna.get('w_rsi', 0):.3f}", help="Importancia dada ao RSI")

                with _col_d2:
                    st.markdown("**🎯 Parametros de Decisao**")
                    st.metric("Limiar de Entrada", f"{_dna.get('threshold', 0):.3f}", help="Score minimo para decidir entrar")
                    st.metric("Stop Loss (%)", f"{_dna.get('stop_loss_pct', 0):.2f}%", help="Perda maxima tolerada antes de sair")
                    st.metric("Banca Final (EUR)", f"EUR {_dna.get('net_bank', 0):.2f}", help="Capital final no ultimo treino")
                    st.markdown("---")
                    st.markdown("**🌍 Habitat & Metadados**")
                    _habitat_raw = _dna.get("market_habitat", "Desconhecido")
                    _habitat_emoji = "🐂" if "Alta" in _habitat_raw or "Bull" in _habitat_raw else (
                                     "🐻" if "Baixa" in _habitat_raw or "Bear" in _habitat_raw else (
                                     "↔️" if "Lateral" in _habitat_raw else "💥"))
                    st.markdown(f"**Habitat:** {_habitat_emoji} `{_habitat_raw.split('(')[0].strip()}`")
                    st.markdown(f"**Treinada em:** `{_dna.get('trained_at', 'N/A')}`")
                    st.markdown(f"**Velas de treino:** `{_dna.get('training_candles', 'N/A')}`")
                    st.markdown(f"**Sessoes de treino:** `{_dna.get('training_sessions', 'N/A')}`")
                    st.code("caterpillars.json", language="text")

                with _col_d3:
                    st.markdown("**📊 Regra de Entrada (Visualizacao)**")
                    _w_dict = {
                        "Tendencia": _dna.get('w_trend', 0),
                        "Momentum": _dna.get('w_slope', 0),
                        "Volatilidade": _dna.get('w_vol', 0),
                        "Suporte": _dna.get('w_floor', 0),
                        "RSI": _dna.get('w_rsi', 0)
                    }
                    _max_w_val = max(_w_dict.values()) if _w_dict else 1
                    _thresh_val = _dna.get('threshold', 0.5)
                    for _sn, _sw in sorted(_w_dict.items(), key=lambda x: -x[1]):
                        _bar_len = int((_sw / max(_max_w_val, 0.001)) * 10)
                        _bar_viz = "█" * _bar_len + "░" * (10 - _bar_len)
                        st.markdown(f"`{_sn:<12}` {_bar_viz} `{_sw:.3f}`")
                    st.markdown(f"**Score >= `{_thresh_val:.3f}` para COMPRAR**")
                    st.caption("score = soma(peso x sensor). Se score > limiar → entra no mercado")

                # Acoes
                _col_a1, _col_a2, _col_a3 = st.columns(3)
                with _col_a1:
                    if st.button(f"🗑️ Apagar '{_sel_spec}'", key="del_spec_btn", type="secondary"):
                        del st.session_state.game_trained_caterpillars[_sel_spec]
                        try:
                            _cfp = os.path.join(os.path.dirname(__file__), "caterpillars.json")
                            with open(_cfp, "w", encoding="utf-8") as _f:
                                json.dump(st.session_state.game_trained_caterpillars, _f, indent=2, ensure_ascii=False)
                        except Exception:
                            pass
                        st.success(f"Lagarta '{_sel_spec}' apagada!")
                        st.rerun()
                with _col_a2:
                    _export_data = json.dumps({_sel_spec: _dna}, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="📥 Exportar DNA (JSON)",
                        data=_export_data,
                        file_name=f"lagarta_{_sel_spec.replace(' ', '_')}.json",
                        mime="application/json",
                        key="export_spec_btn"
                    )
                with _col_a3:
                    st.success(f"💾 Disponivel no menu principal como estrategia")

        # 5. AUDITORIA VISUAL DO GRÁFICO PÓS-TREINO & CÉREBRO DA CAMPEÃ
        st.markdown("---")
        st.markdown("##### 🔍 Auditoria Visual Pós-Treino (Como a Campeã opera no final?)")
        
        champ = st.session_state.game_trained_champion
        
        # Calcular os indicadores para todo o terreno de teste cego
        df_post = pd.DataFrame({"close": st.session_state.game_prices})
        df_post['MA_Fast'] = df_post['close'].rolling(window=5).mean()
        df_post['MA_Slow'] = df_post['close'].rolling(window=12).mean()
        df_post['MA_200'] = df_post['close'].rolling(window=20).mean()
        df_post['Std'] = df_post['close'].rolling(window=8).std()
        
        delta_p = df_post['close'].diff()
        gain_p = (delta_p.where(delta_p > 0, 0)).rolling(window=8).mean()
        loss_p = (-delta_p.where(delta_p < 0, 0)).rolling(window=8).mean()
        rs_p = gain_p / (loss_p + 1e-5)
        df_post['RSI'] = 100 - (100 / (1 + rs_p))
        df_post = df_post.fillna(method='bfill')
        
        # Simular a campeã em TODO o terreno do Exame Cego (Prova de Fogo Financeira Completa e Justa)
        post_decisions = []
        in_trade = False
        entry_price = 0.0
        entry_real = 0.0
        trade_size = 0.0
        units = 0.0
        audit_bank = 100.0
        
        start_idx = 20
        completed_trades_post = []
        trade_start = None
        
        for idx in range(start_idx, len(st.session_state.game_prices)):
            p_c = st.session_state.game_prices[idx]
            ma_f_c = df_post.at[idx, 'MA_Fast']
            ma_s_c = df_post.at[idx, 'MA_Slow']
            ma_f_p = df_post.at[idx-1, 'MA_Fast'] if idx > 0 else ma_f_c
            ma_200 = df_post.at[idx, 'MA_200']
            std_val = df_post.at[idx, 'Std']
            rsi_val = df_post.at[idx, 'RSI']
            
            s1_trend = 1.0 if (p_c > ma_f_c > ma_s_c) else -1.0
            s2_slope = 1.0 if (ma_f_c > ma_f_p) else -1.0
            s3_vol = -1.0 if (std_val > 6.0) else 1.0
            s4_floor = -1.0 if ((p_c - ma_200)/ma_200 > 0.09) else 1.0
            s5_rsi = 1.0 if (rsi_val < 35) else (-1.0 if rsi_val > 65 else 0.0)
            
            if in_trade:
                pnl_pct_ind = (p_c - entry_real) / entry_real * 100
                if pnl_pct_ind < -champ["stop_loss_pct"]:
                    # Stop Loss disparado instantaneamente (Preço piorado pelo slippage)
                    real_exit = p_c * (1 - slippage_pct / 100.0)
                    gross_val = real_exit * units
                    en_fee = trade_size * (fee_pct / 100.0)
                    ex_fee = gross_val * (fee_pct / 100.0)
                    net_pnl = gross_val - trade_size - (en_fee + ex_fee)
                    
                    audit_bank += net_pnl
                    if audit_bank < 10.0:
                        audit_bank = 0.0
                        
                    completed_trades_post.append({
                        "start": trade_start,
                        "end": idx,
                        "entry": entry_price,
                        "exit": p_c,
                        "entry_real": entry_real,
                        "exit_real": real_exit,
                        "trade_size": trade_size,
                        "pnl_raw_pct": (real_exit - entry_real) / entry_real * 100,
                        "net_pnl_eur": net_pnl,
                        "was_stopped": True,
                        "bank_after": audit_bank
                    })
                    in_trade = False
                    post_decisions.append("sair")
                    continue
            
            score = (
                champ["w_trend"] * s1_trend +
                champ["w_slope"] * s2_slope +
                champ["w_vol"] * s3_vol +
                champ["w_floor"] * s4_floor +
                champ["w_rsi"] * s5_rsi
            )
            
            w_dec = "entrar" if (score > champ["threshold"]) else "sair"
            
            if w_dec == "entrar" and not in_trade and audit_bank >= 10.0:
                in_trade = True
                trade_size = audit_bank * 0.95
                entry_price = p_c
                entry_real = entry_price * (1 + slippage_pct / 100.0)
                units = trade_size / entry_real
                trade_start = idx
                post_decisions.append("entrar")
            elif w_dec == "sair" and in_trade:
                # Fechar posição (Preço piorado pelo slippage)
                real_exit = p_c * (1 - slippage_pct / 100.0)
                gross_val = real_exit * units
                en_fee = trade_size * (fee_pct / 100.0)
                ex_fee = gross_val * (fee_pct / 100.0)
                net_pnl = gross_val - trade_size - (en_fee + ex_fee)
                
                audit_bank += net_pnl
                if audit_bank < 10.0:
                    audit_bank = 0.0
                    
                completed_trades_post.append({
                    "start": trade_start,
                    "end": idx,
                    "entry": entry_price,
                    "exit": p_c,
                    "entry_real": entry_real,
                    "exit_real": real_exit,
                    "trade_size": trade_size,
                    "pnl_raw_pct": (real_exit - entry_real) / entry_real * 100,
                    "net_pnl_eur": net_pnl,
                    "was_stopped": False,
                    "bank_after": audit_bank
                })
                in_trade = False
                post_decisions.append("sair")
            else:
                post_decisions.append("manter" if in_trade else "esperar")
                
        # Fechar trade pendente na última vela
        if in_trade:
            idx = len(st.session_state.game_prices) - 1
            p_c = st.session_state.game_prices[idx]
            real_exit = p_c * (1 - slippage_pct / 100.0)
            gross_val = real_exit * units
            en_fee = trade_size * (fee_pct / 100.0)
            ex_fee = gross_val * (fee_pct / 100.0)
            net_pnl = gross_val - trade_size - (en_fee + ex_fee)
            
            audit_bank += net_pnl
            if audit_bank < 10.0:
                audit_bank = 0.0
                
            completed_trades_post.append({
                "start": trade_start,
                "end": idx,
                "entry": entry_price,
                "exit": p_c,
                "entry_real": entry_real,
                "exit_real": real_exit,
                "trade_size": trade_size,
                "pnl_raw_pct": (real_exit - entry_real) / entry_real * 100,
                "net_pnl_eur": net_pnl,
                "was_stopped": False,
                "bank_after": audit_bank
            })
            in_trade = False
            
        # Fitness líquida do Exame Cego (Impostos)
        gross_profit_exame = audit_bank - 100.0
        if gross_profit_exame > 0:
            tax_due_exame = gross_profit_exame * (tax_pct / 100.0)
            audit_net_bank = audit_bank - tax_due_exame
        else:
            tax_due_exame = 0.0
            audit_net_bank = audit_bank
            
        # Calcular estatísticas do exame cego
        total_audit_trades = len(completed_trades_post)
        winning_audit_trades = sum(1 for t in completed_trades_post if t["net_pnl_eur"] > 0)
        losing_audit_trades = total_audit_trades - winning_audit_trades
        win_rate_audit = (winning_audit_trades / total_audit_trades * 100.0) if total_audit_trades > 0 else 0.0
        
        m_start = st.session_state.game_prices[0]
        m_end = st.session_state.game_prices[-1]
        market_return_pct = ((m_end - m_start) / m_start) * 100.0
        caterpillar_return_pct = ((audit_net_bank - 100.0) / 100.0) * 100.0
        alpha_pct = caterpillar_return_pct - market_return_pct
        
        # A. Painel Explicativo Didático Premium
        st.markdown(f'''
        <div style="background-color:rgba(30, 41, 59, 0.5); padding:1.2rem; border-radius:12px; border:1px solid rgba(255,255,255,0.08); margin-bottom:1.5rem;">
            <h6 style="margin:0 0 0.5rem 0; color:#e2e8f0; font-size:1.05rem;">🎓 O mistério desvendado: Como interpretar estes dados?</h6>
            <p style="margin:0; font-size:0.9rem; color:#94a3b8; line-height:1.5;">
                O valor de <b>{round(champ["net_bank"], 2):,.2f} EUR</b> que vê no histórico acima representa o capital líquido acumulado pela lagarta ao longo de <b>todo o treino de {st.session_state.game_training_history[-1]['Velas'] if len(st.session_state.game_training_history) > 0 else 5000} velas</b>. Durante esse longo treino, ela surfou dezenas de ciclos de alta e acumulou esse lucro extraordinário.<br><br>
                Em contraste, o gráfico e painel abaixo representam um <b>Exame Cego de {len(st.session_state.game_prices)} velas (Terreno Novo)</b> com capitais resetados (começando com <b>1.000,00 EUR</b>). Este exame serve para auditar se ela reage de forma inteligente a mercados que nunca viu!
            </p>
        </div>
        ''', unsafe_allow_html=True)
        
        # B. Métricas Financeiras Consolidadas do Exame Cego (Prova de Fogo)
        st.markdown(f"<span style='font-size:0.95rem; font-weight:700; color:#38bdf8;'>📊 Desempenho Financeiro no Exame Cego ({len(st.session_state.game_prices)} Velas Completas)</span>", unsafe_allow_html=True)
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        
        # Calcular banca final equivalente do mercado Buy & Hold baseado em 100 EUR
        market_final_capital = 100.0 * (m_end / m_start)
        
        with col_m1:
            st.metric(
                label="Banca Final Líquida (Exame)",
                value=f"{audit_net_bank:,.2f} EUR",
                delta=f"{audit_net_bank - 100.0:+.2f} EUR ({caterpillar_return_pct:+.2f}%)"
            )
            
        with col_m2:
            st.metric(
                label="Banca Mercado (Buy & Hold)",
                value=f"{market_final_capital:,.2f} EUR",
                delta=f"{market_return_pct:+.2f}%",
                delta_color="normal"
            )
            
        with col_m3:
            st.metric(
                label="Métricas de Operações",
                value=f"{total_audit_trades} Trades",
                delta=f"{win_rate_audit:.1f}% Win Rate",
                delta_color="normal" if win_rate_audit >= 50 else "off"
            )
            
        with col_m4:
            st.metric(
                label="Alpha vs Mercado (Diferencial)",
                value=f"{alpha_pct:+.2f}%",
                delta=f"{alpha_pct:+.2f}% contra o Mercado",
                delta_color="normal"
            )
            
        # Explicação de resiliência de Alpha
        if alpha_pct > 0:
            if caterpillar_return_pct < 0:
                st.info(f"💡 **Vitória Estrondosa da Sobrevivência:** Embora a lagarta tenha tido um saldo ligeiramente negativo ({caterpillar_return_pct:+.2f}%) neste mercado em queda livre, ela **bateu o mercado por {alpha_pct:.2f}%**! Em vez de perder os {abs(market_return_pct):.2f}% do mercado passivo, ela cortou as perdas rápido e protegeu a sua banca!")
            else:
                st.success(f"🎉 **Super Performance Real:** A lagarta não só bateu o mercado por {alpha_pct:.2f}%, como conseguiu arrancar lucros reais ({caterpillar_return_pct:+.2f}%) num terreno completamente cego!")
        else:
            st.warning("⚠️ **Alinhamento do DNA:** A lagarta não conseguiu bater o buy and hold passivo neste exame rápido. Recomenda-se treinar por mais gerações (Epochs) em modo dinâmico para melhorar a robustez do DNA.")

        # C. Gráficos de Auditoria Visual & Cérebro
        st.markdown("<br>", unsafe_allow_html=True)
        col_post_chart, col_brain_radar = st.columns([1.6, 1.0])
        
        with col_post_chart:
            # Mostrar visualmente as últimas 150 velas no gráfico Plotly para manter interatividade rápida e fluida
            show_window = min(150, len(st.session_state.game_prices))
            prices_subset = st.session_state.game_prices[-show_window:]
            xs_post = [f"V{k+1}" for k in range(len(st.session_state.game_prices) - show_window, len(st.session_state.game_prices))]
            
            st.markdown(f"<span style='font-size:0.9rem; font-weight:600;'>Gráfico de Auditoria (Últimas {show_window} Velas do Exame de {len(st.session_state.game_prices)} Velas)</span>", unsafe_allow_html=True)
            
            fig_post = go.Figure()
            
            # Preço cinzento geral
            # Gerar OHLC pseudo-realista se for terreno sintético (se não houver open, criamos)
            if 'open_post' not in locals():
                import numpy as np
                open_post = prices_subset - np.random.normal(0, 0.5, len(prices_subset))
                high_post = np.maximum(open_post, prices_subset) + np.abs(np.random.normal(0, 0.5, len(prices_subset)))
                low_post = np.minimum(open_post, prices_subset) - np.abs(np.random.normal(0, 0.5, len(prices_subset)))
            
            fig_post.add_trace(go.Candlestick(
                x=xs_post,
                open=open_post,
                high=high_post,
                low=low_post,
                close=prices_subset,
                name='Velas',
                increasing_line_color='#22c55e',
                decreasing_line_color='#ef4444'
            ))
            fig_post.update_layout(xaxis_rangeslider_visible=False)
            
            # Pintar apenas os trades decididos pelo cérebro campeão que intersectam a janela visível
            start_visible_idx = len(st.session_state.game_prices) - show_window
            for tr in completed_trades_post:
                t_start = tr["start"]
                t_end = tr["end"]
                
                if t_end >= start_visible_idx:
                    v_start = max(0, t_start - start_visible_idx)
                    v_end = t_end - start_visible_idx
                    t_color = '#22c55e' if tr["net_pnl_eur"] >= 0 else '#ef4444'
                    
                    fig_post.add_trace(go.Scatter(
                        x=xs_post[v_start:v_end+1],
                        y=prices_subset[v_start:v_end+1],
                        mode='lines+markers',
                        name='Lagarta Ativa (Trade)',
                        line=dict(color=t_color, width=4),
                        marker=dict(size=5, color=t_color),
                        showlegend=False
                    ))
                    
                    # Triângulos de entrada e saída se caírem dentro da janela
                    if t_start >= start_visible_idx:
                        fig_post.add_trace(go.Scatter(
                            x=[xs_post[v_start]], y=[tr["entry"]], mode='markers',
                            marker=dict(symbol='triangle-up', size=11, color='#22c55e'), showlegend=False
                        ))
                    fig_post.add_trace(go.Scatter(
                        x=[xs_post[v_end]], y=[tr["exit"]], mode='markers',
                        marker=dict(symbol='triangle-down', size=11, color='#ef4444'), showlegend=False
                    ))
                
            fig_post.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(title="Velas Finais", showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
                yaxis=dict(title="Valor (EUR)", showgrid=True, gridcolor='rgba(255,255,255,0.03)')
            )
            st.plotly_chart(fig_post, use_container_width=True)
            st.info("🟢 **Rasto Verde:** Posição em Lucro Líquido | 🔴 **Rasto Vermelho:** Posição em Prejuízo Líquido | **Preço Cinzento:** Lagarta de fora (Protegida).")
            
        with col_brain_radar:
            st.markdown("<span style='font-size:0.9rem; font-weight:600;'>🧠 Cérebro Sintonizado do Campeão</span>", unsafe_allow_html=True)
            
            genes_d = {
                "Sensor/Gene": ["Trend (S1)", "Slope (S2)", "Volat. (S3)", "Chão (S4)", "RSI (S5)", "Stop Loss (SL)"],
                "Sensibilidade": [champ["w_trend"], champ["w_slope"], champ["w_vol"], champ["w_floor"], champ["w_rsi"], champ["w_stop"]]
            }
            df_g_v = pd.DataFrame(genes_d)
            
            fig_g_b = go.Figure()
            cols = ['#22c55e' if w > 0 else '#ef4444' for w in df_g_v["Sensibilidade"]]
            
            fig_g_b.add_trace(go.Bar(
                x=df_g_v["Sensor/Gene"],
                y=df_g_v["Sensibilidade"],
                marker_color=cols
            ))
            
            fig_g_b.update_layout(
                height=200,
                margin=dict(l=10, r=10, t=10, b=10),
                yaxis=dict(title="Sensibilidade", range=[-1.1, 1.1])
            )
            st.plotly_chart(fig_g_b, use_container_width=True)
            
            st.write(f"🛑 **Stop Loss Aprendido:** `{champ['stop_loss_pct']:.2f}%`")
            st.write(f"🎯 **Limiar de Boca Aberta:** `{champ['threshold']:.2f}`")
            
            # Ficha Técnica de DNA Copiável (JSON Interativo)
            st.markdown("<span style='font-size:0.9rem; font-weight:600;'>🧬 Ficha Técnica do DNA (Copiável)</span>", unsafe_allow_html=True)
            dna_summary = {
                "w_trend": round(champ["w_trend"], 4),
                "w_slope": round(champ["w_slope"], 4),
                "w_vol": round(champ["w_vol"], 4),
                "w_floor": round(champ["w_floor"], 4),
                "w_rsi": round(champ["w_rsi"], 4),
                "threshold": round(champ["threshold"], 4),
                "stop_loss_pct": round(champ["stop_loss_pct"], 2)
            }
            st.json(dna_summary)
            
            # Botão de Sinergia Real
            if st.button("🔌 Ativar esta Especialista no Robô Principal", width='stretch', type="primary"):
                # Ativa diretamente a estratégia da Lagarta pelo seu nome
                st.session_state.strategy_type_val = f"🎓 {st.session_state.game_specialist_name}"
                st.session_state.stop_loss_pct_val = float(round(champ["stop_loss_pct"], 1))
                st.session_state.sl_active_val = True
                st.success(f"🔌 Cérebro IA da '{st.session_state.game_specialist_name}' Injetado no Robô Principal! Verifique a aba 1.")
                st.rerun()

        # D. Tabela Detalhada de Trades do Exame Cego (O Dossiê de Provas)
        with st.expander("🔍 Dossiê de Provas: Dados Detalhados de cada Trade no Exame Cego"):
            if len(completed_trades_post) == 0:
                st.info(f"A lagarta campeã optou por segurança absoluta e não efetuou nenhuma operação nas {len(st.session_state.game_prices)} velas deste exame.")
            else:
                trades_df_data = []
                for idx_t, tr in enumerate(completed_trades_post):
                    status_emoji = "🟢 Lucro" if tr["net_pnl_eur"] > 0 else "🔴 Prejuízo"
                    motivo = "🛑 Stop Loss Ativado" if tr["was_stopped"] else "🧠 Sinal do Cérebro"
                    
                    trades_df_data.append({
                        "Operação": f"Trade #{idx_t + 1}",
                        "Capital Investido": f"{tr['trade_size']:,.2f} EUR",
                        "Entrada (Vela)": f"Vela {tr['start'] + 1}",
                        "Preço Entrada (Mkt)": f"{tr['entry']:.2f} EUR",
                        "Entrada Real (Slippage)": f"{tr['entry_real']:.2f} EUR",
                        "Saída (Vela)": f"Vela {tr['end'] + 1}",
                        "Preço Saída (Mkt)": f"{tr['exit']:.2f} EUR",
                        "Saída Real (Slippage)": f"{tr['exit_real']:.2f} EUR",
                        "PnL Bruto (%)": f"{tr['pnl_raw_pct']:+.2f}%",
                        "PnL Líquido (EUR)": f"{tr['net_pnl_eur']:+.2f} EUR",
                        "Resultado": status_emoji,
                        "Motivo de Saída": motivo,
                        "Banca Restante": f"{tr['bank_after']:.2f} EUR"
                    })
                
                df_trades_audit = pd.DataFrame(trades_df_data)
                st.dataframe(
                    df_trades_audit,
                    width='stretch',
                    column_config={
                        "Operação": st.column_config.TextColumn("Operação", width=60),
                        "Capital Investido": st.column_config.TextColumn("Capital Investido", width=105),
                        "Entrada (Vela)": st.column_config.TextColumn("Entrada", width=80),
                        "Preço Entrada (Mkt)": st.column_config.TextColumn("Mkt Entrada", width=80),
                        "Entrada Real (Slippage)": st.column_config.TextColumn("Real Entrada", width=95),
                        "Saída (Vela)": st.column_config.TextColumn("Saída", width=80),
                        "Preço Saída (Mkt)": st.column_config.TextColumn("Mkt Saída", width=80),
                        "Saída Real (Slippage)": st.column_config.TextColumn("Real Saída", width=95),
                        "PnL Bruto (%)": st.column_config.TextColumn("PnL (%)", width=70),
                        "PnL Líquido (EUR)": st.column_config.TextColumn("PnL Líquido", width=85),
                        "Resultado": st.column_config.TextColumn("Resultado", width=75),
                        "Motivo de Saída": st.column_config.TextColumn("Motivo Fim", width=120),
                        "Banca Restante": st.column_config.TextColumn("Banca Pós-Trade", width=90)
                    },
                    hide_index=True
                )

    st.markdown('</div>', unsafe_allow_html=True)


with tab_math_lab:
    import tab_math_lab
    tab_math_lab.render()
# =========================================================================
# SEPARADOR 5: JOGO DO TRADER QUANTITATIVO (ARENA BLIND TRADER)
# =========================================================================
with tab_trader_game:


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
                df.bfill(inplace=True)
                st.session_state.tg_data = df

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
                        
                        # --- CONDIÇÕES DE COMPRA (LONG) ---
                        opp_rules = reg_rules.get("buy_rules", {})
                        cond_long = {}
                        if opp_rules.get("stretching", {}).get("stable", False):
                            min_l = opp_rules["stretching"].get("min_limit")
                            max_l = opp_rules["stretching"].get("max_limit")
                            if min_l is not None and max_l is not None:
                                cond_long["Stretching Fundo"] = (min_l <= stretch <= max_l)
                        if opp_rules.get("mola", {}).get("stable", False):
                            max_l = opp_rules["mola"].get("max_limit")
                            if max_l is not None:
                                cond_long["Coesão Mola"] = (mola_pct <= max_l)
                        if opp_rules.get("disp", {}).get("stable", False):
                            max_l = opp_rules["disp"].get("max_limit")
                            if max_l is not None:
                                cond_long["Dispersão Mola"] = (disp_pct <= max_l)
                        if opp_rules.get("acceleration", {}).get("stable", False):
                            mean_acc = opp_rules["acceleration"].get("mean", 0.0)
                            cond_long["Aceleração Reversão"] = (acc > 0) if mean_acc > 0 else (acc < 0)
                        if opp_rules.get("infil", {}).get("active", False):
                            cond_long["Infiltração Bull"] = bool(df['infil_bull'].iloc[step])
                        if opp_rules.get("reteste", {}).get("active", False):
                            cond_long["Reteste Fibo"] = bool(df['reteste_val'].iloc[step])
                        cond_long["Cruzamento Rápido (5 > 13)"] = bool(df['sma_5'].iloc[step] > df['sma_13'].iloc[step])
                        
                        # --- CONDIÇÕES DE VENDA (SHORT) ---
                        thr_rules = reg_rules.get("sell_rules", {})
                        cond_short = {}
                        if thr_rules.get("stretching", {}).get("stable", False):
                            min_l = thr_rules["stretching"].get("min_limit")
                            max_l = thr_rules["stretching"].get("max_limit")
                            if min_l is not None and max_l is not None:
                                cond_short["Stretching Topo"] = (min_l <= stretch <= max_l)
                        if thr_rules.get("mola", {}).get("stable", False):
                            mean_m = thr_rules["mola"].get("mean", 0.0)
                            cond_short["Coesão Mola"] = (mola_pct >= mean_m)
                        if thr_rules.get("disp", {}).get("stable", False):
                            limit_d = thr_rules["disp"].get("limit")
                            if limit_d is not None:
                                cond_short["Parede Sobrestiramento"] = (disp_pct >= limit_d) if limit_d >= 0 else (disp_pct >= limit_d)
                        if thr_rules.get("acceleration", {}).get("stable", False):
                            mean_acc = thr_rules["acceleration"].get("mean", 0.0)
                            cond_short["Aceleração Reversão"] = (acc > 0) if mean_acc > 0 else (acc < 0)
                        cond_short["Cruzamento Rápido (5 < 13)"] = bool(df['sma_5'].iloc[step] < df['sma_13'].iloc[step])
                        
                        long_score = sum(cond_long.values()) / len(cond_long) if cond_long else 0.0
                        short_score = sum(cond_short.values()) / len(cond_short) if cond_short else 0.0
                        
                        if long_score > short_score and long_score >= 0.60:
                            return "LONG", round(long_score * 100), cond_long
                        elif short_score > long_score and short_score >= 0.60:
                            return "SHORT", round(short_score * 100), cond_short
                        else:
                            return "HOLD", round(max(long_score, short_score) * 100), cond_long if long_score >= short_score else cond_short
                except Exception:
                    pass
                    
            # Fallback para regras padrão do jogo
            vel = df['velocity'].iloc[step]
            acc = df['acceleration'].iloc[step]
            stretch = df['stretching'].iloc[step]
            compress_thresh = st.session_state.tg_bot_compress_thresh
            vel_thresh = st.session_state.tg_bot_vel_thresh

            # Condicoes individuais
            vel_pos = vel > vel_thresh
            vel_neg = vel < -vel_thresh
            acc_pos = acc > 0
            acc_neg = acc < 0
            compressed = stretch < compress_thresh
            overextended = stretch > compress_thresh * 3.5

            cond_long  = {"Velocity +": vel_pos, "Acceleration +": acc_pos, "Compressao": compressed}
            cond_short = {"Velocity -": vel_neg, "Acceleration -": acc_neg, "Compressao": compressed}

            long_score  = sum(cond_long.values())  / len(cond_long)
            short_score = sum(cond_short.values()) / len(cond_short)

            # Penalizar sobreextensao
            if overextended:
                long_score  *= 0.4
                short_score *= 0.4

            if long_score > short_score and long_score >= 0.60:
                confidence = round(long_score * 100)
                return "LONG", confidence, cond_long
            elif short_score > long_score and short_score >= 0.60:
                confidence = round(short_score * 100)
                return "SHORT", confidence, cond_short
            else:
                confidence = round(max(long_score, short_score) * 100)
                return "HOLD", confidence, cond_long if long_score >= short_score else cond_short

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

        # CSS dos botoes casino
        st.markdown("""
        <style>
        div[data-testid="column"]:has(div.game-control-anchor) {
            background: rgba(255,255,255,0.45) !important;
            backdrop-filter: blur(16px) !important;
            border-radius: 16px !important;
            border: 1px solid rgba(255,255,255,0.2) !important;
            padding: 16px !important;
            box-shadow: 0 8px 32px 0 rgba(31,38,135,0.08) !important;
            border-left: 5px solid #7c3aed !important;
        }
        @keyframes pulse-green {
            0% { box-shadow: 0 0 15px rgba(34,197,94,0.6), inset 0 0 5px rgba(255,255,255,0.4); }
            100% { box-shadow: 0 0 35px rgba(34,197,94,1.0), inset 0 0 10px rgba(255,255,255,0.8); }
        }
        @keyframes pulse-red {
            0% { box-shadow: 0 0 15px rgba(239,68,68,0.6), inset 0 0 5px rgba(255,255,255,0.4); }
            100% { box-shadow: 0 0 35px rgba(239,68,68,1.0), inset 0 0 10px rgba(255,255,255,0.8); }
        }
        .review-banner {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            border-radius: 14px;
            padding: 18px 24px;
            margin-bottom: 14px;
            border: 1px solid rgba(99,102,241,0.4);
            box-shadow: 0 0 40px rgba(99,102,241,0.15);
        }
        .review-stat {
            text-align: center;
            padding: 8px 12px;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.08);
        }
        </style>
        """, unsafe_allow_html=True)

        # --- COCKPIT DE CONFIGURACOES ---
        with st.expander("Configuracao: Periodos das Medias & Risco", expanded=not st.session_state.tg_active and not st.session_state.tg_game_finished):
            col_c1, col_c2, col_c3 = st.columns([0.8, 1.8, 1.0])
            with col_c1:
                st.markdown("##### Jogador")
                name_input = st.text_input("Nome:", value=st.session_state.tg_trader_name, key="tg_name_wdg")
                if name_input: st.session_state.tg_trader_name = name_input
                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
                if st.button("Iniciar / Novo Jogo", type="primary", use_container_width=True):
                    start_new_game()
                    st.rerun()
            with col_c2:
                st.markdown("##### Periodos das Medias Moveis")
                s1,s2,s3,s4,s5 = st.columns(5)
                with s1: new_p2 = st.number_input("Rapida", min_value=2, max_value=20, value=st.session_state.tg_p2, step=1, key="tg_in_p2")
                with s2: new_p3 = st.number_input("Confirm.", min_value=5, max_value=40, value=st.session_state.tg_p3, step=1, key="tg_in_p3")
                with s3: new_p4 = st.number_input("Media", min_value=10, max_value=80, value=st.session_state.tg_p4, step=1, key="tg_in_p4")
                with s4: new_p5 = st.number_input("Longa", min_value=20, max_value=150, value=st.session_state.tg_p5, step=1, key="tg_in_p5")
                with s5: new_p6 = st.number_input("Mestra", min_value=50, max_value=300, value=st.session_state.tg_p6, step=1, key="tg_in_p6")
                if (new_p2!=st.session_state.tg_p2 or new_p3!=st.session_state.tg_p3 or
                    new_p4!=st.session_state.tg_p4 or new_p5!=st.session_state.tg_p5 or new_p6!=st.session_state.tg_p6):
                    st.session_state.tg_p2,st.session_state.tg_p3 = new_p2,new_p3
                    st.session_state.tg_p4,st.session_state.tg_p5 = new_p4,new_p5
                    st.session_state.tg_p6 = new_p6
                    recalculate_indicators()
                    st.toast("Medias recalculadas!")
                    st.rerun()
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
                
                st.markdown("##### Risco")
                st.session_state.tg_sl_active = st.checkbox("Stop Loss (SL)", value=st.session_state.tg_sl_active)
                if st.session_state.tg_sl_active:
                    st.session_state.tg_sl_pct = st.slider("SL (%)", 0.5, 5.0, value=st.session_state.tg_sl_pct, step=0.1)
                st.session_state.tg_tp_active = st.checkbox("Take Profit (TP)", value=st.session_state.tg_tp_active)
                if st.session_state.tg_tp_active:
                    st.session_state.tg_tp_pct = st.slider("TP (%)", 1.0, 10.0, value=st.session_state.tg_tp_pct, step=0.1)
                st.session_state.tg_ts_active = st.checkbox("Trailing Stop (TS)", value=st.session_state.tg_ts_active)
                if st.session_state.tg_ts_active:
                    st.session_state.tg_ts_pct = st.slider("TS (%)", 0.5, 4.0, value=st.session_state.tg_ts_pct, step=0.1)

        # =========================================================================
        # MODO REVISAO: gráfico completo apos o fim do jogo
        # =========================================================================
        if st.session_state.tg_game_finished and st.session_state.tg_data is not None:
            df = st.session_state.tg_data
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
                        <div style="color:#e2e8f0; font-size:22px; font-weight:900; font-family:monospace;">{len(st.session_state.tg_trades)}</div>
                    </div>
                    <div class="review-stat" style="flex:1;">
                        <div style="color:#64748b; font-size:11px; text-transform:uppercase;">Win Rate</div>
                        <div style="color:#e2e8f0; font-size:22px; font-weight:900; font-family:monospace;">
                            {(sum(1 for t in st.session_state.tg_trades if t.get('pnl_pct', 0) > 0) / max(len(st.session_state.tg_trades), 1) * 100):.0f}%
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
                st.plotly_chart(fig_review, use_container_width=True)

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
            if st.session_state.tg_position == "LONG":
                pos_str = f"LONG ({st.session_state.tg_entry_price:.2f})"
            elif st.session_state.tg_position == "SHORT":
                pos_str = f"SHORT ({st.session_state.tg_entry_price:.2f})"

            ret_pct = st.session_state.tg_capital - 100.0
            ret_color = "#10B981" if ret_pct >= 0 else "#EF4444"
            st.markdown(f"""
            <div style="padding:10px 20px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;
                 border-radius:10px; background:rgba(255,255,255,0.6); backdrop-filter:blur(12px);
                 box-shadow:0 4px 15px rgba(0,0,0,0.05); border:1px solid rgba(255,255,255,0.3);">
                <div>Banca: <b style="color:#10B981; font-family:monospace;">{st.session_state.tg_capital:.2f} EUR</b></div>
                <div>Retorno: <b style="color:{ret_color}; font-family:monospace;">{ret_pct:+.2f}%</b></div>
                <div>Posicao: <b style="color:#00B0FF;">{pos_str}</b></div>
                <div>Progresso: <b style="font-family:monospace;">{progress_candles} / 100</b></div>
            </div>
            """, unsafe_allow_html=True)

            col_left, col_right = st.columns([7, 3])

            with col_left:
                start_idx = max(50, current_step - 49)
                sub_df = df.iloc[start_idx:current_step+1]
                # Checkboxes cinzentas redundantes removidas. Controlo feito diretamente por clique na legenda do Plotly!

                fig = _build_chart(
                    sub_df, df,
                    title_str=f"Arena Real — Batimento {progress_candles} / 100 Velas (ultimas {len(sub_df)})"
                )
                st.plotly_chart(fig, use_container_width=True)

            with col_right:
                st.markdown('<div class="game-control-anchor"></div>', unsafe_allow_html=True)

                # Controlo de fluxo
                st.markdown("##### Controlo de Fluxo")
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    if st.button("Avancar", width='stretch', key="tg_step_btn"):
                        st.session_state.tg_step += 1
                        st.rerun()
                with col_t2:
                    btn_label = "Pausar" if st.session_state.tg_running else "Auto"
                    if st.button(btn_label, width='stretch', key="tg_loop_btn"):
                        st.session_state.tg_running = not st.session_state.tg_running
                        st.rerun()

                tg_speed_select = st.selectbox(
                    "Velocidade:", ["Lento (1.0s)", "Medio (0.3s)", "Rapido (0.05s)"],
                    index=1, label_visibility="collapsed", key="tg_speed_widget"
                )
                tg_delay = 1.0 if "Lento" in tg_speed_select else (0.3 if "Medio" in tg_speed_select else 0.05)

                st.markdown("<hr style='margin:8px 0; border:0; border-top:1px solid rgba(0,0,0,0.08);'>", unsafe_allow_html=True)

                # --- PAINEL DO BOT ---
                st.markdown("##### 🤖 Co-piloto & Bot")
                bot_mode_choice = st.radio(
                    "Modo:", ["Manual", "Co-piloto", "Bot Autónomo"],
                    horizontal=True, index=["Manual","Co-piloto","Bot Autónomo"].index(st.session_state.tg_bot_mode),
                    key="tg_bot_mode_radio", label_visibility="collapsed"
                )
                if bot_mode_choice != st.session_state.tg_bot_mode:
                    st.session_state.tg_bot_mode = bot_mode_choice

                # Compute signal always (needed for co-pilot display and bot mode)
                _bot_signal, _bot_conf, _bot_conds = compute_bot_signal(df, current_step)
                _sig_color = {"LONG": "#10B981", "SHORT": "#EF4444", "HOLD": "#94a3b8"}[_bot_signal]
                _sig_emoji = {"LONG": "🟢", "SHORT": "🔴", "HOLD": "⚪"}[_bot_signal]

                # Signal display (always visible in co-pilot and autonomous)
                if st.session_state.tg_bot_mode != "Manual":
                    # Mapeamento do nome do DNA e regime detetado
                    dna_active = st.session_state.get("tg_strategy_type", "Default") == "Cérebro de Consenso (Lab)"
                    regime_label = ""
                    if dna_active:
                        regime_name = df['regime'].iloc[current_step]
                        regime_emoji = {"BULL": "🟢 BULL", "BEAR": "🔴 BEAR", "LATERAL": "🟡 LATERAL", "CAOTICO": "⚡ CAÓTICO"}.get(regime_name, "🟡 LATERAL")
                        regime_label = f'<div style="font-size:11px; margin-bottom:4px; font-weight:bold; color:#7c3aed;">🧠 DNA ATIVO | REGIME DETETADO: {regime_emoji}</div>'
                    
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.45); border-radius:10px; padding:10px 14px; margin:6px 0;
                         border-left:4px solid {_sig_color}; box-shadow:0 4px 15px rgba(0,0,0,0.02); border:1px solid rgba(255,255,255,0.25);">
                        {regime_label}
                        <div style="font-size:18px; font-weight:900; color:{_sig_color};">
                            {_sig_emoji} {_bot_signal} &nbsp;<span style="font-size:13px; color:#64748b;">confiança {_bot_conf}%</span>
                        </div>
                        <div style="margin-top:6px; font-size:12px; line-height:1.8;">
                            {"".join(f"<span style=\'color:{"#10B981" if v else "#EF4444"};\'>{"✅" if v else "❌"} {k}</span><br>" for k, v in _bot_conds.items())}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # BOT AUTONOMO: executa posicoes automaticamente
                    if st.session_state.tg_bot_mode == "Bot Autónomo":
                        _pos = st.session_state.tg_position
                        # Entrar em posicao se HOLD e sinal claro
                        if _pos == "NONE" and _bot_signal == "LONG" and _bot_conf >= 67:
                            st.session_state.tg_position = "LONG"
                            st.session_state.tg_entry_price = price_now
                            st.session_state.tg_entry_step = current_step
                            st.session_state.tg_highest_price = price_now
                            st.toast(f"🤖 Bot entrou LONG a {price_now:.2f}")
                        elif _pos == "NONE" and _bot_signal == "SHORT" and _bot_conf >= 67:
                            st.session_state.tg_position = "SHORT"
                            st.session_state.tg_entry_price = price_now
                            st.session_state.tg_entry_step = current_step
                            st.session_state.tg_lowest_price = price_now
                            st.toast(f"🤖 Bot entrou SHORT a {price_now:.2f}")
                        # Sair se sinal invertido ou HOLD com posicao aberta
                        elif _pos == "LONG" and (_bot_signal == "SHORT" or (_bot_signal == "HOLD" and _bot_conf >= 67)):
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
                            st.toast(f"🤖 Bot saiu LONG a {price_now:.2f} ({pnl_pct:+.2f}%)")
                        elif _pos == "SHORT" and (_bot_signal == "LONG" or (_bot_signal == "HOLD" and _bot_conf >= 67)):
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
                            st.toast(f"🤖 Bot saiu SHORT a {price_now:.2f} ({pnl_pct:+.2f}%)")

                st.markdown("<hr style='margin:8px 0; border:0; border-top:1px solid rgba(0,0,0,0.08);'>", unsafe_allow_html=True)

                # (second hr removed - now merged above)
                _dummy_hr = True  # placeholder

                # Visibilidade das linhas

                # Operar posicoes
                st.markdown("##### Operar Posicoes")
                if st.session_state.tg_position == "LONG":
                    long_pnl = (price_now - st.session_state.tg_entry_price)/st.session_state.tg_entry_price*100
                    if st.button(f"LONG ATIVO [ON] | {long_pnl:+.2f}%", width='stretch', key="tg_btn_long_act"):
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
                elif st.session_state.tg_position == "NONE":
                    if st.button("ENTRAR LONG [OFF]", width='stretch', key="tg_btn_long_inact"):
                        st.session_state.tg_position = "LONG"
                        st.session_state.tg_entry_price = price_now
                        st.session_state.tg_entry_step = current_step
                        st.session_state.tg_highest_price = price_now
                        st.toast(f"LONG ativado a {price_now:.2f}")
                        st.rerun()
                else:
                    st.button("LONG BLOQUEADO", disabled=True, width='stretch', key="tg_btn_long_blk")

                st.markdown('<div style="height:5px;"></div>', unsafe_allow_html=True)

                if st.session_state.tg_position == "SHORT":
                    short_pnl = (st.session_state.tg_entry_price - price_now)/st.session_state.tg_entry_price*100
                    if st.button(f"SHORT ATIVO [ON] | {short_pnl:+.2f}%", width='stretch', key="tg_btn_short_act"):
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
                elif st.session_state.tg_position == "NONE":
                    if st.button("ENTRAR SHORT [OFF]", width='stretch', key="tg_btn_short_inact"):
                        st.session_state.tg_position = "SHORT"
                        st.session_state.tg_entry_price = price_now
                        st.session_state.tg_entry_step = current_step
                        st.session_state.tg_lowest_price = price_now
                        st.toast(f"SHORT ativado a {price_now:.2f}")
                        st.rerun()
                else:
                    st.button("SHORT BLOQUEADO", disabled=True, width='stretch', key="tg_btn_short_blk")

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
                    }), use_container_width=True)
                else:
                    st.info("Nenhuma ordem fechada.")
            with col_h2:
                st.markdown("#### Top 5 Recordes")
                scores = load_highscores()
                if scores:
                    st.dataframe(pd.DataFrame(scores).rename(columns={
                        "name":"Nome","capital":"Banca Final","return":"Lucro",
                        "trades":"Trades","config":"Config","date":"Data"
                    }), use_container_width=True)
                else:
                    st.info("Ainda nao ha recordes!")
