"""
strategy_report_generator.py — Gerador de Relatório Quantitativo Completo (.md)
para diagnóstico profundo de estratégias por IA e arquivo de testes.
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
LATEST_REPORT_PATH = BASE_DIR / "ultimo_relatorio_estrategia.md"
REPORTS_DIR = BASE_DIR / "relatorios"


def generate_arena_report(df: pd.DataFrame, trades: List[Dict[str, Any]], state: Dict[str, Any]) -> str:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    strat_name = state.get("tg_strategy_type", "Desconhecida")
    trader_name = state.get("tg_trader_name", "Sessão")
    symbol_raw = state.get("symbol_val", "Cenário Didático")
    scenario = state.get("math_scenario", "Didatico Classico")
    noise = state.get("math_noise", 1.0)
    max_candles = int(state.get("tg_max_candles", 100))
    final_cap = float(state.get("tg_capital", 100.0))
    ret_pct = final_cap - 100.0
    fee_pct = float(state.get("fee_pct_val", 0.1))
    slip_pct = float(state.get("slippage_pct_val", 0.05))
    tax_pct = float(state.get("tax_pct_val", 28.0))
    ret_net_tax = ret_pct - (max(0.0, ret_pct) * (tax_pct / 100.0))

    # ── 1. Radiografia do Mercado Jogado ──────────────────────────────────────
    start_idx = 144
    end_idx = min(len(df), start_idx + max_candles + 1) if df is not None else 0
    sub_df = df.iloc[start_idx:end_idx] if (df is not None and len(df) > start_idx) else df

    if sub_df is not None and not sub_df.empty and "close" in sub_df.columns:
        p_start = float(sub_df["close"].iloc[0])
        p_end = float(sub_df["close"].iloc[-1])
        p_min = float(sub_df["close"].min())
        p_max = float(sub_df["close"].max())
        bh_ret = ((p_end - p_start) / p_start * 100.0) if p_start > 0 else 0.0
        amp_pct = ((p_max - p_min) / p_min * 100.0) if p_min > 0 else 0.0
        if "adx_14" in sub_df.columns:
            adx_s = sub_df["adx_14"].dropna()
            pct_lat = float((adx_s <= 25.0).mean() * 100.0) if len(adx_s) else 0.0
            pct_trend = 100.0 - pct_lat
            adx_mean = float(adx_s.mean()) if len(adx_s) else 0.0
        else:
            pct_lat, pct_trend, adx_mean = 0.0, 0.0, 0.0
        rsi_mean = float(sub_df["rsi_14"].dropna().mean()) if "rsi_14" in sub_df.columns else 50.0
    else:
        p_start = p_end = p_min = p_max = bh_ret = amp_pct = pct_lat = pct_trend = adx_mean = 0.0
        rsi_mean = 50.0

    # ── 2. Estatísticas de Operações ──────────────────────────────────────────
    n_trades = len(trades)
    wins = [t for t in trades if float(t.get("pnl_pct", 0.0)) > 0]
    losses = [t for t in trades if float(t.get("pnl_pct", 0.0)) <= 0]
    longs = [t for t in trades if t.get("type") == "LONG"]
    shorts = [t for t in trades if t.get("type") == "SHORT"]
    long_wins = sum(1 for t in longs if float(t.get("pnl_pct", 0.0)) > 0)
    short_wins = sum(1 for t in shorts if float(t.get("pnl_pct", 0.0)) > 0)

    wr_total = (len(wins) / n_trades * 100.0) if n_trades else 0.0
    wr_long = (long_wins / len(longs) * 100.0) if longs else 0.0
    wr_short = (short_wins / len(shorts) * 100.0) if shorts else 0.0

    gross_sum_pct = sum(float(t.get("pnl_pct", 0.0)) for t in trades)
    est_fees_pct = n_trades * (fee_pct + slip_pct) * 2.0
    avg_win = (sum(float(t.get("pnl_pct", 0.0)) for t in wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(float(t.get("pnl_pct", 0.0)) for t in losses) / len(losses)) if losses else 0.0
    sum_pos_eur = sum(float(t.get("pnl_eur", 0.0)) for t in trades if float(t.get("pnl_eur", 0.0)) > 0)
    sum_neg_eur = abs(sum(float(t.get("pnl_eur", 0.0)) for t in trades if float(t.get("pnl_eur", 0.0)) < 0))
    profit_factor = (sum_pos_eur / sum_neg_eur) if sum_neg_eur > 0 else (99.0 if sum_pos_eur > 0 else 0.0)

    # Max Drawdown sobre curva de capital realizada
    eq = 100.0
    peak = 100.0
    max_dd_pct = 0.0
    for t in trades:
        eq += float(t.get("pnl_eur", 0.0))
        if eq > peak:
            peak = eq
        dd = ((eq - peak) / peak * 100.0) if peak > 0 else 0.0
        if dd < max_dd_pct:
            max_dd_pct = dd

    avg_dur_w = (sum(int(t.get("candles", 0)) for t in wins) / len(wins)) if wins else 0.0
    avg_dur_l = (sum(int(t.get("candles", 0)) for t in losses) / len(losses)) if losses else 0.0

    # ── 3. Agrupamento por Motivo de Saída e por Regime ADX na Entrada ────────
    by_reason: Dict[str, List[float]] = {}
    lat_trades, trend_trades = [], []
    for t in trades:
        r = str(t.get("reason", "Outro"))
        by_reason.setdefault(r, []).append(float(t.get("pnl_pct", 0.0)))
        in_step = int(t.get("entry_step", -1))
        ent_adx = None
        if df is not None and "adx_14" in df.columns and 0 <= in_step < len(df):
            val = df["adx_14"].iloc[in_step]
            ent_adx = float(val) if pd.notna(val) else None
        if ent_adx is not None:
            if ent_adx <= 25.0:
                lat_trades.append(t)
            else:
                trend_trades.append(t)

    def _fmt_bucket(bucket: List[Dict[str, Any]]) -> str:
        if not bucket:
            return "0 trades"
        bw = sum(1 for x in bucket if float(x.get("pnl_pct", 0.0)) > 0)
        b_avg = sum(float(x.get("pnl_pct", 0.0)) for x in bucket) / len(bucket)
        b_tot = sum(float(x.get("pnl_pct", 0.0)) for x in bucket)
        return f"{len(bucket)} trades | WR: {bw/len(bucket)*100:.0f}% | PnL Médio: {b_avg:+.2f}% | Soma PnL: {b_tot:+.2f}%"

    lines = [
        f"# 📊 Relatório de Diagnóstico de Estratégia — {trader_name}",
        f"- **Gerado em:** {now_str}",
        f"- **Estratégia Ativa:** `{strat_name}`",
        f"- **Ativo / Fonte:** `{symbol_raw}`" + (f" (Cenário: `{scenario}` | Ruído: `{noise}`)" if "Cenário" in str(symbol_raw) else ""),
        f"- **Velas Jogadas:** `{max_candles}`",
        "",
        "## 1. Parâmetros & Travões Configurados",
        f"- **Vetor SMAs (P2..P6):** `[{state.get('tg_p2', 5)}, {state.get('tg_p3', 13)}, {state.get('tg_p4', 21)}, {state.get('tg_p5', 55)}, {state.get('tg_p6', 144)}]`",
        f"- **Stop Loss:** `{state.get('tg_sl_pct', 0)}%` | **Take Profit:** `{state.get('tg_tp_pct', 0)}%` | **Trailing Stop:** `{state.get('tg_ts_pct', 0)}%` (Ativo: `{state.get('tg_ts_active', False)}`)",
        f"- **Custos:** Taxa `{fee_pct}%` + Slippage `{slip_pct}%` por ordem (`{(fee_pct+slip_pct)*2:.2f}%` ida e volta) | IRS `{tax_pct}%`",
        f"- **Filtros Extras:** Confiança Mín `{state.get('tg_min_confidence_pct', 80)}%` | Dispersão Mín `{state.get('tg_lagarta_min_disp', 0)}` | MACD `{state.get('tg_filter_macd_active', False)}` | Momentum `{state.get('tg_filter_momentum_active', False)}` | Squeeze `{state.get('tg_filter_squeeze_active', False)}` | 1 Mov/Vela `{state.get('tg_only_one_move_per_candle', True)}`",
        "",
        "## 2. Radiografia do Mercado (O Terreno)",
        f"- **Preço Inicial → Final:** `{p_start:.2f}` → `{p_end:.2f}` (**Buy & Hold:** `{bh_ret:+.2f}%`)",
        f"- **Mínimo / Máximo:** `{p_min:.2f}` / `{p_max:.2f}` (**Amplitude Total:** `{amp_pct:.2f}%`)",
        f"- **Regime Dominante:** `{pct_lat:.1f}%` das velas em Lateral (`ADX ≤ 25`) vs `{pct_trend:.1f}%` em Tendência (`ADX > 25`)",
        f"- **ADX Médio:** `{adx_mean:.1f}` | **RSI Médio:** `{rsi_mean:.1f}`",
        "",
        "## 3. Desempenho Financeiro & Estatístico",
        f"- **Banca Final:** `{final_cap:.2f} EUR` (Inicial: `100.00 EUR`)",
        f"- **Retorno após Comissões:** `{ret_pct:+.2f}%` | **Líquido após IRS ({tax_pct:.0f}%):** `{ret_net_tax:+.2f}%`",
        f"- **Soma PnL Bruto das Operações (antes de taxas):** `{gross_sum_pct:+.2f}%` | **Peso Estimado das Taxas/Slippage:** `-{est_fees_pct:.2f}%`",
        f"- **Total de Operações:** `{n_trades}` | **Win Rate Global:** `{wr_total:.1f}%` (`{len(wins)}V / {len(losses)}D`)",
        f"- **Win Rate por Direção:** LONG `{wr_long:.1f}%` (`{long_wins}/{len(longs)}`) | SHORT `{wr_short:.1f}%` (`{short_wins}/{len(shorts)}`)",
        f"- **Ganho Médio (Bruto):** `{avg_win:+.2f}%` | **Perda Média (Bruta):** `{avg_loss:+.2f}%` | **Fator de Lucro (Líquido):** `{profit_factor:.2f}`",
        f"- **Max Drawdown Realizado:** `{max_dd_pct:.2f}%` | **Duração Média:** Vencedores `{avg_dur_w:.1f}` velas vs Perdedores `{avg_dur_l:.1f}` velas",
        "",
        "## 4. Desempenho por Regime ADX na Entrada & Motivo de Saída",
        f"- **Entradas em Mercado Lateral (`ADX ≤ 25`):** {_fmt_bucket(lat_trades)}",
        f"- **Entradas em Tendência Forte (`ADX > 25`):** {_fmt_bucket(trend_trades)}",
        "",
        "| Motivo de Saída | Operações | Win Rate | PnL Médio Bruto | Soma PnL |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]

    for r_name, pnls in by_reason.items():
        rw = sum(1 for p in pnls if p > 0) / len(pnls) * 100.0
        lines.append(f"| {r_name} | {len(pnls)} | {rw:.0f}% | {sum(pnls)/len(pnls):+.2f}% | {sum(pnls):+.2f}% |")

    lines.extend([
        "",
        "## 5. Lista Completa de Operações (Indicadores no Momento Exato da Entrada)",
        "| # | Dir | Velas (In→Out) | Dur | Preço (In→Out) | PnL Bruto | PnL EUR | ADX In | RSI In | MACD In | Disp In | Motivo Saída |",
        "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |",
    ])

    for idx, t in enumerate(trades):
        in_s = int(t.get("entry_step", -1))
        out_s = int(t.get("exit_step", -1))
        adx_in = rsi_in = macd_in = disp_in = "-"
        if df is not None and 0 <= in_s < len(df):
            row = df.iloc[in_s]
            if "adx_14" in df.columns and pd.notna(row.get("adx_14")):
                adx_in = f"{float(row['adx_14']):.1f}"
            if "rsi_14" in df.columns and pd.notna(row.get("rsi_14")):
                rsi_in = f"{float(row['rsi_14']):.1f}"
            if "macd_hist" in df.columns and pd.notna(row.get("macd_hist")):
                macd_in = f"{float(row['macd_hist']):+.3f}"
            if "sma_std" in df.columns and pd.notna(row.get("sma_std")):
                disp_in = f"{float(row['sma_std']):.2f}"

        lines.append(
            f"| {idx} | {t.get('type','')} | {in_s}→{out_s} | {t.get('candles',0)}v | "
            f"{float(t.get('entry_price',0)):.2f}→{float(t.get('exit_price',0)):.2f} | "
            f"{float(t.get('pnl_pct',0)):+.2f}% | {float(t.get('pnl_eur',0)):+.2f}€ | "
            f"{adx_in} | {rsi_in} | {macd_in} | {disp_in} | {t.get('reason','')} |"
        )

    report_md = "\n".join(lines) + "\n"
    try:
        LATEST_REPORT_PATH.write_text(report_md, encoding="utf-8")
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in str(trader_name))[:40]
        hist_file = REPORTS_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_name}.md"
        hist_file.write_text(report_md, encoding="utf-8")
    except Exception:
        pass
    return report_md
