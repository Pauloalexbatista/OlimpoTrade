with open('app_ui.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'with tab3:' in line:
            for j in range(max(0, i-2), min(i+50, sum(1 for _ in open('app_ui.py', 'r', encoding='utf-8')))):
                f.seek(0)
                print(f"{j}: {f.readlines()[j].strip().encode('ascii', 'ignore').decode()}")
            break
