# -*- coding: utf-8 -*-
import sys

with open("app_ui.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: app_ui.py:571
t1 = "collector = DataCollector(exchange_id='binance', symbol=symbol, timeframe=timeframe)"
r1 = "collector = DataCollector({'EXCHANGE_NAME': 'binance', 'SYMBOL': symbol, 'TIMEFRAME': timeframe})"
content = content.replace(t1, r1)

# Fix 2: app_ui.py:1134
t2 = "collector = DataCollector(exchange_id='binance', symbol=symbol, timeframe=timeframe)"
r2 = "collector = DataCollector({'EXCHANGE_NAME': 'binance', 'SYMBOL': symbol, 'TIMEFRAME': timeframe})"
content = content.replace(t2, r2)

# Fix 3: app_ui.py:3965
t3 = "collector = DataCollector(exchange_id='binance', symbol=symbol, timeframe='1h')"
r3 = "collector = DataCollector({'EXCHANGE_NAME': 'binance', 'SYMBOL': symbol, 'TIMEFRAME': '1h'})"
content = content.replace(t3, r3)

with open("app_ui.py", "w", encoding="utf-8") as f:
    f.write(content)
print("DataCollector calls fixed")
