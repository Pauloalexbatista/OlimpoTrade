import os
import ccxt
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# Symbol map: OlimpoTrade format -> Binance Futures format
SYMBOL_MAP = {
    "BTC/USDT": "BTC/USDT",
    "ETH/USDT": "ETH/USDT",
    "SOL/USDT": "SOL/USDT",
    "BNB/USDT": "BNB/USDT",
    "ADA/USDT": "ADA/USDT",
    "XRP/USDT": "XRP/USDT",
    "DOGE/USDT": "DOGE/USDT",
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

def _get_client():
    env = _read_env_direct()
    api_key = env.get("BINANCE_API_KEY", os.getenv("BINANCE_API_KEY", ""))
    secret_key = env.get("BINANCE_SECRET_KEY", os.getenv("BINANCE_SECRET_KEY", ""))
    is_testnet = env.get("BINANCE_TESTNET", os.getenv("BINANCE_TESTNET", "true")).lower() == "true"

    if not api_key or api_key.startswith("COLOCA"):
        raise ValueError("Chaves Binance não configuradas. Edita o ficheiro .env.")

    exchange = ccxt.binanceusdm({
        'apiKey': api_key,
        'secret': secret_key,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future'
        }
    })
    
    if is_testnet:
        exchange.set_sandbox_mode(True)
    
    exchange.load_markets()
    return exchange

def get_account():
    """Returns account info dict: balance, buying_power, equity."""
    client = _get_client()
    balance = client.fetch_balance()
    
    # Binance Futures returns totalMarginBalance as equity
    equity = float(balance['info'].get('totalMarginBalance', balance.get('USDT', {}).get('total', 0)))
    cash = float(balance.get('USDT', {}).get('free', 0))
    
    env = _read_env_direct()
    is_testnet = env.get("BINANCE_TESTNET", os.getenv("BINANCE_TESTNET", "true")).lower() == "true"

    return {
        "status": "ACTIVE",
        "currency": "USDT",
        "cash": cash,
        "buying_power": cash, # Simplified
        "equity": equity,
        "portfolio_value": equity,
        "paper": is_testnet,
    }

def get_positions():
    """Returns list of open positions."""
    client = _get_client()
    try:
        # Use raw API to bypass CCXT testnet parsing bugs
        positions = client.fapiPrivateV2GetPositionRisk()
    except Exception:
        positions = client.fetch_positions()
        
    result = []
    
    for p in positions:
        qty = float(p.get('positionAmt', p.get('contracts', 0) or 0))
        if qty != 0:
            side = 'long' if qty > 0 else 'short'
            qty_abs = abs(qty)
            unrealized_pl = float(p.get('unRealizedProfit', p.get('unrealizedPnl', 0)))
            entry = float(p.get('entryPrice', 0))
            current = float(p.get('markPrice', 0))
            plpc = 0
            if entry > 0:
                if side == 'long':
                    plpc = (current - entry) / entry * 100
                else:
                    plpc = (entry - current) / entry * 100

            # Convert symbol back to CCXT format like BTC/USDT instead of BTCUSDT
            sym = p.get('symbol', '')
            if not '/' in sym and sym.endswith('USDT'):
                sym = sym[:-4] + '/USDT'

            result.append({
                "symbol": sym,
                "qty": qty_abs,
                "avg_entry": entry,
                "current_price": current,
                "unrealized_pl": unrealized_pl,
                "unrealized_plpc": plpc,
                "side": side,
            })
    return result

def get_orders(status="open", limit=20):
    """Returns recent orders."""
    client = _get_client()
    
    all_orders = []
    # Loop over symbols in SYMBOL_MAP to fetch orders per symbol (required by Binance Futures)
    for sym in SYMBOL_MAP.values():
        try:
            if status == "open":
                orders = client.fetch_open_orders(sym, limit=limit)
            else:
                orders = client.fetch_orders(sym, limit=limit)
            all_orders.extend(orders)
        except Exception as e:
            print(f"Error fetching orders for {sym}: {e}")
            
    # Sort orders by timestamp descending
    all_orders.sort(key=lambda x: x.get('timestamp', 0) or 0, reverse=True)
    
    result = []
    for o in all_orders:
        if status == "open" and o['status'] != "open":
            continue
        if status == "closed" and o['status'] == "open":
            continue
            
        result.append({
            "id": str(o['id']),
            "symbol": o['symbol'],
            "side": str(o['side']),
            "qty": float(o['amount']) if o['amount'] else 0,
            "filled_qty": float(o['filled']) if o['filled'] else 0,
            "status": str(o['status']),
            "created_at": o['datetime'],
            "filled_avg_price": float(o['average']) if o['average'] else None,
        })
        if len(result) >= limit:
            break
            
    return result

def place_order(olimpo_symbol: str, side: str, qty: float, notional: float = None):
    """
    Place a market order on Binance.
    side: 'buy' or 'sell'
    qty: quantity in base asset (e.g. 0.001 BTC)
    notional: alternative - spend/receive this USD amount
    """
    client = _get_client()
    binance_symbol = SYMBOL_MAP.get(olimpo_symbol, olimpo_symbol)
    
    # Need to get current price if using notional to convert to qty
    if notional:
        ticker = client.fetch_ticker(binance_symbol)
        price = ticker['last']
        qty = notional / price
    
    # Binance requires precision formatting, ccxt handle it mostly with create_market_order, 
    # but we should ensure valid qty. Let CCXT handle the rounding via load_markets
    client.load_markets()
    qty = client.amount_to_precision(binance_symbol, qty)
    
    order = client.create_market_order(binance_symbol, side.lower(), float(qty))
    
    return {
        "id": str(order['id']),
        "symbol": order['symbol'],
        "side": str(order['side']),
        "qty": float(order['amount']),
        "status": str(order['status']),
        "created_at": order['datetime'],
    }

def close_position(olimpo_symbol: str):
    """Close entire position for a symbol."""
    client = _get_client()
    binance_symbol = SYMBOL_MAP.get(olimpo_symbol, olimpo_symbol)
    
    positions = get_positions()
    pos = None
    for p in positions:
        if p['symbol'] == binance_symbol or p['symbol'].replace('/', '') == binance_symbol.replace('/', ''):
            pos = p
            break
            
    if not pos:
        return {"symbol": binance_symbol, "status": "closed", "order_id": "none"}
        
    side = 'sell' if pos['side'].lower() == 'long' else 'buy'
    qty = float(pos['qty'])
    
    # Close via market order
    order = client.create_market_order(binance_symbol, side, qty, params={'reduceOnly': True})
    
    return {"symbol": binance_symbol, "status": "closed", "order_id": str(order['id'])}

def get_ohlcv(olimpo_symbol: str, timeframe: str = "1h", limit: int = 200) -> pd.DataFrame:
    """Fetch OHLCV bars from Binance Futures."""
    client = _get_client()
    binance_symbol = SYMBOL_MAP.get(olimpo_symbol, olimpo_symbol)
    
    # Mapping timeframe to ccxt standard if needed
    tf_map = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
    tf = tf_map.get(timeframe, "1h")
    
    bars = client.fetch_ohlcv(binance_symbol, tf, limit=limit)
    
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df.set_index('timestamp', inplace=True)
    
    return df

def test_connection():
    """Quick connectivity test. Returns (ok: bool, message: str)."""
    try:
        acc = get_account()
        mode = "PAPER (Testnet)" if acc["paper"] else "LIVE"
        return True, f"✅ Ligado Binance Futures ({mode}) | Saldo USDT: ${acc['cash']:,.2f} | Equity: ${acc['equity']:,.2f}"
    except ValueError as e:
        return False, f"❌ {e}"
    except Exception as e:
        return False, f"❌ Erro de ligação: {e}"

if __name__ == "__main__":
    ok, msg = test_connection()
    print(msg)
