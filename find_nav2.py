with open('tab_math_lab.py', 'r', encoding='utf-8', errors='ignore') as f:
    for i, line in enumerate(f):
        if 'st.button' in line and ('<' in line or '>' in line or 'Ant' in line or 'Seg' in line):
            print(f"{i}: {line.strip()}")
