import os
for root, _, files in os.walk('.'):
    for file in files:
        if file.endswith('.py'):
            with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    if 'st.button' in line and ('<' in line or '>' in line or 'Ant' in line or 'Prox' in line or 'Seg' in line):
                        print(f"Found in {file} line {i}: {line.strip()}")
