with open('variables_registry.py', 'r', encoding='utf-8') as f:
    content = f.read()
    start = content.find("if _arena_selected != st.session_state.get('tg_strategy_type'):")
    if start != -1:
        print("Found at:", start)
        print(repr(content[start:start+100]))
