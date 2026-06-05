# -*- coding: utf-8 -*-
import sys

with open("app_ui.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix Heatmap Velocity calculation (make it responsive to price)
t1 = "df['velocity'] = df['sma_5'].diff(periods=2)"
r1 = "df['velocity'] = df['close'].diff(periods=1)"
content = content.replace(t1, r1)

t2 = "df_train['velocity'] = df_train['sma_5'].diff(periods=2)"
r2 = "df_train['velocity'] = df_train['close'].diff(periods=1)"
content = content.replace(t2, r2)

with open("app_ui.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Velocity logic updated")
