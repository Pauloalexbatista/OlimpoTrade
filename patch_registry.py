# -*- coding: utf-8 -*-
import sys

with open("variables_registry.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace 1: add to list
t1 = """        _arena_strategies = [
            'Default (Manual)',
            'Cérebro de Consenso (IA)',
            'Lagarta (Todas as Linhas)',
            'Linha Solitária',
            'Média Camadas (Duas Linhas)',
            '⭐ Claude - Pirâmide Fibonacci'
        ]"""
r1 = """        _arena_strategies = [
            'Default (Manual)',
            'Cérebro de Consenso (IA)',
            'Lagarta (Todas as Linhas)',
            'Linha Solitária',
            'Média Camadas (Duas Linhas)',
            'Momentum Puro',
            '⭐ Claude - Pirâmide Fibonacci'
        ]"""
if t1 in content:
    content = content.replace(t1, r1)
    print("Replace 1 done")

# Replace 2: Auto config
t2 = """          elif 'Camadas' in _arena_selected or 'Esmigalhador' in _arena_selected:"""
r2 = """          elif 'Momentum Puro' in _arena_selected:
              st.session_state.tg_sl_pct_active = True
              st.session_state.tg_sl_active = True
              st.session_state.tg_sl_pct = 0.5
              st.session_state.tg_ts_pct_active = True
              st.session_state.tg_ts_active = True
              st.session_state.tg_ts_pct = 0.5
              st.session_state.tg_tp_pct_active = False
              st.session_state.tg_tp_active = False
              st.session_state.tg_bot_mode = "Bot Autonomo"
              st.session_state.tg_lagarta_min_disp = 0.0
              st.toast('Momentum Puro: SL=0.5% TS=0.5% - Só entra com Vel 1:1 Acel 1!')
          elif 'Camadas' in _arena_selected or 'Esmigalhador' in _arena_selected:"""
if t2 in content:
    content = content.replace(t2, r2)
    print("Replace 2 done")

# Replace 3: Description block
t3 = """                'Lagarta (Todas as Linhas)': {"""
r3 = """                'Momentum Puro': {
                    'gradient': 'linear-gradient(135deg, rgba(239,68,68,0.15) 0%, rgba(185,28,28,0.3) 100%)',
                    'border': 'rgba(239,68,68,0.2)',
                    'icon': '⚡',
                    'color': '#ef4444',
                    'title': 'Estratégia Momentum Puro',
                    'desc': '<b>🔥 Funcionamento:</b><br>'
                            '  Ignora as linhas e usa apenas a física de mercado (Aceleração e Velocidade).<br>'
                            '  <b>Gatilho LONG:</b> Entra APENAS quando Velocidade > 0 e Aceleração > 0.<br>'
                            '  <b>Saída LONG:</b> Sai quando a Velocidade inverte para negativo.<br>'
                            '  <b>Gatilho SHORT:</b> Entra APENAS quando Velocidade < 0 e Aceleração < 0.<br>'
                            '  <b>Saída SHORT:</b> Sai quando a Velocidade inverte para positivo.'
                },
                'Lagarta (Todas as Linhas)': {"""
if t3 in content:
    content = content.replace(t3, r3)
    print("Replace 3 done")

with open("variables_registry.py", "w", encoding="utf-8") as f:
    f.write(content)
print("variables_registry.py updated")
