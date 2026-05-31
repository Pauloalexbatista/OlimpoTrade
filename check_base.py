with open('variables_registry.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(220, 245):
        print(f"{i}: {lines[i].strip().encode('ascii', 'ignore').decode()}")
