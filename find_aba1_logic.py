with open('app_ui.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if ('position = ' in line or 'signal =' in line) and i < 1000:
            print(f"{i}: {line.strip().encode('ascii', 'ignore').decode()}")
