"""
tab_stage2_paper.py — Parte 2 do OlimpoTrade 2.0:
Testes em Tempo Real ligados à API em modo OFF (Paper Trading / Testnet, sem dinheiro real).
"""
import json
from datetime import datetime
from pathlib import Path
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
TRAINED_BEST_FILE = BASE_DIR / "trained_best_strategy.json"
PREFS_FILE = BASE_DIR / "user_preferences.json"


def _load_json(path: Path, default: dict) -> dict:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return dict(default)


def _save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def render():
    st.markdown(
        """
        <div style="background:#ffffff;border:1px solid #e2e8f0;border-left:5px solid #0284c7;
                    border-radius:12px;padding:18px 22px;margin-bottom:18px;
                    box-shadow:0 2px 10px rgba(15,23,42,0.04);">
            <h3 style="margin:0 0 6px 0;color:#0f172a;font-size:1.25rem;">
                📡 Parte 2 — Estágio em Tempo Real (API em OFF / Sem Risco Real)
            </h3>
            <p style="margin:0;color:#475569;font-size:0.92rem;line-height:1.55;">
                Depois de criares e testares uma estratégia na <b>Parte 1 (Laboratório)</b>, aqui deixas essa estratégia
                a observar o mercado ao vivo com <b>dinheiro virtual (Paper Trading / Testnet)</b>.
                Só quando estivermos confiantes nos resultados é que a aprovamos para a <b>Parte 3 (Bot ON)</b>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("ℹ️ O que devo fazer nesta Parte 2? (Passo a Passo)", expanded=False):
        st.markdown(
            """
1. **Confirmar a Receita Candidata:** Verifica no cartão abaixo qual é a estratégia trazida do Laboratório (ou carrega no botão para puxar a estratégia que tens selecionada atualmente no Centro de Comando).
2. **Testar em Tempo Real (Sem Dinheiro Real):** Usa um dos ambientes de *Paper Trading* abaixo para deixar a estratégia operar durante vários dias em condições reais de mercado.
3. **Aprovar para o Bot ON:** Quando tiveres pelo menos **15–20 operações**, **retorno líquido positivo** e **quedas controladas**, clica em **✅ Aprovar Estratégia para Parte 3 (Bot ON)**.
"""
        )

    best = _load_json(TRAINED_BEST_FILE, {})
    prefs = _load_json(PREFS_FILE, {})

    # ── Cartão da Estratégia Candidata & Portão de Aprovação ──────────────────
    st.markdown("#### 📋 1. Ficha da Estratégia em Estágio")
    col_info, col_actions = st.columns([2.2, 1.2], gap="large")

    current_ui_strat = st.session_state.get("tg_strategy_type", prefs.get("tg_strategy_type", "🦎 Camaleão ADX (3 Mercados — Lateral + Tendência)"))
    current_ui_sym = st.session_state.get("symbol_val", "BTC/USDT")
    if "Cenário Didático" in str(current_ui_sym):
        current_ui_sym = "BTC/USDT"

    with col_info:
        if best.get("strategy_type"):
            is_val = bool(best.get("validated_for_live", False))
            badge_bg = "#dcfce7" if is_val else "#fef3c7"
            badge_fg = "#166534" if is_val else "#92400e"
            badge_txt = "✅ VALIDADA PARA BOT ON (PARTE 3)" if is_val else "⏳ EM ESTÁGIO / TESTE PAPER"
            _p = best.get("params", {})
            _risk_line = (
                f"SL={_p.get('STOP_LOSS_PERCENT', '-')}% · "
                f"TP={_p.get('TAKE_PROFIT_PERCENT', '-')}% · "
                f"TS={_p.get('TRAILING_STOP_PERCENT', '-')}% ({'ON' if _p.get('TRAILING_STOP_ACTIVE') else 'OFF'}) · "
                f"P2–P3≥{_p.get('MIN_P2_P3_PCT', 0)}% · "
                f"Pausa SL={_p.get('SL_COOLDOWN_CANDLES', 0)}"
            )
            _smas_line = f"[{_p.get('SHORT_WINDOW', 5)}, {_p.get('P3_WINDOW', 13)}, {_p.get('LONG_WINDOW', 21)}, {_p.get('P5_WINDOW', 55)}, {_p.get('P6_WINDOW', 144)}]"
            st.markdown(
                f"""
                <div style="background:#f8fafc;border:1px solid #cbd5e1;border-radius:10px;padding:16px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
                        <strong style="color:#0f172a;font-size:1.02rem;">Estratégia: {best.get('strategy_label') or best.get('strategy_type')}</strong>
                        <span style="background:{badge_bg};color:{badge_fg};padding:4px 10px;border-radius:999px;font-size:0.75rem;font-weight:700;">
                            {badge_txt}
                        </span>
                    </div>
                    <div style="color:#334155;font-size:0.88rem;line-height:1.65;">
                        • <b>Ativo Base:</b> {best.get('symbol', 'BTC/USDT')} ({best.get('timeframe', '1h')})<br>
                        • <b>Médias Móveis:</b> <code>{_smas_line}</code><br>
                        • <b>Travões &amp; Filtros:</b> <code>{_risk_line}</code><br>
                        • <b>Última atualização:</b> {str(best.get('promoted_at', '-'))[:19].replace('T', ' ')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info(
                "Ainda não tens uma ficha de estratégia guardada. Podes usar o botão ao lado para importar já a "
                f"estratégia atual do Laboratório (**{current_ui_strat}**)."
            )

    with col_actions:
        if st.button("📥 Importar Estratégia Atual do Laboratório", use_container_width=True, key="s2_import_from_lab"):
            strat_map = {
                "🦎 Camaleão ADX (3 Mercados — Lateral + Tendência)": "CAMALEAO_ADX",
                "🎯 Reversão à Média (Bollinger + RSI)": "BB_RSI_REVERSION",
                "🤖 Claude — Pirâmide Fibonacci": "LAGARTA_2LINES",
                "Lagarta (Todas as Linhas)": "LAGARTA_5LINES",
                "Linha Solitária": "LAGARTA_1LINE",
                "Média Camadas (Duas Linhas)": "LAGARTA_2LINES",
                "Cérebro de Consenso (IA)": "QUANTUM_CONSENSUS",
            }
            mapped = strat_map.get(current_ui_strat, "CAMALEAO_ADX")
            new_best = {
                "promoted_at": datetime.now().isoformat(),
                "symbol": current_ui_sym,
                "timeframe": st.session_state.get("timeframe_val", "1h"),
                "strategy_type": mapped,
                "strategy_label": current_ui_strat,
                "validated_for_live": False,
                "params": {
                    "ADX_THRESHOLD": 27.0,
                    "STOP_LOSS_PERCENT": float(st.session_state.get("tg_sl_pct", 1.2) or 1.2),
                    "TAKE_PROFIT_PERCENT": float(st.session_state.get("tg_tp_pct", 6.0) or 6.0),
                    "TRAILING_STOP_PERCENT": float(st.session_state.get("tg_ts_pct", 1.0) or 1.0),
                    "TRAILING_STOP_ACTIVE": bool(st.session_state.get("tg_ts_pct_active", True)),
                    "SHORT_WINDOW": int(st.session_state.get("tg_p2", 5)),
                    "P3_WINDOW": int(st.session_state.get("tg_p3", 13)),
                    "LONG_WINDOW": int(st.session_state.get("tg_p4", 21)),
                    "P5_WINDOW": int(st.session_state.get("tg_p5", 55)),
                    "P6_WINDOW": int(st.session_state.get("tg_p6", 144)),
                    "MIN_P2_P3_PCT": float(st.session_state.get("tg_min_p2_p3_pct", 0.15) or 0.0),
                    "MIN_DISPERSION": float(st.session_state.get("tg_lagarta_min_disp", 0.0) or 0.0),
                    "SL_COOLDOWN_CANDLES": int(st.session_state.get("tg_sl_cooldown_candles", 0) or 0),
                },
            }
            _save_json(TRAINED_BEST_FILE, new_best)
            st.toast("📥 Estratégia trazida para Estágio na Parte 2!")
            st.rerun()

        if best.get("strategy_type"):
            if not best.get("validated_for_live", False):
                if st.button("✅ Aprovar para Parte 3 (Bot ON)", type="primary", use_container_width=True, key="s2_approve_live"):
                    best["validated_for_live"] = True
                    best["validated_at"] = datetime.now().isoformat()
                    _save_json(TRAINED_BEST_FILE, best)
                    st.toast("✅ Estratégia aprovada e disponível na Parte 3 (Bot ON)!")
                    st.rerun()
            else:
                if st.button("↩️ Voltar a colocar apenas em Estágio", use_container_width=True, key="s2_revoke_live"):
                    best["validated_for_live"] = False
                    _save_json(TRAINED_BEST_FILE, best)
                    st.toast("Estratégia regressou ao estado de Estágio.")
                    st.rerun()

    st.divider()

    # ── Sub-abas de Teste ao Vivo e Escolha de Corretora ──────────────────────
    sub_brokers, sub_alpaca, sub_crypto = st.tabs([
        "🌍 Opções de Corretora (Futuro)",
        "📊 Paper Trading — Alpaca (Ações & Cripto)",
        "🔶 Paper Trading — Cripto Testnet",
    ])

    with sub_brokers:
        st.markdown("#### 🌍 Preparado para Qualquer Corretora (Sem ficar preso à Binance)")
        st.markdown(
            """
Como o OlimpoTrade usa a biblioteca universal **`ccxt`**, quando decidirmos ligar o **Bot ON** na VPS podemos escolher a corretora mais vantajosa e regulada para Portugal/Europa sem ter de refazer as estratégias:

| Corretora | Pontos Fortes | Estado no OlimpoTrade |
| :--- | :--- | :--- |
| **Kraken / Kraken Pro** | Muito sólida na Europa (licença MiCA), taxas baixas em Pro e API muito estável | Suportada via `ccxt` (`kraken`) |
| **Coinbase Advanced** | Forte regulação europeia, simples para pares EUR (`BTC/EUR`, `ETH/EUR`) | Suportada via `ccxt` (`coinbase`) |
| **Bybit EU / Bitget** | Boas ferramentas de ordens automáticas (Stop Loss / Take Profit nativos) | Suportada via `ccxt` (`bybit`, `bitget`) |
| **Alpaca Markets** | Conta Paper gratuita excelente para testar 24h (Ações EUA + Cripto) | Já integrada na aba ao lado |
"""
        )

    with sub_alpaca:
        import tab_alpaca as _tab_alpaca
        _tab_alpaca.render()

    with sub_crypto:
        import tab_binance as _tab_binance
        _tab_binance.render()
