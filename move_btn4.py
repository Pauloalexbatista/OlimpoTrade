import re

with open('app_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# The Markdown block starts with a try: block, and we know it contains "Descarregar Relat" and "Auditoria Completo".
# Let's find the try: block that contains this text.
# An easy way is to find the index of "Descarregar Relat", then search backwards for "try:".
btn_idx = content.find("Descarregar Relat")
# Actually, the button text is "Descarregar Relatório de Auditoria Completo (Markdown)"
btn_idx = content.find("Auditoria Completo (Markdown)")
if btn_idx != -1:
    try_idx = content.rfind("try:", 0, btn_idx)
    # The end of the block is the end of the except block.
    # We find "except Exception as e_rep:"
    except_idx = content.find("except Exception as e_rep:", btn_idx)
    if except_idx != -1:
        end_err_idx = content.find("st.error(", except_idx)
        # Find the end of the line containing st.error
        end_idx = content.find("\n", end_err_idx) + 1
        
        # We have the block
        markdown_block = content[try_idx:end_idx]
        
        # Remove from original string
        content = content[:try_idx] + content[end_idx:]
        
        # Now find where to insert: under the CSV block.
        # Find "Erro ao gerar CSV:"
        csv_err_idx = content.find("Erro ao gerar CSV:")
        if csv_err_idx != -1:
            csv_end_idx = content.find("\n", csv_err_idx) + 1
            
            # The indentation of the markdown block is the same as the CSV block
            # Let's get the indentation before the CSV try block
            csv_try_idx = content.rfind("try:\n", 0, csv_err_idx)
            
            # Insert
            content = content[:csv_end_idx] + "\n" + (" " * 16) + markdown_block + content[csv_end_idx:]
            
            with open('app_ui.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print("Successfully moved!")
        else:
            print("CSV err not found")
    else:
        print("except not found")
else:
    print("btn not found")
