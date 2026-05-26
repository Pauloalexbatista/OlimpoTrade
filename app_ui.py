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

# 4. Cabeçalho da Aplicação
st.markdown('<div class="main-title">OLIMPOTRADE</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Algorithmic Trading & Analytics Lab</div>', unsafe_allow_html=True)

# Status de Conexão (Paper trading ativo)
col_status1, col_status2 = st.columns([1, 6])
with col_status1:
    st.markdown('<span class="status-badge status-active">● SIMULADOR ATIVO</span>', unsafe_allow_html=True)

# 5. Painel de Ajuda Rápida no Topo da Sidebar
with st.sidebar.expander("📚 Guia e Dicionário de Parâmetros"):
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

# 6. Configurações da Strategy e Risk Management no Menu Lateral
st.sidebar.markdown("### ⚙️ Configurações Gerais")
symbol = st.sidebar.selectbox(
    "Par de Trading",
    ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"],
    index=0,
    help="Par de moedas a transacionar. Todos os cálculos de banca e lucro são exibidos na sua moeda local (EUR)."
)
timeframe = st.sidebar.selectbox(
    "Timeframe",
    ["15m", "1h", "4h", "1d"],
    index=1,
    help="Escala de tempo de cada candle (vela). Timeframes maiores (1h, 1d) filtram ruído e mostram tendências mais fortes."
)
limit_candles = st.sidebar.slider(
    "Quantidade de Candles",
    100, 1000, 500,
    step=50,
    help="Quantidade de velas a obter do histórico. Dica: Para simular 1 ano instantaneamente, use timeframe '1d' e 365 candles."
)

st.sidebar.markdown("### ⚙️ Configuração da Estratégia")

strategy_type = st.sidebar.selectbox(
    "Estratégia Ativa",
    ["SMA_CROSSOVER", "EMA_CROSSOVER", "MULTIPOINT_VECTOR"],
    index=2 if st.session_state.strategy_type_val == "MULTIPOINT_VECTOR" else (1 if st.session_state.strategy_type_val == "EMA_CROSSOVER" else 0),
    format_func=lambda x: "Média Simples (SMA Crossover)" if x == "SMA_CROSSOVER" else ("Média Exponencial (EMA Crossover)" if x == "EMA_CROSSOVER" else "Vetor de 5 Pontos (MultiPoint)"),
    help="Escolha o algoritmo quantitativo de decisão."
)

if strategy_type in ["SMA_CROSSOVER", "EMA_CROSSOVER"]:
    short_window = st.sidebar.number_input(
        "Janela Curta (Rápida)",
        min_value=2, max_value=100,
        value=st.session_state.short_window_val,
        help="Número de candles para calcular a média móvel curta. Padrões profissionais: 9 a 20."
    )
    long_window = st.sidebar.number_input(
        "Janela Longa (Lenta)",
        min_value=5, max_value=200,
        value=st.session_state.long_window_val,
        help="Número de candles para calcular a média móvel lenta. Padrões profissionais: 21 a 50."
    )
    p2_window = 9
    p3_window = 21
    p4_window = 50
    p5_window = 200
    multipoint_mode = "AGILE"
    exhaustion_filter = True
    exhaustion_threshold = 2.5
    p5_filter_active = True
    entry_mode = "4PONTOS"
    exit_mode = "P3" 
else:
    short_window = 9
    long_window = 21
    
    operation_mode = st.sidebar.selectbox(
        "Modo Operacional da Lagarta",
        ["TREND_FOLLOWING", "MEAN_REVERSION"],
        index=0 if st.session_state.operation_mode_val == "TREND_FOLLOWING" else 1,
        format_func=lambda x: "Seguimento de Tendência (Lagarta Clássica)" if x == "TREND_FOLLOWING" else "Reversão à Média (Lagarta Reversa)",
        help="Seguimento de Tendência compra na alta e vende na queda. Reversão à Média compra nos baixos (sobrevenda) e vende nos altos (picos)!"
    )
    
    multipoint_mode = st.sidebar.selectbox(
        "Modo do Vetor de Pontos",
        ["AGILE", "CONSERVATIVE"],
        index=0 if st.session_state.multipoint_mode_val == "AGILE" else 1,
        format_func=lambda x: "Modo Ágil (4 Pontos)" if x == "AGILE" else "Modo Conservador (5 Pontos)",
        help="Modo Ágil evita o lag da Média 200 usando-a apenas como filtro de inclinação. Modo Conservador exige alinhamento dos 5 pontos."
    )
    
    entry_mode = st.sidebar.selectbox(
        "Modo de Entrada (Gatilho)",
        ["3PONTOS", "4PONTOS", "5PONTOS"],
        index=0 if st.session_state.entry_mode_val == "3PONTOS" else (1 if st.session_state.entry_mode_val == "4PONTOS" else 2),
        format_func=lambda x: "Super-Ágil (3 Pernas: P1 > P2 > P3)" if x == "3PONTOS" else ("Equilibrada (4 Pernas: P1 > P2 > P3 > P4)" if x == "4PONTOS" else "Conservadora (5 Pernas: P1 > P2 > P3 > P4 > P5)"),
        help="Escolha quantas pernas da lagarta devem alinhar para disparar a COMPRA."
    )
    
    exit_mode = st.sidebar.selectbox(
        "Modo de Saída (Suporte)",
        ["P2", "P3", "P4"],
        index=0 if st.session_state.exit_mode_val == "P2" else (1 if st.session_state.exit_mode_val == "P3" else 2),
        format_func=lambda x: "Saída Rápida (Preço < P2/Média 9)" if x == "P2" else ("Saída Intermédia (Preço < P3/Média 21)" if x == "P3" else "Saída Lenta (Preço < P4/Média 50)"),
        help="Escolha que suporte a cabeça da lagarta deve quebrar para disparar a VENDA."
    )
    
    p2_window = st.sidebar.number_input(
        "Média Muito Rápida - P2",
        min_value=2, max_value=50,
        value=st.session_state.p2_window_val,
        help="Representa o Ponto 2 (Média Rápida de curto-prazo, ex: 9)."
    )
    p3_window = st.sidebar.number_input(
        "Média Curta/Confirmadora - P3",
        min_value=5, max_value=100,
        value=st.session_state.p3_window_val,
        help="Representa o Ponto 3 (Média Curta confirmadora, ex: 21)."
    )
    p4_window = st.sidebar.number_input(
        "Média Média - P4",
        min_value=10, max_value=150,
        value=st.session_state.p4_window_val,
        help="Representa o Ponto 4 (Média de suporte dinâmico, ex: 50)."
    )
    p5_window = st.sidebar.number_input(
        "Média Longa/Mestra - P5",
        min_value=50, max_value=500,
        value=st.session_state.p5_window_val,
        help="Representa o Ponto 5 (Média Longa da tendência macro global, ex: 200)."
    )
    p5_filter_active = st.sidebar.checkbox(
        "Filtro de Inclinação P5 (Média 200) Ativo",
        value=st.session_state.p5_filter_active_val if "p5_filter_active_val" in st.session_state else True,
        help="Se ativado, bloqueia novas compras se a Média 200 estiver inclinada para baixo (macro queda)."
    )
    
    exhaustion_filter = st.sidebar.checkbox(
        "Ativar Filtro de Exaustão",
        value=st.session_state.exhaustion_filter_val,
        help="Se ativado, bloqueia novas compras caso o Preço Atual (P1) esteja demasiado longe da Média Rápida (P2)."
    )
    
    if exhaustion_filter:
        exhaustion_threshold = st.sidebar.slider(
            "Limite de Exaustão (%)",
            0.5, 10.0,
            value=st.session_state.exhaustion_threshold_val,
            step=0.1,
            help="Distância máxima percentual entre o Preço (P1) e a Média Rápida (P2) para permitir a compra."
        )
    else:
        exhaustion_threshold = 2.5

st.sidebar.markdown("### 🛡️ Gestão de Risco")
initial_capital = st.sidebar.number_input(
    "Capital Inicial (EUR)",
    min_value=100.0, max_value=100000.0,
    value=1000.0,
    step=100.0,
    help="Saldo simulado de Euros (€) com que inicia a sua conta no primeiro dia."
)
max_risk_pct = st.sidebar.slider(
    "Risco por Trade (%)",
    0.1, 5.0, 1.0,
    step=0.1,
    help="A percentagem máxima da sua banca total que aceita perder caso a operação atinja o Stop Loss. Padrão profissional: 1.0%."
)

stop_loss_pct = st.sidebar.slider(
    "Stop Loss (%)",
    0.5, 10.0,
    value=st.session_state.stop_loss_pct_val,
    step=0.1,
    help="Limite de perda automática. Se o preço cair esta percentagem abaixo da compra, o robô vende imediatamente para o proteger."
)

# Checkbox para Ativar Trailing Stop (Stop Loss Móvel)
trailing_stop_active = st.sidebar.checkbox(
    "Acompanhar Lucros (Trailing Stop)",
    value=st.session_state.trailing_stop_active_val,
    help="Se ativado, o seu Stop Loss subirá automaticamente acompanhando o preço sempre que a moeda valorizar. Isto protege o seu lucro acumulado contra quedas repentinas sem limitar a subida!"
)

# Checkbox: Ativar/Desativar Meta de Lucro (Take Profit)
tp_active = st.sidebar.checkbox(
    "Take Profit Ativo (Meta de Lucro)",
    value=st.session_state.tp_active_val,
    help="Se ativado, o robô vende quando atinge a percentagem de ganho definida no slider abaixo. Se desativado, o robô não vende por meta de lucro fixa e deixa os lucros correrem livremente até as médias se cruzarem de volta no sentido inverso (STRATEGY_SELL)."
)

if not tp_active:
    take_profit_pct = 999.0
    st.sidebar.info("ℹ️ Take Profit desativado. Lucros a correr sem limite!")
else:
    take_profit_pct = st.sidebar.slider(
        "Take Profit (%)",
        1.0, 30.0,
        value=st.session_state.take_profit_pct_val,
        step=0.5,
        help="Alvo de ganho automático. Se o preço subir esta percentagem acima da compra, o robô vende para guardar o lucro."
    )

max_daily_loss_pct = st.sidebar.slider(
    "Limite Perda Diária (%)",
    1.0, 20.0, 5.0,
    step=0.5,
    help="Se a sua conta perder esta percentagem total num único dia, o robô desliga-se automaticamente para o proteger contra quedas catastróficas."
)

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

# Carregar configurações e atualizar com a seleção da UI
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

# Botão para Executar Backtesting Principal
run_button = st.sidebar.button("⚡ Executar Simulação")

# 7. Abas Principais do Laboratório (Tabs)
tab_backtest, tab_optimizer, tab_recipes, tab_simulator, tab_scanner, tab_news = st.tabs(["📊 Simulação & Gráficos", "🔬 Otimizador de Parâmetros", "📚 Livro de Receitas", "🎮 Simulador de Mercado", "🔍 Scanner de Mercado", "📰 Notícias & Sentimento"])

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

        # Guardar no Session State
        st.session_state.backtest_results = {
            "trades": trades,
            "capital_history": capital_history,
            "metrics": metrics,
            "df_ohlcv": df_ohlcv
        }
    else:
        st.error("Erro ao obter dados históricos da Binance.")

# --- CONTEÚDO DA ABA 1: BACKTEST & GRAFICOS ---
with tab_backtest:
    if st.session_state.backtest_results is not None:
        results = st.session_state.backtest_results
        trades = results["trades"]
        capital_history = results["capital_history"]
        metrics = results["metrics"]
        df_ohlcv = results["df_ohlcv"]

        # Calcular as Médias no histórico de acordo com a estratégia ativa para exibição visual
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
            line1_name = f"P2 - Média Rápida ({p2_window})"
            line2_name = f"P3 - Média Curta ({p3_window})"
            line3_name = f"P4 - Média Média ({p4_window})"
            line4_name = f"P5 - Média Longa ({p5_window})"
            line1_color = "#0ea5e9"
            line2_color = "#f97316" 

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

        # Linha do Preço Real do Ativo - INTERATIVA (Unified Hover)
        fig_prices.add_trace(go.Scatter(
            x=df_visualization.index,
            y=df_visualization['close'],
            mode='lines',
            name=f'Preço {symbol}',
            line=dict(color='rgba(71, 85, 105, 0.25)', width=1.5),
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
                use_container_width=True
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
with tab_optimizer:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<h3>🧠 Otimizador de Parâmetros Inteligente</h3>', unsafe_allow_html=True)
    st.markdown("""
    Este painel permite-lhe descobrir **as melhores configurações históricas** para a sua estratégia de médias móveis.
    O sistema realiza uma pesquisa matemática detalhada (**Grid Search**) cruzando dezenas de combinações de médias móveis,
    valores de Stop Loss e Take Profit.

    Para o proteger contra o risco de **Overfitting** (otimização perfeita do passado que depois perde dinheiro no futuro),
    dividimos os dados em dois períodos específicos:
    1. **Período de Treino (In-Sample)**: Onde o robô pesquisa e descobre as melhores configurações.
    2. **Período de Teste (Out-of-Sample)**: Onde testamos as melhores configurações em dados 100% novos, simulando o futuro real!
    """)

    # Inputs do Otimizador
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        train_pct = st.slider(
            "Divisão de Treino / In-Sample (%)",
            min_value=50, max_value=90, value=65, step=5,
            help="Percentagem do histórico usada para procurar os melhores parâmetros. O restante é guardado para testar no futuro simulado."
        )
    with col_opt2:
        st.markdown("<br>", unsafe_allow_html=True)
        opt_button = st.button("🧠 Iniciar Pesquisa de Parâmetros Ideais")

    st.markdown('</div>', unsafe_allow_html=True)

    if opt_button:
        st.markdown("### ⏳ A carregar dados históricos e a processar pesquisa inteligente...")

        # Obter dados
        collector = DataCollector(exchange_id='binance', symbol=symbol, timeframe=timeframe)
        df_ohlcv = collector.get_ohlcv(limit=limit_candles)

        if df_ohlcv is not None and not df_ohlcv.empty:
            # Função para correr a otimização
            async def execute_optimization_flow():
                # Split dados
                split_idx = int(len(df_ohlcv) * (train_pct / 100))
                df_train = df_ohlcv.iloc[:split_idx]
                df_test = df_ohlcv.iloc[split_idx:]

                st.info(f"Dados divididos em: **{len(df_train)} velas de Treino** e **{len(df_test)} velas de Teste**.")

                # Silenciar logs para extrema velocidade de CPU
                main_logger = logging.getLogger("TradingBot")
                old_level = main_logger.level
                main_logger.setLevel(logging.WARNING)

                # Grids inteligentes (incluindo a opção 999.0 = Sem Take Profit e Trailing Stop)
                short_grid = [5, 9, 12, 15]
                long_grid = [21, 26, 30, 50]
                sl_grid = [1.0, 1.5, 2.0, 3.0]
                tp_grid = [3.0, 5.0, 10.0, 999.0]
                ts_grid = [True, False]

                results_list = []

                # Calcular total
                total_comb = 0
                for sw in short_grid:
                    for lw in long_grid:
                        if sw >= lw: continue
                        for sl in sl_grid:
                            for tp in tp_grid:
                                for ts in ts_grid:
                                    total_comb += 1

                progress_bar_opt = st.progress(0)
                status_text = st.empty()

                current = 0
                for sw in short_grid:
                    for lw in long_grid:
                        if sw >= lw: continue
                        for sl in sl_grid:
                            for tp in tp_grid:
                                for ts in ts_grid:
                                    local_config = config.copy()
                                    local_config.update({
                                        "SHORT_WINDOW": sw,
                                        "LONG_WINDOW": lw,
                                        "P2_WINDOW": sw,
                                        "P3_WINDOW": lw,
                                        "P4_WINDOW": 50,
                                        "P5_WINDOW": 200,
                                        "STOP_LOSS_PERCENT": sl,
                                        "TAKE_PROFIT_PERCENT": tp,
                                        "INITIAL_CAPITAL": 1000.0,
                                        "TRAILING_STOP_ACTIVE": ts
                                    })

                                    # Treino
                                    bt_train = Backtester(local_config, main_logger)
                                    await bt_train.run_backtest(df_train)
                                    m_train = bt_train.get_performance_metrics()

                                    # Teste
                                    bt_test = Backtester(local_config, main_logger)
                                    await bt_test.run_backtest(df_test)
                                    m_test = bt_test.get_performance_metrics()

                                    results_list.append({
                                        "SMA Rápida": sw,
                                        "SMA Lenta": lw,
                                        "Stop Loss (%)": sl,
                                        "Take Profit (%)": tp,
                                        "Stop Móvel (Trailing)": ts,
                                        "Take Profit Ativo": tp != 999.0,
                                        "Retorno Treino": m_train["total_return_pct"],
                                        "Retorno Teste (Futuro)": m_test["total_return_pct"],
                                        "Trades Treino": m_train["num_trades"],
                                        "Trades Teste": m_test["num_trades"],
                                        "Win Rate Treino (%)": m_train["win_rate"] * 100,
                                        "Max Drawdown (%)": m_train["max_drawdown_pct"]
                                    })

                                    current += 1
                                    progress_bar_opt.progress(int((current / total_comb) * 100))
                                    status_text.text(f"A analisar combinação {current}/{total_comb} (Curta: {sw}, Lenta: {lw})")

                progress_bar_opt.empty()
                status_text.empty()
                main_logger.setLevel(old_level)

                df_results = pd.DataFrame(results_list)
                if not df_results.empty:
                    df_results = df_results.sort_values(by="Retorno Treino", ascending=False).reset_index(drop=True)
                return df_results

            # Correr fluxo
            loop_opt = asyncio.new_event_loop()
            asyncio.set_event_loop(loop_opt)
            df_opt = loop_opt.run_until_complete(execute_optimization_flow())

            st.session_state.optimizer_results = df_opt

        else:
            st.error("Erro ao obter dados históricos para otimização.")

    # Exibir resultados guardados
    if st.session_state.optimizer_results is not None:
        df_opt = st.session_state.optimizer_results

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("<h4>🏆 Top 5 Configurações Encontradas</h4>", unsafe_allow_html=True)
        st.markdown(
            "💡 **Dica de Ouro**: Escolha configurações que tenham um **Retorno Treino** excelente "
            "E que também tenham mantido um **Retorno Teste (Futuro)** positivo. Isso prova que o padrão é estável!"
        )

        # Mostrar tabela formatada
        df_display_opt = df_opt.head(5).copy()
        df_display_opt.index = range(1, len(df_display_opt) + 1)
        df_display_opt.index.name = "Rank"

        # Formatando Take Profit bonita
        df_display_opt['Take Profit (%)'] = df_display_opt['Take Profit (%)'].apply(
            lambda x: "Sem Limite" if x == 999.0 else f"{x:.1f}%"
        )
        # Formatando as duas novas colunas de Sim/Não
        df_display_opt['Stop Móvel (Trailing)'] = df_display_opt['Stop Móvel (Trailing)'].apply(
            lambda x: "Sim" if x else "Não"
        )
        df_display_opt['Take Profit Ativo'] = df_display_opt['Take Profit Ativo'].apply(
            lambda x: "Sim" if x else "Não"
        )

        def color_opt_pnl(val):
            if isinstance(val, (int, float)):
                color = '#059669' if val >= 0 else '#e11d48'
                return f'color: {color}; font-weight: bold;'
            return ''

        st.dataframe(
            df_display_opt.style.map(color_opt_pnl, subset=['Retorno Treino', 'Retorno Teste (Futuro)'])
            .format({
                'SMA Rápida': '{:d}',
                'SMA Lenta': '{:d}',
                'Stop Loss (%)': '{:.1f}%',
                'Retorno Treino': '{:+.2f}%',
                'Retorno Teste (Futuro)': '{:+.2f}%',
                'Trades Treino': '{:d}',
                'Trades Teste': '{:d}',
                'Win Rate Treino (%)': '{:.1f}%',
                'Max Drawdown (%)': '{:+.2f}%'
            }),
            use_container_width=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

        # Aplicar Parâmetros Recomendados
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("<h4>⚙️ Aplicar Configuração Recomendada</h4>", unsafe_allow_html=True)

        options_list = []
        for idx, row in df_display_opt.iterrows():
            tp_label = "Sem Limite" if row['Take Profit (%)'] == "Sem Limite" else f"{row['Take Profit (%)']}"
            ts_label = "Sim" if row['Stop Móvel (Trailing)'] == "Sim" else "Não"
            tp_active = "Sim" if row['Take Profit Ativo'] == "Sim" else "Não"
            label = (
                f"Rank #{idx}: Média Curta: {int(row['SMA Rápida'])}, Média Lenta: {int(row['SMA Lenta'])}, "
                f"SL: {row['Stop Loss (%)']:.1f}%, TP Ativo: {tp_active} ({tp_label}), Stop Móvel: {ts_label} | "
                f"Retorno Treino: {row['Retorno Treino']:.2f}% | Retorno Teste: {row['Retorno Teste (Futuro)']:.2f}%"
            )
            options_list.append((label, row))

        selected_option = st.selectbox(
            "Selecione uma configuração para aplicar no Simulador Principal:",
            options=range(len(options_list)),
            format_func=lambda x: options_list[x][0]
        )

        if st.button("🚀 Aplicar Configuração Selecionada"):
            chosen_row = options_list[selected_option][1]
            st.session_state.short_window_val = int(chosen_row['SMA Rápida'])
            st.session_state.long_window_val = int(chosen_row['SMA Lenta'])
            st.session_state.p2_window_val = int(chosen_row['SMA Rápida'])
            st.session_state.p3_window_val = int(chosen_row['SMA Lenta'])
            st.session_state.stop_loss_pct_val = float(chosen_row['Stop Loss (%)'])

            # Tratar o toggle de desativar TP
            if chosen_row['Take Profit Ativo'] == "Não":
                st.session_state.tp_active_val = False
            else:
                st.session_state.tp_active_val = True
                # Limpar a string formatada para obter o float original
                tp_val = float(chosen_row['Take Profit (%)'].replace('%', ''))
                st.session_state.take_profit_pct_val = tp_val

            # Tratar o toggle de Trailing Stop
            if chosen_row['Stop Móvel (Trailing)'] == "Sim":
                st.session_state.trailing_stop_active_val = True
            else:
                st.session_state.trailing_stop_active_val = False

            st.success("Configurações aplicadas com sucesso! Vá para o separador 'Simulação & Gráficos' e clique em 'Executar Simulação'!")
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        # --- NOVO: Registar no Livro de Receitas ---
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("<h4>💾 Registar no Livro de Receitas</h4>", unsafe_allow_html=True)
        st.markdown(
            "Guarde esta configuração diretamente na base de dados local do seu Livro de Receitas "
            "para poder consultá-la ou filtrá-la mais tarde!"
        )

        recipe_note = st.text_input(
            "Comportamento do Mercado / Notas do Teste:",
            placeholder="Ex: Excelente rampa de alta em ETH, muito robusta, drawdown baixo.",
            key="opt_recipe_note"
        )

        if st.button("💾 Guardar Configuração no Livro de Receitas"):
            chosen_row = options_list[selected_option][1]

            recipe_tp_val = chosen_row['Take Profit (%)']
            recipe_ts_val = chosen_row['Stop Móvel (Trailing)']
            recipe_tp_active = chosen_row['Take Profit Ativo']

            new_recipe = {
                "Criptomoeda": symbol,
                "SMA Rápida": int(chosen_row['SMA Rápida']),
                "SMA Lenta": int(chosen_row['SMA Lenta']),
                "Stop Loss (%)": float(chosen_row['Stop Loss (%)']),
                "Take Profit": recipe_tp_val if isinstance(recipe_tp_val, str) else f"{recipe_tp_val:.1f}%",
                "Stop Móvel (Trailing)": recipe_ts_val,
                "Take Profit Ativo": recipe_tp_active,
                "Retorno Treino (%)": float(chosen_row['Retorno Treino']),
                "Retorno Teste (%)": float(chosen_row['Retorno Teste (Futuro)']),
                "Trades Treino": int(chosen_row['Trades Treino']),
                "Trades Teste": int(chosen_row['Trades Teste']),
                "Win Rate Treino (%)": float(chosen_row['Win Rate Treino (%)']),
                "Max Drawdown (%)": float(chosen_row['Max Drawdown (%)']),
                "Notas": recipe_note if recipe_note.strip() != "" else "Sem observações."
            }

            save_recipe(new_recipe)
            st.success("💾 Configuração guardada com sucesso! Vá ao separador 'Livro de Receitas' para ver e filtrar!")
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

# --- CONTEÚDO DA ABA 3: LIVRO DE RECEITAS ---
with tab_recipes:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<h3>📚 Livro de Receitas de Parâmetros</h3>', unsafe_allow_html=True)
    st.markdown("""
    Consulte, filtre e faça a gestão de **todas as configurações otimizadas** que guardou anteriormente.
    Use os filtros abaixo para encontrar rapidamente a parametrização perfeita para cada mercado sem misturar as moedas!
    """)

    df_db = load_recipes_db()

    if not df_db.empty:
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            available_coins = ["Todas"] + sorted(list(df_db["Criptomoeda"].unique()))
            filter_coin = st.selectbox(
                "🔍 Filtrar por Criptomoeda:",
                options=available_coins,
                help="Escolha uma moeda específica para ver apenas os seus testes otimizados."
            )

        if filter_coin != "Todas":
            df_display_db = df_db[df_db["Criptomoeda"] == filter_coin].copy()
        else:
            df_display_db = df_db.copy()

        df_display_db.index = range(1, len(df_display_db) + 1)
        df_display_db.index.name = "Receita"

        st.markdown("<h4>📋 Parametrizações Guardadas</h4>", unsafe_allow_html=True)

        def color_db_pnl(val):
            if isinstance(val, (int, float)):
                color = '#059669' if val >= 0 else '#e11d48'
                return f'color: {color}; font-weight: bold;'
            return ''

        st.dataframe(
            df_display_db.style.map(color_db_pnl, subset=['Retorno Treino (%)', 'Retorno Teste (%)'])
            .format({
                'SMA Rápida': '{:d}',
                'SMA Lenta': '{:d}',
                'Stop Loss (%)': '{:.1f}%',
                'Retorno Treino (%)': '{:+.2f}%',
                'Retorno Teste (%)': '{:+.2f}%',
                'Trades Treino': '{:d}',
                'Trades Teste': '{:d}',
                'Win Rate Treino (%)': '{:.1f}%',
                'Max Drawdown (%)': '{:+.2f}%'
            }),
            use_container_width=True
        )

        st.markdown("<h4>🗑️ Apagar Receita do Livro</h4>", unsafe_allow_html=True)
        col_del1, col_del2 = st.columns([2, 1])
        with col_del1:
            delete_options = []
            for idx, row in df_display_db.iterrows():
                tp_lbl = row['Take Profit']
                ts_lbl = row['Stop Móvel (Trailing)']
                label = (
                    f"Receita #{idx}: {row['Criptomoeda']} | Médias: {row['SMA Rápida']}/{row['SMA Lenta']} | "
                    f"SL: {row['Stop Loss (%)']:.1f}% | TP: {tp_lbl} | Stop Móvel: {ts_lbl} | "
                    f"Retorno Treino: {row['Retorno Treino (%)']:.2f}%"
                )
                delete_options.append((label, row, idx))

            selected_to_delete = st.selectbox(
                "Selecione uma receita para remover permanentemente:",
                options=range(len(delete_options)),
                format_func=lambda x: delete_options[x][0],
                key="delete_recipe_select"
            )

        with col_del2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("🗑️ Apagar Receita Selecionada", use_container_width=True):
                target_row = delete_options[selected_to_delete][1]
                original_df = load_recipes_db()
                mask = (
                    (original_df["Criptomoeda"] == target_row["Criptomoeda"]) &
                    (original_df["SMA Rápida"] == int(target_row["SMA Rápida"])) &
                    (original_df["SMA Lenta"] == int(target_row["SMA Lenta"])) &
                    (original_df["Stop Loss (%)"] == float(target_row["Stop Loss (%)"])) &
                    (original_df["Take Profit"] == target_row["Take Profit"]) &
                    (original_df["Stop Móvel (Trailing)"] == target_row["Stop Móvel (Trailing)"]) &
                    (original_df["Take Profit Ativo"] == target_row["Take Profit Ativo"])
                )
                original_df = original_df[~mask].reset_index(drop=True)
                csv_path = r"c:\Users\paulo\.gemini\antigravity\playground\core-omega\PRJT_OlimpoTrade\registro_otimizacao_moedas.csv"
                original_df.to_csv(csv_path, index=False, encoding="utf-8")
                st.success("Receita removida com sucesso!")
                st.rerun()

    else:
        st.info("Nenhuma receita guardada. Execute uma otimização e guarde as suas melhores configurações!")

    st.markdown('</div>', unsafe_allow_html=True)

# --- CONTEÚDO DA ABA 3 (NOVA ABA 4): SIMULADOR DE MERCADO ---
with tab_simulator:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<h3>🎮 Simulador de Mercado Interativo (Monte Carlo / Random Walk)</h3>', unsafe_allow_html=True)
    st.markdown("""
    Teste a sua estratégia de **Médias Móveis** ou **Vetor de 5 Pontos de Medição** num mercado sintético simulado!
    Este simulador utiliza o modelo matemático de **Movimento Browniano Geométrico (Geometric Brownian Motion)**
    para gerar um gráfico de preços com base na volatilidade e na tendência que escolher.
    Ideal para ver o robô a "aprender" e a reagir ao vivo sem riscos.
    """)
    
    col_sim_1, col_sim_2, col_sim_3 = st.columns(3)
    with col_sim_1:
        sim_drift = st.slider("Tendência Geral (Drift %)", -5.0, 5.0, 0.5, step=0.1, help="Direção média do preço. Valores positivos forçam subida, negativos queda.")
    with col_sim_2:
        sim_vol = st.slider("Volatilidade (Instabilidade %)", 0.5, 10.0, 2.5, step=0.1, help="Nível de ruído e tamanho das oscilações. Cripto costuma ter entre 2% e 5%.")
    with col_sim_3:
        sim_steps = st.slider("Número de Velas (Passos)", 100, 500, 250, step=50, help="Quantidade de candles que o mercado sintético terá.")

    if st.button("🎲 Gerar e Testar em Mercado Sintético", use_container_width=True):
        st.markdown("---")
        with st.spinner("A gerar dados de mercado aleatórios e a simular operações..."):
            import numpy as np
            dt = 1.0
            mu = (sim_drift / 100.0) / sim_steps
            sigma = (sim_vol / 100.0)
            
            prices = [100.0]
            for _ in range(sim_steps - 1):
                shock = np.random.normal(0, 1)
                pct_change = mu * dt + sigma * np.sqrt(dt) * shock
                next_price = prices[-1] * (1 + pct_change)
                prices.append(max(0.1, next_price))
            
            dates = pd.date_range(start="2026-01-01", periods=sim_steps, freq="1h")
            sim_df = pd.DataFrame({
                'open': prices,
                'high': [p * (1 + np.abs(np.random.normal(0, 0.002))) for p in prices],
                'low': [p * (1 - np.abs(np.random.normal(0, 0.002))) for p in prices],
                'close': prices,
                'volume': [1000] * sim_steps
            }, index=dates)
            
            sim_df['high'] = sim_df[['open', 'close', 'high']].max(axis=1)
            sim_df['low'] = sim_df[['open', 'close', 'low']].min(axis=1)

            # Salvar no session state para o otimizador local sintético e matriz de lógicas
            st.session_state.sim_df_val = sim_df
            st.session_state.opt_sim_results = None 
            st.session_state.logic_matrix_results = None

            # 1. Correr o backtest principal para a configuração atual do utilizador
            sim_config = config.copy()
            sim_config["INITIAL_CAPITAL"] = 1000.0
            
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
                
                # Apenas calcula e exibe Média 200 (Line_4) se o modo for 5 pontos ou filtro P5 estiver ativo
                if p5_filter_active or entry_mode == "5PONTOS":
                    sim_viz['Line_4'] = ta.trend.sma_indicator(sim_viz['close'], window=p5_window)
                
                l1_n, l2_n, l3_n = f"P2 ({p2_window})", f"P3 ({p3_window})", f"P4 ({p4_window})"
                l4_n = f"P5 ({p5_window})" if (p5_filter_active or entry_mode == "5PONTOS") else None
            
            fig_sim = go.Figure()
            
            # Linha de Preço Sintético de fundo (cinzenta suave)
            fig_sim.add_trace(go.Scatter(
                x=sim_viz.index, 
                y=sim_viz['close'], 
                mode='lines', 
                name='Preço Sintético', 
                line=dict(color='rgba(100, 116, 139, 0.25)', width=1.5),
                hovertemplate='Preço: %{y:.2f} EUR<extra></extra>'
            ))
            
            # Segmentos verde lagarta vibrante (#22c55e) ligando a Entrada à Saída de cada trade
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
            
            fig_sim.add_trace(go.Scatter(
                x=sim_viz.index, 
                y=sim_viz['Line_1'], 
                mode='lines', 
                name=l1_n, 
                line=dict(color='#0ea5e9', width=2),
                hovertemplate=f'{l1_n}: %{{y:.2f}} EUR<extra></extra>'
            ))
            fig_sim.add_trace(go.Scatter(
                x=sim_viz.index, 
                y=sim_viz['Line_2'], 
                mode='lines', 
                name=l2_n, 
                line=dict(color='#f97316', width=2),
                hovertemplate=f'{l2_n}: %{{y:.2f}} EUR<extra></extra>'
            ))
            
            if strategy_type == "MULTIPOINT_VECTOR":
                fig_sim.add_trace(go.Scatter(
                    x=sim_viz.index, 
                    y=sim_viz['Line_3'], 
                    mode='lines', 
                    name=l3_n, 
                    line=dict(color='#10b981', width=1.5),
                    hovertemplate=f'{l3_n}: %{{y:.2f}} EUR<extra></extra>'
                ))
                if (p5_filter_active or entry_mode == "5PONTOS") and 'Line_4' in sim_viz:
                    fig_sim.add_trace(go.Scatter(
                        x=sim_viz.index, 
                        y=sim_viz['Line_4'], 
                        mode='lines', 
                        name=l4_n, 
                        line=dict(color='#8b5cf6', width=1.5),
                        hovertemplate=f'{l4_n}: %{{y:.2f}} EUR<extra></extra>'
                    ))
                
            sim_buy_x, sim_buy_y, sim_buy_text = [], [], []
            sim_sell_x, sim_sell_y, sim_sell_text = [], [], []
            for t_s in sim_trades:
                entry_t = t_s['entry_timestamp']
                exit_t = t_s['exit_timestamp']
                
                sim_buy_x.append(entry_t)
                sim_buy_y.append(t_s['entry_price'])
                
                # Obter os 5 pontos no momento da compra
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
                        f"<b>P2 (Média {p2_window if 'p2_window' in locals() else 9})</b>: {p2_val:.2f} EUR<br>"
                        f"<b>P3 (Média {p3_window if 'p3_window' in locals() else 21})</b>: {p3_val:.2f} EUR<br>"
                        f"<b>P4 (Média {p4_window if 'p4_window' in locals() else 50})</b>: {p4_val:.2f} EUR<br>"
                    )
                    if p5_filter_active or entry_mode == "5PONTOS":
                        buy_info += f"<b>P5 (Média {p5_window if 'p5_window' in locals() else 200})</b>: {p5_val:.2f} EUR<br>"
                    
                    buy_info += f"<i>Gatilho: Entrada {entry_mode} de Alinhamento!</i>"
                    sim_buy_text.append(buy_info)
                except Exception:
                    sim_buy_text.append(f"COMPRA ao preço de {t_s['entry_price']:.2f}")

                sim_sell_x.append(exit_t)
                sim_sell_y.append(t_s['exit_price'])
                
                # Obter os 5 pontos no momento da venda
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
                        f"<b>P2 (Média {p2_window if 'p2_window' in locals() else 9})</b>: {p2_val:.2f} EUR<br>"
                        f"<b>P3 (Média {p3_window if 'p3_window' in locals() else 21})</b>: {p3_val:.2f} EUR<br>"
                        f"<b>P4 (Média {p4_window if 'p4_window' in locals() else 50})</b>: {p4_val:.2f} EUR<br>"
                    )
                    if p5_filter_active or entry_mode == "5PONTOS":
                        sell_info += f"<b>P5 (Média {p5_window if 'p5_window' in locals() else 200})</b>: {p5_val:.2f} EUR<br>"
                    
                    sell_info += f"<i>Resultado: {t_s['pnl']:.2f} EUR ({t_s['pnl_pct']:.2f}%)</i>"
                    sim_sell_text.append(sell_info)
                except Exception:
                    sim_sell_text.append(f"VENDA ao preço de {t_s['exit_price']:.2f} ({t_s['reason']})")
                
            fig_sim.add_trace(go.Scatter(
                x=sim_buy_x, 
                y=sim_buy_y, 
                mode='markers', 
                name='COMPRA', 
                marker=dict(symbol='triangle-up', size=14, color='#10b981', line=dict(width=1.5, color='#047857')), 
                text=sim_buy_text, 
                hoverinfo='text'
            ))
            fig_sim.add_trace(go.Scatter(
                x=sim_sell_x, 
                y=sim_sell_y, 
                mode='markers', 
                name='VENDA', 
                marker=dict(symbol='triangle-down', size=14, color='#ef4444', line=dict(width=1.5, color='#b91c1c')), 
                text=sim_sell_text, 
                hoverinfo='text'
            ))
            
            fig_sim.update_layout(
                title="Comportamento da Estratégia no Mercado Aleatório (Simulador)", 
                hovermode='x unified', # Guia vertical unificada com todos os 5 pontos!
                template='plotly_white', 
                height=500, 
                margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig_sim, use_container_width=True)
            # 2. Correr a Matriz de 9 Lógicas em Background (Instantâneo)
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
                            "INITIAL_CAPITAL": 1000.0
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
                st.session_state.logic_matrix_results = matrix_data

    # --- NOVO PAINEL: A MATRIZ DE LÓGICAS DA LAGARTA ---
    if strategy_type == "MULTIPOINT_VECTOR" and "logic_matrix_results" in st.session_state and st.session_state.logic_matrix_results is not None:
        st.markdown("---")
        st.markdown("<h3>📊 A Matriz de Lógicas da Lagarta (Análise de 9 Lógicas)</h3>", unsafe_allow_html=True)
        st.markdown("""
        Esta tabela exibe o resultado financeiro de **todas as 9 combinações de Entrada e Saída** possíveis para a nossa lagarta 
        **neste mesmo gráfico sintético**. 
        Descubra instantaneamente qual a melhor forma biológica de se mover perante estas ondas!
        """)
        
        st.info("💡 **Segredo Quantitativo**: Se os resultados de saídas diferentes (P2, P3, P4) derem o mesmo valor na tabela, significa que a tua **Gestão de Risco (Take Profit ou Stop Loss)** fechou as operações antes de o preço tocar nos gatilhos de saída das médias! Para veres a diferença dinâmica das saídas da lagarta pura, experimenta desativar o Take Profit ou alargar o Stop Loss!")
        
        matrix_list = st.session_state.logic_matrix_results
        
        # Encontrar a melhor combinação absoluta para destacar
        best_ret = -999.0
        best_combo = None
        for row in matrix_list:
            for ex in ["P2", "P3", "P4"]:
                cell = row[f"Saída {ex}"]
                if cell["ret"] > best_ret:
                    best_ret = cell["ret"]
                    best_combo = cell
        
                # Renderizar uma tabela HTML premium com estilo de cores (Verde para Lucro, Vermelho para Perda)
        html_code = '<table style="width:100%; border-collapse: collapse; text-align: center; font-family:\'Outfit\',sans-serif; background:rgba(255,255,255,0.7); border-radius:8px; overflow:hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">'
        html_code += '<thead><tr style="background:#0f172a; color:#ffffff;">'
        html_code += '<th style="padding:15px; border:1px solid #334155;">Gatilho de Entrada (Pernas)</th>'
        html_code += '<th style="padding:15px; border:1px solid #334155;">⚡ Saída Rápida (P2 / Média 9)</th>'
        html_code += '<th style="padding:15px; border:1px solid #334155;">⚖️ Saída Intermédia (P3 / Média 21)</th>'
        html_code += '<th style="padding:15px; border:1px solid #334155;">🐢 Saída Lenta (P4 / Média 50)</th>'
        html_code += '</tr></thead><tbody>'
        
        for row in matrix_list:
            html_code += '<tr style="border-bottom: 1px solid #cbd5e1;">'
            html_code += f'<td style="padding:15px; font-weight:bold; background:#f8fafc; border:1px solid #cbd5e1;">{row["Modo de Entrada"]}</td>'
            
            for ex in ["P2", "P3", "P4"]:
                cell = row[f"Saída {ex}"]
                ret = cell["ret"]
                dd = cell["dd"]
                trades = cell["trades"]
                
                # Cores dinâmicas baseadas no retorno
                bg_color = "rgba(5, 150, 105, 0.15)" if ret > 0 else ("rgba(225, 29, 72, 0.15)" if ret < 0 else "transparent")
                text_color = "#059669" if ret > 0 else ("#e11d48" if ret < 0 else "#0f172a")
                border_style = "3px solid #3b82f6" if cell == best_combo else "1px solid #cbd5e1"
                best_tag = "<br><span style=\'font-size:0.8rem; font-weight:bold; background:#3b82f6; color:white; padding:2px 6px; border-radius:4px;\'>🏆 Campeã</span>" if cell == best_combo else ""
                
                html_code += f'<td style="padding:15px; background:{bg_color}; color:{text_color}; border:{border_style}; font-weight:bold;">{ret:+.2f}%<br><span style="font-size:0.85rem; color:#64748b;">(Drawdown: {dd:.2f}%)</span><br><span style="font-size:0.8rem; font-weight:normal; color:#475569;">{trades} Trades</span>{best_tag}</td>'
            html_code += "</tr>"
            
        html_code += "</tbody></table>"
        st.markdown(html_code, unsafe_allow_html=True)
        
        # Botão dinâmico em streamlit para carregar a vencedora imediatamente no painel principal
        if best_combo is not None:
            col_l1, col_l2 = st.columns([3, 1])
            with col_l1:
                st.info(f"💡 **Análise Quantitativa**: A melhor lógica para este bioma de mercado gerado foi **Entrada {best_combo['entry']}** + **Saída {best_combo['exit']}**, obtendo um retorno de **{best_combo['ret']:+.2f}%**.")
            with col_l2:
                if st.button("🚀 Aplicar Lógica Campeã", use_container_width=True):
                    st.session_state.entry_mode_val = best_combo["entry"]
                    st.session_state.exit_mode_val = best_combo["exit"]
                    if best_combo["entry"] == "3PONTOS":
                        st.session_state.p5_filter_active_val = False
                    st.success("✨ Lógica carregada com sucesso na barra lateral! Re-execute para ver os novos sinais.")
                    st.rerun()

    # --- NOVO PAINEL DE OTIMIZAÇÃO LOCAL SINTÉTICA ---
    if "sim_df_val" in st.session_state and st.session_state.sim_df_val is not None:
        st.markdown("---")
        st.markdown("<h4>🔬 Otimização Automática de Parâmetros Sintética</h4>", unsafe_allow_html=True)
        st.markdown("Encontre a combinação perfeita de médias e de gestão de risco **especificamente para este gráfico gerado**!")
        
        if st.button("⚡ Otimizar Parâmetros neste Mercado Sintético", use_container_width=True):
            sim_df = st.session_state.sim_df_val
            with st.spinner("A correr 32 simulações rápidas em background..."):
                import logging
                main_logger = logging.getLogger("TradingBot")
                old_level = main_logger.level
                main_logger.setLevel(logging.WARNING)
                
                # Grelha compacta, ultra rápida
                sw_grid = [9, 12]
                lw_grid = [21, 26]
                sl_grid = [1.5, 3.0]
                tp_grid = [5.0, 10.0]
                ts_grid = [True, False]
                
                results_sint = []
                for sw in sw_grid:
                    for lw in lw_grid:
                        if sw >= lw: continue
                        for sl in sl_grid:
                            for tp in tp_grid:
                                for ts in ts_grid:
                                    local_cfg = config.copy()
                                    local_cfg.update({
                                        "STRATEGY_TYPE": strategy_type,
                                        "SHORT_WINDOW": sw,
                                        "LONG_WINDOW": lw,
                                        "P2_WINDOW": sw,
                                        "P3_WINDOW": lw,
                                        "P4_WINDOW": 50,
                                        "P5_WINDOW": 200,
                                        "P5_SLOPE_FILTER_ACTIVE": False, # Desativar slope na otimização ágil para máximo proveito local
                                        "STOP_LOSS_PERCENT": sl,
                                        "TAKE_PROFIT_PERCENT": tp,
                                        "TRAILING_STOP_ACTIVE": ts,
                                        "INITIAL_CAPITAL": 1000.0
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
                                        "Nº Trades": metrics_sint["num_trades"],
                                        "Win Rate (%)": metrics_sint["win_rate"] * 100,
                                        "Max Drawdown (%)": metrics_sint["max_drawdown_pct"]
                                    })
                
                main_logger.setLevel(old_level)
                df_sint = pd.DataFrame(results_sint)
                df_sint = df_sint.sort_values(by=["Retorno (%)", "Max Drawdown (%)"], ascending=[False, True])
                st.session_state.opt_sim_results = df_sint
        
        # Exibir tabela top 5
        if "opt_sim_results" in st.session_state and st.session_state.opt_sim_results is not None:
            st.markdown("<h5>🏆 Top 5 Configurações Encontradas</h5>", unsafe_allow_html=True)
            top_df = st.session_state.opt_sim_results.head(5)
            st.dataframe(
                top_df.style.format({
                    'Retorno (%)': '{:+.2f}%',
                    'Win Rate (%)': '{:.1f}%',
                    'Max Drawdown (%)': '{:.2f}%'
                }),
                use_container_width=True
            )
            
            best_row = top_df.iloc[0]
            if st.button("🚀 Aplicar Melhor Configuração Otimizada (Top 1) no Painel Principal", use_container_width=True):
                st.session_state.p2_window_val = int(best_row["P2 (Rápida)"])
                st.session_state.p3_window_val = int(best_row["P3 (Confirmadora)"])
                st.session_state.short_window_val = int(best_row["P2 (Rápida)"])
                st.session_state.long_window_val = int(best_row["P3 (Confirmadora)"])
                st.session_state.stop_loss_pct_val = float(best_row["Stop Loss (%)"])
                st.session_state.take_profit_pct_val = float(best_row["Take Profit (%)"])
                st.session_state.trailing_stop_active_val = bool(best_row["Trailing Stop"])
                st.session_state.p5_filter_active_val = False # Desativar o filtro P5 para libertar as trades locais
                
                st.success("✨ Configuração Top 1 aplicada com sucesso na barra lateral! Clique em 'Gerar e Testar' para ver o resultado visual!")
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)# --- CONTEÚDO DA ABA 4: SCANNER DE MERCADO ---
with tab_scanner:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<h3>🔍 Scanner de Mercado em Tempo Real</h3>', unsafe_allow_html=True)
    st.markdown("""
    Analise o mercado das criptomoedas na **Binance** em direto! 
    Este scanner pesquisa mais de 100 ativos voláteis e exibe as **Top 10 moedas mais líquidas** e as **Top 10 com maior crescimento (Top Gainers)**.
    Use estes dados para escolher o par de trading ideal na barra lateral e otimizar a sua estratégia antes de todos!
    """)
    
    if st.button("⚡ Executar Varredura de Mercado (Binance)", use_container_width=True):
        st.markdown("---")
        with st.spinner("A ligar à Binance e a analisar mais de 100 ativos..."):
            from daily_market_scanner import DailyMarketScanner
            try:
                scanner = DailyMarketScanner()
                top_volume, top_gainers = scanner.scan_market()
                
                col_s1, col_s2 = st.columns(2)
                
                with col_s1:
                    st.markdown("<h4>🔥 Moedas mais Transacionadas (Volume)</h4>", unsafe_allow_html=True)
                    st.markdown("Representa o maior interesse e liquidez das baleias e do mercado institucional.")
                    df_vol = pd.DataFrame(top_volume)
                    df_vol.index = range(1, len(df_vol) + 1)
                    df_vol.index.name = "Rank"
                    
                    st.dataframe(
                        df_vol.style.format({
                            'Preço Atual (USDT)': '{:,.4f}',
                            'Variação 24h (%)': '{:+.2f}%',
                            'Volume 24h (USDT)': '${:,.0f}',
                            'Máxima 24h (USDT)': '{:,.4f}',
                            'Mínima 24h (USDT)': '{:,.4f}'
                        }),
                        use_container_width=True
                    )
                    
                with col_s2:
                    st.markdown("<h4>🚀 Moedas em Maior Crescimento (Gainers)</h4>", unsafe_allow_html=True)
                    st.markdown("Ativos com forte impulso vertical nas últimas 24h. Excelentes para estratégias de seguimento de tendência!")
                    df_gain = pd.DataFrame(top_gainers)
                    df_gain.index = range(1, len(df_gain) + 1)
                    df_gain.index.name = "Rank"
                    
                    def color_positive_gain(val):
                        if isinstance(val, (int, float)):
                            return 'color: #059669; font-weight: bold;'
                        return ''
                        
                    st.dataframe(
                        df_gain.style.map(color_positive_gain, subset=['Variação 24h (%)'])
                        .format({
                            'Preço Atual (USDT)': '{:,.4f}',
                            'Variação 24h (%)': '{:+.2f}%',
                            'Volume 24h (USDT)': '${:,.0f}',
                            'Máxima 24h (USDT)': '{:,.4f}',
                            'Mínima 24h (USDT)': '{:,.4f}'
                        }),
                        use_container_width=True
                    )
                    
                st.success("✨ Varredura de mercado concluída com sucesso!")
                
            except Exception as e:
                st.error(f"Erro ao executar o scanner de mercado: {e}")
                
    st.markdown('</div>', unsafe_allow_html=True)

# --- CONTEÚDO DA ABA 5: NOTÍCIAS & SENTIMENTO ---
with tab_news:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<h3>📰 Notícias Cripto & Sentimento em Tempo Real</h3>', unsafe_allow_html=True)
    st.markdown("""
    Acompanhe as notícias de mercado mais quentes e saiba a "temperatura fundamental" do ecossistema cripto.
    O OlimpoTrade analisa automaticamente o texto de cada notícia e atribui uma classificação emocional rápida.
    """)
    
    if st.button("🔄 Carregar Últimas Notícias (CoinTelegraph / CoinDesk)", use_container_width=True):
        st.markdown("---")
        with st.spinner("A descarregar e a analisar notícias de mercado..."):
            from crypto_news_service import CryptoNewsService
            try:
                ns = CryptoNewsService()
                news = ns.fetch_news()
                
                # Calcular estatísticas do sentimento geral
                sentiments = [item["sentiment"] for item in news]
                pos_count = sentiments.count("🟢 Alta (Bullish)")
                neg_count = sentiments.count("🔴 Baixa (Bearish)")
                neu_count = sentiments.count("⚪ Neutro")
                
                st.markdown("<h4>📊 Termómetro de Sentimento do Mercado</h4>", unsafe_allow_html=True)
                col_n1, col_n2, col_n3 = st.columns(3)
                with col_n1:
                    st.metric("🟢 Notícias de Alta", f"{pos_count} / {len(news)}")
                with col_n2:
                    st.metric("🔴 Notícias de Baixa", f"{neg_count} / {len(news)}")
                with col_n3:
                    st.metric("⚪ Neutras", f"{neu_count} / {len(news)}")
                    
                if pos_count > neg_count:
                    st.success("📈 **Sentimento Geral: BULLISH (Alta)** — O mercado está com sentimentos maioritariamente otimistas. Excelente para estratégias de tendência de alta!")
                elif neg_count > pos_count:
                    st.error("📉 **Sentimento Geral: BEARISH (Baixa)** — O mercado está sob sentimentos de medo ou realização. Mantenha os seus Stops de proteção bem ajustados!")
                else:
                    st.info("⚖️ **Sentimento Geral: NEUTRO** — O mercado está em consolidação e equilíbrio emocional.")
                
                st.markdown("---")
                st.markdown("<h4>📰 Breaking News Recentes</h4>", unsafe_allow_html=True)
                
                for idx, art in enumerate(news):
                    color_border = "#059669" if "Alta" in art["sentiment"] else ("#e11d48" if "Baixa" in art["sentiment"] else "#64748b")
                    
                    st.markdown(f"""
                    <div style="
                        background: rgba(255, 255, 255, 0.7);
                        border-left: 5px solid {color_border};
                        padding: 15px;
                        margin-bottom: 15px;
                        border-radius: 8px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                            <span style="font-weight: bold; color: {color_border}; font-size: 0.9rem;">{art["sentiment"]}</span>
                            <span style="color: #64748b; font-size: 0.8rem;">{art["date"]}</span>
                        </div>
                        <h4 style="margin: 5px 0; color: #0f172a;"><a href="{art["link"]}" target="_blank" style="text-decoration: none; color: inherit; hover: color: #3b82f6;">{art["title"]}</a></h4>
                        <p style="margin: 5px 0 0 0; color: #334155; font-size: 0.9rem; line-height: 1.4;">{art["desc"]}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.success("✨ Notícias carregadas e analisadas com sucesso!")
                
            except Exception as e:
                st.error(f"Erro ao carregar notícias: {e}")
                
    st.markdown('</div>', unsafe_allow_html=True)
