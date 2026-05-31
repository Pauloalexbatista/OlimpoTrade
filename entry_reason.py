import re

with open('app_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Store entry reason in Bot Autonomo
# We need to find the exact block for Bot Autonomo entry
bot_entry_long_pattern = r'(elif _bot_signal == "LONG" and _bot_conf >= st\.session_state\.get\("tg_min_confidence_pct", 80\.0\):\s*\n\s*st\.session_state\.tg_position = "LONG"\s*\n\s*st\.session_state\.tg_entry_price = price_now\s*\n\s*st\.session_state\.tg_entry_step = current_step\s*\n\s*st\.session_state\.tg_highest_price = price_now)'
bot_entry_long_replacement = r'\1\n                                    st.session_state.tg_entry_reason = _bot_conds.get("Gatilho", "Sinal do Robô")'
content = re.sub(bot_entry_long_pattern, bot_entry_long_replacement, content)

bot_entry_short_pattern = r'(elif _bot_signal == "SHORT" and _bot_conf >= st\.session_state\.get\("tg_min_confidence_pct", 80\.0\):\s*\n\s*st\.session_state\.tg_position = "SHORT"\s*\n\s*st\.session_state\.tg_entry_price = price_now\s*\n\s*st\.session_state\.tg_entry_step = current_step\s*\n\s*st\.session_state\.tg_lowest_price = price_now)'
bot_entry_short_replacement = r'\1\n                                    st.session_state.tg_entry_reason = _bot_conds.get("Gatilho", "Sinal do Robô")'
content = re.sub(bot_entry_short_pattern, bot_entry_short_replacement, content)

# 2. Add entry reason in Manual Entry (under Casino Buttons)
manual_long_pattern = r'(if st\.button\("ENTRAR LONG  \[OFF\]", width="stretch", key="tg_btn_long_inact"\):\s*\n\s*st\.session_state\.tg_position = "LONG"\s*\n\s*st\.session_state\.tg_entry_price = price_now\s*\n\s*st\.session_state\.tg_entry_step = current_step)'
manual_long_replacement = r'\1\n                            st.session_state.tg_entry_reason = "Manual (Decisão do Utilizador)"'
content = re.sub(manual_long_pattern, manual_long_replacement, content)

manual_short_pattern = r'(if st\.button\("ENTRAR SHORT  \[OFF\]", width="stretch", key="tg_btn_short_inact"\):\s*\n\s*st\.session_state\.tg_position = "SHORT"\s*\n\s*st\.session_state\.tg_entry_price = price_now\s*\n\s*st\.session_state\.tg_entry_step = current_step)'
manual_short_replacement = r'\1\n                            st.session_state.tg_entry_reason = "Manual (Decisão do Utilizador)"'
content = re.sub(manual_short_pattern, manual_short_replacement, content)


# 3. Read it in record_and_append_trade
append_pattern = r'(t_dict\["entry_mola"\] = float\(df_data\[\'mola_pct\'\]\.iloc\[e_step\]\) if \'mola_pct\' in df_data\.columns else 0\.0\s*\n\s*except Exception as e:\s*\n\s*pass\s*\n\s*)'
append_replacement = r'\1            t_dict["entry_reason"] = st.session_state.get("tg_entry_reason", "Desconhecido")\n            '
content = re.sub(append_pattern, append_replacement, content)


# 4. Add it to the detailed analysis card table
# Search for: <tr><td style='padding:6px 0; color:#334155;'>Motivo da Saída</td>...
# And insert Motivo da Entrada before it.
card1_row_pattern = r"(<tr><td style='padding:6px 0; color:#334155;'>Motivo da Saída</td>)"
card1_row_replacement = r"<tr><td style='padding:6px 0; color:#334155;'>Motivo da Entrada</td><td style='padding:6px 0; text-align:right; font-weight:bold; color:#0f172a;'>{tr.get('entry_reason', 'N/A')}</td></tr>\n\1"
content = re.sub(card1_row_pattern, card1_row_replacement, content)

with open('app_ui.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated bot reason logic successfully.")
