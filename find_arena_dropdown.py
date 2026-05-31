with open('variables_registry.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(230, 270):
        if i < len(lines):
            print(f"{i}: {lines[i].strip().encode('ascii', 'ignore').decode()}")
