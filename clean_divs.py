import re

with open('app_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace newlines inside ALL style attributes for multiline divs in st.markdown blocks
# A robust way is to just find all <div style="[^>]+"> and if they have \n, replace \n with space.
# But we must be careful not to match too broadly.
# Let's find all instances of <div style="[^"]+"> and replace \n inside the double quotes.

def replacer(match):
    # match.group(1) is everything inside style="..."
    clean_style = match.group(1).replace('\n', ' ')
    clean_style = re.sub(r'\s+', ' ', clean_style)
    return f'<div style="{clean_style}">'

new_content = re.sub(r'<div\s+style="([^"]+)">', replacer, content)

if content != new_content:
    with open('app_ui.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Cleaned all <div style=...> tags with newlines.")
else:
    print("No other multiline div style tags to clean.")
