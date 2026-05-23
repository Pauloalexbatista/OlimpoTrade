# my_trading_bot/config.py
import os
from dotenv import load_dotenv

def load_config():
    load_dotenv() # Load environment variables from .env file

    return {
        "ENV": os.getenv("ENV", "development"),
        "API_KEY": os.getenv("API_KEY"),
        "API_SECRET": os.getenv("API_SECRET"),
        "EXCHANGE_NAME": "binance", # Starting with Binance as discussed
        "SYMBOL": "BTC/USDT", # Example symbol
        "TIMEFRAME": "1h", # 1 hour candles
        "TRADING_INTERVAL_SECONDS": 60 * 5, # Check every 5 minutes
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "LOG_FILE": "trading_bot.log",

        # Risk Management (initial placeholders)
        "MAX_RISK_PER_TRADE_PERCENT": 1.0, # 1% of total capital
        "STOP_LOSS_PERCENT": 2.0, # 2% below entry
        "TAKE_PROFIT_PERCENT": 5.0, # 5% above entry
        "MAX_DAILY_LOSS_PERCENT": 5.0, # 5% of total capital allowed to lose per day
        "INITIAL_CAPITAL": 1000.0, # For simulation/paper trading
    }
