with open('app_ui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(850, 950):
        if 'def ' in lines[i] or 'sim_df' in lines[i] or 'PAULO_GOLD' in lines[i]:
            print(f"{i}: {lines[i].strip().encode('ascii', 'ignore').decode()}")
