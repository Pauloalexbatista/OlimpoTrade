import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import time
import os
import io

def generate_math_market(scenario="Didatico Classico", noise=1.0):
    np.random.seed(int(datetime.datetime.now().timestamp()))
    prices = [1000.0]
    
    if scenario == "Didatico Classico":
        for _ in range(200):
            change = np.random.normal(0.5, 2.0 * noise)
            prices.append(max(10.0, prices[-1] + change))
        for _ in range(200):
            change = np.random.normal(0.0, 1.2 * noise)
            prices.append(max(10.0, prices[-1] + change))
        for _ in range(200):
            change = np.random.normal(-1.2, 2.5 * noise)
            prices.append(max(10.0, prices[-1] + change))
        for _ in range(200):
            change = np.random.normal(0.0, 6.0 * noise)
            prices.append(max(10.0, prices[-1] + change))
        for _ in range(199):
            change = np.random.normal(0.8, 1.5 * noise)
            prices.append(max(10.0, prices[-1] + change))
            
    elif scenario == "Montanha Russa":
        for cycle in range(10):
            direction = 1.0 if cycle % 2 == 0 else -1.2
            for _ in range(100):
                change = np.random.normal(0.6 * direction, 2.2 * noise)
                prices.append(max(10.0, prices[-1] + change))
                
    elif scenario == "Flash Crash":
        for _ in range(400):
            change = np.random.normal(0.1, 1.0 * noise)
            prices.append(max(10.0, prices[-1] + change))
        for _ in range(50):
            change = np.random.normal(-15.0, 4.0 * noise)
            prices.append(max(10.0, prices[-1] + change))
        for _ in range(549):
            change = np.random.normal(1.2, 1.8 * noise)
            prices.append(max(10.0, prices[-1] + change))
            
    elif scenario == "Lateralizacao Eterna":
        mean_p = 1000.0
        for _ in range(999):
            gravity = (mean_p - prices[-1]) * 0.05
            change = np.random.normal(gravity, 3.5 * noise)
            prices.append(max(10.0, prices[-1] + change))
            
    elif scenario == "Tendencia Saudavel (Bull)":
        for _ in range(999):
            change = np.random.normal(0.4, 1.5 * noise)
            prices.append(max(10.0, prices[-1] + change))
            
    return prices

def recalculate_math_df():
    p2 = st.session_state.get('math_active_sma_p2', 5)
    p3 = st.session_state.get('math_active_sma_p3', 13)
    p4 = st.session_state.get('math_active_sma_p4', 21)
    p5 = st.session_state.get('math_active_sma_p5', 55)
    p6 = st.session_state.get('math_active_sma_p6', 144)
    
    if st.session_state.math_source == "Sintetico":
        prices = st.session_state.math_prices
        timestamps = [f"V{idx}" for idx in range(len(prices))]
    else:
        df_real = st.session_state.math_df_real
        prices = df_real["close"].tolist()
        timestamps = df_real["timestamp"].tolist()
        
    df = pd.DataFrame({'price': prices, 'timestamp': timestamps})
    df[f'sma_{p2}'] = df['price'].rolling(window=p2).mean()
    df[f'sma_{p3}'] = df['price'].rolling(window=p3).mean()
    df[f'sma_{p4}'] = df['price'].rolling(window=p4).mean()
    df[f'sma_{p5}'] = df['price'].rolling(window=p5).mean()
    df[f'sma_{p6}'] = df['price'].rolling(window=p6).mean()
    df['velocity'] = df[f'sma_{p2}'].diff(1)
    df['acceleration'] = df['velocity'].diff(1)
    df['volatility'] = df['price'].rolling(window=20).std()
    
    smas = [f'sma_{p2}', f'sma_{p3}', f'sma_{p4}', f'sma_{p5}', f'sma_{p6}']
    avg_sma = df[smas].mean(axis=1)
    df['stretching'] = df[smas].sub(avg_sma, axis=0).abs().mean(axis=1).div(avg_sma).mul(100)
    
    # Pre-calculate regimes
    regimes = []
    for idx in range(len(df)):
        regimes.append(classify_regime_row(df.iloc[idx], p2, p3, p4, p5, p6))
    df['regime'] = regimes
    
    st.session_state.math_df = df

def classify_regime_row(row, p2, p3, p4, p5, p6):
    p = row['price']
    s2 = row[f'sma_{p2}']
    s3 = row[f'sma_{p3}']
    s4 = row[f'sma_{p4}']
    s5 = row[f'sma_{p5}']
    s6 = row[f'sma_{p6}']
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

def find_structural_points(df):
    prices = df["price"].tolist()
    n = len(prices)
    fundos = []
    topos = []
    for i in range(10, n - 30):
        p_curr = prices[i]
        is_min = all(p_curr <= prices[j] for j in range(i-10, i+11))
        if is_min:
            future_prices = prices[i:i+30]
            max_future = max(future_prices)
            future_idx = future_prices.index(max_future) + i
            gain_pct = (max_future - p_curr) / p_curr * 100
            if gain_pct >= 2.0:
                fundos.append({"idx_fundo": i, "price_fundo": p_curr, "idx_topo": future_idx, "price_topo": max_future, "gain_pct": gain_pct})
        is_max = all(p_curr >= prices[j] for j in range(i-10, i+11))
        if is_max:
            future_prices = prices[i:i+30]
            min_future = min(future_prices)
            future_idx = future_prices.index(min_future) + i
            loss_pct = (p_curr - min_future) / p_curr * 100
            if loss_pct >= 2.0:
                topos.append({"idx_topo": i, "price_topo": p_curr, "idx_fundo": future_idx, "price_fundo": min_future, "loss_pct": loss_pct})
    fundos = sorted(fundos, key=lambda x: x["gain_pct"], reverse=True)
    topos = sorted(topos, key=lambda x: x["loss_pct"], reverse=True)
    return fundos, topos

def get_pattern_stats(points_list, df, regime_filter=None):
    if not points_list:
        return pd.DataFrame()
        
    p2 = st.session_state.get('math_active_sma_p2', 5)
    p3 = st.session_state.get('math_active_sma_p3', 13)
    p4 = st.session_state.get('math_active_sma_p4', 21)
    p5 = st.session_state.get('math_active_sma_p5', 55)
    p6 = st.session_state.get('math_active_sma_p6', 144)
    
    # O(1) speedup: Convert columns to native lists for lightning-fast indexing
    prices = df['price'].tolist()
    regimes = df['regime'].tolist()
    velocity_list = df['velocity'].tolist()
    acceleration_list = df['acceleration'].tolist()
    stretching_list = df['stretching'].tolist()
    
    sma_p2 = df[f'sma_{p2}'].tolist()
    sma_p3 = df[f'sma_{p3}'].tolist()
    sma_p4 = df[f'sma_{p4}'].tolist()
    sma_p5 = df[f'sma_{p5}'].tolist()
    sma_p6 = df[f'sma_{p6}'].tolist()
    
    records = []
    for pt in points_list:
        is_fundo = "gain_pct" in pt
        idx = pt.get("idx_fundo") if is_fundo else pt.get("idx_topo")
        if idx is None or idx >= len(df):
            continue
            
        regime = regimes[idx]
        if regime_filter and regime_filter != "Todos" and regime != regime_filter:
            continue
            
        p2_val = sma_p2[idx]
        p3_val = sma_p3[idx]
        p4_val = sma_p4[idx]
        p5_val = sma_p5[idx]
        p6_val = sma_p6[idx]
        
        disp_pct = ((p2_val - p6_val) / p6_val * 100) if not pd.isna(p6_val) and p6_val != 0 else 0.0
        
        gain_pct = pt.get("gain_pct", 0.0)
        loss_pct = pt.get("loss_pct", 0.0)
        
        # Novos indicadores da Geometria Sagrada Fibonacci
        smas = [p2_val, p3_val, p4_val, p5_val, p6_val]
        if not any(pd.isna(x) for x in smas):
            std_val = np.std(smas)
            mean_val = np.mean(smas)
            mola_pct = (std_val / mean_val * 100) if mean_val != 0 else 0.0
            
            infil_bull = "Sim" if (p2_val > p3_val > p4_val and p5_val < p6_val) else "Não"
            infil_bear = "Sim" if (p2_val < p3_val < p4_val and p5_val > p6_val) else "Não"
            infil_val = infil_bull if is_fundo else infil_bear
            
            dist_p5 = (abs(prices[idx] - p5_val) / p5_val * 100) if p5_val != 0 else 999.0
            dist_p6 = (abs(prices[idx] - p6_val) / p6_val * 100) if p6_val != 0 else 999.0
            reteste_val = "Sim" if (dist_p5 < 0.8 or dist_p6 < 0.8) else "Não"
            
            spread_fast = p2_val - p3_val
            spread_slow = p3_val - p4_val
            vel_spread = spread_fast - spread_slow
        else:
            mola_pct = np.nan
            infil_val = "Não"
            reteste_val = "Não"
            vel_spread = np.nan
        
        records.append({
            "Batimento Inicial": idx,
            "Preço Inicial": f"{prices[idx]:.2f}",
            "Batimento Final": pt.get("idx_topo") if is_fundo else pt.get("idx_fundo"),
            "Preço Final": f"{pt.get('price_topo'):.2f}" if is_fundo else f"{pt.get('price_fundo'):.2f}",
            "Variação %": f"{gain_pct:+.2f}%" if is_fundo else f"-{loss_pct:.2f}%",
            "var_raw": gain_pct if is_fundo else -loss_pct,
            "Velocidade": velocity_list[idx],
            "Aceleração": acceleration_list[idx],
            "Stretching": stretching_list[idx],
            "Regime Inicial": regime,
            f"Média {p2}": f"{p2_val:.2f}" if not pd.isna(p2_val) else "",
            f"Média {p3}": f"{p3_val:.2f}" if not pd.isna(p3_val) else "",
            f"Média {p4}": f"{p4_val:.2f}" if not pd.isna(p4_val) else "",
            f"Média {p5}": f"{p5_val:.2f}" if not pd.isna(p5_val) else "",
            f"Média {p6}": f"{p6_val:.2f}" if not pd.isna(p6_val) else "",
            "Disp. Vetorial %": f"{disp_pct:+.2f}%" if not pd.isna(p2_val) and not pd.isna(p6_val) else "",
            "Compressão Mola %": f"{mola_pct:.2f}%" if not pd.isna(mola_pct) else "",
            "Infiltração": infil_val,
            "Reteste Gravitacional": reteste_val,
            "Velocidade Spread": f"{vel_spread:+.4f}" if not pd.isna(vel_spread) else ""
        })
        
    if not records:
        return pd.DataFrame()
        
    return pd.DataFrame(records)

def style_regime_row(val):
    if val == "BULL":
        return "background-color: rgba(46, 204, 113, 0.2); color: #000; font-weight: bold;"
    elif val == "BEAR":
        return "background-color: rgba(231, 76, 60, 0.2); color: #000; font-weight: bold;"
    elif val == "LATERAL":
        return "background-color: rgba(241, 196, 15, 0.15); color: #000;"
    elif val == "CAOTICO":
        return "background-color: rgba(155, 89, 182, 0.2); color: #000; font-weight: bold;"
    return ""

def apply_styler(styled_df, subset_col):
    try:
        if hasattr(styled_df, 'map'):
            return styled_df.map(style_regime_row, subset=[subset_col])
        else:
            return styled_df.applymap(style_regime_row, subset=[subset_col])
    except Exception:
        return styled_df

def load_uploaded_csv(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
        price_col = None
        for col in df.columns:
            if col.lower() in ["close", "price", "ultimo", "last", "val"]:
                price_col = col
                break
        if price_col is None:
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    price_col = col
                    break
        if price_col is None:
            st.error("Não foi possível encontrar uma coluna numérica de preço no CSV!")
            return False
            
        prices = df[price_col].astype(float).tolist()
        
        time_col = None
        for col in df.columns:
            if col.lower() in ["timestamp", "time", "date", "data", "datetime"]:
                time_col = col
                break
        if time_col is not None:
            timestamps = df[time_col].astype(str).tolist()
        else:
            timestamps = [f"V{i}" for i in range(len(prices))]
            
        st.session_state.math_df_real = pd.DataFrame({"close": prices, "timestamp": timestamps})
        st.session_state.math_source = "Binance CSV"
        st.session_state.math_prices = prices
        st.session_state.math_step = 50
        st.session_state.math_running = False
        recalculate_math_df()
        st.success("CSV Importado com sucesso! Simulação pronta.")
        return True
    except Exception as e:
        st.error(f"Erro ao processar o CSV: {str(e)}")
        return False

def render():
    st.markdown("""
    <div style='background: linear-gradient(135deg, #1e3a8a 0%, #0d1b2a 100%); padding: 25px; border-radius: 12px; margin-bottom: 25px; color: white;'>
        <h1 style='margin:0; font-size: 2.2rem;'>🔮 Laboratório Matemático & Regimes Adaptativos</h1>
        <p style='margin: 5px 0 0 0; opacity: 0.8;'>Simulador quântico de regimes de mercado, derivadas e mineração de padrões estatísticos em tempo real.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 📚 Dicionário de Física Financeira Incorporado
    with st.expander("📚 Dicionário de Física Financeira: Como ler as colunas?", expanded=False):
        st.markdown("""
        ### 📚 O Dicionário de Variáveis do OlimpoTrade
        
        * **1. Stretching (Sobrestiramento) ── *"A Distância ao Elástico"***
          * **O que é**: O quão longe o preço atual se afastou do feixe de médias móveis.
          * **Como ler**: Pensa no preço preso às médias por um elástico. Se ele se afasta demasiado (Stretching alto), tende a voltar para trás (reversão). Em mercado lateral, reversões seguras ocorrem com Stretching muito baixo (< 0.60%).
          
        * **2. Disp. Vetorial % (Dispersão Vetorial) ── *"A Tensão da Mola"***
          * **O que é**: A distância percentual entre a média mais rápida (Média 5) e a média mais lenta (Média 144).
          * **Como ler**: 
            * **Valores Negativos (ex: -1.5%)**: A mola está comprimida para baixo. Armazena energia potencial elástica enorme para uma explosão de alta (reversão forte com lucros > 5%).
            * **Valores Positivos (ex: +3.0%)**: A mola já está esticada para cima. O movimento já está a meio, tendo menos energia de explosão (ganhos menores < 3.8%).
            
        * **3. Compressão Mola % (Coesão) ── *"O Aperto das Linhas"***
          * **O que é**: Mede o quão juntas ou afastadas estão as 5 médias entre si (desvio padrão interno).
          * **Como ler**: Valores muito baixos (feixe de linhas afastado) indicam compressão máxima de energia antes de uma violenta rutura de preço (breakout).
          
        * **4. Infiltração Fractal ── *"A Mudança no Micro-Tempo"***
          * **O que é**: Indica se a tendência já começou a mudar nos prazos muito rápidos (médias 5, 13, 21) antes de se ver nas tendências lentas de longo prazo (55, 144).
          * **Como ler**: Permite-nos entrar de forma antecipada logo no início da reversão macro, apanhando o fundo cirúrgico.
          
        * **5. Reteste Gravitacional ── *"O Trampolim"***
          * **O que é**: Ocorre quando o preço recua exatamente até tocar no suporte de betão da média institucional de 55 ou na gravidade de 144.
          * **Como ler**: Toques precisos nestas médias lentas oferecem os ricochetes com melhor rácio risco/retorno a favor da tendência principal.
          
        * **6. Velocidade e Aceleração ── *"O Acelerador e o Travão"***
          * **Como ler**: A **Velocidade** indica a rapidez do movimento das médias rápidas. A **Aceleração** mede a força por trás dessa velocidade. Se a velocidade cai mas a aceleração inverte, o mercado está a travar para mudar de direção.
        """)
    
    # 1. Setup Session States
    if 'math_source' not in st.session_state:
        st.session_state.math_source = "Sintetico"
    if 'math_scenario' not in st.session_state:
        st.session_state.math_scenario = "Didatico Classico"
    if 'math_noise' not in st.session_state:
        st.session_state.math_noise = 1.0
    if 'math_size' not in st.session_state:
        st.session_state.math_size = 500
    if 'math_prices' not in st.session_state:
        st.session_state.math_prices = generate_math_market("Didatico Classico", 1.0)
    if 'math_step' not in st.session_state:
        st.session_state.math_step = 50
    if 'math_running' not in st.session_state:
        st.session_state.math_running = False
    
    # Custom SMA parameter session states (Design Mode)
    if 'math_sma_p2' not in st.session_state: st.session_state.math_sma_p2 = 5
    if 'math_sma_p3' not in st.session_state: st.session_state.math_sma_p3 = 13
    if 'math_sma_p4' not in st.session_state: st.session_state.math_sma_p4 = 21
    if 'math_sma_p5' not in st.session_state: st.session_state.math_sma_p5 = 55
    if 'math_sma_p6' not in st.session_state: st.session_state.math_sma_p6 = 144
    
    # Active SMA parameter session states (usados nos cálculos de math_df ativo)
    if 'math_active_sma_p2' not in st.session_state: st.session_state.math_active_sma_p2 = 5
    if 'math_active_sma_p3' not in st.session_state: st.session_state.math_active_sma_p3 = 13
    if 'math_active_sma_p4' not in st.session_state: st.session_state.math_active_sma_p4 = 21
    if 'math_active_sma_p5' not in st.session_state: st.session_state.math_active_sma_p5 = 55
    if 'math_active_sma_p6' not in st.session_state: st.session_state.math_active_sma_p6 = 144
    
    if 'math_df' not in st.session_state:
        recalculate_math_df()
        
    # 2. Control Columns Layout
    col_setup, col_sma, col_sim = st.columns(3)
    
    with col_setup:
        st.subheader("🛠️ Configuração do Mercado")
        source_opt = st.radio("Fonte de Dados", ["Sintetico", "Binance CSV"], index=0 if st.session_state.math_source == "Sintetico" else 1, horizontal=True)
        
        if source_opt != st.session_state.math_source:
            st.session_state.math_source = source_opt
            if source_opt == "Sintetico":
                st.session_state.math_prices = generate_math_market(st.session_state.math_scenario, st.session_state.math_noise)
                st.session_state.math_step = 50
            recalculate_math_df()
            st.rerun()
            
        if st.session_state.math_source == "Sintetico":
            scenario = st.selectbox("Cenário Didático", ["Didatico Classico", "Montanha Russa", "Flash Crash", "Lateralizacao Eterna", "Tendencia Saudavel (Bull)"], index=["Didatico Classico", "Montanha Russa", "Flash Crash", "Lateralizacao Eterna", "Tendencia Saudavel (Bull)"].index(st.session_state.math_scenario))
            noise = st.slider("Ruído do Mercado", 0.1, 5.0, float(st.session_state.math_noise), step=0.1)
            size = st.slider("Tamanho da Série", 100, 2000, int(st.session_state.math_size), step=100)
            
            if scenario != st.session_state.math_scenario or noise != st.session_state.math_noise or size != st.session_state.math_size:
                st.session_state.math_scenario = scenario
                st.session_state.math_noise = noise
                st.session_state.math_size = size
                st.session_state.math_prices = generate_math_market(scenario, noise)[:size]
                st.session_state.math_step = 50
                recalculate_math_df()
                st.rerun()
        else:
            uploaded_file = st.file_uploader("Carregar Ficheiro CSV (ex: Binance)", type=["csv"])
            if uploaded_file is not None:
                if load_uploaded_csv(uploaded_file):
                    st.rerun()
                    
    with col_sma:

                    
        st.subheader("📐 Vetor de Médias Móveis")

                    
        st.markdown("*Insira qualquer período de média móvel desejado:*")

                    
        

                    
        p2_val = st.number_input("Média Rápida (P2)", min_value=2, max_value=500, value=int(st.session_state.math_sma_p2), step=1)

                    
        p3_val = st.number_input("Média Curta (P3)", min_value=2, max_value=500, value=int(st.session_state.math_sma_p3), step=1)

                    
        p4_val = st.number_input("Média Média (P4)", min_value=2, max_value=500, value=int(st.session_state.math_sma_p4), step=1)

                    
        p5_val = st.number_input("Média Longa (P5)", min_value=2, max_value=500, value=int(st.session_state.math_sma_p5), step=1)

                    
        p6_val = st.number_input("Super Longa (P6)", min_value=2, max_value=500, value=int(st.session_state.math_sma_p6), step=1)

                    
        

                    
        if (p2_val != st.session_state.math_sma_p2 or 

                    
            p3_val != st.session_state.math_sma_p3 or 

                    
            p4_val != st.session_state.math_sma_p4 or 

                    
            p5_val != st.session_state.math_sma_p5 or 

                    
            p6_val != st.session_state.math_sma_p6):

                    
            st.session_state.math_sma_p2 = p2_val

                    
            st.session_state.math_sma_p3 = p3_val

                    
            st.session_state.math_sma_p4 = p4_val

                    
            st.session_state.math_sma_p5 = p5_val

                    
            st.session_state.math_sma_p6 = p6_val

                    
            recalculate_math_df()

                    
            st.rerun()
            
    with col_sim:

            
        st.subheader("⚙️ Controlo de Batimentos")

            
        

            
        # Modo Instantâneo checkbox

            
        instant_mode = st.checkbox("⚡ Modo Instantâneo (Processar Tudo)", value=st.session_state.get('math_instant_mode', False), help="Calcula e exibe a série completa imediatamente, ignorando a animação passo-a-passo.")

            
        if instant_mode != st.session_state.get('math_instant_mode', False):

            
            st.session_state.math_instant_mode = instant_mode

            
            if instant_mode:

            
                st.session_state.math_step = len(st.session_state.math_df) - 1

            
                st.session_state.math_running = False

            
            else:

            
                st.session_state.math_step = 50

            
            st.rerun()

            
            

            
        if instant_mode:

            
            st.session_state.math_step = len(st.session_state.math_df) - 1

            
            st.session_state.math_running = False

            
            

            
        # Play/Pause toggle (only if not in instant mode)

            
        if not instant_mode:

            
            running_label = "⏸️ Pausar Simulação" if st.session_state.math_running else "▶️ Iniciar Simulação"

            
            if st.button(running_label, use_container_width=True):

            
                st.session_state.math_running = not st.session_state.math_running

            
                st.rerun()

            
                

            
            col_btn1, col_btn2 = st.columns(2)

            
            with col_btn1:

            
                if st.button("➡️ Avançar 1 Passo", use_container_width=True):

            
                    st.session_state.math_running = False

            
                    df_len = len(st.session_state.math_df)

            
                    if st.session_state.math_step < df_len - 1:

            
                        st.session_state.math_step += 1

            
                    st.rerun()

            
            with col_btn2:

            
                if st.button("🔄 Reiniciar", use_container_width=True):

            
                    st.session_state.math_step = 50

            
                    st.session_state.math_running = False

            
                    if st.session_state.math_source == "Sintetico":

            
                        st.session_state.math_prices = generate_math_market(st.session_state.math_scenario, st.session_state.math_noise)

            
                    recalculate_math_df()

            
                    st.rerun()

            
                    

            
            speed = st.selectbox("Velocidade do Batimento", ["Lento (1.0s)", "Médio (0.3s)", "Rápido (0.05s)"], index=1)

            
            speed_map = {"Lento (1.0s)": 1.0, "Médio (0.3s)": 0.3, "Rápido (0.05s)": 0.05}

            
            step_delay = speed_map[speed]

            
        else:

            
            st.info("⚡ Modo Instantâneo Ativo: Série completa processada e exibida abaixo.")

            
            step_delay = 0.05

            
            

            
        # Export data as CSV

            
        df_full = st.session_state.math_df

            
        csv_buffer = io.StringIO()

            
        df_full.to_csv(csv_buffer, index=False)

            
        csv_data = csv_buffer.getvalue()

            
        

            
        st.download_button(

            
            label="📥 Exportar Toda a Série (CSV)",

            
            data=csv_data,

            
            file_name=f"serie_olimpotrade_{int(time.time())}.csv",

            
            mime="text/csv",

            
            use_container_width=True

            
        )

    # 3. Dynamic Cockpit Cards
    step = st.session_state.math_step
    df = st.session_state.math_df
    
    # Boundary check
    if step >= len(df):
        step = len(df) - 1
        st.session_state.math_step = step
        st.session_state.math_running = False
        
    row = df.iloc[step]
    regime = row['regime']
    
    regime_display = {
        "BULL": ("🟢 BULL MARKET", "rgba(46, 204, 113, 0.2)"),
        "BEAR": ("🔴 BEAR MARKET", "rgba(231, 76, 60, 0.2)"),
        "LATERAL": ("🟡 LATERAL / CONSOLIDAÇÃO", "rgba(241, 196, 15, 0.15)"),
        "CAOTICO": ("🟣 MERCADO CAÓTICO", "rgba(155, 89, 182, 0.2)")
    }
    label, bg_color = regime_display.get(regime, ("🟡 LATERAL", "rgba(241, 196, 15, 0.15)"))
    
    st.markdown(f"""
    <div class="glass-card" style="background: {bg_color}; padding: 20px; border-radius: 12px; margin-bottom: 25px; border: 1px solid rgba(255,255,255,0.3); text-align: center;">
        <span style="font-size: 1.1rem; letter-spacing: 1px; color:#1e293b; font-weight:bold;">REGIME DE MERCADO ATUAL</span>
        <h2 style="margin: 5px 0 0 0; font-size: 2.2rem; font-weight: 800; color:#0f172a;">{label}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Preço Atual", f"{row['price']:.2f}", delta=f"{row['price'] - df.iloc[max(0, step-1)]['price']:+.2f}")
    with col_m2:
        st.metric("Velocidade (1ª Derivada)", f"{row['velocity']:.4f}", delta=f"{row['velocity'] - df.iloc[max(0, step-1)]['velocity']:+.4f}")
    with col_m3:
        st.metric("Aceleração (2ª Derivada)", f"{row['acceleration']:.4f}", delta=f"{row['acceleration'] - df.iloc[max(0, step-1)]['acceleration']:+.4f}")
    with col_m4:
        st.metric("Stretching (Dispersão)", f"{row['stretching']:.2f}%", delta=f"{row['stretching'] - df.iloc[max(0, step-1)]['stretching']:+.2f}%")

    # 4. Interactive High-Precision Charts
    st.subheader(f"📊 Gráfico Blueprint & Regimes (Batimento {step} / {len(df) - 1})")
    
    sub_df = df.iloc[:step+1]
    
    p2 = st.session_state.math_active_sma_p2
    p3 = st.session_state.math_active_sma_p3
    p4 = st.session_state.math_active_sma_p4
    p5 = st.session_state.math_active_sma_p5
    p6 = st.session_state.math_active_sma_p6
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.7, 0.3])
    
    # Subplot 1: Price and SMAs
    fig.add_trace(go.Scatter(x=sub_df.index, y=sub_df['price'], name='Preço', line=dict(color='#475569', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=sub_df.index, y=sub_df[f'sma_{p2}'], name=f'SMA {p2}', line=dict(color='#2ecc71', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=sub_df.index, y=sub_df[f'sma_{p3}'], name=f'SMA {p3}', line=dict(color='#3498db', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=sub_df.index, y=sub_df[f'sma_{p4}'], name=f'SMA {p4}', line=dict(color='#e67e22', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=sub_df.index, y=sub_df[f'sma_{p5}'], name=f'SMA {p5}', line=dict(color='#9b59b6', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=sub_df.index, y=sub_df[f'sma_{p6}'], name=f'SMA {p6}', line=dict(color='#e74c3c', width=1.5)), row=1, col=1)
    
    # Subplot 2: Speed and Acceleration
    fig.add_trace(go.Scatter(x=sub_df.index, y=sub_df['velocity'], name='Velocidade', line=dict(color='#1abc9c', width=1.5)), row=2, col=1)
    fig.add_trace(go.Scatter(x=sub_df.index, y=sub_df['acceleration'], name='Aceleração', line=dict(color='#e67e22', width=1.5, dash='dot')), row=2, col=1)
    
    # Highlight continuous regime background zones on Subplot 1
    zones = []
    current_reg = None
    start_idx = None
    
    for idx, r in sub_df.iterrows():
        reg = r['regime']
        if reg != current_reg:
            if current_reg is not None:
                zones.append((start_idx, idx - 1, current_reg))
            current_reg = reg
            start_idx = idx
    if current_reg is not None:
        zones.append((start_idx, len(sub_df) - 1, current_reg))
        
    colors_map = {
        "BULL": "rgba(46, 204, 113, 0.12)",
        "BEAR": "rgba(231, 76, 60, 0.12)",
        "LATERAL": "rgba(241, 196, 15, 0.08)",
        "CAOTICO": "rgba(155, 89, 182, 0.12)"
    }
    
    for start, end, reg in zones:
        fig.add_vrect(
            x0=start, x1=end,
            fillcolor=colors_map.get(reg, "rgba(0,0,0,0)"),
            opacity=1.0,
            layer="below",
            line_width=0,
            row=1, col=1
        )
        
    fig.update_layout(
        height=600,
        margin=dict(l=10, r=10, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor='rgba(255,255,255,0.95)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#e2e8f0', title="Número de Batimentos (t)"),
        yaxis=dict(showgrid=True, gridcolor='#e2e8f0', title="Preço"),
        xaxis2=dict(showgrid=True, gridcolor='#e2e8f0', title="Batimentos (t)"),
        yaxis2=dict(showgrid=True, gridcolor='#e2e8f0', title="Derivadas")
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 5. Live Bloomberg Reversed Table (Reversed view: latest at top)
    st.subheader("📜 Registo Detalhado de Variáveis (Real-time)")
    
    rev_sub_df = sub_df.iloc[::-1].copy()
    rev_sub_df['Preço'] = rev_sub_df['price'].map(lambda x: f"{x:.2f}")
    rev_sub_df['Velocidade'] = rev_sub_df['velocity'].map(lambda x: f"{x:+.4f}" if not pd.isna(x) else "")
    rev_sub_df['Aceleração'] = rev_sub_df['acceleration'].map(lambda x: f"{x:+.4f}" if not pd.isna(x) else "")
    rev_sub_df['Volatilidade'] = rev_sub_df['volatility'].map(lambda x: f"{x:.4f}" if not pd.isna(x) else "")
    rev_sub_df['Stretching'] = rev_sub_df['stretching'].map(lambda x: f"{x:.2f}%" if not pd.isna(x) else "")
    rev_sub_df['Regime'] = rev_sub_df['regime']
    rev_sub_df['Batimento'] = rev_sub_df.index
    
    display_cols = ['Batimento', 'Preço', 'Velocidade', 'Aceleração', 'Volatilidade', 'Stretching', 'Regime']
    
    styled_view = rev_sub_df[display_cols].style
    styled_view = apply_styler(styled_view, 'Regime')
    
    st.dataframe(styled_view, use_container_width=True, height=250)

    # 6. Auto-Miner: Retrospective Structural Analysis
    st.markdown("---")
    st.markdown("## 🔍 Auto-Miner Quântico de Padrões & Regras de Ouro")
    st.markdown("O Minerador de Padrões vasculha **toda a série temporal activa** (não apenas a simulação em tempo real) para extrair reversões de tendência estruturais e mapear as condições iniciais de lucro.")
    
    fundos_list, topos_list = find_structural_points(df)
    
    # Sub-abas para os 5 relatórios simultâneos
    tab_all, tab_bull, tab_bear, tab_lateral, tab_caotico = st.tabs([
        "🌐 Geral (Todos)", 
        "📈 Regime BULL", 
        "📉 Regime BEAR", 
        "↔️ Regime LATERAL", 
        "🌀 Regime CAÓTICO"
    ])
    
    regimes_mapping = [
        (tab_all, "Todos"),
        (tab_bull, "BULL"),
        (tab_bear, "BEAR"),
        (tab_lateral, "LATERAL"),
        (tab_caotico, "CAOTICO")
    ]
    
    for tab_obj, reg_val in regimes_mapping:
        with tab_obj:
            opp_df = get_pattern_stats(fundos_list, df, reg_val)
            thr_df = get_pattern_stats(topos_list, df, reg_val)
            
            show_golden_rules(opp_df, thr_df, reg_val)
            
            col_tab1, col_tab2 = st.columns(2)
            
            with col_tab1:
                st.markdown(f"##### 💚 Oportunidades de Compra (Fundos de Ouro - {len(opp_df)} Encontradas)")
                if not opp_df.empty:
                    opp_df_disp = opp_df.drop(columns=["var_raw"])
                    styled_opp = opp_df_disp.style
                    styled_opp = apply_styler(styled_opp, 'Regime Inicial')
                    st.dataframe(styled_opp, use_container_width=True, height=350)
                else:
                    st.info(f"Sem fundos estruturais para o regime {reg_val}.")
                    
            with col_tab2:
                st.markdown(f"##### 💔 Ameaças de Venda (Topos de Alerta - {len(thr_df)} Encontradas)")
                if not thr_df.empty:
                    thr_df_disp = thr_df.drop(columns=["var_raw"])
                    styled_thr = thr_df_disp.style
                    styled_thr = apply_styler(styled_thr, 'Regime Inicial')
                    st.dataframe(styled_thr, use_container_width=True, height=350)
                else:
                    st.info(f"Sem topos estruturais para o regime {reg_val}.")
# 7. Módulo de Persistência de Testes
    st.markdown("---")
    st.markdown("### 💾 Registar Conclusões do Teste para o Bot")
    st.markdown("Guarda as regras estatísticas de ouro geradas nesta simulação para acumulá-las no Cérebro do Bot.")
    
    col_save1, col_save2 = st.columns([3, 1])
    with col_save1:
        test_name_input = st.text_input("Nome do Teste / Ativo (ex: BTC-USD Alta Volatilidade)", placeholder="Insira o nome para identificar este teste...", key="math_test_name_input")
    with col_save2:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("💾 Guardar Conclusões", use_container_width=True, key="math_save_test_btn"):
            if test_name_input.strip() == "":
                st.error("Por favor, insira um nome válido para o teste.")
            else:
                save_current_test_rules(test_name_input.strip(), df, fundos_list, topos_list)
                st.success(f"Teste '{test_name_input}' guardado com sucesso no historial!")
                st.rerun()

    # 8. Cérebro de Consenso & Inteligência do Bot
    st.markdown("---")
    st.markdown("## 🧠 Cérebro de Consenso do Bot")
    st.markdown("Selecione os testes guardados no historial para gerar o DNA unificado e livre de contradições do Bot.")
    
    render_consensus_engine()

    # 9. Loop de Simulação
    if st.session_state.math_running:
        time.sleep(step_delay)
        if st.session_state.math_step < len(df) - 1:
            st.session_state.math_step += 1
            st.rerun()
        else:
            st.session_state.math_running = False
            st.success("Simulação terminada! Toda a série foi processada.")
            st.rerun()

def show_golden_rules(filtered_opp, filtered_thr, selected_regime):
    st.markdown("### 🏆 Conclusões de Ouro (Intervalos Sagrados)")
    
    p2 = st.session_state.get('math_active_sma_p2', 5)
    p3 = st.session_state.get('math_active_sma_p3', 13)
    p4 = st.session_state.get('math_active_sma_p4', 21)
    p5 = st.session_state.get('math_active_sma_p5', 55)
    p6 = st.session_state.get('math_active_sma_p6', 144)
    
    col_p2 = f"Média {p2}"
    col_p3 = f"Média {p3}"
    col_p4 = f"Média {p4}"
    col_p5 = f"Média {p5}"
    col_p6 = f"Média {p6}"
    
    opp_msg = ""
    opp_geo_msg = ""
    if filtered_opp.empty:
        opp_msg = f"Sem dados suficientes para minerar padrões de compra no regime {selected_regime}."
    else:
        acc_m = filtered_opp["Aceleração"].astype(float).mean()
        strt_m = filtered_opp["Stretching"].astype(float).mean()
        acc_min = filtered_opp["Aceleração"].astype(float).min()
        acc_max = filtered_opp["Aceleração"].astype(float).max()
        
        opp_msg = f"As reversões de alta no regime **{selected_regime}** ocorrem com uma **Aceleração média de {acc_m:+.4f}** (entre {acc_min:+.4f} e {acc_max:+.4f}) e um **Stretching médio de {strt_m:.2f}%**."
        
        if col_p2 in filtered_opp.columns and col_p3 in filtered_opp.columns:
            sma2 = pd.to_numeric(filtered_opp[col_p2], errors='coerce')
            sma3 = pd.to_numeric(filtered_opp[col_p3], errors='coerce')
            sma4 = pd.to_numeric(filtered_opp[col_p4], errors='coerce')
            sma5 = pd.to_numeric(filtered_opp[col_p5], errors='coerce')
            sma6 = pd.to_numeric(filtered_opp[col_p6], errors='coerce')
            
            # Tensão e dispersão médias
            mola_vals = filtered_opp["Compressão Mola %"].str.rstrip("%").replace('', '0').astype(float)
            mola_m = mola_vals.mean()
            
            disp_vals = filtered_opp["Disp. Vetorial %"].str.rstrip("%").replace('', '0').astype(float)
            disp_m = disp_vals.mean()
            
            infil_rate = (filtered_opp["Infiltração"] == "Sim").mean() * 100
            reteste_rate = (filtered_opp["Reteste Gravitacional"] == "Sim").mean() * 100
            
            opp_geo_msg = f"📐 **Assinatura Geométrica da Reversão:**\n"
            opp_geo_msg += f"• **Dispersão Vetorial (Mola):** {disp_m:+.2f}% de esticamento médio.\n"
            opp_geo_msg += f"• **Compressão de Feixe (Coesão):** {mola_m:.2f}% (linhas muito juntas).\n"
            opp_geo_msg += f"• **Taxa de Infiltração Fractal:** {infil_rate:.1f}% das vezes (sinal antecipado de micro-tempo).\n"
            opp_geo_msg += f"• **Taxa de Reteste Gravitacional:** {reteste_rate:.1f}% das vezes (ricochete no trampolim de suporte)."
            
    thr_msg = ""
    thr_geo_msg = ""
    if filtered_thr.empty:
        thr_msg = f"Sem dados suficientes para minerar padrões de venda/segurança no regime {selected_regime}."
    else:
        acc_m = filtered_thr["Aceleração"].astype(float).mean()
        strt_m = filtered_thr["Stretching"].astype(float).mean()
        acc_min = filtered_thr["Aceleração"].astype(float).min()
        acc_max = filtered_thr["Aceleração"].astype(float).max()
        
        thr_msg = f"As reversões de queda no regime **{selected_regime}** ocorrem com uma **Aceleração média de {acc_m:+.4f}** (entre {acc_min:+.4f} e {acc_max:+.4f}) e um **Stretching médio de {strt_m:.2f}%**."
        
        if col_p2 in filtered_thr.columns and col_p3 in filtered_thr.columns:
            sma2 = pd.to_numeric(filtered_thr[col_p2], errors='coerce')
            sma3 = pd.to_numeric(filtered_thr[col_p3], errors='coerce')
            sma4 = pd.to_numeric(filtered_thr[col_p4], errors='coerce')
            sma5 = pd.to_numeric(filtered_thr[col_p5], errors='coerce')
            sma6 = pd.to_numeric(filtered_thr[col_p6], errors='coerce')
            
            mola_vals = filtered_thr["Compressão Mola %"].str.rstrip("%").replace('', '0').astype(float)
            mola_m = mola_vals.mean()
            
            disp_vals = filtered_thr["Disp. Vetorial %"].str.rstrip("%").replace('', '0').astype(float)
            disp_m = disp_vals.mean()
            
            infil_rate = (filtered_thr["Infiltração"] == "Sim").mean() * 100
            reteste_rate = (filtered_thr["Reteste Gravitacional"] == "Sim").mean() * 100
            
            thr_geo_msg = f"📐 **Assinatura Geométrica do Topo/Queda:**\n"
            thr_geo_msg += f"• **Dispersão Vetorial (Mola):** {disp_m:+.2f}% de dispersão no topo.\n"
            thr_geo_msg += f"• **Compressão de Feixe (Coesão):** {mola_m:.2f}%.\n"
            thr_geo_msg += f"• **Taxa de Infiltração Fractal:** {infil_rate:.1f}% das vezes.\n"
            thr_geo_msg += f"• **Taxa de Reteste Gravitacional:** {reteste_rate:.1f}% das vezes (quebra de trampolim)."

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'''
        <div class="glass-card" style="padding:20px; border-left: 5px solid #2ecc71; margin-bottom: 15px;">
            <h5 style="color:#2ecc71; margin-top:0;">💚 Oportunidades de Compra (Fundos)</h5>
            <p style="font-size: 14px; line-height: 1.5; color: #1e293b;">{opp_msg}</p>
        </div>
        ''', unsafe_allow_html=True)
        if opp_geo_msg:
            st.markdown(f'''
            <div class="glass-card" style="padding:20px; border-left: 5px solid #00B0FF; margin-bottom: 15px; background: rgba(0, 176, 255, 0.03);">
                <h5 style="color:#00B0FF; margin-top:0;">📐 Geometria Sagrada de Alta (Fibonacci)</h5>
                <p style="font-size: 13px; line-height: 1.5; color: #1e293b; white-space: pre-line;">{opp_geo_msg}</p>
            </div>
            ''', unsafe_allow_html=True)
            
    with col2:
        st.markdown(f'''
        <div class="glass-card" style="padding:20px; border-left: 5px solid #e74c3c; margin-bottom: 15px;">
            <h5 style="color:#e74c3c; margin-top:0;">💔 Sinais de Alerta (Queda)</h5>
            <p style="font-size: 14px; line-height: 1.5; color: #1e293b;">{thr_msg}</p>
        </div>
        ''', unsafe_allow_html=True)
        if thr_geo_msg:
            st.markdown(f'''
            <div class="glass-card" style="padding:20px; border-left: 5px solid #FFAB00; margin-bottom: 15px; background: rgba(255, 171, 0, 0.03);">
                <h5 style="color:#FFAB00; margin-top:0;">📐 Geometria Sagrada de Queda (Fibonacci)</h5>
                <p style="font-size: 13px; line-height: 1.5; color: #1e293b; white-space: pre-line;">{thr_geo_msg}</p>
            </div>
            ''', unsafe_allow_html=True)

import json
import os

def save_current_test_rules(test_name, df, fundos_list, topos_list):
    filepath = "bot_knowledge_base.json"
    
    # Carregar historial existente
    knowledge = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                knowledge = json.load(f)
        except Exception:
            knowledge = {}
            
    p2 = st.session_state.get('math_active_sma_p2', 5)
    p3 = st.session_state.get('math_active_sma_p3', 13)
    p4 = st.session_state.get('math_active_sma_p4', 21)
    p5 = st.session_state.get('math_active_sma_p5', 55)
    p6 = st.session_state.get('math_active_sma_p6', 144)
    
    regimes = ["Todos", "BULL", "BEAR", "LATERAL", "CAOTICO"]
    test_data = {
        "test_name": test_name,
        "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "smas": [p2, p3, p4, p5, p6],
        "regimes": {}
    }
    
    for reg in regimes:
        opp_df = get_pattern_stats(fundos_list, df, reg)
        thr_df = get_pattern_stats(topos_list, df, reg)
        
        reg_data = {
            "opp_count": len(opp_df),
            "thr_count": len(thr_df),
            "opp_stats": {},
            "thr_stats": {}
        }
        
        # BUY Stats
        if not opp_df.empty:
            mola_mean = 0.0
            if "Compressão Mola %" in opp_df.columns:
                mola_vals = opp_df["Compressão Mola %"].str.rstrip("%").replace('', '0').astype(float)
                mola_mean = float(mola_vals.mean())
                
            disp_mean = 0.0
            if "Disp. Vetorial %" in opp_df.columns:
                disp_vals = opp_df["Disp. Vetorial %"].str.rstrip("%").replace('', '0').astype(float)
                disp_mean = float(disp_vals.mean())
                
            infil_rate = 0.0
            if "Infiltração" in opp_df.columns:
                infil_rate = float((opp_df["Infiltração"] == "Sim").mean() * 100)
                
            reteste_rate = 0.0
            if "Reteste Gravitacional" in opp_df.columns:
                reteste_rate = float((opp_df["Reteste Gravitacional"] == "Sim").mean() * 100)
                
            reg_data["opp_stats"] = {
                "acc_mean": float(opp_df["Aceleração"].astype(float).mean()),
                "acc_std": float(opp_df["Aceleração"].astype(float).std()) if len(opp_df) > 1 else 0.0,
                "strt_mean": float(opp_df["Stretching"].astype(float).mean()),
                "strt_std": float(opp_df["Stretching"].astype(float).std()) if len(opp_df) > 1 else 0.0,
                "mola_mean": mola_mean,
                "disp_mean": disp_mean,
                "infil_rate": infil_rate,
                "reteste_rate": reteste_rate
            }
            
        # SELL Stats
        if not thr_df.empty:
            mola_mean = 0.0
            if "Compressão Mola %" in thr_df.columns:
                mola_vals = thr_df["Compressão Mola %"].str.rstrip("%").replace('', '0').astype(float)
                mola_mean = float(mola_vals.mean())
                
            disp_mean = 0.0
            if "Disp. Vetorial %" in thr_df.columns:
                disp_vals = thr_df["Disp. Vetorial %"].str.rstrip("%").replace('', '0').astype(float)
                disp_mean = float(disp_vals.mean())
                
            infil_rate = 0.0
            if "Infiltração" in thr_df.columns:
                infil_rate = float((thr_df["Infiltração"] == "Sim").mean() * 100)
                
            reteste_rate = 0.0
            if "Reteste Gravitacional" in thr_df.columns:
                reteste_rate = float((thr_df["Reteste Gravitacional"] == "Sim").mean() * 100)
                
            reg_data["thr_stats"] = {
                "acc_mean": float(thr_df["Aceleração"].astype(float).mean()),
                "acc_std": float(thr_df["Aceleração"].astype(float).std()) if len(thr_df) > 1 else 0.0,
                "strt_mean": float(thr_df["Stretching"].astype(float).mean()),
                "strt_std": float(thr_df["Stretching"].astype(float).std()) if len(thr_df) > 1 else 0.0,
                "mola_mean": mola_mean,
                "disp_mean": disp_mean,
                "infil_rate": infil_rate,
                "reteste_rate": reteste_rate
            }
            
        test_data["regimes"][reg] = reg_data
        
    knowledge[test_name] = test_data
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(knowledge, f, indent=2, ensure_ascii=False)


def render_consensus_engine():
    filepath = "bot_knowledge_base.json"
    dna_path = "bot_consensus_dna.json"
    
    if not os.path.exists(filepath):
        st.info("Nenhum teste guardado no historial. Execute uma simulação e clique em 'Guardar Conclusões' acima para começar a acumular conhecimento.")
        return
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            knowledge = json.load(f)
    except Exception:
        st.error("Erro ao ler a base de dados de testes. O ficheiro pode estar corrompido.")
        return
        
    if not knowledge:
        st.info("O historial de testes está vazio.")
        return
        
    # 📚 Tabela de Historial de Lições / Regras
    st.subheader("📚 Historial de Lições Guardadas (Base de Conhecimento)")
    st.markdown("Esta tabela lista todos os exames estatísticos efetuados e guardados em disco, permitindo ao Bot acumular inteligência de múltiplos mercados.")
    
    records = []
    for t_name, t_data in knowledge.items():
        smas_str = ", ".join(map(str, t_data.get("smas", [])))
        # Contagem de fundos e topos totais somados por todos os regimes
        opp_total = sum(reg_data.get("opp_count", 0) for reg_data in t_data.get("regimes", {}).values() if isinstance(reg_data, dict))
        thr_total = sum(reg_data.get("thr_count", 0) for reg_data in t_data.get("regimes", {}).values() if isinstance(reg_data, dict))
        
        records.append({
            "Nome do Teste / Ativo": t_name,
            "Data/Hora": t_data.get("timestamp", ""),
            "Médias Móveis (SMAs)": smas_str,
            "Total Fundos": opp_total,
            "Total Topos": thr_total
        })
        
    df_lessons = pd.DataFrame(records)
    st.dataframe(df_lessons, use_container_width=True, hide_index=True)
    
    col_hist1, col_hist2 = st.columns([1, 3])
    with col_hist1:
        if st.button("🗑️ Limpar Historial", use_container_width=True, key="math_clear_history_btn"):
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass
            st.success("Historial de lições limpo!")
            st.rerun()
            
    st.markdown("---")
    st.subheader("🧬 Cérebro de Consenso & DNA Unificado")
    st.markdown("Selecione quais as lições do historial que deseja unificar no Cérebro de Consenso do Bot:")
    
    # Multi-select of tests
    test_options = list(knowledge.keys())
    selected_tests = st.multiselect("Selecione os testes para integrar no Cérebro do Bot:", options=test_options, default=test_options[-1:])
    
    if not selected_tests:
        st.warning("Selecione pelo menos um teste para iniciar a consolidação de consenso.")
        return
        
    # 🔍 Botão para Analisar Contradições nas Regras
    st.markdown("---")
    st.markdown("### ⚖️ Analisador de Contradições Cruzadas")
    st.markdown("Compara as regras extraídas de diferentes sessões de treino para detetar conflitos de sinal ou desvios de volatilidade incompatíveis.")
    
    col_an1, col_an2 = st.columns([1, 2])
    with col_an1:
        run_analysis = st.button("🔍 Analisar Contradições nas Regras", use_container_width=True, key="math_run_contradictions_analysis")
        
    if run_analysis:
        if len(selected_tests) < 2:
            st.info("💡 **Dica:** Selecione pelo menos 2 testes no multi-select acima para realizar uma análise comparativa de contradições!")
        else:
            st.markdown("#### 📋 Relatório de Consistência das Regras")
            
            # Agrupar testes que pertencem ao mesmo mercado
            market_groups = {}
            for t_name in selected_tests:
                # Detect base name
                base_market = "Outros Mercados"
                for keyword in ["Didatico Classico", "Didático Clássico", "Montanha Russa", "Flash Crash", "Lateralização", "Lateralizacao"]:
                    if keyword.lower() in t_name.lower():
                        base_market = keyword
                        break
                if base_market not in market_groups:
                    market_groups[base_market] = []
                market_groups[base_market].append(t_name)
            
            # Analisar contradições de sinal
            has_any_conflict = False
            regimes = ["BULL", "BEAR", "LATERAL", "CAOTICO"]
            
            for m_type, t_names in market_groups.items():
                if len(t_names) < 2:
                    continue
                
                st.markdown(f"##### 🎯 Comparação de Regras no Mercado: **{m_type}** ({len(t_names)} treinos)")
                
                # Para cada regime, comparar os valores de Compra e Venda
                for reg in regimes:
                    reg_conflicts = []
                    reg_stable = []
                    
                    # Variáveis a verificar
                    metrics = [
                        ("acc_mean", "Aceleração Média"),
                        ("strt_mean", "Stretching Médio"),
                        ("mola_mean", "Coesão da Mola"),
                        ("disp_mean", "Dispersão Vetorial")
                    ]
                    
                    # BUY stats
                    for metric_key, metric_name in metrics:
                        vals = []
                        tests_with_val = []
                        for t_name in t_names:
                            reg_data = knowledge[t_name]["regimes"].get(reg, {})
                            opp_c = reg_data.get("opp_count", 0)
                            opp_s = reg_data.get("opp_stats", {})
                            if opp_c > 0 and metric_key in opp_s:
                                vals.append(opp_s[metric_key])
                                tests_with_val.append((t_name, opp_s[metric_key]))
                        
                        if len(vals) >= 2:
                            # Verificar se há inversão de sinal
                            has_pos = any(x > 0.0001 for x in vals)
                            has_neg = any(x < -0.0001 for x in vals)
                            if has_pos and has_neg:
                                conflict_desc = " vs ".join([f"'{t}': {v:+.4f}" for t, v in tests_with_val])
                                reg_conflicts.append(f"⚠️ **{metric_name} (Compra):** Sinais contraditórios! {conflict_desc}")
                            else:
                                reg_stable.append(metric_name)
                                
                    # SELL stats
                    for metric_key, metric_name in metrics:
                        vals = []
                        tests_with_val = []
                        for t_name in t_names:
                            reg_data = knowledge[t_name]["regimes"].get(reg, {})
                            thr_c = reg_data.get("thr_count", 0)
                            thr_s = reg_data.get("thr_stats", {})
                            if thr_c > 0 and metric_key in thr_s:
                                vals.append(thr_s[metric_key])
                                tests_with_val.append((t_name, thr_s[metric_key]))
                        
                        if len(vals) >= 2:
                            has_pos = any(x > 0.0001 for x in vals)
                            has_neg = any(x < -0.0001 for x in vals)
                            if has_pos and has_neg:
                                conflict_desc = " vs ".join([f"'{t}': {v:+.4f}" for t, v in tests_with_val])
                                reg_conflicts.append(f"⚠️ **{metric_name} (Venda):** Sinais contraditórios! {conflict_desc}")
                            else:
                                reg_stable.append(metric_name)
                    
                    if reg_conflicts:
                        has_any_conflict = True
                        st.markdown(f"###### ⚠️ Conflitos Detetados no Regime {reg}:")
                        for conf in reg_conflicts:
                            st.error(conf)
                    elif reg_stable:
                        st.success(f"✅ **Regime {reg} Estável:** As regras de {', '.join(reg_stable)} são perfeitamente consistentes entre todos os treinos deste mercado.")
            
            if not has_any_conflict:
                st.success("🎉 **Historial de Consenso Impecável!** Executámos uma análise cruzada de todos os mercados selecionados e **não encontrámos qualquer contradição lógica de sinais** nas assinaturas geométricas. O Bot pode operar de forma perfeitamente harmonizada.")

    st.markdown("---")
    st.markdown("### 🧬 Análise de Consenso e Estabilidade das Variáveis")
    
    # Agrupar dados por regime
    regimes = ["BULL", "BEAR", "LATERAL", "CAOTICO"]
    consensus_dna = {}
    
    # Vamos criar abas para ver o consenso em cada regime
    tabs_reg = st.tabs([f"🎯 Regime {r}" for r in regimes])
    
    for tab_obj, reg in zip(tabs_reg, regimes):
        with tab_obj:
            opp_samples = 0
            thr_samples = 0
            
            # Listas para coletar valores de cada teste para verificação de estabilidade
            opp_acc_list, opp_strt_list, opp_mola_list, opp_disp_list = [], [], [], []
            thr_acc_list, thr_strt_list, thr_mola_list, thr_disp_list = [], [], [], []
            
            opp_weighted_acc, opp_weighted_strt, opp_weighted_mola, opp_weighted_disp = 0.0, 0.0, 0.0, 0.0
            thr_weighted_acc, thr_weighted_strt, thr_weighted_mola, thr_weighted_disp = 0.0, 0.0, 0.0, 0.0
            
            opp_infil_weighted, opp_reteste_weighted = 0.0, 0.0
            thr_infil_weighted, thr_reteste_weighted = 0.0, 0.0
            
            for t_name in selected_tests:
                t_data = knowledge[t_name]
                reg_data = t_data["regimes"].get(reg, {})
                if not reg_data:
                    continue
                    
                opp_c = reg_data.get("opp_count", 0)
                thr_c = reg_data.get("thr_count", 0)
                
                # BUY stats
                opp_s = reg_data.get("opp_stats", {})
                if opp_c > 0 and opp_s:
                    opp_samples += opp_c
                    opp_acc_list.append(opp_s["acc_mean"])
                    opp_strt_list.append(opp_s["strt_mean"])
                    opp_mola_list.append(opp_s.get("mola_mean", 0.0))
                    opp_disp_list.append(opp_s.get("disp_mean", 0.0))
                    
                    opp_weighted_acc += opp_s["acc_mean"] * opp_c
                    opp_weighted_strt += opp_s["strt_mean"] * opp_c
                    opp_weighted_mola += opp_s.get("mola_mean", 0.0) * opp_c
                    opp_weighted_disp += opp_s.get("disp_mean", 0.0) * opp_c
                    opp_infil_weighted += opp_s.get("infil_rate", 0.0) * opp_c
                    opp_reteste_weighted += opp_s.get("reteste_rate", 0.0) * opp_c
                    
                # SELL stats
                thr_s = reg_data.get("thr_stats", {})
                if thr_c > 0 and thr_s:
                    thr_samples += thr_c
                    thr_acc_list.append(thr_s["acc_mean"])
                    thr_strt_list.append(thr_s["strt_mean"])
                    thr_mola_list.append(thr_s.get("mola_mean", 0.0))
                    thr_disp_list.append(thr_s.get("disp_mean", 0.0))
                    
                    thr_weighted_acc += thr_s["acc_mean"] * thr_c
                    thr_weighted_strt += thr_s["strt_mean"] * thr_c
                    thr_weighted_mola += thr_s.get("mola_mean", 0.0) * thr_c
                    thr_weighted_disp += thr_s.get("disp_mean", 0.0) * thr_c
                    thr_infil_weighted += thr_s.get("infil_rate", 0.0) * thr_c
                    thr_reteste_weighted += thr_s.get("reteste_rate", 0.0) * thr_c
            
            # Calcular médias ponderadas finais
            opp_final_acc = opp_weighted_acc / opp_samples if opp_samples > 0 else 0.0
            opp_final_strt = opp_weighted_strt / opp_samples if opp_samples > 0 else 0.0
            opp_final_mola = opp_weighted_mola / opp_samples if opp_samples > 0 else 0.0
            opp_final_disp = opp_weighted_disp / opp_samples if opp_samples > 0 else 0.0
            opp_final_infil = opp_infil_weighted / opp_samples if opp_samples > 0 else 0.0
            opp_final_reteste = opp_reteste_weighted / opp_samples if opp_samples > 0 else 0.0
            
            thr_final_acc = thr_weighted_acc / thr_samples if thr_samples > 0 else 0.0
            thr_final_strt = thr_weighted_strt / thr_samples if thr_samples > 0 else 0.0
            thr_final_mola = thr_weighted_mola / thr_samples if thr_samples > 0 else 0.0
            thr_final_disp = thr_weighted_disp / thr_samples if thr_samples > 0 else 0.0
            thr_final_infil = thr_infil_weighted / thr_samples if thr_samples > 0 else 0.0
            thr_final_reteste = thr_reteste_weighted / thr_samples if thr_samples > 0 else 0.0

            # --- FILTRO DE CONTRADIÇÃO AUTOMÁTICO ---
            def check_stability(lst):
                if not lst:
                    return True
                has_pos = any(x > 0.0001 for x in lst)
                has_neg = any(x < -0.0001 for x in lst)
                return not (has_pos and has_neg)
                
            opp_acc_stable = check_stability(opp_acc_list)
            opp_strt_stable = check_stability(opp_strt_list)
            opp_mola_stable = check_stability(opp_mola_list)
            opp_disp_stable = check_stability(opp_disp_list)
            
            thr_acc_stable = check_stability(thr_acc_list)
            thr_strt_stable = check_stability(thr_strt_list)
            thr_mola_stable = check_stability(thr_mola_list)
            thr_disp_stable = check_stability(thr_disp_list)
            
            # Exibir Métricas de Compra (BUY)
            st.markdown(f"#### 💚 Gatilhos de Entrada (BUY) - Consenso Baseado em {opp_samples} Fundos")
            if opp_samples == 0:
                st.warning("Sem dados de compra suficientes nos testes selecionados.")
            else:
                col_b1, col_b2, col_b3, col_b4 = st.columns(4)
                
                with col_b1:
                    if opp_strt_stable:
                        st.metric("Stretching Médio", f"{opp_final_strt:+.2f}%", help="Estabilidade: Excelente")
                    else:
                        st.metric("Stretching Médio", "Rejeitado", delta="Contradição!", delta_color="inverse", help="Instável: Sinais contraditórios entre testes.")
                        
                with col_b2:
                    if opp_mola_stable:
                        st.metric("Coesão da Mola", f"{opp_final_mola:.2f}%", help="Estabilidade: Excelente")
                    else:
                        st.metric("Coesão da Mola", "Rejeitado", delta="Contradição!", delta_color="inverse")
                        
                with col_b3:
                    if opp_disp_stable:
                        st.metric("Disp. Vetorial", f"{opp_final_disp:+.2f}%")
                    else:
                        st.metric("Disp. Vetorial", "Rejeitado", delta="Contradição!", delta_color="inverse")
                        
                with col_b4:
                    if opp_acc_stable:
                        st.metric("Aceleração Média", f"{opp_final_acc:+.4f}")
                    else:
                        st.metric("Aceleração Média", "Rejeitado", delta="Contradição!", delta_color="inverse")
                        
                st.markdown(f"* **Infiltração Bull Média:** {opp_final_infil:.1f}% das vezes. | **Reteste Gravitacional Médio:** {opp_final_reteste:.1f}% das vezes.")
                
            # Exibir Métricas de Venda (SELL)
            st.markdown(f"#### 💔 Gatilhos de Saída/Alerta (SELL) - Consenso Baseado em {thr_samples} Topos")
            if thr_samples == 0:
                st.warning("Sem dados de venda suficientes nos testes selecionados.")
            else:
                col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                
                with col_s1:
                    if thr_strt_stable:
                        st.metric("Stretching Médio", f"{thr_final_strt:+.2f}%")
                    else:
                        st.metric("Stretching Médio", "Rejeitado", delta="Contradição!", delta_color="inverse")
                        
                with col_s2:
                    if thr_mola_stable:
                        st.metric("Coesão da Mola", f"{thr_final_mola:.2f}%")
                    else:
                        st.metric("Coesão da Mola", "Rejeitado", delta="Contradição!", delta_color="inverse")
                        
                with col_s3:
                    if thr_disp_stable:
                        st.metric("Disp. Vetorial", f"{thr_final_disp:+.2f}%")
                    else:
                        st.metric("Disp. Vetorial", "Rejeitado", delta="Contradição!", delta_color="inverse")
                        
                with col_s4:
                    if thr_acc_stable:
                        st.metric("Aceleração Média", f"{thr_final_acc:+.4f}")
                    else:
                        st.metric("Aceleração Média", "Rejeitado", delta="Contradição!", delta_color="inverse")
                        
                st.markdown(f"* **Infiltração Bear Média:** {thr_final_infil:.1f}% das vezes. | **Reteste Gravitacional Médio:** {thr_final_reteste:.1f}% das vezes.")
            
            # Construir Ficha de DNA para Gravação
            consensus_dna[reg] = {
                "active": True,
                "opp_samples": opp_samples,
                "thr_samples": thr_samples,
                "buy_rules": {
                    "stretching": {
                        "stable": bool(opp_strt_stable),
                        "mean": float(opp_final_strt),
                        "min_limit": float(opp_final_strt - 1.5) if opp_strt_stable else None,
                        "max_limit": float(opp_final_strt + 1.5) if opp_strt_stable else None
                    },
                    "mola": {
                        "stable": bool(opp_mola_stable),
                        "mean": float(opp_final_mola),
                        "max_limit": float(opp_final_mola * 1.3) if opp_mola_stable else None
                    },
                    "disp": {
                        "stable": bool(opp_disp_stable),
                        "mean": float(opp_final_disp),
                        "max_limit": float(opp_final_disp * 1.1) if opp_disp_stable else None
                    },
                    "acceleration": {
                        "stable": bool(opp_acc_stable),
                        "mean": float(opp_final_acc)
                    },
                    "infil": {
                        "rate": float(opp_final_infil),
                        "active": bool(opp_final_infil > 50.0)
                    },
                    "reteste": {
                        "rate": float(opp_final_reteste),
                        "active": bool(opp_final_reteste > 40.0)
                    }
                },
                "sell_rules": {
                    "stretching": {
                        "stable": bool(thr_strt_stable),
                        "mean": float(thr_final_strt),
                        "min_limit": float(thr_final_strt - 1.5) if thr_strt_stable else None,
                        "max_limit": float(thr_final_strt + 1.5) if thr_strt_stable else None
                    },
                    "mola": {
                        "stable": bool(thr_mola_stable),
                        "mean": float(thr_final_mola)
                    },
                    "disp": {
                        "stable": bool(thr_disp_stable),
                        "mean": float(thr_final_disp),
                        "limit": float(thr_final_disp * 0.9) if thr_disp_stable else None
                    },
                    "acceleration": {
                        "stable": bool(thr_acc_stable),
                        "mean": float(thr_final_acc)
                    }
                }
            }

    # Gravar o DNA
    st.markdown("---")
    if st.button("💾 Gravar Consenso DNA Activo no Bot", type="primary", use_container_width=True, key="math_save_dna_btn"):
        try:
            p2 = st.session_state.get('math_active_sma_p2', 5)
            p3 = st.session_state.get('math_active_sma_p3', 13)
            p4 = st.session_state.get('math_active_sma_p4', 21)
            p5 = st.session_state.get('math_active_sma_p5', 55)
            p6 = st.session_state.get('math_active_sma_p6', 144)
            
            full_dna = {
                "smas": [p2, p3, p4, p5, p6],
                "regimes": consensus_dna,
                "last_updated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                "selected_tests": selected_tests
            }
            
            with open(dna_path, "w", encoding="utf-8") as f:
                json.dump(full_dna, f, indent=2, ensure_ascii=False)
                
            st.toast("🧠 Cérebro de Consenso DNA gravado com sucesso!")
        except Exception as e:
            st.error(f"Erro ao gravar o DNA Consolidado: {e}")
