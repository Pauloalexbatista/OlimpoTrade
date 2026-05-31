with open('app_ui.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'st.number_input' in line:
            print(f"{i}: {line.strip().encode('ascii', 'ignore').decode()}")
