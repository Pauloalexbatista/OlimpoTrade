with open('app_ui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if 'PAULO_GOLD' in line and i > 1700:
            print(f"{i}: {line.strip().encode('ascii', 'ignore').decode()}")
