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
    p2 = st.session_state.get('math_sma_p2', 9)
    p3 = st.session_state.get('math_sma_p3', 21)
    p4 = st.session_state.get('math_sma_p4', 50)
    p5 = st.session_state.get('math_sma_p5', 200)
    p6 = st.session_state.get('math_sma_p6', 350)
    
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
    records = []
    for pt in points_list:
        idx = pt.get("idx_fundo") if "idx_fundo" in pt else pt.get("idx_topo")
        if idx is None or idx >= len(df):
            continue
        row = df.iloc[idx]
        regime = row.get("regime", "LATERAL")
        
        if regime_filter and regime_filter != "Todos" and regime != regime_filter:
            continue
            
        records.append({
            "Batimento Inicial": idx,
            "Preço Inicial": f"{row['price']:.2f}",
            "Batimento Final": pt.get("idx_topo") if "idx_fundo" in pt else pt.get("idx_fundo"),
            "Preço Final": f"{pt.get('price_topo'):.2f}" if "idx_fundo" in pt else f"{pt.get('price_fundo'):.2f}",
            "Variação %": f"{pt.get('gain_pct'):+.2f}%" if "idx_fundo" in pt else f"-{pt.get('loss_pct'):.2f}%",
            "var_raw": pt.get('gain_pct') if 'idx_fundo' in pt else -pt.get('loss_pct'),
            "Velocidade": row["velocity"],
            "Aceleração": row["acceleration"],
            "Stretching": row["stretching"],
            "Regime Inicial": regime
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
        <h1 style='margin:0; font-size: 2.2rem;'>📐 Laboratório Matemático & Regimes Adaptativos</h1>
        <p style='margin: 5px 0 0 0; opacity: 0.8;'>Simulador quântico de regimes de mercado, derivadas e mineração de padrões estatísticos em tempo real.</p>
    </div>
    """, unsafe_allow_html=True)
    
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
    
    # Custom SMA parameter session states
    if 'math_sma_p2' not in st.session_state: st.session_state.math_sma_p2 = 9
    if 'math_sma_p3' not in st.session_state: st.session_state.math_sma_p3 = 21
    if 'math_sma_p4' not in st.session_state: st.session_state.math_sma_p4 = 50
    if 'math_sma_p5' not in st.session_state: st.session_state.math_sma_p5 = 200
    if 'math_sma_p6' not in st.session_state: st.session_state.math_sma_p6 = 350
    
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
        st.subheader("📈 Vetor de Médias Móveis")
        st.session_state.math_sma_p2 = st.slider("Média Rápida (P2)", 2, 20, int(st.session_state.math_sma_p2))
        st.session_state.math_sma_p3 = st.slider("Média Curta (P3)", 21, 40, int(st.session_state.math_sma_p3))
        st.session_state.math_sma_p4 = st.slider("Média Média (P4)", 41, 100, int(st.session_state.math_sma_p4))
        st.session_state.math_sma_p5 = st.slider("Média Longa (P5)", 101, 250, int(st.session_state.math_sma_p5))
        st.session_state.math_sma_p6 = st.slider("Super Longa (P6)", 251, 500, int(st.session_state.math_sma_p6))
        
        # Re-calculate when SMA parameters change
        if st.button("Aplicar Parâmetros de SMA"):
            recalculate_math_df()
            st.rerun()
            
    with col_sim:
        st.subheader("🎮 Controlo de Batimentos")
        
        # Play/Pause toggle
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
        
        # Export data as CSV
        df_full = st.session_state.math_df
        csv_buffer = io.StringIO()
        df_full.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        st.download_button(
            label="💾 Exportar Toda a Série (CSV)",
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
    
    p2 = st.session_state.math_sma_p2
    p3 = st.session_state.math_sma_p3
    p4 = st.session_state.math_sma_p4
    p5 = st.session_state.math_sma_p5
    p6 = st.session_state.math_sma_p6
    
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
    st.markdown("## 📐 Auto-Miner Quântico de Padrões & Regras de Ouro")
    st.markdown("O Minerador de Padrões vasculha **toda a série temporal ativa** (não apenas a simulação em tempo real) para extrair reversões de tendência estruturais e mapear as condições iniciais de lucro.")
    
    fundos_list, topos_list = find_structural_points(df)
    
    # Interactive Regime Filtering for mining
    regime_filter = st.selectbox("Filtrar Coorte Estatística por Regime Inicial", ["Todos", "BULL", "BEAR", "LATERAL", "CAOTICO"])
    
    opp_df = get_pattern_stats(fundos_list, df, regime_filter)
    thr_df = get_pattern_stats(topos_list, df, regime_filter)
    
    # 7. Render Conclusões de Ouro (Intervalos Sagrados)
    show_golden_rules(opp_df, thr_df, regime_filter)
    
    # Render Tables
    col_tab1, col_tab2 = st.columns(2)
    
    with col_tab1:
        st.markdown(f"##### 🟢 Tabela de Oportunidades de Compra (Fundos de Ouro - {len(opp_df)} Encontradas)")
        if not opp_df.empty:
            opp_df_disp = opp_df.drop(columns=["var_raw"])
            styled_opp = opp_df_disp.style
            styled_opp = apply_styler(styled_opp, 'Regime Inicial')
            st.dataframe(styled_opp, use_container_width=True, height=350)
        else:
            st.info("Sem fundos estruturais para o regime selecionado.")
            
    with col_tab2:
        st.markdown(f"##### 🔴 Tabela de Ameaças de Venda (Topos de Alerta - {len(thr_df)} Encontradas)")
        if not thr_df.empty:
            thr_df_disp = thr_df.drop(columns=["var_raw"])
            styled_thr = thr_df_disp.style
            styled_thr = apply_styler(styled_thr, 'Regime Inicial')
            st.dataframe(styled_thr, use_container_width=True, height=350)
        else:
            st.info("Sem topos estruturais para o regime selecionado.")

    # 8. Loop de Simulação
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
    
    if filtered_opp.empty:
        opp_msg = f"Sem dados suficientes para minerar padrões de compra no regime {selected_regime}."
    else:
        vel_m = filtered_opp["Velocidade"].astype(float).mean()
        acc_m = filtered_opp["Aceleração"].astype(float).mean()
        strt_m = filtered_opp["Stretching"].astype(float).mean()
        acc_min = filtered_opp["Aceleração"].astype(float).min()
        acc_max = filtered_opp["Aceleração"].astype(float).max()
        opp_msg = f"""
        **🟢 Padrão Oculto de Alta (Gatilho de Compra):**
        No regime **{selected_regime}**, as reversões de alta começam tipicamente com uma **Aceleração média de {acc_m:+.4f}** (intervalo de {acc_min:+.4f} a {acc_max:+.4f}) e um **Stretching médio de {strt_m:.2f}%**.
        
        *Regra Prática:* Se vires a Aceleração entrar no intervalo **[{acc_min:+.4f} a {acc_max:+.4f}]** com Stretching acima de **{strt_m*0.8:.2f}%**, a probabilidade de um movimento lucrativo é extremamente elevada!
        """
        
    if filtered_thr.empty:
        thr_msg = f"Sem dados suficientes para minerar padrões de venda/segurança no regime {selected_regime}."
    else:
        vel_m = filtered_thr["Velocidade"].astype(float).mean()
        acc_m = filtered_thr["Aceleração"].astype(float).mean()
        strt_m = filtered_thr["Stretching"].astype(float).mean()
        acc_min = filtered_thr["Aceleração"].astype(float).min()
        acc_max = filtered_thr["Aceleração"].astype(float).max()
        thr_msg = f"""
        **🔴 Filtro de Segurança (Prevenção de Perdas):**
        No regime **{selected_regime}**, as reversões de queda começam com uma **Aceleração média de {acc_m:+.4f}** (intervalo de {acc_min:+.4f} a {acc_max:+.4f}).
        
        *Regra Prática:* Se a aceleração ficar negativa ou entrar no intervalo **[{acc_min:+.4f} a {acc_max:+.4f}]**, o risco de derretimento é severo. Retira o capital ou evita posições longas!
        """
        
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="glass-card" style="padding:20px; border-left: 5px solid #2ecc71; margin-bottom: 15px;">
            <h5 style="color:#2ecc71; margin-top:0;">🟢 Sinais de Entrada (Alta)</h5>
            <p style="font-size: 14px; line-height: 1.5; color: #1e293b;">{opp_msg}</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="glass-card" style="padding:20px; border-left: 5px solid #e74c3c; margin-bottom: 15px;">
            <h5 style="color:#e74c3c; margin-top:0;">🔴 Sinais de Alerta (Queda)</h5>
            <p style="font-size: 14px; line-height: 1.5; color: #1e293b;">{thr_msg}</p>
        </div>
        """, unsafe_allow_html=True)
