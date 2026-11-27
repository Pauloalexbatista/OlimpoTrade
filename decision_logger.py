import sqlite3
import json
import os
from datetime import datetime

class DecisionLogger:
    def __init__(self, db_path="decision_log.sqlite"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    symbol TEXT,
                    action TEXT,
                    price REAL,
                    strategy_name TEXT,
                    context_json TEXT
                )
            ''')
            conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_ts ON decisions(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_action ON decisions(action)")

    def log_decision(self, timestamp, symbol, action, price, strategy_name, context):
        context_str = json.dumps(context) if context else "{}"
        if isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()
        else:
            timestamp = str(timestamp)
            
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO decisions (timestamp, symbol, action, price, strategy_name, context_json)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (timestamp, symbol, action, price, strategy_name, context_str))
