import ccxt
import pandas as pd
import time
import os
from datetime import datetime
from market_database import MarketDatabase

class DataCollector:
    def __init__(self, config=None, logger=None):
        # Support both initialization styles
        if isinstance(config, str):
            # Old style: DataCollector(exchange_id, symbol, timeframe)
            self.exchange_id = config
            self.symbol = logger if logger else 'BTC/USDT'
            self.timeframe = 'BTC/USDT'  # placeholder
            self.logger = None
        else:
            # New style: DataCollector(config, logger)
            self.exchange_id = config.get("EXCHANGE_NAME", "binance") if config else "binance"
            self.symbol = config.get("SYMBOL", "BTC/USDT") if config else "BTC/USDT"
            self.timeframe = config.get("TIMEFRAME", "1h") if config else "1h"
            self.logger = logger

        self.exchange = getattr(ccxt, self.exchange_id)()
        self.db = MarketDatabase()

    async def get_latest_data(self, limit=100):
        """Async wrapper para get_ohlcv"""
        return self.get_ohlcv(limit)

    def get_ohlcv(self, limit=100):
        """Obtém dados OHLCV (candlesticks) para o símbolo e timeframe especificados."""
        try:
            last_ts = self.db.get_last_timestamp(self.symbol, self.timeframe)
            
            if last_ts is not None:
                ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, since=last_ts, limit=1000)
            else:
                ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=limit)
            
            df_new = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            self.db.upsert_data(self.symbol, self.timeframe, df_new)
            
            df = self.db.get_data(self.symbol, self.timeframe, limit=limit)
            
            print(f"Dados sincronizados e lidos da BD para {self.symbol} ({self.timeframe}): {len(df)} candles.")
            return df
        except ccxt.NetworkError as e:
            print(f"Erro de rede ao obter OHLCV: {e}")
            return None
        except ccxt.ExchangeError as e:
            print(f"Erro da exchange ao obter OHLCV: {e}")
            return None
        except Exception as e:
            print(f"Ocorreu um erro inesperado ao obter OHLCV: {e}")
            return None

    def test_connection(self):
        """Testa a conexão com a exchange."""
        try:
            markets = self.exchange.load_markets()
            print(f"Conectado com sucesso a {self.exchange_id}. Total de mercados: {len(markets)}")
            return True
        except ccxt.NetworkError as e:
            print(f"Erro de rede ao conectar a exchange: {e}")
            return False
        except ccxt.ExchangeError as e:
            print(f"Erro da exchange ao conectar: {e}")
            return False
        except Exception as e:
            print(f"Ocorreu um erro inesperado ao conectar a exchange: {e}")
            return False

if __name__ == "__main__":
    collector = DataCollector(exchange_id='binance', symbol='BTC/USDT', timeframe='1h')
    
    if collector.test_connection():
        data = collector.get_ohlcv(limit=100)
        if data is not None:
            print("\nPrimeiras 5 linhas dos dados obtidos:")
            print(data.head())
            print("\nUltimas 5 linhas dos dados obtidos:")
            print(data.tail())
            print(f"Total de candles: {len(data)}")
