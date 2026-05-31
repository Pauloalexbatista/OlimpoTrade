import re

with open('app_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's find the st.markdown block that starts with <div style="background:linear-gradient(90deg,#0f172a,#1e293b,#0f172a);
# and ends with """, unsafe_allow_html=True)
pattern = r'(st\.markdown\(f\"\"\"\n\s*<div style="background:linear-gradient\(90deg,#0f172a,#1e293b,#0f172a\).*?\"\"\", unsafe_allow_html=True\))'

def clean_html_block(match):
    block = match.group(1)
    # remove all empty lines
    lines = block.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip() != '']
    # reconstruct
    return "\n".join(cleaned_lines)

new_content = re.sub(pattern, clean_html_block, content, flags=re.DOTALL)

if content != new_content:
    with open('app_ui.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Cleaned empty lines and indentation in the header div block.")
else:
    print("Could not find the block or no changes made.")
