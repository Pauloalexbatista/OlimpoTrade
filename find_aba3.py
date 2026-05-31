with open('app_ui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(1200, 1260):
        if 'st.' in lines[i]:
            print(f"{i}: {lines[i].strip().encode('ascii', 'ignore').decode()}")
