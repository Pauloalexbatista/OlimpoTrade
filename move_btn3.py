import re

with open('app_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Locate the Markdown report block
# It starts around eport_md = [f"# Relatório de Auditoria das Operações\n\n**Trader:** {st.session_state.tg_trader_name}\n**Jogo:** {st.session_state.get('tg_game_name', 'Sem Nome')}\n\n"]
# And ends with st.error(f"Erro ao gerar relat\u00f3rio Markdown: {str(e_rep)}")
start_pattern = r'(\s+)(try:\s*report_md = \[f"# Relat[^"]*rio de Auditoria das Opera.*?st\.error\(f"Erro ao gerar relat[^"]*rio Markdown: \{str\(e_rep\)\}"\))'
match = re.search(start_pattern, content, re.DOTALL)

if match:
    indent = match.group(1)
    markdown_block = match.group(2)
    # Remove it from current location
    content = content.replace(match.group(0), "")
    
    # Locate the CSV block
    csv_pattern = r'(st\.error\(f"Erro ao gerar CSV: \{str\(e_csv\)\}"\))'
    csv_match = re.search(csv_pattern, content)
    
    if csv_match:
        csv_error_line = csv_match.group(1)
        # We need to insert after the try/except block for CSV.
        # So we insert right after st.error(f"Erro ao gerar CSV: {str(e_csv)}") + "\n"
        
        # Build replacement string
        insertion = csv_error_line + "\n" + indent + markdown_block
        content = content.replace(csv_error_line, insertion)
        
        with open('app_ui.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully moved the Markdown report button!")
    else:
        print("Could not find CSV error line.")
else:
    print("Could not find Markdown block.")

