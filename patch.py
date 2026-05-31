import sys
file_path = 'app_ui.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_long = '''                    if is_growing and is_crossover_long:
                        return "LONG", 100.0, cond_dict'''
new_long = '''                    if is_growing and is_crossover_long:
                        if "Lagarta" in st.session_state.get("tg_strategy_type", "") and st.session_state.get("tg_position", "NONE") == "SHORT":
                            return "HOLD", 0.0, cond_dict
                        return "LONG", 100.0, cond_dict'''

old_short = '''                    elif is_falling and is_crossover_short:
                        cond_dict_short = {'''
new_short = '''                    elif is_falling and is_crossover_short:
                        if "Lagarta" in st.session_state.get("tg_strategy_type", "") and st.session_state.get("tg_position", "NONE") == "LONG":
                            return "HOLD", 0.0, {"Gatilho": "Ignorado pela Lagarta (Apenas SL/TS saem)"}
                        cond_dict_short = {'''

content = content.replace(old_long, new_long)
content = content.replace(old_short, new_short)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated compute_bot_signal successfully.')
