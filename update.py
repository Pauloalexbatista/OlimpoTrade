import sys

file_path = 'app_ui.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'if "Cruzamento" in st.session_state.get("tg_strategy_type", "Default"):',
    'if "Lagarta" in st.session_state.get("tg_strategy_type", "Default") or "Cruzamento" in st.session_state.get("tg_strategy_type", "Default"):'
)

content = content.replace(
    "_tag_map = {'Default': 'EQ', 'Cerebro': 'DNA', 'Cruzamento': 'X-LINE', 'Camadas': 'LAYERS'}",
    "_tag_map = {'Default': 'EQ', 'Cerebro': 'DNA', 'Cruzamento': 'X-LINE', 'Lagarta': 'LAGARTA', 'Camadas': 'LAYERS'}"
)

content = content.replace(
    "_clr_map = {'Default': '#64748b', 'Cerebro': '#7c3aed', 'Cruzamento': '#0284c7', 'Camadas': '#dc2626'}",
    "_clr_map = {'Default': '#64748b', 'Cerebro': '#7c3aed', 'Cruzamento': '#0284c7', 'Lagarta': '#10b981', 'Camadas': '#dc2626'}"
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated app_ui.py successfully.')
