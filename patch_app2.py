# -*- coding: utf-8 -*-
import sys

with open("app_ui.py", "r", encoding="utf-8") as f:
    content = f.read()

t = "            # --- ESTRATÉGIA CUSTOMIZADA: CRUZAMENTO DE LINHA ÚNICA ---"
r = """            elif "Momentum Puro" in st.session_state.get("tg_strategy_type", "Default"):
                vel = df['velocity'].iloc[step] if 'velocity' in df.columns else 0.0
                acc = df['acceleration'].iloc[step] if 'acceleration' in df.columns else 0.0
                
                cond_dict = {"Velocidade": vel, "Aceleração": acc}
                _cur = st.session_state.get("tg_position", "NONE")
                
                # Prioridade 1: Condições de Entrada
                if vel > 0 and acc > 0:
                    return "LONG", 100.0, cond_dict
                elif vel < 0 and acc < 0:
                    return "SHORT", 100.0, cond_dict
                    
                # Prioridade 2: Saída para FLAT se a direção inverter
                if _cur == "LONG" and vel < 0:
                    return "HOLD", 100.0, {**cond_dict, "Gatilho": "Saída Direção Negativa"}
                elif _cur == "SHORT" and vel > 0:
                    return "HOLD", 100.0, {**cond_dict, "Gatilho": "Saída Direção Positiva"}
                    
                return "HOLD", 0.0, cond_dict

            # --- ESTRATÉGIA CUSTOMIZADA: CRUZAMENTO DE LINHA ÚNICA ---"""

# T might be encoded slightly differently, I will just match 'ESTRAT' and 'CRUZAMENTO DE LINHA'
lines = content.split('\n')
target_idx = -1
for i, line in enumerate(lines):
    if "ESTRAT" in line and "CRUZAMENTO DE LINHA" in line:
        target_idx = i
        break

if target_idx != -1:
    lines.insert(target_idx, """            elif "Momentum Puro" in st.session_state.get("tg_strategy_type", "Default"):
                vel = df['velocity'].iloc[step] if 'velocity' in df.columns else 0.0
                acc = df['acceleration'].iloc[step] if 'acceleration' in df.columns else 0.0
                
                cond_dict = {"Velocidade": vel, "Aceleração": acc}
                _cur = st.session_state.get("tg_position", "NONE")
                
                if vel > 0 and acc > 0:
                    return "LONG", 100.0, cond_dict
                elif vel < 0 and acc < 0:
                    return "SHORT", 100.0, cond_dict
                    
                if _cur == "LONG" and vel < 0:
                    return "HOLD", 100.0, {**cond_dict, "Gatilho": "Saída Direção Negativa"}
                elif _cur == "SHORT" and vel > 0:
                    return "HOLD", 100.0, {**cond_dict, "Gatilho": "Saída Direção Positiva"}
                    
                return "HOLD", 0.0, cond_dict
""")
    with open("app_ui.py", "w", encoding="utf-8") as f:
        f.write('\n'.join(lines))
    print("app_ui.py patched successfully")
else:
    print("Target not found")
