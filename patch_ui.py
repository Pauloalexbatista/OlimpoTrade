# -*- coding: utf-8 -*-
import sys
import os

with open("app_ui.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace 1
t1 = '''            l_eff = (_l_wins / len(_l_trades) * 100) if _l_trades else 0.0
            s_eff = (_s_wins / len(_s_trades) * 100) if _s_trades else 0.0
            
            scores.append({
                "name": name, 
                "capital": float(final_capital),
                "return": float(final_capital - 100.0), 
                "trades": int(trades_count),
                "strategy": strat_type,'''
r1 = '''            l_eff = (_l_wins / len(_l_trades) * 100) if _l_trades else 0.0
            s_eff = (_s_wins / len(_s_trades) * 100) if _s_trades else 0.0
            
            num_tests = st.session_state.get("tg_max_candles", 100)
            
            scores.append({
                "name": name, 
                "capital": float(final_capital),
                "return": float(final_capital - 100.0), 
                "trades": int(trades_count),
                "num_tests": int(num_tests),
                "strategy": strat_type,'''
if t1 in content:
    content = content.replace(t1, r1)
    print("Replace 1 applied")
else:
    print("Replace 1 failed")

# Replace 2
t2 = '''            scores = load_highscores()
            
            if scores:
                tab_melhores, tab_piores = st.tabs('''
r2 = '''            col_ldr1, col_ldr2 = st.columns([8, 2])
            with col_ldr2:
                if st.button("🗑️ Apagar Histórico", key="clear_leaderboard"):
                    if os.path.exists(highscores_file):
                        os.remove(highscores_file)
                    st.toast("Histórico da Arena apagado com sucesso!")
                    st.rerun()

            scores = load_highscores()
            
            if scores:
                tab_melhores, tab_piores = st.tabs('''
if t2 in content:
    content = content.replace(t2, r2)
    print("Replace 2 applied")
else:
    print("Replace 2 failed")

# Replace 3
t3 = '''                            "Nome": s.get("name", "Trader Anon"),
                            "Banca Final": f"{s.get('capital', 100.0):.2f} EUR",
                            "Retorno": f"{s.get('return', 0.0):+.2f}%",
                            "Trades": s.get("trades", 0),'''
r3 = '''                            "Nome": s.get("name", "Trader Anon"),
                            "Banca Final": f"{s.get('capital', 100.0):.2f} EUR",
                            "Retorno": f"{s.get('return', 0.0):+.2f}%",
                            "Trades": s.get("trades", 0),
                            "Testes": s.get("num_tests", 100),'''
if t3 in content:
    content = content.replace(t3, r3)
    print("Replace 3 applied")
else:
    print("Replace 3 failed")

with open("app_ui.py", "w", encoding="utf-8") as f:
    f.write(content)
print("app_ui.py updated successfully!")
