"""
Tab Alpaca — Deploy & Monitor Paper Trading no OlimpoTrade.
"""
import streamlit as st
import pandas as pd


def render():
    # CSS compacto estilo Sala de Controlo (métricas e espaçamentos mais pequenos)
    st.markdown("""<style>
    div[data-testid="stMetric"] { padding: 4px 8px !important; }
    div[data-testid="stMetric"] label { font-size: 0.72rem !important; }
    div[data-testid="stMetricValue"] { font-size: 1.05rem !important; }
    div[data-testid="stMetricDelta"] { font-size: 0.70rem !important; }
    </style>""", unsafe_allow_html=True)

    # ── Barra de topo compacta: Título + Ligação Automática ─────────────────────
    col_title, col_status, col_btn = st.columns([2.0, 3.0, 1.0])
    with col_title:
        st.markdown("#### 🎛️ Sala de Controlo — Alpaca")
    with col_btn:
        test_btn = st.button("🔄 Atualizar", use_container_width=True)

    # Liga automaticamente à Alpaca ao abrir (não perde após F5)
    try:
        from alpaca_connector import test_connection
        if test_btn or not st.session_state.get("alpaca_connected"):
            ok, msg = test_connection()
            st.session_state.alpaca_connected = bool(ok)
            st.session_state.alpaca_status_msg = msg
        with col_status:
            if st.session_state.get("alpaca_connected"):
                st.success(st.session_state.get("alpaca_status_msg", "Ligado"))
            else:
                st.error(st.session_state.get("alpaca_status_msg", "Desligado"))
    except ImportError:
        with col_status:
            st.error("❌ alpaca_connector.py não encontrado.")
        return

    if not st.session_state.get("alpaca_connected"):
        st.info("Verifica as chaves `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` nas variáveis de ambiente.")
        _show_env_help()
        return

    from alpaca_connector import get_account, get_positions, get_orders, get_market_clock, SYMBOL_MAP
    from alpaca_bot_runner import read_bot_state, write_bot_state

    # ── Faixa única compacta: Mercados + Conta ─────────────────────────────────
    _render_compact_status_bar(get_market_clock, get_account)

    # ── Controlo do Bot Automático (1 linha) ───────────────────────────────────
    all_syms = list(SYMBOL_MAP.keys())
    default_i = all_syms.index("SPY") if "SPY" in all_syms else 0
    strategies = [
        "🦎 Camaleão ADX (3 Mercados — Lateral + Tendência)",
        "SMA Cruzamento (Curta/Longa)",
        "🎯 Reversão à Média (Bollinger + RSI)",
        "Lagarta (Todas as Linhas)",
        "Linha Solitária",
        "Média Camadas (Duas Linhas)",
        "Cérebro de Consenso (IA)",
    ]
    interval_options = [10, 30, 60, 120, 300, 600, 900, 1800, 3600]

    col_b1, col_b2, col_b3, col_b4, col_b5, col_b6 = st.columns([1.0, 2.0, 0.85, 0.75, 0.9, 0.9])
    with col_b1:
        bot_symbol = st.selectbox("Ativo", all_syms, index=default_i, key="alpaca_bot_sym")
    with col_b2:
        bot_strategy = st.selectbox("Estratégia", strategies, key="alpaca_bot_strategy")
    with col_b3:
        bot_capital = st.number_input("Capital ($)", min_value=10.0, max_value=10000.0,
                                      value=100.0, step=10.0, key="alpaca_bot_capital")
    with col_b4:
        interval_sec = st.selectbox(
            "Ciclo",
            options=interval_options,
            index=2,
            format_func=lambda x: f"{x}s" if x < 60 else f"{x//60}m" if x < 3600 else "1h",
            key="alpaca_interval",
        )

    p2 = int(st.session_state.get("tg_p2", 5))
    p3 = int(st.session_state.get("tg_p3", 13))
    p4 = int(st.session_state.get("tg_p4", 21))
    p5 = int(st.session_state.get("tg_p5", 55))
    p6 = int(st.session_state.get("tg_p6", 144))
    sl_pct = float(st.session_state.get("tg_sl_pct", 1.0))

    bot_state = read_bot_state()
    is_bot_running = bool(bot_state.get("enabled", False))
    if "alpaca_bot_log" not in st.session_state:
        st.session_state.alpaca_bot_log = []

    with col_b5:
        st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
        if st.button("▶️ Iniciar", type="primary", use_container_width=True, disabled=is_bot_running):
            write_bot_state({
                "enabled": True,
                "symbol": bot_symbol,
                "strategy": bot_strategy,
                "capital": float(bot_capital),
                "p2": int(p2), "p3": int(p3), "p4": int(p4),
                "p5": int(p5), "p6": int(p6),
                "sl_pct": float(sl_pct),
                "min_p2_p3_pct": float(st.session_state.get("tg_min_p2_p3_pct", 0.15) or 0.15),
                "interval": int(interval_sec),
                "last_signal": None,
            })
            st.rerun()
    with col_b6:
        st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
        if st.button("⏹️ Parar", use_container_width=True, disabled=not is_bot_running):
            bot_state["enabled"] = False
            write_bot_state(bot_state)
            st.rerun()

    st.caption(f"🧬 Centro de Comando: **P2={p2} · P3={p3} · P4={p4} · P5={p5} · P6={p6} · SL={sl_pct}%**")

    # Estado persistente do Bot 24h na VPS (mantém-se ligado mesmo com PC desligado!)
    if is_bot_running:
        from streamlit_autorefresh import st_autorefresh

        interval = int(bot_state.get("interval", 60))
        st_autorefresh(interval=interval * 1000, key="alpaca_autorefresh")
        last_msg = bot_state.get("last_message", "A aguardar próximo ciclo na VPS...")
        st.success(
            f"🟢 **Bot ATIVO 24h na VPS** — **{bot_state.get('symbol')}** | **{bot_state.get('strategy')}** | "
            f"**${float(bot_state.get('capital', 100)):.0f}/ordem** | ciclo **{interval}s** · Último: `{last_msg}`"
        )
        # Atualiza o gráfico ao vivo a partir da Alpaca
        bot_symbol = bot_state.get("symbol", bot_symbol)

    # ── Ecrã Principal 50% / 50%: Gráfico ao Vivo + Lista de Movimentos ────────
    col_chart, col_moves = st.columns([1.05, 1.0])
    with col_chart:
        _render_live_chart(bot_symbol, p2, p3, p4, p5, p6)
    with col_moves:
        _render_market_checks_log()

    # ── Rodapé compacto: Posições | Ordens | Log ───────────────────────────────
    col_pos, col_ord, col_log = st.columns(3)
    with col_pos:
        st.markdown("**📊 Posições Abertas**")
        try:
            positions = get_positions()
            if positions:
                df_pos = pd.DataFrame(positions)
                df_pos["unrealized_plpc"] = df_pos["unrealized_plpc"].map(lambda x: f"{x:.2f}%")
                df_pos["unrealized_pl"] = df_pos["unrealized_pl"].map(lambda x: f"${x:+.2f}")
                df_pos.columns = ["Símbolo", "Qty", "Entrada", "Atual", "P&L ($)", "P&L (%)", "Dir."]
                st.dataframe(df_pos, use_container_width=True, height=150, hide_index=True)
            else:
                st.caption("Nenhuma posição aberta.")
        except Exception as e:
            st.error(f"Erro: {e}")

    with col_ord:
        st.markdown("**📋 Ordens Recentes**")
        try:
            orders_open = get_orders(status="open", limit=5)
            orders_closed = get_orders(status="closed", limit=5)
            if orders_open:
                st.dataframe(pd.DataFrame(orders_open)[["symbol", "side", "qty", "status"]], use_container_width=True, height=100, hide_index=True)
            if orders_closed:
                st.dataframe(pd.DataFrame(orders_closed)[["symbol", "side", "qty", "filled_avg_price", "status"]], use_container_width=True, height=150, hide_index=True)
            if not orders_open and not orders_closed:
                st.caption("Nenhuma ordem recente.")
        except Exception as e:
            st.error(f"Erro: {e}")

    with col_log:
        st.markdown("**📋 Log de Atividade**")
        if st.session_state.alpaca_bot_log:
            for entry in reversed(st.session_state.alpaca_bot_log[-8:]):
                if "BUY" in entry:
                    st.markdown(f"🟢 `{entry}`")
                elif "SELL" in entry or "CLOSE" in entry:
                    st.markdown(f"🔴 `{entry}`")
                elif "Erro" in entry:
                    st.markdown(f"❌ `{entry}`")
                else:
                    st.caption(entry)
            if st.button("🗑️ Limpar Log", key="alpaca_clear_log"):
                st.session_state.alpaca_bot_log = []
                st.rerun()
        else:
            st.caption("Sem eventos recentes.")


def _render_compact_status_bar(get_market_clock, get_account):
    """Faixa única compacta com estado dos mercados e saldo da conta."""
    us_txt = "—"
    ny_txt = "—"
    try:
        clk = get_market_clock()
        us_open = clk["is_open"]
        us_txt = "🟢 ABERTO" if us_open else "🔴 FECHADO"
        ny_txt = clk["timestamp"].strftime("%H:%M NY")
    except Exception:
        pass

    cash_txt = eq_txt = bp_txt = mode_txt = "—"
    try:
        acc = get_account()
        cash_txt = f"${acc['cash']:,.2f}"
        eq_txt = f"${acc['equity']:,.2f}"
        bp_txt = f"${acc['buying_power']:,.2f}"
        mode_txt = "📄 PAPER" if acc["paper"] else "🔴 LIVE"
    except Exception as e:
        st.error(f"Erro ao obter conta: {e}")

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Bolsa EUA", us_txt)
    c2.metric("Cripto 24/7", "🟢 ABERTO")
    c3.metric("Nova Iorque", ny_txt)
    c4.metric("Saldo (Cash)", cash_txt)
    c5.metric("Equity", eq_txt)
    c6.metric("Buying Power", bp_txt)
    c7.metric("Modo", mode_txt)


def _render_live_chart(symbol: str, p2: int, p3: int, p4: int, p5: int, p6: int):
    """Gráfico candlestick + médias P2..P6 em tempo real (metade esquerda da Sala de Controlo)."""
    import plotly.graph_objects as go

    st.markdown(f"**📈 Gráfico ao Vivo — {symbol} (5m)**")
    df = st.session_state.get("alpaca_last_df")
    if df is None or df.empty or st.session_state.get("alpaca_last_symbol") != symbol:
        try:
            from alpaca_connector import get_ohlcv
            df_fetch = get_ohlcv(symbol, timeframe="5m", limit=max(p6 * 2, 120))
            if df_fetch is not None and not df_fetch.empty:
                df_fetch["P2"] = df_fetch["close"].rolling(p2).mean()
                df_fetch["P3"] = df_fetch["close"].rolling(p3).mean()
                df_fetch["P4"] = df_fetch["close"].rolling(p4).mean()
                df_fetch["P5"] = df_fetch["close"].rolling(p5).mean()
                df_fetch["P6"] = df_fetch["close"].rolling(p6).mean()
                df = df_fetch.tail(100)
                st.session_state["alpaca_last_df"] = df
                st.session_state["alpaca_last_symbol"] = symbol
        except Exception as e:
            st.caption(f"A aguardar dados para o gráfico: {e}")
            return

    if df is None or df.empty:
        st.info("Inicia o bot para construir o gráfico em tempo real.")
        return

    df_plot = df.tail(100)
    fig = go.Figure()
    if all(c in df_plot.columns for c in ("open", "high", "low", "close")):
        fig.add_trace(go.Candlestick(
            x=df_plot.index,
            open=df_plot["open"],
            high=df_plot["high"],
            low=df_plot["low"],
            close=df_plot["close"],
            name=symbol,
            increasing_line_color="#10b981",
            decreasing_line_color="#ef4444",
        ))
    else:
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["close"], name=symbol, line=dict(color="#60a5fa", width=2)))

    ma_styles = [
        ("P2", f"P2 ({p2})", "#3b82f6", 1.5),
        ("P3", f"P3 ({p3})", "#f59e0b", 1.5),
        ("P4", f"P4 ({p4})", "#ec4899", 1.5),
        ("P5", f"P5 ({p5})", "#8b5cf6", 1.5),
        ("P6", f"P6 ({p6})", "#10b981", 1.8),
    ]
    for col_name, label, color, width in ma_styles:
        if col_name in df_plot.columns:
            fig.add_trace(go.Scatter(
                x=df_plot.index,
                y=df_plot[col_name],
                name=label,
                line=dict(color=color, width=width),
                opacity=0.85,
            ))

    fig.update_layout(
        height=380,
        margin=dict(l=8, r=8, t=10, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0, font=dict(size=10)),
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
    )
    st.plotly_chart(fig, use_container_width=True)


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
    """Mostra resumo e download do histórico persistente de verificações de mercado (metade direita)."""
    from alpaca_bot_runner import get_checks_csv_file
    log_path = get_checks_csv_file()
    st.markdown("**🕒 Movimentos & Verificações (`alpaca_market_checks.csv`)**")
    if not log_path.exists():
        st.caption("Ainda sem registos. O histórico aparece aqui após o primeiro ciclo.")
        return
    try:
        df_log = pd.read_csv(log_path)
        c1, c2, c3 = st.columns([1, 1, 1.3])
        c1.metric("Verificações", len(df_log))
        c2.metric("Sinais", int(df_log["signal"].isin(["BUY", "SELL"]).sum()) if "signal" in df_log else 0)
        with c3:
            st.download_button(
                "⬇️ Exportar CSV",
                data=log_path.read_bytes(),
                file_name="alpaca_market_checks.csv",
                mime="text/csv",
                use_container_width=True,
            )
        cols_show = [c for c in ["timestamp_local", "symbol", "price", "signal", "order_action", "notes"] if c in df_log.columns]
        st.dataframe(df_log[cols_show].tail(20).iloc[::-1], use_container_width=True, hide_index=True, height=310)
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
        st.session_state["alpaca_last_df"] = df.tail(120).copy()
        st.session_state["alpaca_last_symbol"] = symbol
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
