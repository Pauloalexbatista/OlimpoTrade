"""
alpaca_bot_runner.py — Motor partilhado 24h entre a Sala de Controlo (UI) e o serviço VPS (main.py).
Guarda o estado e o histórico CSV numa pasta partilhada (OLIMPO_STATE_DIR ou raiz do projeto).
"""
import csv
import json
import os
from pathlib import Path
import pandas as pd


def get_state_dir() -> Path:
    env_dir = os.getenv("OLIMPO_STATE_DIR", "").strip()
    base = Path(env_dir) if env_dir else Path(__file__).resolve().parent
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_state_file() -> Path:
    return get_state_dir() / "alpaca_bot_state.json"


def get_checks_csv_file() -> Path:
    return get_state_dir() / "alpaca_market_checks.csv"


def read_bot_state() -> dict:
    path = get_state_file()
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def write_bot_state(state: dict) -> None:
    path = get_state_file()
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def append_market_check_log(row: dict) -> None:
    log_path = get_checks_csv_file()
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


def compute_signal_for_df(
    df: pd.DataFrame,
    strategy: str,
    p2: int,
    p3: int,
    p4: int,
    p5: int,
    p6: int,
    min_p2_p3_pct: float = 0.15,
):
    """Calcula médias P2..P6 e devolve 'BUY', 'SELL' ou None."""
    df["P2"] = df["close"].rolling(p2).mean()
    df["P3"] = df["close"].rolling(p3).mean()
    df["P4"] = df["close"].rolling(p4).mean()
    df["P5"] = df["close"].rolling(p5).mean()
    df["P6"] = df["close"].rolling(p6).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]
    current_price = float(last["close"])
    signal = None

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
            "MIN_P2_P3_PCT": float(min_p2_p3_pct or 0.15),
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
        if prev["P2"] <= prev["P4"] and last["P2"] > last["P4"]:
            signal = "BUY"
        elif prev["P2"] >= prev["P4"] and last["P2"] < last["P4"]:
            signal = "SELL"
    elif "Camadas" in strategy:
        if prev["P2"] <= prev["P3"] and last["P2"] > last["P3"] and last["P4"] > last["P5"]:
            signal = "BUY"
        elif prev["P2"] >= prev["P3"] and last["P2"] < last["P3"] and last["P4"] < last["P5"]:
            signal = "SELL"
    elif "Cérebro" in strategy or "IA" in strategy:
        if last["P2"] > last["P3"] > last["P4"] > last["P5"]:
            signal = "BUY"
        elif last["P2"] < last["P3"] < last["P4"] < last["P5"]:
            signal = "SELL"
    else:
        if prev["P2"] <= prev["P4"] and last["P2"] > last["P4"]:
            signal = "BUY"
        elif prev["P2"] >= prev["P4"] and last["P2"] < last["P4"]:
            signal = "SELL"

    return signal


def run_alpaca_paper_cycle(cfg: dict) -> tuple:
    """Executa 1 ciclo completo do bot Alpaca (usado pelo serviço 24h em main.py)."""
    from alpaca_connector import get_ohlcv, SYMBOL_MAP, get_market_clock, place_order, close_position, get_positions

    symbol = cfg["symbol"]
    p2, p3, p4, p5, p6 = int(cfg["p2"]), int(cfg["p3"]), int(cfg["p4"]), int(cfg["p5"]), int(cfg["p6"])
    capital = float(cfg["capital"])
    strategy = cfg["strategy"]
    min_p2_p3 = float(cfg.get("min_p2_p3_pct", 0.15))
    last_signal = cfg.get("last_signal")

    now_utc = pd.Timestamp.now(tz="UTC")
    now_local = pd.Timestamp.now()
    now_str = now_local.strftime("%H:%M:%S")
    alpaca_sym = SYMBOL_MAP.get(symbol, symbol.replace("/USDT", "/USD"))
    is_crypto = "/" in alpaca_sym
    market_type = "CRYPTO" if is_crypto else "US_STOCK"
    try:
        market_open = True if is_crypto else bool(get_market_clock()["is_open"])
    except Exception:
        market_open = is_crypto

    df = get_ohlcv(symbol, timeframe="5m", limit=max(p6 * 2, 100))
    if df is None or df.empty or len(df) < p6:
        msg = f"[{now_str}] ⚠️ Dados insuficientes para {symbol} ({len(df) if df is not None else 0} velas)"
        append_market_check_log({
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
        return None, {"status": "warn", "message": msg}

    signal = compute_signal_for_df(df, strategy, p2, p3, p4, p5, p6, min_p2_p3)
    last = df.iloc[-1]
    current_price = float(last["close"])
    order_action = "NONE"
    notes = f"Monitorizado (ultimo sinal: {last_signal or 'nenhum'})"

    if signal and signal != last_signal:
        try:
            if signal == "BUY":
                result = place_order(symbol, "buy", qty=None, notional=capital)
                notes = f"[{now_str}] 🟢 BUY {symbol} ~${capital:.0f} @ ${current_price:.2f} | ID: {result['id'][:8]}..."
                order_action = "BUY_SUBMITTED"
            else:
                positions = get_positions()
                has_pos = any(p["symbol"] == alpaca_sym for p in positions)
                if has_pos:
                    close_position(symbol)
                    notes = f"[{now_str}] 🔴 SELL/CLOSE {symbol} @ ${current_price:.2f}"
                    order_action = "CLOSE_SUBMITTED"
                else:
                    notes = f"[{now_str}] ⚪ Sinal SELL mas sem posição aberta."
                    order_action = "SELL_NO_POS"
            cfg["last_signal"] = signal
        except Exception as e:
            notes = f"[{now_str}] ❌ Erro ao executar ordem: {e}"
            order_action = "ORDER_ERROR"

    cfg["last_run_utc"] = now_utc.isoformat()
    cfg["last_price"] = round(current_price, 6)
    cfg["last_message"] = notes
    write_bot_state(cfg)

    append_market_check_log({
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

    return df, {"status": "ok", "signal": signal, "price": current_price, "message": notes}
