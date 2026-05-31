import os
for root, _, files in os.walk('.'):
    for file in files:
        if file.endswith('.py') and not file.startswith('find_') and not file.startswith('read_'):
            with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if 'st.button' in line:
                        print(f"{file}: {line.strip().encode('ascii', 'ignore').decode()}")
