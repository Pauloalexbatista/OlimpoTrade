# -*- coding: utf-8 -*-
import sys

with open("variables_registry.py", "r", encoding="utf-8") as f:
    content = f.read()

t1 = "'Lagarta (Todas as Linhas)',"
r1 = "'Momentum Puro',\n            'Lagarta (Todas as Linhas)',"
if t1 in content:
    content = content.replace(t1, r1, 1)
    print("Replace 1 done")

with open("variables_registry.py", "w", encoding="utf-8") as f:
    f.write(content)
