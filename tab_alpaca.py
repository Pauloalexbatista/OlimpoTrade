"""
Tab Alpaca — Deploy & Monitor Paper Trading no OlimpoTrade.
"""
import streamlit as st
import pandas as pd


def render():
    st.markdown("## 🚀 Deploy Alpaca — Paper Trading")
    st.markdown("Executa as estratégias testadas no laboratório diretamente na conta Alpaca Paper.")

    with st.expander("ℹ️ Como funciona esta aba (Deploy Alpaca)?", expanded=False):
        st.markdown("""
**Para que serve:** Liga o OlimpoTrade à tua conta **Alpaca Paper Trading** (dinheiro virtual, sem risco real) para executar ordens e testar o bot em tempo real no mercado.

1. **🔌 Testar Ligação:** Verifica se as chaves da Alpaca no ficheiro `.env` estão válidas.
2. **💰 Conta & Posições:** Mostra o saldo (*Cash*, *Equity*, *Buying Power*), posições abertas e permite fechá-las manualmente.
3. **📋 Ordens Recentes:** Lista as ordens abertas e fechadas na conta.
4. **🤖 Execução Automática:** Permite correr a estratégia escolhida sobre dados reais da Alpaca em modo Paper.
""")

    # ── Teste de ligação ────────────────────────────────────────────────────────
    col_status, col_btn = st.columns([3, 1])
    with col_btn:
        test_btn = st.button("🔌 Testar Ligação", use_container_width=True)

    if test_btn or st.session_state.get("alpaca_connected"):
        try:
            from alpaca_connector import test_connection, get_account, get_positions, get_orders
            ok, msg = test_connection()
            with col_status:
                if ok:
                    st.success(msg)
                    st.session_state.alpaca_connected = True
                else:
                    st.error(msg)
                    st.session_state.alpaca_connected = False
        except ImportError:
            with col_status:
                st.error("❌ alpaca_connector.py não encontrado.")
            return

    if not st.session_state.get("alpaca_connected"):
        st.info("👆 Clica em **Testar Ligação** para começar. Certifica-te que as chaves estão no ficheiro `.env`.")
        _show_env_help()
        return

    from alpaca_connector import get_account, get_positions, get_orders, place_order, close_position, get_market_clock

    # ── Quadro de Mercados Abertos ─────────────────────────────────────────────
    _render_open_markets_panel(get_market_clock)

    # ── Account Overview ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 💰 Conta Paper Trading")
    try:
        acc = get_account()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Saldo (Cash)", f"${acc['cash']:,.2f}")
        c2.metric("Equity Total", f"${acc['equity']:,.2f}")
        c3.metric("Buying Power", f"${acc['buying_power']:,.2f}")
        c4.metric("Modo", "📄 PAPER" if acc["paper"] else "🔴 LIVE")
    except Exception as e:
        st.error(f"Erro ao obter conta: {e}")

    # ── Posições abertas ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 Posições Abertas")
    try:
        positions = get_positions()
        if positions:
            df_pos = pd.DataFrame(positions)
            df_pos["unrealized_plpc"] = df_pos["unrealized_plpc"].map(lambda x: f"{x:.2f}%")
            df_pos["unrealized_pl"] = df_pos["unrealized_pl"].map(lambda x: f"${x:+.2f}")
            df_pos.columns = ["Símbolo", "Qty", "Entrada Média", "Preço Atual", "P&L ($)", "P&L (%)", "Direção"]
            st.dataframe(df_pos, use_container_width=True)

            st.markdown("#### Fechar Posição")
            pos_symbols = [p["symbol"] for p in positions]
            close_sym = st.selectbox("Seleciona símbolo a fechar:", pos_symbols, key="alpaca_close_sym")
            try:
                _open_for_sym = [o for o in get_orders(status="open", limit=20) if o["symbol"] == close_sym]
            except Exception:
                _open_for_sym = []
            if _open_for_sym:
                st.warning(
                    f"⏳ Já existe uma ordem pendente para **{close_sym}** (`{_open_for_sym[0]['side']}` | estado: `{_open_for_sym[0]['status']}`). "
                    "Se o mercado estiver fechado, será executada automaticamente na abertura."
                )
            if st.button("❌ Fechar Posição Selecionada", type="primary", disabled=bool(_open_for_sym)):
                result = close_position(close_sym)
                st.success(f"Posição {result['symbol']} fechada! Order ID: {result['order_id']}")
                st.rerun()
        else:
            st.info("Nenhuma posição aberta de momento.")
    except Exception as e:
        st.error(f"Erro ao obter posições: {e}")

    # ── Ordens recentes ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📋 Ordens Recentes")
    try:
        col_ord1, col_ord2 = st.columns(2)
        with col_ord1:
            orders_open = get_orders(status="open", limit=10)
            st.markdown("**🟡 Abertas**")
            if orders_open:
                st.dataframe(pd.DataFrame(orders_open)[["symbol","side","qty","status","created_at"]], use_container_width=True)
            else:
                st.caption("Nenhuma ordem aberta.")
        with col_ord2:
            orders_closed = get_orders(status="closed", limit=10)
            st.markdown("**✅ Fechadas (últimas 10)**")
            if orders_closed:
                df_cl = pd.DataFrame(orders_closed)[["symbol","side","qty","filled_avg_price","status"]]
                st.dataframe(df_cl, use_container_width=True)
            else:
                st.caption("Nenhuma ordem fechada.")
    except Exception as e:
        st.error(f"Erro ao obter ordens: {e}")

    # ── Execução manual ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### ⚡ Executar Ordem Manual")
    st.caption("Testa a ligação executando uma ordem pequena de forma manual.")

    from alpaca_connector import SYMBOL_MAP
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        all_symbols = list(SYMBOL_MAP.keys())
        # Default to SPY (stock) until crypto is enabled on Alpaca account
        default_idx = all_symbols.index("SPY") if "SPY" in all_symbols else 0
        manual_symbol = st.selectbox("Par / Ativo", all_symbols, index=default_idx, key="alpaca_manual_sym")
    with col_m2:
        manual_side = st.radio("Direção", ["buy", "sell"], horizontal=True, key="alpaca_manual_side")
    with col_m3:
        manual_notional = st.number_input("Valor USD ($)", min_value=1.0, max_value=1000.0, value=10.0, step=1.0, key="alpaca_manual_notional")
    with col_m4:
        st.markdown("<br>", unsafe_allow_html=True)
        execute_btn = st.button("🚀 Executar", type="primary", use_container_width=True)

    if execute_btn:
        try:
            result = place_order(manual_symbol, manual_side, qty=None, notional=manual_notional)
            st.success(f"✅ Ordem submetida! ID: `{result['id']}` | {result['side']} {result['symbol']} ~${manual_notional:.2f}")
            st.json(result)
        except Exception as e:
            st.error(f"❌ Erro ao executar ordem: {e}")

    # ── Deploy automático da estratégia ───────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🤖 Bot Automático — Ligar Estratégia à Alpaca")
    st.caption("O bot lê os sinais da estratégia escolhida e executa ordens na Alpaca automaticamente.")

    col_b1, col_b2, col_b3 = st.columns(3)

    with col_b1:
        st.markdown("**1. Escolhe o Ativo**")
        from alpaca_connector import SYMBOL_MAP
        all_syms = list(SYMBOL_MAP.keys())
        default_i = all_syms.index("SPY") if "SPY" in all_syms else 0
        bot_symbol = st.selectbox("Ativo para o Bot", all_syms, index=default_i, key="alpaca_bot_sym")

    with col_b2:
        st.markdown("**2. Escolhe a Estratégia**")
        strategies = [
            "🦎 Camaleão ADX (3 Mercados — Lateral + Tendência)",
            "SMA Cruzamento (Curta/Longa)",
            "🎯 Reversão à Média (Bollinger + RSI)",
            "Lagarta (Todas as Linhas)",
            "Linha Solitária",
            "Média Camadas (Duas Linhas)",
            "Cérebro de Consenso (IA)",
        ]
        bot_strategy = st.selectbox("Estratégia", strategies, key="alpaca_bot_strategy")

    with col_b3:
        st.markdown("**3. Capital por Operação ($)**")
        bot_capital = st.number_input("USD por ordem", min_value=10.0, max_value=10000.0,
                                      value=100.0, step=10.0, key="alpaca_bot_capital")

    # Parâmetros lidos automaticamente do Centro de Comando
    p2 = int(st.session_state.get("tg_p2", 5))
    p3 = int(st.session_state.get("tg_p3", 13))
    p4 = int(st.session_state.get("tg_p4", 21))
    p5 = int(st.session_state.get("tg_p5", 55))
    p6 = int(st.session_state.get("tg_p6", 144))
    sl_pct = float(st.session_state.get("tg_sl_pct", 1.0))

    st.info(f"🧬 Parâmetros do Centro de Comando: **P2={p2} | P3={p3} | P4={p4} | P5={p5} | P6={p6}** | SL={sl_pct}%")

    interval_sec = st.select_slider(
        "⏱️ Intervalo de verificação",
        options=[10, 30, 60, 120, 300, 600, 900, 1800, 3600],
        value=60,
        format_func=lambda x: f"{x}s" if x < 60 else f"{x//60}min" if x < 3600 else "1h",
        key="alpaca_interval"
    )

    # Estado do bot
    if "alpaca_bot_running" not in st.session_state:
        st.session_state.alpaca_bot_running = False
    if "alpaca_bot_log" not in st.session_state:
        st.session_state.alpaca_bot_log = []

    col_start, col_stop = st.columns(2)
    with col_start:
        if st.button("▶️ Iniciar Bot", type="primary", width="stretch",
                     disabled=st.session_state.alpaca_bot_running):
            st.session_state.alpaca_bot_running = True
            st.session_state.alpaca_bot_log = []
            st.session_state.alpaca_bot_config = {
                "symbol": bot_symbol,
                "strategy": bot_strategy,
                "capital": bot_capital,
                "p2": int(p2), "p3": int(p3), "p4": int(p4),
                "p5": int(p5), "p6": int(p6),
                "sl_pct": float(sl_pct),
                "interval": int(interval_sec),
                "last_signal": None,
                "position": None,
            }
            st.rerun()

    with col_stop:
        if st.button("⏹️ Parar Bot", width="stretch",
                     disabled=not st.session_state.alpaca_bot_running):
            st.session_state.alpaca_bot_running = False
            st.rerun()

    # Painel de estado e log
    if st.session_state.alpaca_bot_running:
        import time
        from streamlit_autorefresh import st_autorefresh

        cfg = st.session_state.get("alpaca_bot_config", {})
        interval = cfg.get("interval", 60)

        # Auto-refresh da página a cada `interval` segundos
        st_autorefresh(interval=interval * 1000, key="alpaca_autorefresh")

        st.success(f"🟢 Bot ATIVO — **{cfg.get('symbol')}** | **{cfg.get('strategy')}** | **${cfg.get('capital'):.0f}/ordem** | verificação a cada **{interval}s**")

        # Executar ciclo do bot
        _run_bot_cycle(place_order, close_position, get_positions)

    # Log de atividade + histórico de sinais
    if st.session_state.alpaca_bot_log:
        col_log1, col_log2 = st.columns([2, 1])
        with col_log1:
            st.markdown("#### 📋 Log de Atividade")
            for entry in reversed(st.session_state.alpaca_bot_log[-30:]):
                if "BUY" in entry:
                    st.markdown(f"🟢 `{entry}`")
                elif "SELL" in entry or "CLOSE" in entry:
                    st.markdown(f"🔴 `{entry}`")
                elif "Erro" in entry:
                    st.markdown(f"❌ `{entry}`")
                else:
                    st.caption(entry)
        with col_log2:
            st.markdown("#### 📊 Resumo")
            buys  = sum(1 for e in st.session_state.alpaca_bot_log if "BUY" in e)
            sells = sum(1 for e in st.session_state.alpaca_bot_log if "SELL" in e or "CLOSE" in e)
            total = len(st.session_state.alpaca_bot_log)
            st.metric("Ciclos executados", total)
            st.metric("Ordens BUY", buys)
            st.metric("Ordens SELL", sells)
            if st.button("🗑️ Limpar Log", key="alpaca_clear_log"):
                st.session_state.alpaca_bot_log = []
                st.rerun()


    # Log persistente em CSV para análise de horários
    _render_market_checks_log()


def _render_open_markets_panel(get_market_clock):
    """Renderiza o quadro de estado dos mercados (Ações/ETFs EUA vs Cripto 24/7)."""
    from alpaca_connector import SYMBOL_MAP
    st.markdown("---")
    st.markdown("### 🌍 Quadro de Mercados Abertos")
    try:
        clk = get_market_clock()
        us_open = clk["is_open"]
        ts_ny = clk["timestamp"].strftime("%Y-%m-%d %H:%M NY")
        next_open = clk["next_open"].strftime("%d/%m %H:%M NY")
        next_close = clk["next_close"].strftime("%d/%m %H:%M NY")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🇺🇸 Bolsa EUA (NYSE/NASDAQ)", "🟢 ABERTO" if us_open else "🔴 FECHADO")
        m2.metric("🪙 Cripto (Alpaca 24/7)", "🟢 ABERTO 24/7")
        m3.metric("🕒 Hora Nova Iorque", ts_ny)
        m4.metric("📅 Próxima Sessão EUA", f"Fecha {next_close}" if us_open else f"Abre {next_open}")

        rows = []
        for olimpo_sym, alpaca_sym in SYMBOL_MAP.items():
            is_crypto = "/" in alpaca_sym
            rows.append({
                "Ativo": olimpo_sym,
                "Mercado": "🪙 Cripto (24/7)" if is_crypto else "🇺🇸 Ações / ETFs EUA",
                "Estado Atual": "🟢 Aberto" if (is_crypto or us_open) else "🔴 Fechado",
                "Horário": "24h / 7 dias" if is_crypto else "09:30–16:00 NY (14:30–21:00 UTC)",
            })
        with st.expander("📋 Ver estado de todos os ativos disponíveis", expanded=False):
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    except Exception as e:
        st.warning(f"⚠️ Não foi possível consultar o relógio de mercado da Alpaca: {e}")


def _append_market_check_log(row: dict):
    """Grava cada tentativa de verificação de mercado num CSV persistente para análise de horários."""
    import csv
    from pathlib import Path
    log_path = Path(__file__).resolve().parent / "alpaca_market_checks.csv"
    fieldnames = [
        "timestamp_utc", "timestamp_local", "weekday", "hour_utc",
        "symbol", "market_type", "market_open", "timeframe",
        "last_candle_utc", "price", "p2", "p3", "p4", "p5", "p6",
        "signal", "order_action", "notes",
    ]
    file_exists = log_path.exists()
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in fieldnames})


def _render_market_checks_log():
    """Mostra resumo e download do histórico persistente de verificações de mercado."""
    from pathlib import Path
    log_path = Path(__file__).resolve().parent / "alpaca_market_checks.csv"
    if not log_path.exists():
        return
    st.markdown("---")
    st.markdown("### 🕒 Registo de Tentativas de Mercado (`alpaca_market_checks.csv`)")
    try:
        df_log = pd.read_csv(log_path)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de verificações", len(df_log))
        c2.metric("Sinais gerados", int(df_log["signal"].isin(["BUY", "SELL"]).sum()) if "signal" in df_log else 0)
        c3.download_button(
            "⬇️ Exportar CSV de Horários",
            data=log_path.read_bytes(),
            file_name="alpaca_market_checks.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.dataframe(df_log.tail(15).iloc[::-1], use_container_width=True, hide_index=True)
    except Exception as e:
        st.caption(f"Não foi possível ler o histórico de verificações: {e}")


def _run_bot_cycle(place_order, close_position, get_positions):
    """Executa um ciclo de decisão do bot: lê dados, calcula sinal, executa ordem se necessário."""
    import time
    import pandas as pd
    import numpy as np

    cfg = st.session_state.alpaca_bot_config
    symbol   = cfg["symbol"]
    p2, p3, p4, p5, p6 = cfg["p2"], cfg["p3"], cfg["p4"], cfg["p5"], cfg["p6"]
    sl_pct   = cfg["sl_pct"]
    capital  = cfg["capital"]
    strategy = cfg["strategy"]
    now_str  = pd.Timestamp.now().strftime("%H:%M:%S")

    try:
        from alpaca_connector import get_ohlcv, SYMBOL_MAP, get_market_clock
        now_utc = pd.Timestamp.now(tz="UTC")
        now_local = pd.Timestamp.now()
        alpaca_sym = SYMBOL_MAP.get(symbol, symbol.replace("/USDT", "/USD"))
        is_crypto = "/" in alpaca_sym
        market_type = "CRYPTO" if is_crypto else "US_STOCK"
        try:
            market_open = True if is_crypto else bool(get_market_clock()["is_open"])
        except Exception:
            market_open = is_crypto

        df = get_ohlcv(symbol, timeframe="5m", limit=max(p6 * 2, 100))

        if df is None or df.empty or len(df) < p6:
            msg = f"[{now_str}] ⚠️ Dados insuficientes para {symbol} ({len(df) if df is not None else 0} velas, precisa de {p6})"
            st.session_state.alpaca_bot_log.append(msg)
            st.warning(msg)
            _append_market_check_log({
                "timestamp_utc": now_utc.isoformat(),
                "timestamp_local": now_local.strftime("%Y-%m-%d %H:%M:%S"),
                "weekday": now_utc.strftime("%A"),
                "hour_utc": now_utc.hour,
                "symbol": symbol,
                "market_type": market_type,
                "market_open": market_open,
                "timeframe": "5m",
                "signal": "HOLD",
                "order_action": "NONE",
                "notes": msg,
            })
            return

        # Calcular as 6 médias
        df["P2"] = df["close"].rolling(p2).mean()
        df["P3"] = df["close"].rolling(p3).mean()
        df["P4"] = df["close"].rolling(p4).mean()
        df["P5"] = df["close"].rolling(p5).mean()
        df["P6"] = df["close"].rolling(p6).mean()
        last = df.iloc[-1]
        prev = df.iloc[-2]
        current_price = float(last["close"])
        signal = None

        # Lógica de sinal por estratégia
        if "Camaleão" in strategy:
            from strategy import StrategyFactory as _SF
            _df_s = df.copy()
            if "high" not in _df_s.columns:
                _df_s["high"] = _df_s["close"]
            if "low" not in _df_s.columns:
                _df_s["low"] = _df_s["close"]
            _cam_strat = _SF.get_strategy({
                "STRATEGY_TYPE": "CAMALEAO_ADX",
                "ADX_THRESHOLD": 27.0,
                "SHORT_WINDOW": p2,
                "P3_WINDOW": p3,
                "LONG_WINDOW": p4,
                "MIN_P2_P3_PCT": float(st.session_state.get("tg_min_p2_p3_pct", 0.15) or 0.15),
            })
            _res_cam = _cam_strat.generate_signal(_df_s)
            if _res_cam.get("action") in ("BUY", "SELL"):
                signal = _res_cam["action"]
        elif "Reversão à Média" in strategy or "Bollinger" in strategy:
            bb_mid = float(df["close"].iloc[-20:].mean())
            bb_std = float(df["close"].iloc[-20:].std())
            bb_low = bb_mid - 2.0 * bb_std
            bb_high = bb_mid + 2.0 * bb_std
            delta = df["close"].diff()
            gain = delta.clip(lower=0).rolling(14).mean().iloc[-1]
            loss = (-delta.clip(upper=0)).rolling(14).mean().iloc[-1]
            rsi_val = 100.0 - (100.0 / (1.0 + (gain / loss))) if loss and loss > 0 else 50.0
            if current_price <= bb_low * 1.002 and rsi_val <= 35.0:
                signal = "BUY"
            elif current_price >= bb_high or rsi_val >= 65.0 or (current_price >= bb_mid and rsi_val >= 55.0):
                signal = "SELL"
        elif "Lagarta" in strategy or "Linha Solitária" in strategy:
            # P2 cruza P4 (equador)
            if prev["P2"] <= prev["P4"] and last["P2"] > last["P4"]:
                signal = "BUY"
            elif prev["P2"] >= prev["P4"] and last["P2"] < last["P4"]:
                signal = "SELL"
        elif "Camadas" in strategy:
            # P2 cruza P3 com P4 como filtro de tendência
            if prev["P2"] <= prev["P3"] and last["P2"] > last["P3"] and last["P4"] > last["P5"]:
                signal = "BUY"
            elif prev["P2"] >= prev["P3"] and last["P2"] < last["P3"] and last["P4"] < last["P5"]:
                signal = "SELL"
        elif "Cérebro" in strategy or "IA" in strategy:
            # Consenso: P2 > P3 > P4 = BULL, P2 < P3 < P4 = BEAR
            if last["P2"] > last["P3"] > last["P4"] > last["P5"]:
                signal = "BUY"
            elif last["P2"] < last["P3"] < last["P4"] < last["P5"]:
                signal = "SELL"
        else:
            # SMA Cruzamento padrão: P2 cruza P4
            if prev["P2"] <= prev["P4"] and last["P2"] > last["P4"]:
                signal = "BUY"
            elif prev["P2"] >= prev["P4"] and last["P2"] < last["P4"]:
                signal = "SELL"

        last_signal = cfg.get("last_signal")

        # Painel de estado
        col_info1, col_info2, col_info3, col_info4, col_info5, col_info6, col_info7 = st.columns(7)
        col_info1.metric("Preço", f"${current_price:.2f}")
        col_info2.metric(f"P2({p2})", f"${last['P2']:.2f}")
        col_info3.metric(f"P3({p3})", f"${last['P3']:.2f}")
        col_info4.metric(f"P4({p4})", f"${last['P4']:.2f}")
        col_info5.metric(f"P5({p5})", f"${last['P5']:.2f}")
        col_info6.metric(f"P6({p6})", f"${last['P6']:.2f}")
        col_info7.metric("Sinal", signal or "—", delta="NOVO" if signal and signal != last_signal else None)

        order_action = "NONE"
        notes = f"Monitorizado (ultimo sinal: {last_signal or 'nenhum'})"

        if signal and signal != last_signal:
            try:
                if signal == "BUY":
                    result = place_order(symbol, "buy", qty=None, notional=capital)
                    msg = f"[{now_str}] 🟢 BUY {symbol} ~${capital:.0f} @ ${current_price:.2f} | ID: {result['id'][:8]}..."
                    order_action = "BUY_SUBMITTED"
                else:
                    positions = get_positions()
                    has_pos = any(p["symbol"] == SYMBOL_MAP.get(symbol, symbol) for p in positions)
                    if has_pos:
                        close_position(symbol)
                        msg = f"[{now_str}] 🔴 SELL/CLOSE {symbol} @ ${current_price:.2f}"
                        order_action = "CLOSE_SUBMITTED"
                    else:
                        msg = f"[{now_str}] ⚪ Sinal SELL mas sem posição aberta."
                        order_action = "SELL_NO_POS"

                notes = msg
                st.session_state.alpaca_bot_log.append(msg)
                st.session_state.alpaca_bot_config["last_signal"] = signal
                st.toast(msg)
            except Exception as e:
                err = f"[{now_str}] ❌ Erro ao executar ordem: {e}"
                notes = err
                order_action = "ORDER_ERROR"
                st.session_state.alpaca_bot_log.append(err)
                st.error(err)
        else:
            st.info(f"[{now_str}] 👀 A monitorizar {symbol} — sem novo sinal (último: {last_signal or 'nenhum'})")

        _append_market_check_log({
            "timestamp_utc": now_utc.isoformat(),
            "timestamp_local": now_local.strftime("%Y-%m-%d %H:%M:%S"),
            "weekday": now_utc.strftime("%A"),
            "hour_utc": now_utc.hour,
            "symbol": symbol,
            "market_type": market_type,
            "market_open": market_open,
            "timeframe": "5m",
            "last_candle_utc": str(df.index[-1]),
            "price": round(current_price, 6),
            "p2": round(float(last["P2"]), 6) if pd.notna(last["P2"]) else "",
            "p3": round(float(last["P3"]), 6) if pd.notna(last["P3"]) else "",
            "p4": round(float(last["P4"]), 6) if pd.notna(last["P4"]) else "",
            "p5": round(float(last["P5"]), 6) if pd.notna(last["P5"]) else "",
            "p6": round(float(last["P6"]), 6) if pd.notna(last["P6"]) else "",
            "signal": signal or "HOLD",
            "order_action": order_action,
            "notes": notes,
        })

    except Exception as e:
        err = f"[{now_str}] ❌ Erro no ciclo do bot: {e}"
        st.session_state.alpaca_bot_log.append(err)
        st.error(err)


def _show_env_help():
    with st.expander("📖 Como configurar as chaves Alpaca"):
        st.markdown("""
1. Vai a [app.alpaca.markets](https://app.alpaca.markets) → confirma que estás em **Paper Trading**
2. Menu lateral → **API Keys** → **Generate New Key**
3. Copia o **Key ID** e o **Secret Key**
4. Abre o ficheiro `.env` na pasta do projeto e preenche:
```
ALPACA_API_KEY=PKXXXXXXXXXXXXXXXX
ALPACA_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ALPACA_PAPER=true
```
5. Guarda o ficheiro e clica em **Testar Ligação** aqui.
        """)
