with open('variables_registry.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(320, 335):
        if i < len(lines):
            print(f"{i}: {repr(lines[i])}")
