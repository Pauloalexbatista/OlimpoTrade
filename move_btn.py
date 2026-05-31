import re

with open('app_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# The Markdown generation block looks something like:
#                 try:
#                     report_md = [f"# Relat...
#                     ...
#                     st.error(f"Erro ao gerar relatório Markdown: {str(e_rep)}")
# It is under "with col_tr_info:" probably? No, it's outside.

# Let's extract the markdown block exactly.
start_str = "                try:\n                    report_md = ["
end_str = "Erro ao gerar relat" # "st.error(f\"Erro ao gerar relat\u00f3rio Markdown: {str(e_rep)}\")"

# We need to find the block
try_start = content.find(start_str)
if try_start != -1:
    end_index = content.find("st.error(f\"Erro ao", try_start)
    if end_index != -1:
        end_of_block = content.find("\n", end_index) + 1
        markdown_block = content[try_start:end_of_block]
        
        # Now remove it from there
        content = content[:try_start] + content[end_of_block:]
        
        # Now find where to insert it: under CSV download button
        csv_end_str = "st.error(f\"Erro ao gerar CSV"
        csv_end_index = content.find(csv_end_str)
        if csv_end_index != -1:
            csv_end_of_block = content.find("\n", csv_end_index) + 1
            
            # Insert markdown block
            content = content[:csv_end_of_block] + "\n" + markdown_block + content[csv_end_of_block:]
            
            with open('app_ui.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print("Moved Markdown download button successfully.")
        else:
            print("Could not find CSV end block")
    else:
        print("Could not find Markdown end block")
else:
    print("Could not find Markdown start block")
