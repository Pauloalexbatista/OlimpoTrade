import re

with open('app_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's find ALL st.markdown(..., unsafe_allow_html=True) blocks and remove empty lines inside them
def clean_all_html_blocks(match):
    block = match.group(0)
    # Check if it has a f''' or f""" or """ or ''' string
    # Just strip empty lines from the matched block
    lines = block.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip() != '']
    # add a newline before the closing """ if it was joined with the last tag
    return "\n".join(cleaned_lines)

# This regex might be tricky. Let's just find st.markdown(f"""...""", unsafe_allow_html=True)
pattern = r'(st\.markdown\([f]?\"\"\"[\s\S]*?\"\"\",\s*unsafe_allow_html=True\))'

new_content = re.sub(pattern, clean_all_html_blocks, content)

if content != new_content:
    with open('app_ui.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Cleaned empty lines from all st.markdown html blocks.")
else:
    print("No other blocks needed cleaning.")
