with open('tab_math_lab.py', 'r', encoding='utf-8', errors='ignore') as f:
    for i, line in enumerate(f):
        if 'st.button' in line or 'st.columns' in line:
            print(f"{i}: {line.strip().encode('ascii', 'ignore').decode()}")
