with open('app_ui.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'PAULO_GOLD' in line or 'MULTIPOINT_VECTOR' in line or 'SMA_CROSSOVER' in line:
            print(f"{i}: {line.strip().encode('ascii', 'ignore').decode()}")
