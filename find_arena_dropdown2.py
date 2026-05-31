with open('app_ui.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'Modelo de Decisão' in line or 'Modelo de Decis' in line:
            print(f"app_ui.py {i}: {line.strip()}")
            
with open('variables_registry.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'Modelo de Decisão' in line or 'Modelo de Decis' in line:
            print(f"variables_registry.py {i}: {line.strip()}")
