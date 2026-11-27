"""
main.py — Motor Autónomo 24h do OlimpoTrade 2.0 (preparado para PC local ou VPS).
Lê a estratégia aprovada em `trained_best_strategy.json` e os controlos/travões em `bot_live_control.json`.
"""
import asyncio
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from config import load_config
from data_collector import DataCollector
from logger import setup_logging
from order_executor import OrderExecutor
from risk_manager import RiskManager
from strategy import StrategyFactory

BASE_DIR = Path(__file__).resolve().parent
TRAINED_BEST_FILE = BASE_DIR / "trained_best_strategy.json"
CONTROL_FILE = BASE_DIR / "bot_live_control.json"


def _read_json(path: Path) -> dict:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _log_market_check(config: dict, df, signal: dict, order_action: str, notes: str = "") -> None:
    """Regista cada ciclo de verificação de mercado em CSV para análise de horários no VPS."""
    csv_path = BASE_DIR / "alpaca_market_checks.csv"
    fieldnames = [
        "timestamp_utc", "timestamp_local", "weekday", "hour_utc",
        "symbol", "market_type", "market_open", "timeframe",
        "last_candle_utc", "price", "p2", "p3", "p4", "p5", "p6",
        "signal", "order_action", "notes",
    ]
    now_utc = datetime.now(timezone.utc)
    now_local = datetime.now()
    last_candle = str(df.index[-1]) if df is not None and not df.empty else ""
    price = round(float(df["close"].iloc[-1]), 6) if df is not None and not df.empty else ""
    row = {
        "timestamp_utc": now_utc.isoformat(),
        "timestamp_local": now_local.strftime("%Y-%m-%d %H:%M:%S"),
        "weekday": now_utc.strftime("%A"),
        "hour_utc": now_utc.hour,
        "symbol": config.get("SYMBOL", ""),
        "market_type": config.get("EXCHANGE_NAME", "").upper(),
        "market_open": True,
        "timeframe": config.get("TIMEFRAME", ""),
        "last_candle_utc": last_candle,
        "price": price,
        "signal": (signal or {}).get("action", "HOLD"),
        "order_action": order_action,
        "notes": notes,
    }
    file_exists = csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in fieldnames})


def build_runtime_config() -> tuple[dict, str]:
    config = load_config()
    best = _read_json(TRAINED_BEST_FILE)
    ctrl = _read_json(CONTROL_FILE)

    # Aplicar estratégia aprovada
    if best.get("strategy_type"):
        config["STRATEGY_TYPE"] = best["strategy_type"]
        config["SYMBOL"] = best.get("symbol", config["SYMBOL"])
        config["TIMEFRAME"] = best.get("timeframe", config["TIMEFRAME"])
        for k, v in (best.get("params") or {}).items():
            config[k] = v

    # Aplicar controlos operacionais da Parte 3 (Bot ON)
    if ctrl:
        config["EXCHANGE_NAME"] = ctrl.get("exchange", config["EXCHANGE_NAME"])
        config["SYMBOL"] = ctrl.get("symbol", config["SYMBOL"])
        config["TIMEFRAME"] = ctrl.get("timeframe", config["TIMEFRAME"])
        config["TRADING_INTERVAL_SECONDS"] = int(ctrl.get("interval_seconds", config["TRADING_INTERVAL_SECONDS"]))
        config["INITIAL_CAPITAL"] = float(ctrl.get("capital_per_trade", config["INITIAL_CAPITAL"]))
        config["MAX_DAILY_LOSS_PERCENT"] = float(ctrl.get("max_daily_loss_pct", config["MAX_DAILY_LOSS_PERCENT"]))
        if "stop_loss_pct" in ctrl:
            config["STOP_LOSS_PERCENT"] = float(ctrl["stop_loss_pct"])
        if "take_profit_pct" in ctrl:
            config["TAKE_PROFIT_PERCENT"] = float(ctrl["take_profit_pct"])

    mode = ctrl.get("mode", "DRY_RUN")
    if not best.get("validated_for_live", False):
        mode = "DRY_RUN"  # Bloqueio de segurança obrigatório se não estiver validada
    return config, mode


async def main():
    logger = setup_logging()
    config, mode = build_runtime_config()
    logger.info(
        f"=== OlimpoTrade 2.0 Motor Autónomo iniciado | Modo={mode} | "
        f"Corretora={config['EXCHANGE_NAME']} | Par={config['SYMBOL']} ({config['TIMEFRAME']}) | "
        f"Estratégia={config.get('STRATEGY_TYPE', 'CAMALEAO_ADX')} ==="
    )

    risk_manager = RiskManager(config, logger)
    order_executor = OrderExecutor(config, logger)

    while True:
        ctrl = _read_json(CONTROL_FILE)
        if ctrl and not ctrl.get("enabled", True):
            logger.info("Kill-Switch detetado (enabled=False). A encerrar motor autónomo com segurança.")
            break

        config, mode = build_runtime_config()
        try:
            collector = DataCollector(
                {"EXCHANGE_NAME": config["EXCHANGE_NAME"], "SYMBOL": config["SYMBOL"], "TIMEFRAME": config["TIMEFRAME"]},
                logger,
            )
            current_data = collector.get_ohlcv(limit=250)
            if current_data is None or current_data.empty:
                logger.warning("Sem dados recebidos neste ciclo. A aguardar próximo intervalo.")
                await asyncio.sleep(config.get("TRADING_INTERVAL_SECONDS", 300))
                continue

            strategy = StrategyFactory.get_strategy(config, logger)
            signal = strategy.generate_signal(current_data)
            logger.info(f"[{config['SYMBOL']}] Sinal: {signal.get('action')} — {signal.get('message', '')}")
            order_action = "NONE"

            if signal and signal.get("action") in ("BUY", "SELL"):
                approved_order = risk_manager.evaluate_signal(signal, signal.get("price"))
                if approved_order:
                    if mode == "LIVE":
                        logger.info(f"[LIVE] A enviar ordem real: {approved_order}")
                        await order_executor.place_order(approved_order)
                        order_action = f"{approved_order['action']}_LIVE"
                    else:
                        logger.info(
                            f"[DRY-RUN SIMULAÇÃO SEGURA] Ordem aprovada (NÃO enviada a dinheiro real): "
                            f"{approved_order['action']} {approved_order['quantity']:.6f} {approved_order['symbol']} "
                            f"@ {approved_order['price']:.2f} (SL={approved_order['stop_loss']:.2f}, TP={approved_order['take_profit']:.2f})"
                        )
                        order_action = f"{approved_order['action']}_DRY_RUN"
                else:
                    logger.warning("Ordem bloqueada pelo RiskManager (ex: limite de perda diária atingido).")
                    order_action = "BLOCKED_RISK"

            _log_market_check(config, current_data, signal, order_action, signal.get("message", ""))

        except Exception as exc:
            logger.error(f"Erro no ciclo autónomo: {exc}", exc_info=True)

        await asyncio.sleep(config.get("TRADING_INTERVAL_SECONDS", 300))


if __name__ == "__main__":
    asyncio.run(main())
