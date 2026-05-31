with open('app_ui.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'trade_idx' in line or 'view_index' in line or 'current_view' in line or 'current_trade' in line:
            print(f"{i}: {line.strip().encode('ascii', 'ignore').decode()}")
