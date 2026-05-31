with open('app_ui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(1040, 1075):
        print(f"{i}: {lines[i].strip().encode('ascii', 'ignore').decode()}")
