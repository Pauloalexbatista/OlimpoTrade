with open('app_ui.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'st.button' in line and ('>' in line or '<' in line or 'Anterior' in line or 'Seguinte' in line or 'Próximo' in line or 'Proximo' in line):
            print(f"{i}: {line.strip().encode('ascii', 'ignore').decode()}")
