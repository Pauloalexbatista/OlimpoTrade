with open('app_ui.py', 'r', encoding='utf-8') as f:
    in_aba3 = False
    for line in f:
        if 'with tab3:' in line:
            in_aba3 = True
        elif in_aba3 and 'with tab4:' in line:
            break
        if in_aba3:
            print(line.strip().encode('ascii', 'ignore').decode())
