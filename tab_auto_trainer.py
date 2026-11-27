"""
tab_auto_trainer.py — Aba integrada de Treino Automático & Promoção de Estratégias no OlimpoTrade.
Reutiliza diretamente o motor de strategy_trainer_api.py dentro da mesma aplicação Streamlit.
"""
import itertools
import pandas as pd
import streamlit as st

from strategy_trainer_api import (
    SUPPORTED_STRATEGIES,
    BacktestRequest,
    PromoteRequest,
    _load_market_df,
    _run_single_backtest_sync,
    get_active_dna,
    list_market_symbols,
    promote_strategy,
    run_backtest,
)


def render():
    st.markdown("### 🤖 Centro de Treino & Otimização Automática")
    st.caption(
        "Testa rapidamente uma estratégia ou deixa o computador experimentar dezenas de combinações "
        "para encontrar a mais rentável e promovê-la com 1 clique."
    )

    with st.expander("ℹ️ Como funciona esta aba (Treino Automático)?", expanded=False):
        st.markdown("""
**Para que serve:** Permite-te testar ou otimizar estratégias de forma rápida e promover a melhor configuração para ser a estratégia oficial do teu bot (`trained_best_strategy.json` e `user_preferences.json`).

1. **🧬 Estratégia Oficial Ativa:** Mostra no topo qual é a estratégia atualmente promovida.
2. **⚡ 1. Teste Rápido:** Escolhes uma moeda, estratégia, Stop Loss e Take Profit, clicas em **▶ Correr Teste Agora** e vês os resultados em segundos.
3. **🔬 2. Treino Automático:** Escolhes várias estratégias e listas de parâmetros; o programa testa todas as combinações e mostra o **Top 10**.
4. **⭐ Promover:** Com 1 clique guardas a melhor estratégia como oficial para o projeto.
""")

    # ── Estratégia Oficial Ativa ──
    dna_info = get_active_dna()
    best = dna_info.get("trained_best") or {}
    prefs = dna_info.get("user_preferences") or {}
    if best.get("strategy_type"):
        st.success(
            f"🧬 **Estratégia Oficial Ativa:** `{best['strategy_type']}` em **{best.get('symbol', 'BTC/USDT')} "
            f"({best.get('timeframe', '1h')})** | Parâmetros: `{best.get('params', {})}`"
        )
    elif prefs.get("STRATEGY_TYPE"):
        st.info(
            f"🧬 **Configuração Atual (`user_preferences.json`):** `{prefs.get('STRATEGY_TYPE')}` "
            f"em **{prefs.get('SYMBOL', 'BTC/USDT')}**."
        )
    else:
        st.info("ℹ️ Nenhuma estratégia promovida ainda. Corre um teste ou treino abaixo!")

    # ── Pares disponíveis na base local ──
    symbols_data = list_market_symbols().get("symbols", [])
    if symbols_data:
        symbol_options = [f"{s['symbol']} ({s['timeframe']}) — {s['candles']} velas" for s in symbols_data]
        symbol_map = {
            f"{s['symbol']} ({s['timeframe']}) — {s['candles']} velas": (s["symbol"], s["timeframe"])
            for s in symbols_data
        }
    else:
        symbol_options = ["BTC/USDT (1h) — Simulação Sintética"]
        symbol_map = {"BTC/USDT (1h) — Simulação Sintética": ("BTC/USDT", "1h")}

    col_left, col_right = st.columns(2, gap="large")

    # ── 1. Teste Rápido ──
    with col_left:
        st.markdown("#### ⚡ 1. Teste Rápido (1 Estratégia)")
        sel_sym_label = st.selectbox("Moeda / Timeframe", symbol_options, key="at_bt_sym")
        bt_symbol, bt_tf = symbol_map[sel_sym_label]
        bt_strat = st.selectbox("Estratégia", list(SUPPORTED_STRATEGIES.keys()), key="at_bt_strat")

        c1, c2, c3 = st.columns(3)
        bt_cap = c1.number_input("Capital Inicial", min_value=10.0, value=1000.0, step=100.0, key="at_bt_cap")
        bt_short = c2.number_input("Média Rápida", min_value=2, max_value=100, value=9, step=1, key="at_bt_short")
        bt_long = c3.number_input("Média Lenta", min_value=5, max_value=300, value=21, step=1, key="at_bt_long")

        c4, c5, c6 = st.columns(3)
        bt_sl = c4.number_input("Stop Loss (%)", min_value=0.1, max_value=50.0, value=2.0, step=0.5, key="at_bt_sl")
        bt_tp = c5.number_input("Take Profit (%)", min_value=0.1, max_value=200.0, value=5.0, step=0.5, key="at_bt_tp")
        bt_ts = c6.checkbox("Trailing Stop", value=False, key="at_bt_ts")

        if st.button("▶ Correr Teste Agora", type="primary", use_container_width=True, key="at_btn_single"):
            with st.spinner("A simular estratégia..."):
                req = BacktestRequest(
                    symbol=bt_symbol,
                    timeframe=bt_tf,
                    limit=500,
                    strategy_type=bt_strat,
                    initial_capital=float(bt_cap),
                    stop_loss_percent=float(bt_sl),
                    take_profit_percent=float(bt_tp),
                    trailing_stop_active=bool(bt_ts),
                    strategy_params={"SHORT_WINDOW": int(bt_short), "LONG_WINDOW": int(bt_long)},
                    use_synthetic_if_missing=True,
                )
                res = run_backtest(req)
                res["symbol"] = bt_symbol
                res["timeframe"] = bt_tf
                st.session_state["at_last_single"] = res

        last_single = st.session_state.get("at_last_single")
        if last_single:
            m = last_single.get("metrics", {})
            k1, k2, k3 = st.columns(3)
            k1.metric("Retorno Total", f"{m.get('total_return_pct', 0):+.2f}%")
            k2.metric("Win Rate", f"{m.get('win_rate', 0):.1f}%")
            k3.metric("Trades", f"{m.get('num_trades', 0)}")
            k4, k5, k6 = st.columns(3)
            k4.metric("Capital Final", f"{m.get('final_capital', 0):.2f}")
            k5.metric("Max Drawdown", f"{m.get('max_drawdown_pct', 0):.2f}%")
            k6.metric("Fator de Lucro", f"{m.get('profit_factor', 0):.2f}")
            st.caption(f"Fonte: `{last_single.get('data_source')}` ({last_single.get('candles_used')} velas)")

            if st.button("⭐ Promover esta Estratégia", use_container_width=True, key="at_btn_promote_single"):
                promote_strategy(
                    PromoteRequest(
                        strategy_type=last_single["strategy_type"],
                        symbol=last_single["symbol"],
                        timeframe=last_single["timeframe"],
                        params=last_single.get("params", {}),
                        metrics=m,
                        update_user_preferences=True,
                    )
                )
                st.toast("⭐ Estratégia promovida e guardada com sucesso!")
                st.rerun()

    # ── 2. Treino Automático (Otimização) ──
    with col_right:
        st.markdown("#### 🔬 2. Treino Automático (Encontrar a Melhor)")
        opt_sym_label = st.selectbox("Moeda / Timeframe para Treino", symbol_options, key="at_opt_sym")
        opt_symbol, opt_tf = symbol_map[opt_sym_label]

        opt_strats = st.multiselect(
            "Estratégias a testar",
            list(SUPPORTED_STRATEGIES.keys()),
            default=["CAMALEAO_ADX", "BB_RSI_REVERSION", "PAULO_GOLD", "EMA_CROSSOVER"],
            key="at_opt_strats",
        )
        opt_rank = st.selectbox(
            "Critério de Melhor Estratégia",
            ["total_return_pct", "sharpe_ratio", "profit_factor"],
            format_func=lambda x: {
                "total_return_pct": "Maior Retorno (%)",
                "sharpe_ratio": "Melhor Sharpe Ratio",
                "profit_factor": "Maior Fator de Lucro",
            }[x],
            key="at_opt_rank",
        )

        o1, o2 = st.columns(2)
        shorts_str = o1.text_input("Médias Rápidas", value="5, 9, 15", key="at_opt_shorts")
        longs_str = o2.text_input("Médias Lentas", value="21, 50", key="at_opt_longs")
        o3, o4 = st.columns(2)
        sls_str = o3.text_input("Stop Loss (%)", value="1.0, 2.0", key="at_opt_sls")
        tps_str = o4.text_input("Take Profit (%)", value="3.0, 5.0", key="at_opt_tps")

        if st.button("🚀 Iniciar Treino Automático", type="primary", use_container_width=True, key="at_btn_opt"):
            try:
                shorts = [int(x.strip()) for x in shorts_str.split(",") if x.strip()]
                longs = [int(x.strip()) for x in longs_str.split(",") if x.strip()]
                sls = [float(x.strip()) for x in sls_str.split(",") if x.strip()]
                tps = [float(x.strip()) for x in tps_str.split(",") if x.strip()]
            except ValueError:
                st.error("Verifica os números separados por vírgula (ex: 5, 9, 15).")
                return

            if not opt_strats:
                st.warning("Seleciona pelo menos 1 estratégia.")
                return

            combos = [c for c in itertools.product(opt_strats, shorts, longs, sls, tps) if c[1] < c[2]]
            if not combos:
                st.warning("Nenhuma combinação válida (Média Rápida deve ser menor que Média Lenta).")
                return

            df, source = _load_market_df(opt_symbol, opt_tf, 500, use_synthetic_if_missing=True)
            prog = st.progress(0, text="A preparar treino...")
            results = []
            for idx, (strat, sw, lw, sl, tp) in enumerate(combos, start=1):
                req = BacktestRequest(
                    symbol=opt_symbol,
                    timeframe=opt_tf,
                    limit=500,
                    strategy_type=strat,
                    stop_loss_percent=sl,
                    take_profit_percent=tp,
                    strategy_params={"SHORT_WINDOW": sw, "LONG_WINDOW": lw},
                )
                res = _run_single_backtest_sync(df, req)
                res["symbol"] = opt_symbol
                res["timeframe"] = opt_tf
                results.append(res)
                prog.progress(idx / len(combos), text=f"A testar combinação {idx}/{len(combos)}...")

            results.sort(key=lambda r: float(r["metrics"].get(opt_rank, -999999)), reverse=True)
            st.session_state["at_opt_top"] = results[:10]
            st.session_state["at_opt_source"] = f"{source} ({len(df)} velas)"
            prog.empty()

    # ── Tabela Top 10 ──
    top_rows = st.session_state.get("at_opt_top")
    if top_rows:
        st.divider()
        st.markdown(f"#### 🏆 Top 10 Melhores Combinações ({st.session_state.get('at_opt_source', '')})")
        table_data = []
        for i, r in enumerate(top_rows, start=1):
            m = r["metrics"]
            p = r["params"]
            table_data.append({
                "#": i,
                "Estratégia": r["strategy_type"],
                "Médias": f"{p.get('SHORT_WINDOW', '-')}/{p.get('LONG_WINDOW', '-')}",
                "SL / TP": f"{p.get('STOP_LOSS_PERCENT')}% / {p.get('TAKE_PROFIT_PERCENT')}%",
                "Retorno (%)": round(float(m.get("total_return_pct", 0)), 2),
                "Win Rate (%)": round(float(m.get("win_rate", 0)), 1),
                "Trades": int(m.get("num_trades", 0)),
                "Drawdown (%)": round(float(m.get("max_drawdown_pct", 0)), 2),
            })
        st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

        pcol1, pcol2 = st.columns([2, 1])
        choice_idx = pcol1.selectbox(
            "Escolher combinação do Top 10 para promover:",
            options=list(range(len(top_rows))),
            format_func=lambda i: f"#{i+1} — {top_rows[i]['strategy_type']} ({top_rows[i]['params'].get('SHORT_WINDOW')}/{top_rows[i]['params'].get('LONG_WINDOW')}) -> {top_rows[i]['metrics'].get('total_return_pct', 0):+.2f}%",
            key="at_promote_choice",
        )
        if pcol2.button("⭐ Promover Selecionada", type="primary", use_container_width=True, key="at_btn_promote_top"):
            chosen = top_rows[choice_idx]
            promote_strategy(
                PromoteRequest(
                    strategy_type=chosen["strategy_type"],
                    symbol=chosen["symbol"],
                    timeframe=chosen["timeframe"],
                    params=chosen.get("params", {}),
                    metrics=chosen.get("metrics", {}),
                    update_user_preferences=True,
                )
            )
            st.toast("⭐ Estratégia campeã promovida com sucesso!")
            st.rerun()
