"""
tab_stage3_live.py — Parte 3 do OlimpoTrade 2.0:
Sala de Controlo do Bot ON (Produção & Preparação VPS 24h) com travões de risco e Kill-Switch.
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
TRAINED_BEST_FILE = BASE_DIR / "trained_best_strategy.json"
CONTROL_FILE = BASE_DIR / "bot_live_control.json"
LOG_FILE = BASE_DIR / "trading_bot.log"

DEFAULT_CONTROL = {
    "enabled": False,
    "mode": "DRY_RUN",  # DRY_RUN (Simulação Segura) ou LIVE (Ordens Reais)
    "exchange": "kraken",
    "symbol": "BTC/EUR",
    "timeframe": "1h",
    "interval_seconds": 300,
    "capital_per_trade": 100.0,
    "max_daily_loss_pct": 3.0,
    "stop_loss_pct": 2.0,
    "take_profit_pct": 4.0,
    "pid": None,
    "updated_at": None,
}


def _load_json(path: Path, default: dict) -> dict:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return {**default, **data}
    except Exception:
        pass
    return dict(default)


def _save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _is_pid_running(pid) -> bool:
    if not pid:
        return False
    try:
        pid = int(pid)
        if os.name == "nt":
            out = subprocess.check_output(
                ["tasklist", "/FI", f"PID eq {pid}"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            return str(pid) in out
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False


def _stop_bot_process(ctrl: dict) -> None:
    pid = ctrl.get("pid")
    ctrl["enabled"] = False
    ctrl["pid"] = None
    ctrl["updated_at"] = datetime.now().isoformat()
    _save_json(CONTROL_FILE, ctrl)
    if pid:
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                os.kill(int(pid), 15)
        except Exception:
            pass


def render():
    st.markdown(
        """
        <div style="background:#ffffff;border:1px solid #e2e8f0;border-left:5px solid #059669;
                    border-radius:12px;padding:18px 22px;margin-bottom:18px;
                    box-shadow:0 2px 10px rgba(15,23,42,0.04);">
            <h3 style="margin:0 0 6px 0;color:#0f172a;font-size:1.25rem;">
                🤖 Parte 3 — Bot ON (Sala de Controlo & Preparação VPS 24h)
            </h3>
            <p style="margin:0;color:#475569;font-size:0.92rem;line-height:1.55;">
                Esta é a área final onde o robô autónomo (<code>main.py</code>) trabalha sozinho em segundo plano,
                seguindo <b>exclusivamente a estratégia que aprovaste na Parte 2</b> e protegido por travões automáticos de perda diária.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("ℹ️ Como funciona o Bot ON e a futura instalação na VPS 24h?", expanded=False):
        st.markdown(
            """
1. **Portão de Segurança:** O modo com dinheiro real (`LIVE`) permanece trancado até aprovares formalmente uma estratégia na **Parte 2**. Enquanto estiver em **`🛡️ Simulação Segura (Dry-Run)`**, o robô analisa o mercado real e regista todas as decisões no diário, mas **nunca gasta 1 €**.
2. **Independente do Navegador:** Quando clicas em **▶️ Ligar Motor do Bot**, ele corre em segundo plano (`main.py`). Mesmo que feches o navegador, na tua futura VPS ele continua a trabalhar 24h/dia.
3. **Travão Diário & Botão de Emergência:** Se num dia o mercado correr mal e atingir a *Perda Máxima Diária* (ex.: `3%`), o robô suspende novas compras sozinho. E tens sempre o botão vermelho **🛑 PARAR BOT IMEDIATAMENTE**.
"""
        )

    best = _load_json(TRAINED_BEST_FILE, {})
    ctrl = _load_json(CONTROL_FILE, DEFAULT_CONTROL)
    is_validated = bool(best.get("validated_for_live", False))
    running_now = bool(ctrl.get("enabled")) and _is_pid_running(ctrl.get("pid"))
    if ctrl.get("enabled") and not running_now:
        ctrl["enabled"] = False
        ctrl["pid"] = None
        _save_json(CONTROL_FILE, ctrl)

    # ── 1. Estado Atual & Semáforo de Segurança ───────────────────────────────
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Estado do Motor", "🟢 LIGADO" if running_now else "⚪ DESLIGADO")
    s2.metric("Modo de Segurança", "🛡️ DRY-RUN (Sem Risco)" if ctrl["mode"] == "DRY_RUN" else "🔴 PRODUÇÃO REAL")
    s3.metric("Estratégia Aprovada", best.get("strategy_type", "Nenhuma") if is_validated else "🔒 Aguarda Parte 2")
    s4.metric("Travão Perda Diária", f"-{ctrl['max_daily_loss_pct']:.1f}%")

    if not is_validated:
        st.warning(
            "🔒 **Modo Real bloqueado por segurança:** Ainda não existe nenhuma estratégia marcada como validada na **Parte 2**. "
            "Podes configurar tudo abaixo e testar o motor em **🛡️ Simulação Segura (Dry-Run)**."
        )

    st.divider()

    # ── 2. Configuração Sóbria do Motor ───────────────────────────────────────
    col_cfg, col_ctrl = st.columns([2.2, 1.2], gap="large")

    with col_cfg:
        st.markdown("#### ⚙️ Parâmetros de Operação Autónoma")
        c1, c2, c3 = st.columns(3)
        exchanges = ["alpaca", "kraken", "coinbase", "bitget", "bybit", "binance"]
        ex_idx = exchanges.index(ctrl["exchange"]) if ctrl["exchange"] in exchanges else 0
        new_exchange = c1.selectbox("Corretora (CCXT / Alpaca)", exchanges, index=ex_idx, key="s3_ex")
        new_symbol = c2.text_input("Par de Mercado", value=ctrl.get("symbol", "BTC/EUR"), key="s3_sym")
        tf_opts = ["5m", "15m", "1h", "4h"]
        tf_idx = tf_opts.index(ctrl["timeframe"]) if ctrl["timeframe"] in tf_opts else 2
        new_tf = c3.selectbox("Horizonte (Timeframe)", tf_opts, index=tf_idx, key="s3_tf")

        c4, c5, c6 = st.columns(3)
        new_cap = c4.number_input("Capital Base (€/$)", min_value=20.0, value=float(ctrl.get("capital_per_trade", 100.0)), step=50.0, key="s3_cap")
        new_daily_loss = c5.number_input("Travão Perda Diária (%)", min_value=0.5, max_value=20.0, value=float(ctrl.get("max_daily_loss_pct", 3.0)), step=0.5, key="s3_mdl")
        new_interval = c6.selectbox(
            "Verificar Mercado a cada",
            options=[60, 300, 900, 3600],
            index=[60, 300, 900, 3600].index(ctrl["interval_seconds"]) if ctrl["interval_seconds"] in [60, 300, 900, 3600] else 1,
            format_func=lambda s: f"{s // 60} min" if s < 3600 else "1 hora",
            key="s3_int",
        )

        mode_options = ["DRY_RUN"] + (["LIVE"] if is_validated else [])
        new_mode = st.radio(
            "Modo de Execução:",
            options=mode_options,
            index=0 if ctrl.get("mode") != "LIVE" or not is_validated else 1,
            format_func=lambda m: "🛡️ Simulação Segura (Dry-Run — Analisa ao vivo mas NÃO envia dinheiro real)" if m == "DRY_RUN" else "🔴 Produção Real (Envia ordens reais para a corretora)",
            key="s3_mode",
        )

        if st.button("💾 Guardar Definições do Bot", use_container_width=True, key="s3_save_btn"):
            ctrl.update({
                "exchange": new_exchange,
                "symbol": new_symbol,
                "timeframe": new_tf,
                "capital_per_trade": float(new_cap),
                "max_daily_loss_pct": float(new_daily_loss),
                "interval_seconds": int(new_interval),
                "mode": new_mode,
                "updated_at": datetime.now().isoformat(),
            })
            _save_json(CONTROL_FILE, ctrl)
            st.toast("💾 Definições do Bot guardadas com sucesso!")
            st.rerun()

    with col_ctrl:
        st.markdown("#### 🎛️ Comando & Emergência")
        st.caption("Controla o processo autónomo `main.py` em segundo plano.")

        if not running_now:
            if st.button("▶️ Ligar Motor do Bot (Background)", type="primary", use_container_width=True, key="s3_start_btn"):
                ctrl.update({
                    "enabled": True,
                    "exchange": new_exchange,
                    "symbol": new_symbol,
                    "timeframe": new_tf,
                    "capital_per_trade": float(new_cap),
                    "max_daily_loss_pct": float(new_daily_loss),
                    "interval_seconds": int(new_interval),
                    "mode": new_mode,
                    "updated_at": datetime.now().isoformat(),
                })
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                proc = subprocess.Popen(
                    [sys.executable, str(BASE_DIR / "main.py")],
                    cwd=str(BASE_DIR),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creationflags,
                )
                ctrl["pid"] = proc.pid
                _save_json(CONTROL_FILE, ctrl)
                st.toast(f"🟢 Motor autónomo iniciado (PID {proc.pid})!")
                st.rerun()
        else:
            st.success(f"🟢 Motor ativo em segundo plano (PID: `{ctrl.get('pid')}`).")

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        if st.button("🛑 PARAR BOT IMEDIATAMENTE (Kill-Switch)", use_container_width=True, key="s3_kill_btn"):
            _stop_bot_process(ctrl)
            st.toast("🛑 Bot desligado imediatamente com segurança.")
            st.rerun()

    st.divider()

    # ── 3. Diário em Tempo Real (Logs) ────────────────────────────────────────
    col_l1, col_l2 = st.columns([4, 1])
    col_l1.markdown("#### 📜 Diário de Atividade do Motor (`trading_bot.log`)")
    if col_l2.button("🔄 Atualizar Diário", use_container_width=True, key="s3_refresh_log"):
        st.rerun()

    if LOG_FILE.exists():
        try:
            lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()[-25:]
            st.code("\n".join(lines) if lines else "Diário vazio.", language="text")
        except Exception as exc:
            st.warning(f"Não foi possível ler o diário: {exc}")
    else:
        st.info("O ficheiro `trading_bot.log` aparecerá aqui assim que o motor for ligado pela primeira vez.")
