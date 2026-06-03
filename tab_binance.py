import streamlit as st
import pandas as pd
import os
import json
import numpy as np

def render():
    st.markdown("## 🔶 Deploy Binance Futures - Paper Trading")
    st.markdown("Executa as estratégias testadas no laboratório diretamente na tua conta Binance Futures Testnet.")
    
    col_test1, col_test2 = st.columns([1, 2])
    with col_test1:
        test_btn = st.button("🔌 Testar Ligação", type="primary")
    
    with col_test2:
        if test_btn or st.session_state.get("binance_connected"):
            try:
                from binance_connector import test_connection
                ok, msg = test_connection()
                if ok:
                    st.success(msg)
                    st.session_state.binance_connected = True
                else:
                    st.error(msg)
                    st.session_state.binance_connected = False
            except ImportError:
                st.error("❌ binance_connector.py não encontrado.")
    
    if not st.session_state.get("binance_connected"):
        _show_env_help()
        return

    st.divider()

    try:
        from binance_connector import get_account, get_positions, get_orders, place_order, close_position
    except ImportError:
        st.error("Erro a importar binance_connector")
        return

    # Tabs internas para gestão
    t_dash, t_manual, t_bot = st.tabs(["📊 Dashboard & Posições", "✍️ Modo Manual", "🤖 Bot Automático"])

    with t_dash:
        col_acc1, col_acc2, col_acc3 = st.columns(3)
        acc = get_account()
        col_acc1.metric("Saldo USDT", f"${acc['cash']:,.2f}")
        col_acc2.metric("Poder de Compra", f"${acc['buying_power']:,.2f}")
        col_acc3.metric("Capital Total (Equity)", f"${acc['equity']:,.2f}")
        
        st.markdown("### 📈 Posições Abertas")
        positions = get_positions()
        if positions:
            df_pos = pd.DataFrame(positions)
            df_pos['unrealized_pl'] = df_pos['unrealized_pl'].map("${:,.2f}".format)
            df_pos['unrealized_plpc'] = df_pos['unrealized_plpc'].map("{:.2f}%".format)
            st.dataframe(df_pos, use_container_width=True)
            
            # Form para fechar posição manual
            pos_symbols = [p["symbol"] for p in positions]
            close_sym = st.selectbox("Seleciona símbolo a fechar:", pos_symbols, key="binance_close_sym")
            if st.button("❌ Fechar Posição", type="primary", key="binance_close_btn"):
                res = close_position(close_sym)
                st.success(f"Posição {close_sym} fechada! ID: {res['order_id']}")
                st.rerun()
        else:
            st.info("Nenhuma posição aberta no momento.")

        st.markdown("### 📜 Últimas Ordens (Abertas / Preenchidas)")
        orders = get_orders(status="all", limit=10)
        if orders:
            df_ord = pd.DataFrame(orders)
            df_ord = df_ord[["symbol", "side", "qty", "filled_qty", "status", "created_at"]]
            st.dataframe(df_ord, use_container_width=True)
        else:
            st.info("Nenhuma ordem recente.")

    with t_manual:
        st.markdown("### ✍️ Operação Manual (Mercado)")
        from binance_connector import SYMBOL_MAP
        all_symbols = list(SYMBOL_MAP.keys())
        default_idx = all_symbols.index("BTC/USDT") if "BTC/USDT" in all_symbols else 0
        manual_symbol = st.selectbox("Ativo", all_symbols, index=default_idx, key="binance_manual_sym")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            manual_side = st.selectbox("Direção", ["Buy (LONG)", "Sell (SHORT)"], key="binance_manual_side")
        with col_m2:
            manual_notional = st.number_input("Tamanho da Ordem (USDT)", min_value=50.0, max_value=5000.0, value=100.0, step=10.0)
        st.caption("⚠️ Mínimo exigido pela Binance Futures Testnet: 50 USDT")
            
        if st.button("🚀 Executar Ordem Manual", type="primary"):
            side_str = "buy" if "LONG" in manual_side else "sell"
            try:
                res = place_order(manual_symbol, side_str, qty=None, notional=manual_notional)
                st.success(f"Ordem {side_str.upper()} executada! ID: {res['id'][:10]}... | Quantidade: {res['qty']}")
                st.rerun()
            except Exception as e:
                st.error(f"Falha ao executar ordem: {e}")

    with t_bot:
        st.markdown("### 🤖 Bot Automático - Ligar Estratégia à Binance")
        st.caption("O bot lê os sinais em tempo real da estratégia ativa no Centro de Comando e executa ordens na Binance Futures.")
        
        # Resumo visual das variáveis configuradas no centro de comando
        st.markdown("#### ⚙️ Configurações Ativas do Centro de Comando")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("Estratégia Ativa", st.session_state.get('tg_strategy_type', 'Default (Manual)'))
            st.metric("Dispersão Mínima", f"{st.session_state.get('tg_lagarta_min_disp', 0.0):.2f}")
        with col_s2:
            st.markdown("**Vetor de Médias Móveis:**")
            st.markdown(f"* **P2 (Rápida)**: {st.session_state.get('tg_p2', 9)}")
            st.markdown(f"* **P3 (Sinal)**: {st.session_state.get('tg_p3', 21)}")
            st.markdown(f"* **P4 (Intermédia)**: {st.session_state.get('tg_p4', 50)}")
            st.markdown(f"* **P5 (Lenta 1)**: {st.session_state.get('tg_p5', 100)}")
            st.markdown(f"* **P6 (Lenta 2)**: {st.session_state.get('tg_p6', 200)}")
        with col_s3:
            st.markdown("**Gestão de Risco Ativa:**")
            st.markdown(f"* **Stop Loss (SL)**: {st.session_state.get('tg_sl_pct', 1.0)}% ({'Ativo' if st.session_state.get('tg_sl_active', True) else 'Desativado'})")
            st.markdown(f"* **Take Profit (TP)**: {st.session_state.get('tg_tp_pct', 7.0)}% ({'Ativo' if st.session_state.get('tg_tp_active', False) else 'Desativado'})")
            st.markdown(f"* **Trailing Stop (TS)**: {st.session_state.get('tg_ts_pct', 1.0)}% ({'Ativo' if st.session_state.get('tg_ts_active', True) else 'Desativado'})")

        st.markdown("---")
        st.markdown("#### 🚀 Parâmetros de Execução do Bot")
        
        c_exec1, c_exec2, c_exec3 = st.columns(3)
        with c_exec1:
            from binance_connector import SYMBOL_MAP
            all_syms = list(SYMBOL_MAP.keys())
            default_i = all_syms.index("BTC/USDT") if "BTC/USDT" in all_syms else 0
            bot_symbol = st.selectbox("Ativo para o Bot", all_syms, index=default_i, key="binance_bot_sym")
        with c_exec2:
            bot_capital = st.number_input("Tamanho da Posição por Sinal (USDT)", min_value=50.0, max_value=5000.0, value=100.0, step=10.0, key="binance_bot_capital")
            st.caption("⚠️ Mínimo exigido pela Binance Futures Testnet: 50 USDT")
        with c_exec3:
            interval_sec = st.number_input("Verificar mercado a cada (segundos)", min_value=5, max_value=300, value=30, key="binance_interval")
            
        col_start, col_stop, _ = st.columns([1, 1, 1])
        
        if "binance_bot_running" not in st.session_state:
            st.session_state.binance_bot_running = False
        if "binance_bot_log" not in st.session_state:
            st.session_state.binance_bot_log = []

        with col_start:
            if st.button("▶️ Iniciar Bot", type="primary", use_container_width=True, disabled=st.session_state.binance_bot_running):
                st.session_state.binance_bot_running = True
                st.session_state.binance_bot_log = []
                st.session_state.binance_bot_config = {
                    "symbol": bot_symbol,
                    "capital": bot_capital,
                    "interval": int(interval_sec),
                    "last_signal": None,
                    "position_extreme_price": None,
                }
                st.rerun()
                
        with col_stop:
            if st.button("⏹️ Parar Bot", use_container_width=True, disabled=not st.session_state.binance_bot_running):
                st.session_state.binance_bot_running = False
                st.rerun()

        # Bot Loop / Log
        if st.session_state.binance_bot_running:
            from streamlit_autorefresh import st_autorefresh
            cfg = st.session_state.get("binance_bot_config", {})
            interval = cfg.get("interval", 30)
            st_autorefresh(interval=interval * 1000, key="binance_autorefresh")
            st.success(f"🤖 Bot ATIVO - **{cfg.get('symbol')}** | **{st.session_state.get('tg_strategy_type')}** | **${cfg.get('capital'):.0f}/ordem** | a cada **{interval}s**")
            _run_bot_cycle(place_order, close_position, get_positions)

        if st.session_state.binance_bot_log:
            c_log1, c_log2 = st.columns([2, 1])
            with c_log1:
                st.markdown("#### 📜 Log de Atividade")
                for entry in reversed(st.session_state.binance_bot_log[-30:]):
                    st.markdown(f"`{entry}`")
            with c_log2:
                if st.button("🧹 Limpar Log", key="binance_clear_log"):
                    st.session_state.binance_bot_log = []
                    st.rerun()


def _run_bot_cycle(place_order, close_position, get_positions):
    import pandas as pd
    cfg = st.session_state.binance_bot_config
    symbol, capital = cfg["symbol"], cfg["capital"]
    now_str = pd.Timestamp.now().strftime("%H:%M:%S")

    # Obter parâmetros globais do Centro de Comando
    sl_active = st.session_state.get("tg_sl_active", True)
    sl_pct = st.session_state.get("tg_sl_pct", 1.0) if sl_active else 0.0
    
    tp_active = st.session_state.get("tg_tp_active", False)
    tp_pct = st.session_state.get("tg_tp_pct", 7.0) if tp_active else 0.0
    
    ts_active = st.session_state.get("tg_ts_active", True)
    ts_pct = st.session_state.get("tg_ts_pct", 1.0) if ts_active else 0.0

    try:
        from binance_connector import get_ohlcv, SYMBOL_MAP
        # Pedir 300 velas para ter dados suficientes para calcular SMA 144
        df = get_ohlcv(symbol, timeframe="5m", limit=300)

        if df is None or df.empty or len(df) < 150:
            st.warning(f"[{now_str}] ⚠️ Dados insuficientes para {symbol}")
            return

        # Obter posição atual na Binance
        pos_list = get_positions()
        binance_symbol = SYMBOL_MAP.get(symbol, symbol)
        active_pos = None
        for p in pos_list:
            p_sym = p["symbol"].replace("/", "")
            target_sym = binance_symbol.replace("/", "")
            if p_sym == target_sym:
                active_pos = p
                break
        
        active_pos_side = active_pos["side"].upper() if active_pos else "NONE"
        current_price = float(df['close'].iloc[-1])

        # 1. Verificar Stop Loss e Trailing Stop de Posição Aberta
        if active_pos:
            side = active_pos_side.lower() # 'long' or 'short'
            entry = float(active_pos["avg_entry"])
            
            # Verificação de Stop Loss Fixo (Segurança)
            if sl_pct > 0.0:
                if side == "long" and current_price <= entry * (1 - sl_pct / 100):
                    close_position(symbol)
                    msg = f"[{now_str}] 🛑 STOP LOSS LONG atingido ({sl_pct}%) | Saída: ${current_price:.2f} | Entrada: ${entry:.2f}"
                    st.session_state.binance_bot_log.append(msg)
                    st.session_state.binance_bot_config["last_signal"] = None
                    st.session_state.binance_bot_config["position_extreme_price"] = None
                    st.toast(msg)
                    st.rerun()
                elif side == "short" and current_price >= entry * (1 + sl_pct / 100):
                    close_position(symbol)
                    msg = f"[{now_str}] 🛑 STOP LOSS SHORT atingido ({sl_pct}%) | Saída: ${current_price:.2f} | Entrada: ${entry:.2f}"
                    st.session_state.binance_bot_log.append(msg)
                    st.session_state.binance_bot_config["last_signal"] = None
                    st.session_state.binance_bot_config["position_extreme_price"] = None
                    st.toast(msg)
                    st.rerun()
                    
            # Verificação de Take Profit Fixo
            if tp_pct > 0.0:
                if side == "long" and current_price >= entry * (1 + tp_pct / 100):
                    close_position(symbol)
                    msg = f"[{now_str}] 🎯 TAKE PROFIT LONG atingido ({tp_pct}%) | Saída: ${current_price:.2f} | Entrada: ${entry:.2f}"
                    st.session_state.binance_bot_log.append(msg)
                    st.session_state.binance_bot_config["last_signal"] = None
                    st.session_state.binance_bot_config["position_extreme_price"] = None
                    st.toast(msg)
                    st.rerun()
                elif side == "short" and current_price <= entry * (1 - tp_pct / 100):
                    close_position(symbol)
                    msg = f"[{now_str}] 🎯 TAKE PROFIT SHORT atingido ({tp_pct}%) | Saída: ${current_price:.2f} | Entrada: ${entry:.2f}"
                    st.session_state.binance_bot_log.append(msg)
                    st.session_state.binance_bot_config["last_signal"] = None
                    st.session_state.binance_bot_config["position_extreme_price"] = None
                    st.toast(msg)
                    st.rerun()

            # Verificação de Trailing Stop
            if ts_pct > 0.0:
                extreme_price = st.session_state.binance_bot_config.get("position_extreme_price")
                if extreme_price is None:
                    extreme_price = entry if entry > 0 else current_price
                    st.session_state.binance_bot_config["position_extreme_price"] = extreme_price
                    
                if side == "long":
                    if current_price > extreme_price:
                        extreme_price = current_price
                        st.session_state.binance_bot_config["position_extreme_price"] = extreme_price
                    ts_trigger_price = extreme_price * (1 - ts_pct / 100)
                    st.info(f"🛡️ Trailing Stop Ativo (LONG) | Pico: ${extreme_price:.2f} | Gatilho: ${ts_trigger_price:.2f} | Atual: ${current_price:.2f}")
                    if current_price <= ts_trigger_price:
                        close_position(symbol)
                        msg = f"[{now_str}] 📉 TRAILING STOP LONG atingido ({ts_pct}%) | Saída: ${current_price:.2f} | Pico: ${extreme_price:.2f}"
                        st.session_state.binance_bot_log.append(msg)
                        st.session_state.binance_bot_config["last_signal"] = None
                        st.session_state.binance_bot_config["position_extreme_price"] = None
                        st.toast(msg)
                        st.rerun()
                elif side == "short":
                    if current_price < extreme_price:
                        extreme_price = current_price
                        st.session_state.binance_bot_config["position_extreme_price"] = extreme_price
                    ts_trigger_price = extreme_price * (1 + ts_pct / 100)
                    st.info(f"🛡️ Trailing Stop Ativo (SHORT) | Mínimo: ${extreme_price:.2f} | Gatilho: ${ts_trigger_price:.2f} | Atual: ${current_price:.2f}")
                    if current_price >= ts_trigger_price:
                        close_position(symbol)
                        msg = f"[{now_str}] 📈 TRAILING STOP SHORT atingido ({ts_pct}%) | Saída: ${current_price:.2f} | Mínimo: ${extreme_price:.2f}"
                        st.session_state.binance_bot_log.append(msg)
                        st.session_state.binance_bot_config["last_signal"] = None
                        st.session_state.binance_bot_config["position_extreme_price"] = None
                        st.toast(msg)
                        st.rerun()
        else:
            st.session_state.binance_bot_config["position_extreme_price"] = None

        # 2. Avaliar Sinal da Estratégia em Tempo Real
        action, confidence, details = evaluate_strategy_signal(df, _cur_pos=active_pos_side)
        
        last_signal = cfg.get("last_signal")
        st.metric("Preço", f"${current_price:.2f}", delta=f"Estratégia: {action} ({confidence}%)")

        if action != "HOLD" and action != active_pos_side:
            try:
                # Se houver posição oposta aberta, fecha-a primeiro
                if active_pos_side != "NONE":
                    close_position(symbol)
                    msg_c = f"[{now_str}] 📉 Fecho de {active_pos_side} para reversão."
                    st.session_state.binance_bot_log.append(msg_c)
                
                # Executa a nova ordem
                side_str = "buy" if action == "LONG" else "sell"
                res = place_order(symbol, side_str, qty=None, notional=capital)
                
                msg = f"[{now_str}] 🚀 {action} {symbol} ~${capital:.0f} @ ${current_price:.2f} | Gatilho: {details.get('Gatilho', 'Consenso')}"
                st.session_state.binance_bot_log.append(msg)
                st.session_state.binance_bot_config["last_signal"] = action
                st.session_state.binance_bot_config["position_extreme_price"] = None # Reset
                st.toast(msg)
                st.rerun()
            except Exception as e:
                st.session_state.binance_bot_log.append(f"[{now_str}] ❌ Erro: {e}")
                st.error(e)
        elif action == "HOLD" and confidence >= 80.0 and active_pos_side != "NONE":
            # Caso seja um sinal de saída forçada a FLAT (ex: Claude v4 exit)
            try:
                close_position(symbol)
                msg = f"[{now_str}] ⏹️ Exito FLAT atingido @ ${current_price:.2f} | Gatilho: {details.get('Gatilho', 'Saída')}"
                st.session_state.binance_bot_log.append(msg)
                st.session_state.binance_bot_config["last_signal"] = "HOLD"
                st.session_state.binance_bot_config["position_extreme_price"] = None
                st.toast(msg)
                st.rerun()
            except Exception as e:
                st.error(e)
        else:
            st.info(f"[{now_str}] 🔍 A monitorizar {symbol} - sem sinal de inversão (Sinal atual: {action} | Posição: {active_pos_side})")

    except Exception as e:
        st.session_state.binance_bot_log.append(f"[{now_str}] ❌ Erro no ciclo: {e}")
        st.error(e)


def evaluate_strategy_signal(df, _cur_pos="NONE"):
    p2 = st.session_state.get("tg_p2", 9)
    p3 = st.session_state.get("tg_p3", 21)
    p4 = st.session_state.get("tg_p4", 50)
    p5 = st.session_state.get("tg_p5", 100)
    p6 = st.session_state.get("tg_p6", 200)
    
    # Calcular médias
    df['sma_5'] = df['close'].rolling(window=p2).mean()
    df['sma_13'] = df['close'].rolling(window=p3).mean()
    df['sma_21'] = df['close'].rolling(window=p4).mean()
    df['sma_55'] = df['close'].rolling(window=p5).mean()
    df['sma_144'] = df['close'].rolling(window=p6).mean()
    
    smas = ['sma_5','sma_13','sma_21','sma_55','sma_144']
    df['avg_sma'] = df[smas].mean(axis=1)
    df['sma_std'] = df[smas].std(axis=1)
    df['stretching'] = df[smas].sub(df['avg_sma'], axis=0).abs().mean(axis=1).div(df['avg_sma']).mul(100)
    df['velocity'] = df['sma_5'].diff(periods=2)
    df['acceleration'] = df['velocity'].diff(periods=2)
    df['volatility'] = df['close'].rolling(window=20).std()
    
    # Classificação de regime
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
    df['mola_pct'] = df[smas].std(axis=1) / df[smas].mean(axis=1) * 100
    df['infil_bull'] = (df['sma_5'] > df['sma_13']) & (df['sma_13'] > df['sma_21']) & (df['sma_55'] < df['sma_144'])
    df['infil_bear'] = (df['sma_5'] < df['sma_13']) & (df['sma_13'] < df['sma_21']) & (df['sma_55'] > df['sma_144'])
    df['reteste_val'] = ((df['close'] - df['sma_55']).abs() / df['sma_55'] * 100 < 0.8) | ((df['close'] - df['sma_144']).abs() / df['sma_144'] * 100 < 0.8)
    
    # RSI, BB, MACD, ATR
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
    
    # O passo de análise é a vela mais recente (-1)
    step = -1
    
    # Filtro de Dispersão Mínima
    _disp_min = st.session_state.get('tg_lagarta_min_disp', 0.0)
    if _disp_min > 0.0 and 'sma_std' in df.columns:
        _disp_now = float(df['sma_std'].iloc[step])
        if _disp_now < _disp_min:
            return "HOLD", 0.0, {
                "Dispersão SMAs": f"{_disp_now:.3f}",
                f"Mínimo ({_disp_min:.2f})": "🚫 SMAs comprimidas - aguardar expansão",
            }
            
    strategy_type = st.session_state.get("tg_strategy_type", "Default")
    
    # ESTRATÉGIA CLAUDE v4
    if "Claude" in strategy_type:
        p2_now  = df['sma_5'].iloc[step];   p2_prev = df['sma_5'].iloc[step-1]
        p3_now  = df['sma_13'].iloc[step];  p3_prev = df['sma_13'].iloc[step-1]
        p4_now  = df['sma_21'].iloc[step]
        vel     = df['velocity'].iloc[step] if 'velocity' in df.columns else 0.0
        
        cross_p2p3_long  = (p2_prev <= p3_prev) and (p2_now > p3_now)
        cross_p2p3_short = (p2_prev >= p3_prev) and (p2_now < p3_now)
        
        cond = {
            "P2 > P3":   bool(p2_now > p3_now),
            "P2 > P4":   bool(p2_now > p4_now),
            "Cruz ↗ P3":  bool(cross_p2p3_long),
            "Cruz ↘ P3":  bool(cross_p2p3_short),
            "Vel +":     bool(vel > 0),
        }
        
        if cross_p2p3_long and p2_now > p4_now and vel > 0:
            if _cur_pos == "LONG":
                return "HOLD", 0.0, {**cond, "Estado": "Teimosia LONG"}
            return "LONG", 100.0, {**cond, "Gatilho": "Pirâmide ↗ LONG"}
        elif cross_p2p3_short and p2_now < p4_now and vel < 0:
            if _cur_pos == "SHORT":
                return "HOLD", 0.0, {**cond, "Estado": "Teimosia SHORT"}
            return "SHORT", 100.0, {**cond, "Gatilho": "Pirâmide ↘ SHORT"}
        elif _cur_pos == "LONG" and cross_p2p3_short:
            return "HOLD", 90.0, {**cond, "Gatilho": "Pirâmide partiu ↘ ➔ FLAT"}
        elif _cur_pos == "SHORT" and cross_p2p3_long:
            return "HOLD", 90.0, {**cond, "Gatilho": "Pirâmide partiu ↗ ➔ FLAT"}
        else:
            return "HOLD", 0.0, {**cond, "Estado": "A aguardar pirâmide"}
            
    # ESTRATÉGIA MÉDIA CAMADAS / ESMIGALHADOR
    elif "Camadas" in strategy_type or "Esmigalhador" in strategy_type:
        p2_per = st.session_state.get("tg_p2", 5)
        p3_per = st.session_state.get("tg_p3", 13)
        p4_per = st.session_state.get("tg_p4", 21)
        
        col_p2 = "sma_5" if p2_per > 1 else "close"
        col_p3 = "sma_13"
        col_p4 = "sma_21"
        
        price_now = df[col_p2].iloc[step]
        price_prev = df[col_p2].iloc[step-1]
        p3_now = df[col_p3].iloc[step]
        p3_prev = df[col_p3].iloc[step-1]
        p4_now = df[col_p4].iloc[step]
        p4_prev = df[col_p4].iloc[step-1]
        
        cross_p4_long = (price_prev <= p4_prev) and (price_now > p4_now)
        cross_p4_short = (price_prev >= p4_prev) and (price_now < p4_now)
        cross_p3_long = (price_prev <= p3_prev) and (price_now > p3_now)
        cross_p3_short = (price_prev >= p3_prev) and (price_now < p3_now)
        
        cond_dict = {
            "Preço (1)": float(price_now),
            "2ª Média (P3)": float(p3_now),
            "Pivot Meio (P4)": float(p4_now),
            "Acima do Pivot": bool(price_now > p4_now)
        }
        
        if cross_p4_long:
            return "LONG", 100.0, {**cond_dict, "Gatilho": "Cruzamento Equador (P4) de Alta"}
        elif cross_p4_short:
            return "SHORT", 100.0, {**cond_dict, "Gatilho": "Cruzamento Equador (P4) de Baixa"}
        elif price_now > p4_now and cross_p3_long:
            return "LONG", 100.0, {**cond_dict, "Gatilho": "Reentrada 2ª Média (P3) de Alta"}
        elif price_now < p4_now and cross_p3_short:
            return "SHORT", 100.0, {**cond_dict, "Gatilho": "Reentrada 2ª Média (P3) de Baixa"}
        else:
            return "HOLD", 0.0, cond_dict
            
    # ESTRATÉGIA CRUZAMENTO / LAGARTA / LINHA SOLITÁRIA
    elif "Lagarta" in strategy_type or "Linha Solitária" in strategy_type or "Cruzamento" in strategy_type:
        if "Lagarta" in strategy_type:
            ref_line_name = "Qualquer SMA Ativa"
        else:
            ref_line_name = st.session_state.get("tg_single_line_ref", "SMA Rápida (P2)")
            
        mapping = {
            "SMA Rápida (P2)": "sma_5",
            "SMA Sinal (P3)": "sma_13",
            "SMA Intermédia (P4)": "sma_21",
            "SMA Lenta 1 (P5)": "sma_55",
            "SMA Lenta 2 (P6)": "sma_144",
            "Média do Vetor (avg_sma)": "avg_sma",
            "Desvio Padrão (sma_std)": "sma_std"
        }
        col_name = mapping.get(ref_line_name, "sma_5")
        
        price_now = df['close'].iloc[step]
        price_prev = df['close'].iloc[step-1]
        
        fallback_cols = ["sma_13", "sma_21", "sma_55", "sma_144", "avg_sma"]
        if col_name not in ("avg_sma", "sma_std"):
            line_test = df[col_name].iloc[step]
            if abs(line_test - price_now) < 1e-9:
                for fb in fallback_cols:
                    if abs(df[fb].iloc[step] - price_now) > 1e-9:
                        col_name = fb
                        ref_line_name = f"Auto ({fb})"
                        break
                        
        is_growing = price_now > price_prev
        is_falling = price_now < price_prev
        
        if ref_line_name == "Desvio Padrão (sma_std)":
            avg_now  = df['avg_sma'].iloc[step]
            avg_prev = df['avg_sma'].iloc[step-1]
            std_now  = df['sma_std'].iloc[step]
            std_prev = df['sma_std'].iloc[step-1]
            dist_now  = abs(price_now  - avg_now)
            dist_prev = abs(price_prev - avg_prev)
            
            is_breakout = (dist_prev <= std_prev) and (dist_now > std_now)
            
            cond_dict = {
                "Afastamento > Desvio Padrão": bool(dist_now > std_now),
                "Afastamento em Alta": bool(dist_now > dist_prev),
                "Breakout de Volatilidade": bool(is_breakout),
                "Preço a Crescer": bool(is_growing),
            }
            
            if is_breakout and is_growing:
                if _cur_pos == "SHORT":
                    return "HOLD", 0.0, {**cond_dict, "Gatilho": "Ignorado pela Lagarta"}
                return "LONG", 100.0, {**cond_dict, "Gatilho": "Breakout de Alta"}
            elif is_breakout and is_falling:
                if _cur_pos == "LONG":
                    return "HOLD", 0.0, {**cond_dict, "Gatilho": "Ignorado pela Lagarta"}
                return "SHORT", 100.0, {**cond_dict, "Gatilho": "Breakout de Baixa"}
            else:
                return "HOLD", 0.0, cond_dict
        else:
            if ref_line_name == "Qualquer SMA Ativa":
                all_sma_cols = ["sma_5", "sma_13", "sma_21", "sma_55", "sma_144"]
                first_long = None
                first_short = None
                crossed_lines = []
                for sma_col in all_sma_cols:
                    ln  = df[sma_col].iloc[step]
                    lp  = df[sma_col].iloc[step-1]
                    if abs(ln - price_now) < 1e-9:
                        continue
                    if (price_prev <= lp) and (price_now > ln):
                        crossed_lines.append(f"↗ {sma_col}")
                        if first_long is None:
                            first_long = sma_col
                    elif (price_prev >= lp) and (price_now < ln):
                        crossed_lines.append(f"↘ {sma_col}")
                        if first_short is None:
                            first_short = sma_col
                            
                cond_dict = {
                    "Linhas Cruzadas": str(crossed_lines) if crossed_lines else "nenhuma",
                    "Cruzamento Alta":  bool(first_long),
                    "Cruzamento Baixa": bool(first_short),
                }
                if first_long and not first_short:
                    if _cur_pos == "LONG":
                        return "HOLD", 0.0, {**cond_dict, "Gatilho": "Teimosia ➔ já em LONG, mantém"}
                    return "LONG", 100.0, {**cond_dict, "Gatilho": f"↗ cruzou {first_long}"}
                elif first_short and not first_long:
                    if _cur_pos == "SHORT":
                        return "HOLD", 0.0, {**cond_dict, "Gatilho": "Teimosia ➔ já em SHORT, mantém"}
                    return "SHORT", 100.0, {**cond_dict, "Gatilho": f"↘ cruzou {first_short}"}
                else:
                    return "HOLD", 0.0, cond_dict
            else:
                line_now  = df[col_name].iloc[step]
                line_prev = df[col_name].iloc[step-1]
                
                is_crossover_long  = (price_prev <= line_prev) and (price_now > line_now)
                is_crossover_short = (price_prev >= line_prev) and (price_now < line_now)
                
                cond_dict = {
                    f"Preço > {ref_line_name}": bool(price_now > line_now),
                    "Cruzamento de Alta":  bool(is_crossover_long),
                    "Cruzamento de Baixa": bool(is_crossover_short),
                }
                
                if is_crossover_long:
                    if _cur_pos == "LONG":
                        return "HOLD", 0.0, {**cond_dict, "Gatilho": "Teimosia ➔ já em LONG, mantém"}
                    return "LONG", 100.0, {**cond_dict, "Gatilho": "Cruzamento de Alta ➔ LONG"}
                elif is_crossover_short:
                    if _cur_pos == "SHORT":
                        return "HOLD", 0.0, {**cond_dict, "Gatilho": "Teimosia ➔ já em SHORT, mantém"}
                    return "SHORT", 100.0, {**cond_dict, "Gatilho": "Cruzamento de Baixa ➔ SHORT"}
                else:
                    return "HOLD", 0.0, cond_dict
                    
    # CÉREBRO DE CONSENSO (IA)
    elif "Consenso" in strategy_type and os.path.exists("bot_consensus_dna.json"):
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
                
                # CONDICIONAIS LONG
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
                
                # CONDICIONAIS SHORT
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
                
                min_conf = st.session_state.get('tg_min_confidence_pct', 80.0) / 100.0
                long_score = sum(cond_long.values()) / len(cond_long) if cond_long else 0.0
                short_score = sum(cond_short.values()) / len(cond_short) if cond_short else 0.0
                
                if long_score > short_score and long_score >= min_conf:
                    return "LONG", round(long_score * 100), cond_long
                elif short_score > long_score and short_score >= min_conf:
                    return "SHORT", round(short_score * 100), cond_short
                else:
                    return "HOLD", round(max(long_score, short_score) * 100), cond_long if long_score >= short_score else cond_short
        except Exception:
            pass
            
    # FALLBACK/DEFAULT
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


def _show_env_help():
    with st.expander("🛠️ Como configurar as chaves Binance Futures (Testnet)"):
        st.markdown("""
### Opção A: No Servidor VPS (Coolify) - Recomendado
1. Acede ao teu painel do **Coolify**.
2. Abre a aplicação **OlimpoTrade**.
3. Vai ao menu lateral **Environment Variables** (Variáveis de Ambiente).
4. Adiciona as seguintes variáveis com as tuas chaves da Binance Testnet:
   * **Key**: `BINANCE_API_KEY` | **Value**: *[a tua API Key]*
   * **Key**: `BINANCE_SECRET_KEY` | **Value**: *[a tua Secret Key]*
   * **Key**: `BINANCE_TESTNET` | **Value**: `true`
5. Clica em **Save** (Gravar) e depois em **Redeploy** no topo.

### Opção B: No Computador Local (.env)
1. Abre ou cria o ficheiro `.env` na raiz do projeto e preenche:
   ```env
   BINANCE_API_KEY=cola_aqui_a_api
   BINANCE_SECRET_KEY=cola_aqui_a_secret
   BINANCE_TESTNET=true
   ```
2. Guarda o ficheiro.
""")
