with open('app_ui.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'if strategy_type ' in line and i > 1200:
            print(f"{i}: {line.strip().encode('ascii', 'ignore').decode()}")
