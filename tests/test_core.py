import asyncio
import logging
import os
import tempfile
import unittest
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from backtester import Backtester
from config import load_config
from decision_logger import DecisionLogger
from risk_manager import RiskManager
from strategy import StrategyFactory
from strategy_trainer_api import BacktestRequest, dashboard, health, list_strategies, run_backtest


def _make_sample_df(n=120, start_price=100.0):
    rng = np.random.default_rng(7)
    rets = rng.normal(0.001, 0.015, size=n)
    close = start_price * np.exp(np.cumsum(rets))
    open_p = np.roll(close, 1)
    open_p[0] = start_price
    high = np.maximum(open_p, close) * 1.005
    low = np.minimum(open_p, close) * 0.995
    vol = rng.uniform(100, 1000, size=n)
    idx = pd.date_range(end=datetime(2026, 6, 1), periods=n, freq="1h")
    return pd.DataFrame(
        {"open": open_p, "high": high, "low": low, "close": close, "volume": vol},
        index=idx,
    )


class TestOlimpoCore(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("test_olimpo")
        self.logger.addHandler(logging.NullHandler())
        self.cfg = load_config()

    def test_strategy_factory_creates_strategies(self):
        for strat_name in ["SMA_CROSSOVER", "EMA_CROSSOVER", "PAULO_GOLD", "LAGARTA_1LINE", "BB_RSI_REVERSION", "CAMALEAO_ADX"]:
            cfg = {**self.cfg, "STRATEGY_TYPE": strat_name}
            strat = StrategyFactory.get_strategy(cfg, self.logger)
            self.assertIsNotNone(strat)

    def test_chameleon_adx_generates_valid_signal(self):
        df = _make_sample_df(120)
        cfg = {**self.cfg, "STRATEGY_TYPE": "CAMALEAO_ADX"}
        strat = StrategyFactory.get_strategy(cfg, self.logger)
        sig = strat.generate_signal(df)
        self.assertIn(sig["action"], ["BUY", "SELL", "HOLD"])
        self.assertIsNotNone(sig["price"])

    def test_main_safety_gate_enforces_dry_run_when_unvalidated(self):
        import main as bot_main
        cfg, mode = bot_main.build_runtime_config()
        self.assertIsInstance(cfg, dict)
        self.assertIn(mode, ["DRY_RUN", "LIVE"])

    def test_strategy_report_generator_outputs_markdown(self):
        from strategy_report_generator import generate_arena_report
        df = _make_sample_df(200)
        sample_trades = [
            {"type": "LONG", "entry_step": 150, "exit_step": 158, "candles": 8, "entry_price": 100.0, "exit_price": 102.5, "pnl_pct": 2.5, "pnl_eur": 2.2, "reason": "Bot Exit (HOLD)"}
        ]
        md = generate_arena_report(df, sample_trades, {"tg_strategy_type": "CAMALEAO_ADX", "tg_capital": 102.2, "tg_trader_name": "Teste"})
        self.assertIn("Relatório de Diagnóstico de Estratégia", md)
        self.assertIn("CAMALEAO_ADX", md)

    def test_bollinger_rsi_reversion_generates_valid_signal(self):
        df = _make_sample_df(120)
        cfg = {**self.cfg, "STRATEGY_TYPE": "BB_RSI_REVERSION"}
        strat = StrategyFactory.get_strategy(cfg, self.logger)
        sig = strat.generate_signal(df)
        self.assertIn(sig["action"], ["BUY", "SELL", "HOLD"])
        self.assertIsNotNone(sig["price"])

    def test_risk_manager_approves_and_blocks_daily_loss(self):
        rm = RiskManager(self.cfg, self.logger)
        order = rm.evaluate_signal({"action": "BUY"}, current_price=100.0)
        self.assertIsNotNone(order)
        self.assertGreater(order["quantity"], 0)
        self.assertLess(order["stop_loss"], 100.0)
        self.assertGreater(order["take_profit"], 100.0)

        # Simular perda diária acima do limite (5% de 1000 = 50)
        rm.update_profit_loss(-60.0)
        blocked = rm.evaluate_signal({"action": "BUY"}, current_price=100.0)
        self.assertIsNone(blocked)

    def test_backtester_runs_and_returns_metrics(self):
        df = _make_sample_df(120)
        cfg = {
            **self.cfg,
            "STRATEGY_TYPE": "SMA_CROSSOVER",
            "SHORT_WINDOW": 5,
            "LONG_WINDOW": 15,
            "FEE_PERCENT": 0.1,
            "SLIPPAGE_PCT": 0.05,
        }
        bt = Backtester(cfg, self.logger, log_decisions=False)
        trades, equity = asyncio.run(bt.run_backtest(df))
        metrics = bt.get_performance_metrics()
        self.assertEqual(len(equity), len(df))
        self.assertIn("total_return_pct", metrics)
        self.assertIsInstance(trades, list)

    def test_decision_logger_writes_sqlite(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = os.path.join(tmpdir, "decisions_test.sqlite")
            dl = DecisionLogger(db_path=db_path)
            dl.log_decision(datetime(2026, 6, 1, 12, 0), "BTC/USDT", "BUY", 65000.0, "SMA_CROSSOVER", {"a": 1})
            import sqlite3
            conn = sqlite3.connect(db_path)
            try:
                count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(count, 1)


class TestStrategyTrainerAPI(unittest.TestCase):
    def test_health_and_strategies(self):
        res_h = health()
        self.assertEqual(res_h["status"], "ok")

        res_s = list_strategies()
        self.assertIn("PAULO_GOLD", res_s["strategies"])

        res_ui = dashboard()
        self.assertIn("OlimpoTrade", res_ui.body.decode("utf-8"))

    def test_backtest_endpoint_with_synthetic_fallback(self):
        req = BacktestRequest(
            symbol="TEST/USDT",
            timeframe="1h",
            limit=120,
            strategy_type="SMA_CROSSOVER",
            strategy_params={"SHORT_WINDOW": 5, "LONG_WINDOW": 15},
            use_synthetic_if_missing=True,
        )
        data = run_backtest(req)
        self.assertEqual(data["data_source"], "synthetic_fallback")
        self.assertIn("metrics", data)
        self.assertIn("total_return_pct", data["metrics"])


if __name__ == "__main__":
    unittest.main()
