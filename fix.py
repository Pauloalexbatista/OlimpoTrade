import re

with open('app_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to find the specific st.markdown call that starts the arena stats
pattern = r'(st\.markdown\(f\"\"\"\n\s*<div style=\"background:linear-gradient\(90deg,#0f172a,#1e293b,#0f172a\);)\n\s*(border-radius:12px; padding:14px 24px; margin-bottom:14px;)\n\s*(display:flex; justify-content:space-between; align-items:center;)\n\s*(border:1px solid rgba\(124,58,237,0\.3\);)\n\s*(box-shadow:0 4px 24px rgba\(0,0,0,0\.4\);\">)'

replacement = r'\1 \2 \3 \4 \5'
new_content = re.sub(pattern, replacement, content, count=1)

if content != new_content:
    with open('app_ui.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Replaced successfully")
else:
    print("Pattern not found or already replaced")
