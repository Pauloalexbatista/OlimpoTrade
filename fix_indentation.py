with open('variables_registry.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
expander_lines = []
in_expander = False

for i, line in enumerate(lines):
    if 'with st.expander(' in line:
        in_expander = True
        expander_lines.append(line)
    elif in_expander:
        expander_lines.append(line)
        if "''')" in line:
            in_expander = False
    elif line.startswith('        # Auto-configurar risco por estrategia'):
        new_lines.append('            # Auto-configurar risco por estrategia\n')
    elif '            st.rerun()' in line:
        new_lines.append(line)
        new_lines.append('\n')
        new_lines.extend(expander_lines)
        expander_lines = []
    else:
        new_lines.append(line)

with open('variables_registry.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Expander moved down and indentation fixed!')
