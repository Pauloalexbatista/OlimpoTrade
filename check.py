import re

with open('app_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# find other instances of <div style="[^\"]*\n
matches = re.findall(r'<div style="[^>]*\n[^>]*>', content)
if matches:
    print(f"Found {len(matches)} other instances")
    for m in matches:
        print(m[:100] + '...')
else:
    print("No other instances found")
