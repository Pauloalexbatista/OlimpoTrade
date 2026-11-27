import sqlite3
import pandas as pd
import os

class MarketDatabase:
    def __init__(self, db_path='market_data.sqlite'):
        self.db_path = db_path
        self._create_table()

    def _create_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ohlcv (
                symbol TEXT,
                timeframe TEXT,
                timestamp INTEGER,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                PRIMARY KEY (symbol, timeframe, timestamp)
            )
        ''')
        conn.commit()
        conn.close()

    def upsert_data(self, symbol, timeframe, df):
        if df.empty:
            return
            
        conn = sqlite3.connect(self.db_path)
        records = []
        for _, row in df.iterrows():
            records.append((
                symbol,
                timeframe,
                int(row['timestamp']),
                float(row['open']),
                float(row['high']),
                float(row['low']),
                float(row['close']),
                float(row['volume'])
            ))
            
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT OR REPLACE INTO ohlcv (symbol, timeframe, timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', records)
        
        conn.commit()
        conn.close()
        
    def get_data(self, symbol, timeframe, limit=1000):
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT timestamp, open, high, low, close, volume 
            FROM ohlcv 
            WHERE symbol = ? AND timeframe = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        '''
        df = pd.read_sql_query(query, conn, params=(symbol, timeframe, limit))
        conn.close()
        
        if df.empty:
            return df
            
        df = df.sort_values('timestamp').reset_index(drop=True)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('datetime', inplace=True)
        return df

    def get_last_timestamp(self, symbol, timeframe):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(timestamp) FROM ohlcv WHERE symbol = ? AND timeframe = ?", (symbol, timeframe))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result and result[0] else None
