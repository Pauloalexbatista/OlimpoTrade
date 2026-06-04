"""
OlimpoTrade Strategy Lab — Motor de Análise
Gere base de dados de resultados, bot de optimização e recolha de dados.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
import threading
import time
import asyncio
import logging
import json
import random
import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timedelta

from backtester import Backtester

LAB_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lab_results.db")

# ---------------------------------------------------------------------------
# SCORING
# ---------------------------------------------------------------------------

def score_result(metrics):
    """Pontuação composta. Penaliza drawdown, recompensa Sharpe + win rate + retorno."""
    if metrics["num_trades"] < 4:
        return -999.0
    if metrics["total_return_pct"] <= 0:
        return -999.0
    if metrics["max_drawdown_pct"] < -40:
        return -999.0

    sharpe   = metrics.get("sharpe_ratio", 0.0)
    ret      = metrics["total_return_pct"]
    dd       = abs(metrics["max_drawdown_pct"])
    wr       = metrics["win_rate"] * 100
    pf       = min(metrics.get("profit_factor", 1.0), 6.0)
    n        = metrics["num_trades"]

    score = (
        sharpe  * 25   +   # Qualidade do retorno ajustado ao risco
        ret     * 0.4  +   # Retorno bruto (peso moderado)
        wr      * 0.25 +   # Taxa de vitória
        pf      * 5    +   # Factor de lucro (cap 6)
        min(n, 30) * 0.3 - # Mais trades = mais confiança (cap 30)
        dd      * 0.5      # Penalidade por drawdown
    )
    return round(score, 2)


# ---------------------------------------------------------------------------
# BASE DE DADOS
# ---------------------------------------------------------------------------

class LabDatabase:
    def __init__(self, db_path=LAB_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT,
                    strategy        TEXT,
                    params          TEXT,
                    symbol          TEXT,
                    timeframe       TEXT,
                    period_days     INTEGER,
                    score           REAL,
                    total_return_pct REAL,
                    max_drawdown_pct REAL,
                    sharpe_ratio    REAL,
                    sortino_ratio   REAL,
                    win_rate        REAL,
                    num_trades      INTEGER,
                    profit_factor   REAL,
                    initial_capital REAL,
                    final_capital   REAL,
                    fee_pct         REAL,
                    slippage_pct    REAL
                )
            """)
            conn.commit()

    def save_result(self, r):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO results (
                    timestamp, strategy, params, symbol, timeframe, period_days,
                    score, total_return_pct, max_drawdown_pct, sharpe_ratio, sortino_ratio,
                    win_rate, num_trades, profit_factor, initial_capital, final_capital,
                    fee_pct, slippage_pct
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                datetime.now().isoformat(),
                r["strategy"], json.dumps(r["params"], ensure_ascii=False),
                r["symbol"], r["timeframe"], r["period_days"],
                r["score"], r["total_return_pct"], r["max_drawdown_pct"],
                r["sharpe_ratio"], r.get("sortino_ratio", 0.0),
                r["win_rate"], r["num_trades"], r["profit_factor"],
                r["initial_capital"], r["final_capital"],
                r["fee_pct"], r["slippage_pct"],
            ))
            conn.commit()

    def get_top_results(self, limit=100, strategy=None, symbol=None):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            q = "SELECT * FROM results WHERE score > -900"
            p = []
            if strategy and strategy != "Todas":
                q += " AND strategy = ?"; p.append(strategy)
            if symbol and symbol != "Todos":
                q += " AND symbol = ?"; p.append(symbol)
            q += " ORDER BY score DESC LIMIT ?"
            p.append(limit)
            return [dict(r) for r in conn.execute(q, p).fetchall()]

    def count_results(self):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]

    def delete_result(self, result_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM results WHERE id = ?", (result_id,))
            conn.commit()

    def clear_all(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM results")
            conn.commit()


# ---------------------------------------------------------------------------
# DADOS
# ---------------------------------------------------------------------------

def fetch_ohlcv(symbol, timeframe, days=180, exchange_id="binance"):
    """Recolhe dados históricos OHLCV via ccxt com paginação."""
    exchange = getattr(ccxt, exchange_id)({"enableRateLimit": True})
    since_ms = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)

    all_ohlcv = []
    while True:
        try:
            batch = exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=1000)
        except Exception:
            break
        if not batch:
            break
        all_ohlcv.extend(batch)
        last_ts = batch[-1][0]
        now_ms = int(datetime.utcnow().timestamp() * 1000)
        if last_ts >= now_ms - 120_000 or len(batch) < 1000:
            break
        since_ms = last_ts + 1
        time.sleep(max(exchange.rateLimit / 1000, 0.2))

    if not all_ohlcv:
        return None

    df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("timestamp")
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df


# ---------------------------------------------------------------------------
# BACKTEST SÍNCRONO
# ---------------------------------------------------------------------------

def build_config(strategy_type, params, symbol, timeframe, fee_pct, slippage_pct, initial_capital):
    return {
        "STRATEGY_TYPE":            strategy_type,
        "EXCHANGE_NAME":            "binance",
        "SYMBOL":                   symbol,
        "TIMEFRAME":                timeframe,
        "INITIAL_CAPITAL":          initial_capital,
        "FEE_PERCENT":              fee_pct,
        "SLIPPAGE_PCT":             slippage_pct,
        "TAX_PERCENT":              0.0,
        "MAX_RISK_PER_TRADE_PERCENT": params.get("risk_pct", 10.0),
        "STOP_LOSS_PERCENT":        params.get("stop_loss_pct", 2.0),
        "TAKE_PROFIT_PERCENT":      params.get("take_profit_pct", 5.0),
        "TRAILING_STOP_ACTIVE":     params.get("trailing_stop", False),
        "MAX_DAILY_LOSS_PERCENT":   99.0,
        "EMERGENCY_EXIT_PRICE_CROSS": "NONE",
        "ALLOW_REENTRY":            True,
        # SMA / EMA / PAULO_GOLD
        "SHORT_WINDOW":             params.get("short_window", 9),
        "LONG_WINDOW":              params.get("long_window", 21),
        # MULTIPOINT_VECTOR
        "P2_WINDOW":                params.get("p2_window", 9),
        "P3_WINDOW":                params.get("p3_window", 21),
        "P4_WINDOW":                params.get("p4_window", 50),
        "P5_WINDOW":                params.get("p5_window", 200),
        "MULTIPOINT_MODE":          params.get("multipoint_mode", "AGILE"),
        "EXHAUSTION_FILTER":        params.get("exhaustion_filter", True),
        "EXHAUSTION_THRESHOLD":     params.get("exhaustion_threshold", 2.5),
        "P5_SLOPE_FILTER_ACTIVE":   params.get("p5_filter_active", True),
        "ENTRY_MODE":               params.get("entry_mode", "4PONTOS"),
        "EXIT_MODE":                params.get("exit_mode", "P3"),
        "OPERATION_MODE":           params.get("operation_mode", "TREND_FOLLOWING"),
        # PAULO_GOLD extras
        "PAULO_GOLD_TREND_FILTER":  params.get("trend_filter", False),
        "PAULO_GOLD_MIN_DIST_PCT":  params.get("min_dist_pct", 0.0),
        # LAGARTA
        "LAGARTA_REF_WINDOW":       params.get("ref_window", 13),
        "LAGARTA_P2":               params.get("p2", params.get("p2_window", 5)),
        "LAGARTA_P3":               params.get("p3", params.get("p3_window", 13)),
        "LAGARTA_P4":               params.get("p4", params.get("p4_window", 21)),
        "LAGARTA_P5":               params.get("p5", 55),
        "LAGARTA_P6":               params.get("p6", 144),
        "LAGARTA_MODE":             params.get("mode", "PIRAMIDE"),
        "LAGARTA_VEL_FILTER":       params.get("velocity_filter", True),
    }


def run_backtest_sync(strategy_type, params, df, symbol, timeframe,
                      fee_pct, slippage_pct, initial_capital=1000.0):
    """Corre backtest de forma síncrona num loop próprio."""
    logger = logging.getLogger("lab_silent")
    logger.setLevel(logging.CRITICAL)

    config = build_config(strategy_type, params, symbol, timeframe,
                          fee_pct, slippage_pct, initial_capital)
    bt = Backtester(config, logger)

    loop = asyncio.new_event_loop()
    try:
        trades, cap_hist = loop.run_until_complete(bt.run_backtest(df.copy()))
    finally:
        loop.close()

    metrics = bt.get_performance_metrics()
    return bt, trades, cap_hist, metrics


# ---------------------------------------------------------------------------
# GRIDS DE OPTIMIZAÇÃO
# ---------------------------------------------------------------------------

def _grid_crossover(strategy):
    grid = []
    for s in [5, 9, 13, 21]:
        for l in [21, 34, 50, 89, 144]:
            if s >= l:
                continue
            for sl in [1.0, 1.5, 2.0, 3.0]:
                for tp in [3.0, 5.0, 8.0, 10.0, 15.0]:
                    for rsk in [5.0, 10.0, 20.0]:
                        grid.append({
                            "short_window": s, "long_window": l,
                            "stop_loss_pct": sl, "take_profit_pct": tp, "risk_pct": rsk,
                        })
    return [(strategy, p) for p in grid]


def _grid_paulo_gold():
    grid = []
    for s in [9, 13, 21]:
        for l in [21, 34, 50, 89]:
            if s >= l:
                continue
            for sl in [1.0, 2.0, 3.0]:
                for tp in [3.0, 5.0, 10.0]:
                    for tf in [False, True]:
                        for rsk in [10.0, 20.0]:
                            grid.append({
                                "short_window": s, "long_window": l,
                                "stop_loss_pct": sl, "take_profit_pct": tp,
                                "trend_filter": tf, "risk_pct": rsk,
                            })
    return [("PAULO_GOLD", p) for p in grid]


def _grid_multipoint():
    grid = []
    for p2 in [9, 13]:
        for p3 in [21, 34]:
            for p4 in [50, 89]:
                if not (p2 < p3 < p4):
                    continue
                for sl in [1.5, 2.0, 2.5]:
                    for tp in [4.0, 6.0, 10.0]:
                        for mode in ["AGILE", "CONSERVATIVE"]:
                            for rsk in [10.0, 20.0]:
                                grid.append({
                                    "p2_window": p2, "p3_window": p3, "p4_window": p4,
                                    "stop_loss_pct": sl, "take_profit_pct": tp,
                                    "multipoint_mode": mode, "risk_pct": rsk,
                                })
    return [("MULTIPOINT_VECTOR", p) for p in grid]


def _grid_lagarta_1line():
    grid = []
    for ref in [5, 13, 21, 55, 144]:
        for sl in [0.5, 1.0, 1.5, 2.0, 3.0]:
            for tp in [2.0, 4.0, 6.0, 10.0]:
                for rsk in [5.0, 10.0, 20.0]:
                    grid.append({
                        "ref_window": ref,
                        "stop_loss_pct": sl, "take_profit_pct": tp, "risk_pct": rsk,
                    })
    return [("LAGARTA_1LINE", p) for p in grid]


def _grid_lagarta_5lines():
    grid = []
    # Testar diferentes conjuntos de períodos
    configs = [
        (5, 13, 21, 55, 144),   # clássico
        (3, 8,  13, 34, 89),    # Fibonacci puro
        (5, 10, 20, 50, 100),   # décadas
        (7, 14, 21, 50, 200),   # técnico clássico
    ]
    for (p2, p3, p4, p5, p6) in configs:
        for sl in [0.5, 1.0, 2.0]:
            for tp in [2.0, 5.0, 10.0]:
                for rsk in [10.0, 20.0]:
                    grid.append({
                        "p2": p2, "p3": p3, "p4": p4, "p5": p5, "p6": p6,
                        "stop_loss_pct": sl, "take_profit_pct": tp, "risk_pct": rsk,
                    })
    return [("LAGARTA_5LINES", p) for p in grid]


def _grid_lagarta_2lines():
    grid = []
    configs = [
        (5, 13, 21), (5, 13, 34), (8, 21, 50),
        (5, 21, 55), (13, 34, 89),
    ]
    for (p2, p3, p4) in configs:
        for mode in ["PIRAMIDE", "CAMADAS"]:
            for vel in [True, False]:
                for sl in [1.0, 2.0, 3.0]:
                    for tp in [3.0, 6.0, 10.0]:
                        for rsk in [10.0, 20.0]:
                            grid.append({
                                "p2_window": p2, "p3_window": p3, "p4_window": p4,
                                "mode": mode, "velocity_filter": vel,
                                "stop_loss_pct": sl, "take_profit_pct": tp, "risk_pct": rsk,
                            })
    return [("LAGARTA_2LINES", p) for p in grid]


STRATEGY_GRIDS = {
    "SMA_CROSSOVER":     lambda: _grid_crossover("SMA_CROSSOVER"),
    "EMA_CROSSOVER":     lambda: _grid_crossover("EMA_CROSSOVER"),
    "PAULO_GOLD":        _grid_paulo_gold,
    "MULTIPOINT_VECTOR": _grid_multipoint,
    "LAGARTA_1LINE":     _grid_lagarta_1line,
    "LAGARTA_5LINES":    _grid_lagarta_5lines,
    "LAGARTA_2LINES":    _grid_lagarta_2lines,
}


# ---------------------------------------------------------------------------
# BOT AUTÓNOMO
# ---------------------------------------------------------------------------

class LabBot:
    def __init__(self, db: LabDatabase):
        self.db = db
        self._thread = None
        self._stop_event = threading.Event()
        self.progress = {
            "running": False,
            "total": 0,
            "done": 0,
            "saved": 0,
            "errors": 0,
            "best_score": -999.0,
            "best_result": None,
            "last_result": None,
            "current_strategy": "",
            "current_params": {},
            "start_time": None,
            "eta_secs": None,
        }

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, strategies, symbol, timeframe, period_days,
              fee_pct, slippage_pct, initial_capital, min_score):
        if self.is_running():
            return

        self._stop_event.clear()
        self.progress.update({
            "running": True, "done": 0, "saved": 0, "errors": 0,
            "best_score": -999.0, "best_result": None, "last_result": None,
            "start_time": time.time(), "eta_secs": None,
        })

        grid = []
        for strat in strategies:
            builder = STRATEGY_GRIDS.get(strat)
            if builder:
                grid.extend(builder())

        random.shuffle(grid)
        self.progress["total"] = len(grid)

        self._thread = threading.Thread(
            target=self._run,
            args=(grid, symbol, timeframe, period_days,
                  fee_pct, slippage_pct, initial_capital, min_score),
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self.progress["running"] = False

    def _run(self, grid, symbol, timeframe, period_days,
             fee_pct, slippage_pct, initial_capital, min_score):
        try:
            df = fetch_ohlcv(symbol, timeframe, days=period_days)
            if df is None or df.empty:
                self.progress["running"] = False
                return
        except Exception:
            self.progress["running"] = False
            return

        for strategy_type, params in grid:
            if self._stop_event.is_set():
                break

            self.progress["current_strategy"] = strategy_type
            self.progress["current_params"] = params

            try:
                _, _, _, metrics = run_backtest_sync(
                    strategy_type, params, df, symbol, timeframe,
                    fee_pct, slippage_pct, initial_capital,
                )
                s = score_result(metrics)

                result = {
                    "strategy":         strategy_type,
                    "params":           params,
                    "symbol":           symbol,
                    "timeframe":        timeframe,
                    "period_days":      period_days,
                    "score":            s,
                    "total_return_pct": metrics["total_return_pct"],
                    "max_drawdown_pct": metrics["max_drawdown_pct"],
                    "sharpe_ratio":     metrics.get("sharpe_ratio", 0.0),
                    "sortino_ratio":    metrics.get("sortino_ratio", 0.0),
                    "win_rate":         metrics["win_rate"],
                    "num_trades":       metrics["num_trades"],
                    "profit_factor":    metrics.get("profit_factor", 1.0),
                    "initial_capital":  initial_capital,
                    "final_capital":    metrics["final_capital"],
                    "fee_pct":          fee_pct,
                    "slippage_pct":     slippage_pct,
                }

                self.progress["last_result"] = result

                if s > self.progress["best_score"]:
                    self.progress["best_score"] = s
                    self.progress["best_result"] = result

                if s >= min_score:
                    self.db.save_result(result)
                    self.progress["saved"] += 1

            except Exception:
                self.progress["errors"] += 1

            self.progress["done"] += 1

            # ETA
            elapsed = time.time() - self.progress["start_time"]
            done = self.progress["done"]
            total = self.progress["total"]
            if done > 0 and total > done:
                self.progress["eta_secs"] = int(elapsed / done * (total - done))

        self.progress["running"] = False
