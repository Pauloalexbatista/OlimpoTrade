"""
strategy_trainer_api.py — FastAPI para treino, otimização e promoção automática de estratégias.

Execução:
    uvicorn strategy_trainer_api:app --reload --port 8000
"""
import asyncio
import itertools
import json
import logging
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from backtester import Backtester
from config import load_config
from market_database import MarketDatabase

BASE_DIR = Path(__file__).resolve().parent
MARKET_DB_PATH = BASE_DIR / "market_data.sqlite"
DNA_FILE = BASE_DIR / "bot_consensus_dna.json"
PREFS_FILE = BASE_DIR / "user_preferences.json"
TRAINED_BEST_FILE = BASE_DIR / "trained_best_strategy.json"

app = FastAPI(
    title="OlimpoTrade Strategy Trainer API",
    description="API REST para treinar, otimizar e promover estratégias de trading com backtesting real.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_JOBS: Dict[str, Dict[str, Any]] = {}
_JOBS_LOCK = threading.Lock()

SUPPORTED_STRATEGIES = {
    "SMA_CROSSOVER": ["SHORT_WINDOW", "LONG_WINDOW"],
    "EMA_CROSSOVER": ["SHORT_WINDOW", "LONG_WINDOW"],
    "PAULO_GOLD": ["SHORT_WINDOW", "LONG_WINDOW", "PAULO_GOLD_TREND_FILTER", "PAULO_GOLD_MIN_DIST_PCT"],
    "BB_RSI_REVERSION": ["BB_WINDOW", "BB_STD", "RSI_WINDOW", "BB_RSI_OVERSOLD", "BB_RSI_OVERBOUGHT"],
    "CAMALEAO_ADX": ["ADX_THRESHOLD", "SHORT_WINDOW", "P3_WINDOW", "LONG_WINDOW"],
    "MULTIPOINT_VECTOR": ["P2_WINDOW", "P3_WINDOW", "P4_WINDOW", "P5_WINDOW", "MULTIPOINT_MODE", "ENTRY_MODE", "EXIT_MODE"],
    "QUANTUM_CONSENSUS": [],
    "LAGARTA_1LINE": ["LAGARTA_REF_WINDOW"],
    "LAGARTA_2LINES": ["LAGARTA_P2", "LAGARTA_P3", "LAGARTA_P4", "LAGARTA_MODE", "LAGARTA_VEL_FILTER"],
    "LAGARTA_5LINES": ["LAGARTA_P2", "LAGARTA_P3", "LAGARTA_P4", "LAGARTA_P5", "LAGARTA_P6"],
}


def _null_logger() -> logging.Logger:
    logger = logging.getLogger("strategy_trainer_api")
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.WARNING)
    return logger


def _generate_synthetic_ohlcv(n_candles: int = 300, start_price: float = 50000.0, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    returns = rng.normal(loc=0.0002, scale=0.012, size=n_candles)
    close = start_price * np.exp(np.cumsum(returns))
    open_p = np.roll(close, 1)
    open_p[0] = start_price
    spread = np.abs(rng.normal(0.003, 0.002, size=n_candles))
    high = np.maximum(open_p, close) * (1.0 + spread)
    low = np.minimum(open_p, close) * (1.0 - spread)
    volume = rng.uniform(50.0, 500.0, size=n_candles)
    idx = pd.date_range(end=datetime.utcnow(), periods=n_candles, freq="1h")
    return pd.DataFrame(
        {"open": open_p, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


def _load_market_df(
    symbol: str,
    timeframe: str,
    limit: int,
    candles: Optional[List[Dict[str, Any]]] = None,
    use_synthetic_if_missing: bool = True,
) -> tuple[pd.DataFrame, str]:
    if candles:
        df = pd.DataFrame(candles)
        if "timestamp" in df.columns:
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", errors="coerce")
            df = df.set_index("datetime")
        else:
            df.index = pd.date_range(end=datetime.utcnow(), periods=len(df), freq="1h")
        return df[["open", "high", "low", "close", "volume"]].astype(float), "payload"

    if MARKET_DB_PATH.exists():
        db = MarketDatabase(str(MARKET_DB_PATH))
        df = db.get_data(symbol, timeframe, limit=limit)
        if df is not None and not df.empty:
            return df[["open", "high", "low", "close", "volume"]].astype(float), "market_data.sqlite"

    if use_synthetic_if_missing:
        return _generate_synthetic_ohlcv(n_candles=max(100, min(limit, 2000))), "synthetic_fallback"

    raise HTTPException(status_code=404, detail=f"Sem dados para {symbol} ({timeframe}) em market_data.sqlite.")


class CandleInput(BaseModel):
    timestamp: Optional[int] = None
    open: float
    high: float
    low: float
    close: float
    volume: float = 100.0


class BacktestRequest(BaseModel):
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    limit: int = Field(default=500, ge=50, le=5000)
    strategy_type: str = "SMA_CROSSOVER"
    initial_capital: float = Field(default=1000.0, gt=0)
    stop_loss_percent: float = Field(default=2.0, ge=0.1, le=50.0)
    take_profit_percent: float = Field(default=5.0, ge=0.1, le=200.0)
    trailing_stop_active: bool = False
    fee_percent: float = Field(default=0.1, ge=0.0, le=5.0)
    slippage_pct: float = Field(default=0.05, ge=0.0, le=5.0)
    tax_percent: float = Field(default=0.0, ge=0.0, le=50.0)
    strategy_params: Dict[str, Any] = Field(default_factory=dict)
    candles: Optional[List[CandleInput]] = None
    use_synthetic_if_missing: bool = True


class OptimizeRequest(BaseModel):
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    limit: int = Field(default=500, ge=50, le=5000)
    strategy_types: List[str] = Field(default_factory=lambda: ["SMA_CROSSOVER", "EMA_CROSSOVER", "PAULO_GOLD"])
    short_windows: List[int] = Field(default_factory=lambda: [5, 9, 15])
    long_windows: List[int] = Field(default_factory=lambda: [21, 50])
    stop_loss_percents: List[float] = Field(default_factory=lambda: [1.0, 2.0])
    take_profit_percents: List[float] = Field(default_factory=lambda: [3.0, 5.0])
    trailing_stop_options: List[bool] = Field(default_factory=lambda: [False])
    initial_capital: float = Field(default=1000.0, gt=0)
    rank_by: str = "total_return_pct"
    top_k: int = Field(default=10, ge=1, le=50)
    use_synthetic_if_missing: bool = True


class PromoteRequest(BaseModel):
    strategy_type: str
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    params: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    update_user_preferences: bool = True


def _run_single_backtest_sync(df: pd.DataFrame, req: BacktestRequest) -> Dict[str, Any]:
    cfg = load_config()
    cfg.update({
        "SYMBOL": req.symbol,
        "TIMEFRAME": req.timeframe,
        "STRATEGY_TYPE": req.strategy_type,
        "INITIAL_CAPITAL": req.initial_capital,
        "STOP_LOSS_PERCENT": req.stop_loss_percent,
        "TAKE_PROFIT_PERCENT": req.take_profit_percent,
        "TRAILING_STOP_ACTIVE": req.trailing_stop_active,
        "FEE_PERCENT": req.fee_percent,
        "SLIPPAGE_PCT": req.slippage_pct,
        "TAX_PERCENT": req.tax_percent,
    })
    cfg.update(req.strategy_params)

    bt = Backtester(cfg, _null_logger(), log_decisions=False)
    loop = asyncio.new_event_loop()
    try:
        trades, _ = loop.run_until_complete(bt.run_backtest(df))
    finally:
        loop.close()

    metrics = bt.get_performance_metrics()
    return {
        "strategy_type": req.strategy_type,
        "params": {
            "STOP_LOSS_PERCENT": req.stop_loss_percent,
            "TAKE_PROFIT_PERCENT": req.take_profit_percent,
            "TRAILING_STOP_ACTIVE": req.trailing_stop_active,
            **req.strategy_params,
        },
        "metrics": metrics,
        "trades_count": len(trades),
    }


def _execute_optimize_job(job_id: str, req: OptimizeRequest) -> None:
    try:
        df, source = _load_market_df(
            req.symbol, req.timeframe, req.limit, use_synthetic_if_missing=req.use_synthetic_if_missing
        )
        combos = list(itertools.product(
            req.strategy_types,
            req.short_windows,
            req.long_windows,
            req.stop_loss_percents,
            req.take_profit_percents,
            req.trailing_stop_options,
        ))
        valid_combos = [c for c in combos if c[1] < c[2]]

        with _JOBS_LOCK:
            _JOBS[job_id]["status"] = "running"
            _JOBS[job_id]["total"] = len(valid_combos)
            _JOBS[job_id]["data_source"] = source

        results = []
        for idx, (strat, sw, lw, sl, tp, ts) in enumerate(valid_combos, start=1):
            bt_req = BacktestRequest(
                symbol=req.symbol,
                timeframe=req.timeframe,
                limit=req.limit,
                strategy_type=strat,
                initial_capital=req.initial_capital,
                stop_loss_percent=sl,
                take_profit_percent=tp,
                trailing_stop_active=ts,
                strategy_params={"SHORT_WINDOW": sw, "LONG_WINDOW": lw},
            )
            res = _run_single_backtest_sync(df, bt_req)
            results.append(res)
            with _JOBS_LOCK:
                _JOBS[job_id]["completed"] = idx

        results.sort(key=lambda r: float(r["metrics"].get(req.rank_by, -999999)), reverse=True)
        with _JOBS_LOCK:
            _JOBS[job_id]["status"] = "completed"
            _JOBS[job_id]["finished_at"] = datetime.utcnow().isoformat()
            _JOBS[job_id]["top_results"] = results[: req.top_k]
    except Exception as exc:
        with _JOBS_LOCK:
            _JOBS[job_id]["status"] = "failed"
            _JOBS[job_id]["error"] = str(exc)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "market_db_exists": MARKET_DB_PATH.exists(),
        "strategies_count": len(SUPPORTED_STRATEGIES),
    }


@app.get("/strategies")
def list_strategies():
    return {"strategies": SUPPORTED_STRATEGIES}


@app.get("/market-data/symbols")
def list_market_symbols():
    if not MARKET_DB_PATH.exists():
        return {"symbols": []}
    with sqlite3.connect(str(MARKET_DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT symbol, timeframe, COUNT(*) as candles FROM ohlcv GROUP BY symbol, timeframe ORDER BY candles DESC"
        ).fetchall()
    return {
        "symbols": [{"symbol": r[0], "timeframe": r[1], "candles": r[2]} for r in rows]
    }


@app.post("/train/backtest")
def run_backtest(req: BacktestRequest):
    if req.strategy_type not in SUPPORTED_STRATEGIES:
        raise HTTPException(status_code=400, detail=f"Estratégia desconhecida: {req.strategy_type}")
    candles_payload = [c.model_dump() for c in req.candles] if req.candles else None
    df, source = _load_market_df(
        req.symbol,
        req.timeframe,
        req.limit,
        candles=candles_payload,
        use_synthetic_if_missing=req.use_synthetic_if_missing,
    )
    res = _run_single_backtest_sync(df, req)
    res["data_source"] = source
    res["candles_used"] = len(df)
    return res


@app.post("/train/jobs")
def start_optimize_job(req: OptimizeRequest):
    for s in req.strategy_types:
        if s not in SUPPORTED_STRATEGIES:
            raise HTTPException(status_code=400, detail=f"Estratégia desconhecida: {s}")
    job_id = str(uuid.uuid4())[:8]
    with _JOBS_LOCK:
        _JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "created_at": datetime.utcnow().isoformat(),
            "completed": 0,
            "total": 0,
            "top_results": [],
        }
    t = threading.Thread(target=_execute_optimize_job, args=(job_id, req), daemon=True)
    t.start()
    return {"job_id": job_id, "status": "queued"}


@app.get("/train/jobs/{job_id}")
def get_optimize_job(job_id: str):
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job não encontrado")
        return dict(job)


@app.get("/dna")
def get_active_dna():
    dna = json.loads(DNA_FILE.read_text(encoding="utf-8")) if DNA_FILE.exists() else {}
    prefs = json.loads(PREFS_FILE.read_text(encoding="utf-8")) if PREFS_FILE.exists() else {}
    best = json.loads(TRAINED_BEST_FILE.read_text(encoding="utf-8")) if TRAINED_BEST_FILE.exists() else {}
    return {"trained_best": best, "user_preferences": prefs, "consensus_dna_keys": list(dna.keys())}


@app.post("/dna/promote")
def promote_strategy(req: PromoteRequest):
    if req.strategy_type not in SUPPORTED_STRATEGIES:
        raise HTTPException(status_code=400, detail=f"Estratégia desconhecida: {req.strategy_type}")
    payload = {
        "promoted_at": datetime.utcnow().isoformat(),
        "symbol": req.symbol,
        "timeframe": req.timeframe,
        "strategy_type": req.strategy_type,
        "params": req.params,
        "metrics": req.metrics,
    }
    TRAINED_BEST_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    if req.update_user_preferences:
        prefs = json.loads(PREFS_FILE.read_text(encoding="utf-8")) if PREFS_FILE.exists() else {}
        prefs["STRATEGY_TYPE"] = req.strategy_type
        prefs["SYMBOL"] = req.symbol
        prefs["TIMEFRAME"] = req.timeframe
        for k, v in req.params.items():
            prefs[k] = v
        PREFS_FILE.write_text(json.dumps(prefs, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"ok": True, "saved_to": str(TRAINED_BEST_FILE.name), "updated_preferences": req.update_user_preferences}


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(DASHBOARD_HTML)


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OlimpoTrade — Centro de Treino</title>
<style>
  :root {
    --bg: #0b1120; --card: #111827; --border: #1f2937;
    --text: #f3f4f6; --muted: #9ca3af; --accent: #7c3aed;
    --accent2: #10b981; --danger: #ef4444; --warn: #f59e0b;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; padding: 24px; max-width: 1180px; margin: 0 auto; }
  header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--border); }
  h1 { font-size: 1.55rem; color: #fff; }
  .subtitle { color: var(--muted); font-size: 0.9rem; margin-top: 4px; }
  .pill { background: rgba(16,185,129,0.15); color: var(--accent2); border: 1px solid rgba(16,185,129,0.35); padding: 6px 12px; border-radius: 999px; font-size: 0.82rem; font-weight: 600; }
  .grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 18px; margin-bottom: 20px; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 20px; margin-bottom: 18px; }
  .card h2 { font-size: 1.08rem; margin-bottom: 6px; color: #e5e7eb; }
  .card p.desc { font-size: 0.85rem; color: var(--muted); margin-bottom: 16px; line-height: 1.45; }
  .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 14px; }
  label { display: block; font-size: 0.78rem; color: var(--muted); margin-bottom: 5px; }
  input, select { width: 100%; background: #0b1120; color: #fff; border: 1px solid #374151; border-radius: 8px; padding: 9px 10px; font-size: 0.9rem; }
  input:focus, select:focus { outline: none; border-color: var(--accent); }
  .btn { border: none; border-radius: 9px; padding: 11px 18px; font-size: 0.92rem; font-weight: 600; cursor: pointer; transition: 0.15s; display: inline-flex; align-items: center; gap: 8px; }
  .btn-primary { background: var(--accent); color: #fff; }
  .btn-primary:hover { background: #6d28d9; }
  .btn-green { background: var(--accent2); color: #052e16; }
  .btn-green:hover { background: #059669; color: #fff; }
  .btn-sm { padding: 6px 11px; font-size: 0.8rem; border-radius: 6px; }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-top: 16px; }
  .kpi { background: #0b1120; border: 1px solid var(--border); border-radius: 10px; padding: 12px; }
  .kpi .k-label { font-size: 0.72rem; color: var(--muted); text-transform: uppercase; }
  .kpi .k-val { font-size: 1.25rem; font-weight: 700; margin-top: 4px; font-family: monospace; }
  .pos { color: var(--accent2); } .neg { color: var(--danger); }
  .progress-wrap { background: #0b1120; border-radius: 8px; height: 10px; overflow: hidden; margin: 12px 0; border: 1px solid var(--border); }
  .progress-bar { background: linear-gradient(90deg, var(--accent), var(--accent2)); height: 100%; width: 0%; transition: width 0.3s; }
  table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 0.86rem; }
  th { text-align: left; color: var(--muted); font-weight: 600; padding: 9px 8px; border-bottom: 1px solid var(--border); }
  td { padding: 9px 8px; border-bottom: 1px solid #1a2234; }
  tr:hover td { background: rgba(255,255,255,0.02); }
  .checks { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 14px; }
  .checks label { display: flex; align-items: center; gap: 6px; font-size: 0.88rem; color: var(--text); cursor: pointer; margin: 0; }
  .checks input { width: auto; }
  .toast { position: fixed; bottom: 20px; right: 20px; background: #10b981; color: #052e16; padding: 12px 18px; border-radius: 10px; font-weight: 700; display: none; box-shadow: 0 10px 25px rgba(0,0,0,0.4); z-index: 99; }
  .info-box { background: rgba(124,58,237,0.1); border: 1px solid rgba(124,58,237,0.3); border-radius: 10px; padding: 12px 14px; font-size: 0.85rem; color: #ddd6fe; margin-bottom: 16px; line-height: 1.45; }
</style>
</head>
<body>
<header>
  <div>
    <h1>🏆 OlimpoTrade — Centro de Treino de Estratégias</h1>
    <div class="subtitle">Testa estratégias, descobre as melhores combinações e guarda a vencedora com 1 clique.</div>
  </div>
  <div class="pill" id="api-status">A ligar à API...</div>
</header>

<div class="card" id="active-dna-card">
  <h2>🧬 Estratégia Oficial Ativa</h2>
  <p class="desc" id="active-dna-text">A carregar configuração atual...</p>
</div>

<div class="grid2">
  <div class="card">
    <h2>⚡ 1. Teste Rápido (1 Estratégia)</h2>
    <p class="desc">Escolhe uma moeda e uma estratégia para ver imediatamente quanto teria ganho ou perdido.</p>
    <div class="form-grid">
      <div>
        <label>Moeda / Timeframe</label>
        <select id="bt-symbol"></select>
      </div>
      <div>
        <label>Estratégia</label>
        <select id="bt-strategy"></select>
      </div>
      <div>
        <label>Capital Inicial (€/$)</label>
        <input type="number" id="bt-capital" value="1000" min="10">
      </div>
      <div>
        <label>Média Rápida (Short)</label>
        <input type="number" id="bt-short" value="9" min="2" max="100">
      </div>
      <div>
        <label>Média Lenta (Long)</label>
        <input type="number" id="bt-long" value="21" min="5" max="300">
      </div>
      <div>
        <label>Stop Loss (%)</label>
        <input type="number" id="bt-sl" value="2.0" step="0.5" min="0.5">
      </div>
      <div>
        <label>Take Profit (%)</label>
        <input type="number" id="bt-tp" value="5.0" step="0.5" min="0.5">
      </div>
      <div>
        <label>Trailing Stop</label>
        <select id="bt-ts">
          <option value="false">Não</option>
          <option value="true">Sim</option>
        </select>
      </div>
    </div>
    <button class="btn btn-primary" onclick="runSingleBacktest()" id="btn-bt">▶ Correr Teste Agora</button>
    <div id="bt-results" style="display:none;">
      <div class="kpis" id="bt-kpis"></div>
      <div style="margin-top:14px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
        <span id="bt-source" style="font-size:0.8rem;color:var(--muted);"></span>
        <button class="btn btn-green btn-sm" onclick="promoteSingle()">⭐ Promover esta Estratégia</button>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>🔬 2. Treino Automático (Encontrar a Melhor)</h2>
    <p class="desc">O computador testa dezenas de combinações por ti e ordena as que dão mais lucro com menos risco.</p>
    <div class="form-grid">
      <div>
        <label>Moeda / Timeframe</label>
        <select id="opt-symbol"></select>
      </div>
      <div>
        <label>Ordenar Melhor Por</label>
        <select id="opt-rank">
          <option value="total_return_pct">Maior Retorno (%)</option>
          <option value="sharpe_ratio">Melhor Sharpe Ratio</option>
          <option value="profit_factor">Maior Fator de Lucro</option>
        </select>
      </div>
    </div>
    <label>Estratégias a testar</label>
    <div class="checks" id="opt-strategies">
      <label><input type="checkbox" value="SMA_CROSSOVER" checked> SMA Crossover</label>
      <label><input type="checkbox" value="EMA_CROSSOVER" checked> EMA Crossover</label>
      <label><input type="checkbox" value="PAULO_GOLD" checked> Paulo Gold</label>
    </div>
    <div class="form-grid">
      <div>
        <label>Médias Rápidas (ex: 5, 9, 15)</label>
        <input type="text" id="opt-shorts" value="5, 9, 15">
      </div>
      <div>
        <label>Médias Lentas (ex: 21, 50)</label>
        <input type="text" id="opt-longs" value="21, 50">
      </div>
      <div>
        <label>Stop Loss % (ex: 1.0, 2.0)</label>
        <input type="text" id="opt-sls" value="1.0, 2.0">
      </div>
      <div>
        <label>Take Profit % (ex: 3.0, 5.0)</label>
        <input type="text" id="opt-tps" value="3.0, 5.0">
      </div>
    </div>
    <button class="btn btn-primary" onclick="startOptimize()" id="btn-opt">🚀 Iniciar Treino Automático</button>
    <div id="opt-progress-area" style="display:none;margin-top:12px;">
      <div style="font-size:0.84rem;color:var(--muted);" id="opt-status-text">A preparar...</div>
      <div class="progress-wrap"><div class="progress-bar" id="opt-bar"></div></div>
    </div>
  </div>
</div>

<div class="card" id="opt-table-card" style="display:none;">
  <h2>🏆 Top Melhores Combinações Encontradas</h2>
  <p class="desc">Clica em <strong>"⭐ Usar Esta"</strong> na linha que preferires para a definir como estratégia oficial do teu bot.</p>
  <table>
    <thead>
      <tr>
        <th>#</th><th>Estratégia</th><th>Médias</th><th>SL / TP</th><th>Retorno</th><th>Win Rate</th><th>Trades</th><th>Drawdown</th><th>Ação</th>
      </tr>
    </thead>
    <tbody id="opt-tbody"></tbody>
  </table>
</div>

<div class="toast" id="toast"></div>

<script>
let lastSingleResult = null;
let lastOptTop = [];
let pollTimer = null;

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 3200);
}

function parseNumList(str, isFloat=false) {
  return str.split(',').map(s => isFloat ? parseFloat(s.trim()) : parseInt(s.trim(), 10)).filter(n => !isNaN(n));
}

function parseSymbolValue(val) {
  const [symbol, timeframe] = val.split('||');
  return { symbol, timeframe };
}

async function init() {
  try {
    const [h, s, m, d] = await Promise.all([
      fetch('/health').then(r => r.json()),
      fetch('/strategies').then(r => r.json()),
      fetch('/market-data/symbols').then(r => r.json()),
      fetch('/dna').then(r => r.json()),
    ]);

    document.getElementById('api-status').textContent = `● API Ligada • ${m.symbols.length} pares guardados`;

    const stratSel = document.getElementById('bt-strategy');
    Object.keys(s.strategies).forEach(st => {
      const opt = document.createElement('option');
      opt.value = st; opt.textContent = st;
      stratSel.appendChild(opt);
    });

    const symList = m.symbols.length
      ? m.symbols.map(x => ({ value: `${x.symbol}||${x.timeframe}`, label: `${x.symbol} (${x.timeframe}) — ${x.candles} velas` }))
      : [{ value: 'BTC/USDT||1h', label: 'BTC/USDT (1h) — Simulação Sintética' }];

    ['bt-symbol', 'opt-symbol'].forEach(id => {
      const sel = document.getElementById(id);
      symList.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item.value; opt.textContent = item.label;
        sel.appendChild(opt);
      });
    });

    renderActiveDna(d);
  } catch (e) {
    document.getElementById('api-status').textContent = 'Erro ao ligar à API';
  }
}

function renderActiveDna(d) {
  const best = d.trained_best || {};
  const prefs = d.user_preferences || {};
  const el = document.getElementById('active-dna-text');
  if (best.strategy_type) {
    el.innerHTML = `<strong>${best.strategy_type}</strong> em <strong>${best.symbol} (${best.timeframe})</strong> • Parâmetros: <code>${JSON.stringify(best.params || {})}</code> • Promovida em: ${best.promoted_at?.slice(0,19).replace('T',' ') || '-'}`;
  } else if (prefs.STRATEGY_TYPE) {
    el.innerHTML = `Configuração atual em <code>user_preferences.json</code>: <strong>${prefs.STRATEGY_TYPE}</strong> (${prefs.SYMBOL || 'BTC/USDT'}). Ainda não promoveste nenhuma estratégia pela API.`;
  } else {
    el.textContent = 'Nenhuma estratégia promovida ainda. Corre um teste ou treino abaixo!';
  }
}

async function runSingleBacktest() {
  const btn = document.getElementById('btn-bt');
  btn.disabled = true; btn.textContent = 'A calcular...';
  try {
    const { symbol, timeframe } = parseSymbolValue(document.getElementById('bt-symbol').value);
    const payload = {
      symbol, timeframe, limit: 500,
      strategy_type: document.getElementById('bt-strategy').value,
      initial_capital: parseFloat(document.getElementById('bt-capital').value),
      stop_loss_percent: parseFloat(document.getElementById('bt-sl').value),
      take_profit_percent: parseFloat(document.getElementById('bt-tp').value),
      trailing_stop_active: document.getElementById('bt-ts').value === 'true',
      strategy_params: {
        SHORT_WINDOW: parseInt(document.getElementById('bt-short').value, 10),
        LONG_WINDOW: parseInt(document.getElementById('bt-long').value, 10),
      },
      use_synthetic_if_missing: true
    };
    const res = await fetch('/train/backtest', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    }).then(r => r.json());

    lastSingleResult = { ...res, symbol, timeframe };
    const m = res.metrics || {};
    const ret = Number(m.total_return_pct || 0);
    document.getElementById('bt-kpis').innerHTML = `
      <div class="kpi"><div class="k-label">Retorno Total</div><div class="k-val ${ret>=0?'pos':'neg'}">${ret>=0?'+':''}${ret.toFixed(2)}%</div></div>
      <div class="kpi"><div class="k-label">Capital Final</div><div class="k-val">${Number(m.final_capital||0).toFixed(2)}</div></div>
      <div class="kpi"><div class="k-label">Win Rate</div><div class="k-val">${Number(m.win_rate||0).toFixed(1)}%</div></div>
      <div class="kpi"><div class="k-label">Trades</div><div class="k-val">${m.num_trades||0}</div></div>
      <div class="kpi"><div class="k-label">Max Drawdown</div><div class="k-val neg">${Number(m.max_drawdown_pct||0).toFixed(2)}%</div></div>
      <div class="kpi"><div class="k-label">Fator de Lucro</div><div class="k-val">${Number(m.profit_factor||0).toFixed(2)}</div></div>
    `;
    document.getElementById('bt-source').textContent = `Fonte: ${res.data_source} (${res.candles_used} velas analisadas)`;
    document.getElementById('bt-results').style.display = 'block';
  } finally {
    btn.disabled = false; btn.textContent = '▶ Correr Teste Agora';
  }
}

async function promoteStrategy(item) {
  await fetch('/dna/promote', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      strategy_type: item.strategy_type,
      symbol: item.symbol,
      timeframe: item.timeframe,
      params: item.params || {},
      metrics: item.metrics || {},
      update_user_preferences: true
    })
  });
  const d = await fetch('/dna').then(r => r.json());
  renderActiveDna(d);
  showToast('⭐ Estratégia promovida e guardada com sucesso!');
}

function promoteSingle() {
  if (lastSingleResult) promoteStrategy(lastSingleResult);
}

async function startOptimize() {
  const checked = Array.from(document.querySelectorAll('#opt-strategies input:checked')).map(c => c.value);
  if (!checked.length) { alert('Escolhe pelo menos 1 estratégia.'); return; }
  const { symbol, timeframe } = parseSymbolValue(document.getElementById('opt-symbol').value);
  const payload = {
    symbol, timeframe, limit: 500,
    strategy_types: checked,
    short_windows: parseNumList(document.getElementById('opt-shorts').value),
    long_windows: parseNumList(document.getElementById('opt-longs').value),
    stop_loss_percents: parseNumList(document.getElementById('opt-sls').value, true),
    take_profit_percents: parseNumList(document.getElementById('opt-tps').value, true),
    rank_by: document.getElementById('opt-rank').value,
    top_k: 10,
    use_synthetic_if_missing: true
  };
  document.getElementById('btn-opt').disabled = true;
  document.getElementById('opt-progress-area').style.display = 'block';
  document.getElementById('opt-bar').style.width = '5%';
  document.getElementById('opt-status-text').textContent = 'A iniciar treino automático...';

  const job = await fetch('/train/jobs', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
  }).then(r => r.json());

  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    const st = await fetch(`/train/jobs/${job.job_id}`).then(r => r.json());
    const pct = st.total ? Math.round((st.completed / st.total) * 100) : 10;
    document.getElementById('opt-bar').style.width = pct + '%';
    document.getElementById('opt-status-text').textContent = `A testar combinações: ${st.completed} / ${st.total} (${pct}%)`;
    if (st.status === 'completed' || st.status === 'failed') {
      clearInterval(pollTimer);
      document.getElementById('btn-opt').disabled = false;
      if (st.status === 'completed') {
        document.getElementById('opt-status-text').textContent = `✅ Concluído! ${st.total} combinações testadas (${st.data_source}).`;
        renderOptTable(st.top_results || [], symbol, timeframe);
      } else {
        document.getElementById('opt-status-text').textContent = `❌ Erro: ${st.error}`;
      }
    }
  }, 700);
}

function renderOptTable(rows, symbol, timeframe) {
  lastOptTop = rows.map(r => ({ ...r, symbol, timeframe }));
  const tbody = document.getElementById('opt-tbody');
  tbody.innerHTML = rows.map((r, i) => {
    const m = r.metrics || {};
    const p = r.params || {};
    const ret = Number(m.total_return_pct || 0);
    return `<tr>
      <td><strong>#${i+1}</strong></td>
      <td>${r.strategy_type}</td>
      <td>${p.SHORT_WINDOW || '-'} / ${p.LONG_WINDOW || '-'}</td>
      <td>${p.STOP_LOSS_PERCENT}% / ${p.TAKE_PROFIT_PERCENT}%</td>
      <td class="${ret>=0?'pos':'neg'}"><strong>${ret>=0?'+':''}${ret.toFixed(2)}%</strong></td>
      <td>${Number(m.win_rate||0).toFixed(1)}%</td>
      <td>${m.num_trades||0}</td>
      <td class="neg">${Number(m.max_drawdown_pct||0).toFixed(2)}%</td>
      <td><button class="btn btn-green btn-sm" onclick="promoteStrategy(lastOptTop[${i}])">⭐ Usar Esta</button></td>
    </tr>`;
  }).join('');
  document.getElementById('opt-table-card').style.display = 'block';
}

init();
</script>
</body>
</html>
"""
