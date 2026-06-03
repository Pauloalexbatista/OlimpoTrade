import streamlit as st
import pandas as pd
import os

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
    t_dash, t_manual, t_bot = st.tabs(["📊 Dashboard & Posições", "🕹️ Modo Manual", "🤖 Bot Automático"])

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

        st.markdown("### 📋 Últimas Ordens (Abertas / Preenchidas)")
        orders = get_orders(status="all", limit=10)
        if orders:
            df_ord = pd.DataFrame(orders)
            df_ord = df_ord[["symbol", "side", "qty", "filled_qty", "status", "created_at"]]
            st.dataframe(df_ord, use_container_width=True)
        else:
            st.info("Nenhuma ordem recente.")

    with t_manual:
        st.markdown("### 🕹️ Operação Manual (Mercado)")
        from binance_connector import SYMBOL_MAP
        all_symbols = list(SYMBOL_MAP.keys())
        default_idx = all_symbols.index("BTC/USDT") if "BTC/USDT" in all_symbols else 0
        
        manual_symbol = st.selectbox("Par / Ativo", all_symbols, index=default_idx, key="binance_manual_sym")
        manual_side = st.radio("Direção", ["buy", "sell"], horizontal=True, key="binance_manual_side")
        manual_notional = st.number_input("Valor USDT ($)", min_value=1.0, max_value=10000.0, value=10.0, step=1.0, key="binance_manual_notional")
        
        if st.button("🚀 Enviar Ordem Market", type="primary", key="binance_manual_btn"):
            with st.spinner("A processar ordem na Binance..."):
                try:
                    res = place_order(manual_symbol, manual_side, qty=None, notional=manual_notional)
                    st.success(f"Ordem {manual_side.upper()} executada! ID: {res['id'][:10]}... | Quantidade: {res['qty']}")
                except Exception as e:
                    st.error(f"Falha ao executar ordem: {e}")

    with t_bot:
        st.markdown("### 🤖 Bot Automático - Ligar Estratégia à Binance")
        st.caption("O bot lê os sinais da estratégia escolhida e executa ordens na Binance Futures (USD-M) automaticamente.")
        
        c_bot1, c_bot2, c_bot3 = st.columns(3)
        with c_bot1:
            from binance_connector import SYMBOL_MAP
            all_syms = list(SYMBOL_MAP.keys())
            default_i = all_syms.index("BTC/USDT") if "BTC/USDT" in all_syms else 0
            bot_symbol = st.selectbox("Ativo para o Bot", all_syms, index=default_i, key="binance_bot_sym")
            
            p2 = st.number_input("P2 (Rápida)", min_value=1, value=st.session_state.get('tg_p2', 3))
            p3 = st.number_input("P3 (Sinal)", min_value=1, value=st.session_state.get('tg_p3', 5))
            
        with c_bot2:
            strategies = ["Lagarta (Linha Solitária)", "Lagarta (Todas as Linhas)", "Média Camadas", "Esmigalhador", "Cérebro de IA"]
            bot_strategy = st.selectbox("Estratégia", strategies, key="binance_bot_strategy")
            
            p4 = st.number_input("P4 (Equador)", min_value=1, value=st.session_state.get('tg_p4', 8))
            p5 = st.number_input("P5 (Lenta)", min_value=1, value=st.session_state.get('tg_p5', 13))
            
        with c_bot3:
            bot_capital = st.number_input("Tamanho da Posição por Sinal (USDT)", min_value=5.0, max_value=5000.0, value=20.0, step=5.0, key="binance_bot_capital")
            p6 = st.number_input("P6 (Filtro Longo)", min_value=1, value=st.session_state.get('tg_p6', 21))
            sl_pct = st.number_input("Stop Loss Segurança (%)", min_value=0.0, value=1.0, step=0.1)

        st.markdown("---")
        col_start, col_stop, col_int = st.columns([1, 1, 1])
        
        with col_int:
            interval_sec = st.number_input("Verificar mercado a cada (segundos)", min_value=5, max_value=300, value=30, key="binance_interval")
            
        if "binance_bot_running" not in st.session_state:
            st.session_state.binance_bot_running = False
        if "binance_bot_log" not in st.session_state:
            st.session_state.binance_bot_log = []

        with col_start:
            if st.button("▶️ Iniciar Bot", type="primary", width="stretch", disabled=st.session_state.binance_bot_running):
                st.session_state.binance_bot_running = True
                st.session_state.binance_bot_log = []
                st.session_state.binance_bot_config = {
                    "symbol": bot_symbol,
                    "strategy": bot_strategy,
                    "capital": bot_capital,
                    "p2": int(p2), "p3": int(p3), "p4": int(p4),
                    "p5": int(p5), "p6": int(p6),
                    "sl_pct": float(sl_pct),
                    "interval": int(interval_sec),
                    "last_signal": None,
                }
                st.rerun()
                
        with col_stop:
            if st.button("⏹️ Parar Bot", width="stretch", disabled=not st.session_state.binance_bot_running):
                st.session_state.binance_bot_running = False
                st.rerun()

        # Bot Loop / Log
        if st.session_state.binance_bot_running:
            from streamlit_autorefresh import st_autorefresh
            cfg = st.session_state.get("binance_bot_config", {})
            interval = cfg.get("interval", 30)
            st_autorefresh(interval=interval * 1000, key="binance_autorefresh")
            st.success(f"🚀 Bot ATIVO - **{cfg.get('symbol')}** | **{cfg.get('strategy')}** | **${cfg.get('capital'):.0f}/ordem** | a cada **{interval}s**")
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
    symbol, p2, p3, p4, p5, p6, capital, strategy = cfg["symbol"], cfg["p2"], cfg["p3"], cfg["p4"], cfg["p5"], cfg["p6"], cfg["capital"], cfg["strategy"]
    now_str = pd.Timestamp.now().strftime("%H:%M:%S")

    try:
        from binance_connector import get_ohlcv, SYMBOL_MAP
        df = get_ohlcv(symbol, timeframe="5m", limit=max(p6 * 2, 100))

        if df is None or df.empty or len(df) < p6:
            st.warning(f"[{now_str}] ⚠️ Dados insuficientes para {symbol}")
            return

        df["P2"] = df["close"].rolling(p2).mean()
        df["P3"] = df["close"].rolling(p3).mean()
        df["P4"] = df["close"].rolling(p4).mean()
        df["P5"] = df["close"].rolling(p5).mean()
        df["P6"] = df["close"].rolling(p6).mean()
        last = df.iloc[-1]
        prev = df.iloc[-2]
        current_price = float(last["close"])
        signal = None

        if "Lagarta" in strategy:
            if prev["P2"] <= prev["P4"] and last["P2"] > last["P4"]: signal = "BUY"
            elif prev["P2"] >= prev["P4"] and last["P2"] < last["P4"]: signal = "SELL"
        else:
            if prev["P2"] <= prev["P4"] and last["P2"] > last["P4"]: signal = "BUY"
            elif prev["P2"] >= prev["P4"] and last["P2"] < last["P4"]: signal = "SELL"

        last_signal = cfg.get("last_signal")

        st.metric("Preço", f"${current_price:.2f}", delta=f"Sinal: {signal or 'Nenhum'}")

        if signal and signal != last_signal:
            try:
                if signal == "BUY":
                    res = place_order(symbol, "buy", qty=None, notional=capital)
                    msg = f"[{now_str}] 🟢 BUY {symbol} ~${capital:.0f} @ ${current_price:.2f} | ID: {res['id'][:8]}"
                else:
                    pos = get_positions()
                    has_pos = any(p["symbol"] == SYMBOL_MAP.get(symbol, symbol) for p in pos)
                    if has_pos:
                        close_position(symbol)
                        msg = f"[{now_str}] 🔴 SELL/CLOSE {symbol} @ ${current_price:.2f}"
                    else:
                        msg = f"[{now_str}] ⚠️ Sinal SELL mas sem posição aberta."
                st.session_state.binance_bot_log.append(msg)
                st.session_state.binance_bot_config["last_signal"] = signal
                st.toast(msg)
            except Exception as e:
                st.session_state.binance_bot_log.append(f"[{now_str}] ❌ Erro: {e}")
                st.error(e)
        else:
            st.info(f"[{now_str}] 👁️ A monitorizar {symbol} - sem novo sinal (último: {last_signal})")

    except Exception as e:
        st.session_state.binance_bot_log.append(f"[{now_str}] ❌ Erro no ciclo: {e}")
        st.error(e)

def _show_env_help():
    with st.expander("🛠️ Como configurar as chaves Binance Futures (Testnet)"):
        st.markdown("""
1. Vai a [testnet.binancefuture.com](https://testnet.binancefuture.com/) e faz login com a tua conta Binance
2. Vai ao separador **API** e gera uma nova chave "System Generated (HMAC)"
3. Copia a **API Key** e a **Secret Key**
4. Abre o ficheiro `.env` na pasta do projeto e preenche:
```
BINANCE_API_KEY=cola_aqui_a_api
BINANCE_SECRET_KEY=cola_aqui_a_secret
BINANCE_TESTNET=true
```
5. Guarda o ficheiro e clica em **Testar Ligação**.
        """)
