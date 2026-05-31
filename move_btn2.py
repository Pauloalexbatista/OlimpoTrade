import re

with open('app_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's search for "Relatrio de Auditoria Completo (Markdown)"
match = re.search(r'(try:\s*report_md\s*=\s*\[.*?st\.error\(f"Erro.*?e_rep\}\"\))', content, re.DOTALL)
if match:
    markdown_block = match.group(1)
    # remove it
    content = content.replace(markdown_block, "")
    
    # insert it under the CSV button
    csv_match = re.search(r'(st\.error\(f"Erro ao gerar CSV:.*?\}\"\))', content)
    if csv_match:
        csv_block = csv_match.group(1)
        # put markdown block under it
        # Note: the indentation might be different, let's adjust indentation based on csv_block
        lines = markdown_block.split('\n')
        # We assume it's indented the same as the CSV try block
        content = content.replace(csv_block, csv_block + "\n\n" + markdown_block)
        
        with open('app_ui.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Moved Markdown block successfully!")
    else:
        print("Could not find CSV block")
else:
    print("Could not find Markdown block")
