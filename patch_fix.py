import sys

with open("app_ui.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if 'pass' in line and 'slider n' in lines[i-1]:
        # we found the pass line
        new_lines.append(line)
        # skip the next two lines if they contain 'aguardar expans' and '}'
        if i + 1 < len(lines) and 'aguardar expans' in lines[i+1]:
            continue
        continue
    
    # check if we are in the next line that we want to skip
    if i > 0 and 'pass' in lines[i-2] and 'slider n' in lines[i-3] and '}' in line:
        continue
    if i > 0 and 'pass' in lines[i-1] and 'slider n' in lines[i-2] and 'aguardar expans' in line:
        continue
        
    new_lines.append(line)

with open("app_ui.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("app_ui.py fixed")
