
import ccxt
import pandas as pd
import time
import os
from datetime import datetime
from market_database import MarketDatabase

class DataCollector:
    def __init__(self, exchange_id='binance', symbol='BTC/USDT', timeframe='1h'):
        self.exchange_id = exchange_id
        self.symbol = symbol
        self.timeframe = timeframe
        self.exchange = getattr(ccxt, exchange_id)()
        self.db = MarketDatabase()
        
        # Public API access doesn't require keys
        # If private data (e.g., balance, open orders) were needed, keys would be loaded
        # from os.getenv('BINANCE_API_KEY') and os.getenv('BINANCE_SECRET_KEY')

    def get_ohlcv(self, limit=100):
        """
        Obtém dados OHLCV (candlesticks) para o símbolo e timeframe especificados.
        """
        try:
            # 1. Tentar ler os últimos dados gravados na DB para ver qual foi o último timestamp
            last_ts = self.db.get_last_timestamp(self.symbol, self.timeframe)
            
            # Fetch apenas dos dados novos (ou atualizar a última vela aberta)
            if last_ts is not None:
                ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, since=last_ts, limit=1000)
            else:
                ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=limit)
            
            # 2. Convert to DataFrame and save to DB
            df_new = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            self.db.upsert_data(self.symbol, self.timeframe, df_new)
            
            # 3. Read the complete required block directly from local DB
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
        """
        Testa a conexão com a exchange, verificando se a exchange está carregada.
        """
        try:
            markets = self.exchange.load_markets()
            print(f"Conectado com sucesso à {self.exchange_id}. Total de mercados: {len(markets)}")
            return True
        except ccxt.NetworkError as e:
            print(f"Erro de rede ao conectar à exchange: {e}")
            return False
        except ccxt.ExchangeError as e:
            print(f"Erro da exchange ao conectar: {e}")
            return False
        except Exception as e:
            print(f"Ocorreu um erro inesperado ao conectar à exchange: {e}")
            return False

if __name__ == "__main__":
    # Exemplo de uso
    collector = DataCollector(exchange_id='binance', symbol='BTC/USDT', timeframe='1h')
    
    if collector.test_connection():
        # Obter os últimos 100 candles de 1 hora para BTC/USDT
        data = collector.get_ohlcv(limit=100)
        if data is not None:
            print("\nPrimeiras 5 linhas dos dados obtidos:")
            print(data.head())
            print("\nÚltimas 5 linhas dos dados obtidos:")
            print(data.tail())
            print(f"Total de candles: {len(data)}")
