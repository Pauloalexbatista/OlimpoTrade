"""
Alpaca Paper Trading connector for OlimpoTrade.
Handles account info, market data, and order execution via alpaca-py SDK.
"""
import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from alpaca.data.historical.crypto import CryptoHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
import pandas as pd
from datetime import datetime, timezone

load_dotenv()

# Symbol map: OlimpoTrade format → Alpaca format
SYMBOL_MAP = {
    "BTC/USDT": "BTC/USD",
    "ETH/USDT": "ETH/USD",
    "SOL/USDT": "SOL/USD",
    "BNB/USDT": "BNB/USD",
    "ADA/USDT": "ADA/USD",
    "XRP/USDT": "XRP/USD",
    "DOGE/USDT": "DOGE/USD",
    # ETFs (ideais para testar estratégias)
    "SPY": "SPY",       # S&P 500 - o mais estável
    "QQQ": "QQQ",       # Nasdaq 100 - tech
    "GLD": "GLD",       # Ouro (ETF)
    "TLT": "TLT",       # Obrigações longo prazo
    "VXX": "VXX",       # Volatilidade (VIX)
    # Stocks voláteis (bons para testar estratégias)
    "AAPL": "AAPL",     # Apple
    "TSLA": "TSLA",     # Tesla - muito volátil
    "NVDA": "NVDA",     # Nvidia - tendências fortes
    "MSFT": "MSFT",     # Microsoft
    "AMZN": "AMZN",     # Amazon
    "META": "META",     # Meta
    "AMD":  "AMD",      # AMD - parecido com crypto em volatilidade
}

TIMEFRAME_MAP = {
    "1m":  TimeFrame(1,  TimeFrameUnit.Minute),
    "5m":  TimeFrame(5,  TimeFrameUnit.Minute),
    "15m": TimeFrame(15, TimeFrameUnit.Minute),
    "1h":  TimeFrame(1,  TimeFrameUnit.Hour),
    "4h":  TimeFrame(4,  TimeFrameUnit.Hour),
    "1d":  TimeFrame(1,  TimeFrameUnit.Day),
}


def _read_env_direct():
    """Read .env file directly, bypassing os.environ cache."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    values = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    values[k.strip()] = v.strip()
    return values


def _get_clients():
    env = _read_env_direct()
    api_key = env.get("ALPACA_API_KEY", os.getenv("ALPACA_API_KEY", ""))
    secret_key = env.get("ALPACA_SECRET_KEY", os.getenv("ALPACA_SECRET_KEY", ""))
    paper = env.get("ALPACA_PAPER", os.getenv("ALPACA_PAPER", "true")).lower() == "true"

    if not api_key or api_key.startswith("COLOCA"):
        raise ValueError("Chaves Alpaca não configuradas. Edita o ficheiro .env.")

    trading = TradingClient(api_key, secret_key, paper=paper)
    data = CryptoHistoricalDataClient(api_key, secret_key)
    return trading, data


def get_account():
    """Returns account info dict: balance, buying_power, equity."""
    client, _ = _get_clients()
    acc = client.get_account()
    return {
        "status": acc.status,
        "currency": acc.currency,
        "cash": float(acc.cash),
        "buying_power": float(acc.buying_power),
        "equity": float(acc.equity),
        "portfolio_value": float(acc.portfolio_value),
        "paper": os.getenv("ALPACA_PAPER", "true").lower() == "true",
    }


def get_positions():
    """Returns list of open positions."""
    client, _ = _get_clients()
    positions = client.get_all_positions()
    result = []
    for p in positions:
        result.append({
            "symbol": p.symbol,
            "qty": float(p.qty),
            "avg_entry": float(p.avg_entry_price),
            "current_price": float(p.current_price),
            "unrealized_pl": float(p.unrealized_pl),
            "unrealized_plpc": float(p.unrealized_plpc) * 100,
            "side": p.side,
        })
    return result


def get_orders(status="open", limit=20):
    """Returns recent orders."""
    client, _ = _get_clients()
    q_status = QueryOrderStatus.OPEN if status == "open" else QueryOrderStatus.CLOSED
    req = GetOrdersRequest(status=q_status, limit=limit)
    orders = client.get_orders(req)
    result = []
    for o in orders:
        result.append({
            "id": str(o.id),
            "symbol": o.symbol,
            "side": str(o.side),
            "qty": float(o.qty) if o.qty else 0,
            "filled_qty": float(o.filled_qty) if o.filled_qty else 0,
            "status": str(o.status),
            "created_at": o.created_at,
            "filled_avg_price": float(o.filled_avg_price) if o.filled_avg_price else None,
        })
    return result


def place_order(olimpo_symbol: str, side: str, qty: float, notional: float = None):
    """
    Place a market order on Alpaca.
    side: 'buy' or 'sell'
    qty: quantity in base asset (e.g. 0.001 BTC)
    notional: alternative — spend/receive this USD amount (ignores qty if set)
    """
    client, _ = _get_clients()
    alpaca_symbol = SYMBOL_MAP.get(olimpo_symbol, olimpo_symbol.replace("/USDT", "/USD"))

    order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

    # Use DAY for stocks (works outside market hours as pending order)
    # Use IOC for crypto (24/7 market)
    is_crypto = "/" in alpaca_symbol
    tif = TimeInForce.IOC if is_crypto else TimeInForce.DAY

    if notional:
        req = MarketOrderRequest(
            symbol=alpaca_symbol,
            notional=round(notional, 2),
            side=order_side,
            time_in_force=tif,
        )
    else:
        req = MarketOrderRequest(
            symbol=alpaca_symbol,
            qty=qty,
            side=order_side,
            time_in_force=tif,
        )

    order = client.submit_order(req)
    return {
        "id": str(order.id),
        "symbol": order.symbol,
        "side": str(order.side),
        "qty": float(order.qty) if order.qty else notional,
        "status": str(order.status),
        "created_at": order.created_at,
    }


def close_position(olimpo_symbol: str):
    """Close entire position for a symbol."""
    client, _ = _get_clients()
    alpaca_symbol = SYMBOL_MAP.get(olimpo_symbol, olimpo_symbol.replace("/USDT", "/USD"))
    resp = client.close_position(alpaca_symbol)
    return {"symbol": alpaca_symbol, "status": "closed", "order_id": str(resp.id)}


def get_ohlcv(olimpo_symbol: str, timeframe: str = "1h", limit: int = 200) -> pd.DataFrame:
    """Fetch OHLCV bars from Alpaca — auto-detects stock vs crypto."""
    env = _read_env_direct()
    api_key = env.get("ALPACA_API_KEY", os.getenv("ALPACA_API_KEY", ""))
    secret_key = env.get("ALPACA_SECRET_KEY", os.getenv("ALPACA_SECRET_KEY", ""))

    alpaca_symbol = SYMBOL_MAP.get(olimpo_symbol, olimpo_symbol.replace("/USDT", "/USD"))
    tf = TIMEFRAME_MAP.get(timeframe, TimeFrame(1, TimeFrameUnit.Hour))
    is_crypto = "/" in alpaca_symbol

    from datetime import timedelta
    end = datetime.now(timezone.utc)
    minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}.get(timeframe, 60)
    # Multiply by 5 to account for weekends and market closures
    start = end - timedelta(minutes=minutes * limit * 5)

    if is_crypto:
        client = CryptoHistoricalDataClient(api_key, secret_key)
        req = CryptoBarsRequest(symbol_or_symbols=alpaca_symbol, timeframe=tf, start=start, end=end, limit=limit)
        bars = client.get_crypto_bars(req)
    else:
        from alpaca.data.enums import DataFeed
        client = StockHistoricalDataClient(api_key, secret_key)
        req = StockBarsRequest(symbol_or_symbols=alpaca_symbol, timeframe=tf, start=start, end=end, limit=limit, feed=DataFeed.IEX)
        bars = client.get_stock_bars(req)

    df = bars.df
    if df.empty:
        return pd.DataFrame()

    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(alpaca_symbol, level="symbol")

    df.index.name = "timestamp"
    return df[["open", "high", "low", "close", "volume"]].tail(limit)


def test_connection():
    """Quick connectivity test. Returns (ok: bool, message: str)."""
    try:
        acc = get_account()
        mode = "PAPER" if acc["paper"] else "LIVE"
        return True, f"✅ Ligado ({mode}) | Saldo: ${acc['cash']:,.2f} USD | Equity: ${acc['equity']:,.2f}"
    except ValueError as e:
        return False, f"❌ {e}"
    except Exception as e:
        return False, f"❌ Erro de ligação: {e}"
