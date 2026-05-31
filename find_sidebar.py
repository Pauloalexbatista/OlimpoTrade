with open('variables_registry.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'st.sidebar' in line:
            print(f"{i}: {line.strip()}")
