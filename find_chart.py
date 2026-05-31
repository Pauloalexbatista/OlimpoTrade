with open('app_ui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(2750, 2800):
        if 'st.plotly_chart' in lines[i] or '_build_chart' in lines[i] or 'fig' in lines[i]:
            print(f"{i}: {lines[i].strip().encode('ascii', 'ignore').decode()}")
