import re

with open('app_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the indents
content = re.sub(
    r'\n(\s+)st\.session_state\.tg_highest_price = price_now\s*\n(\s*)st\.session_state\.tg_entry_reason = _bot_conds\.get\("Gatilho", "Sinal do Robô"\)',
    r'\n\1st.session_state.tg_highest_price = price_now\n\1st.session_state.tg_entry_reason = _bot_conds.get("Gatilho", "Sinal do Robô")',
    content
)

content = re.sub(
    r'\n(\s+)st\.session_state\.tg_lowest_price = price_now\s*\n(\s*)st\.session_state\.tg_entry_reason = _bot_conds\.get\("Gatilho", "Sinal do Robô"\)',
    r'\n\1st.session_state.tg_lowest_price = price_now\n\1st.session_state.tg_entry_reason = _bot_conds.get("Gatilho", "Sinal do Robô")',
    content
)

# And fix the ones inside the "B) Entradas Imediatamente (reversão na mesma vela)" section
content = re.sub(
    r'(\s+)st\.session_state\.tg_highest_price = price_now\n(\s+)st\.session_state\.tg_entry_reason = _bot_conds\.get\("Gatilho", "Sinal do Robô"\)',
    r'\1st.session_state.tg_highest_price = price_now\1st.session_state.tg_entry_reason = _bot_conds.get("Gatilho", "Sinal do Robô")',
    content
)

content = re.sub(
    r'(\s+)st\.session_state\.tg_lowest_price = price_now\n(\s+)st\.session_state\.tg_entry_reason = _bot_conds\.get\("Gatilho", "Sinal do Robô"\)',
    r'\1st.session_state.tg_lowest_price = price_now\1st.session_state.tg_entry_reason = _bot_conds.get("Gatilho", "Sinal do Robô")',
    content
)

# Replace all occurrences of over-indented st.session_state.tg_entry_reason with 28 spaces (which is the level of st.session_state.tg_lowest_price)
# Actually, let's just find "st.session_state.tg_entry_reason =" and ensure its indent matches the previous line
lines = content.split('\n')
for i in range(1, len(lines)):
    if "st.session_state.tg_entry_reason = " in lines[i]:
        # get indent of previous non-empty line
        prev_idx = i - 1
        while prev_idx >= 0 and lines[prev_idx].strip() == "":
            prev_idx -= 1
        if prev_idx >= 0:
            prev_indent = len(lines[prev_idx]) - len(lines[prev_idx].lstrip())
            curr_indent = len(lines[i]) - len(lines[i].lstrip())
            
            # replace indent
            lines[i] = (" " * prev_indent) + lines[i].lstrip()

content = '\n'.join(lines)

with open('app_ui.py', 'w', encoding='utf-8') as f:
    f.write(content)
