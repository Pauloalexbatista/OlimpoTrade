import re

with open('app_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Card 1 background
old_bg1 = "<div style='background:linear-gradient(90deg,#0f172a,#1e293b,#0f172a); border:1px solid rgba(124,58,237,0.3); border-radius:12px; padding:16px; box-shadow:0 4px 24px rgba(0,0,0,0.4);'>"
new_bg1 = "<div style='background:#e0f2fe; border:1px solid #7dd3fc; border-radius:12px; padding:16px; box-shadow:0 4px 12px rgba(0,0,0,0.1); color:#0f172a;'>"
content = content.replace(old_bg1, new_bg1)

# Replace Card 1 text colors
content = content.replace("color:#a78bfa;'>Opera", "color:#0369a1;'>Opera")
content = content.replace("color:#94a3b8;'>Tipo de Opera", "color:#334155;'>Tipo de Opera")
content = content.replace("color:#94a3b8;'>Preço de Entrada", "color:#334155;'>Preço de Entrada")
content = content.replace("color:#94a3b8;'>Preço de Saída", "color:#334155;'>Preço de Saída")
content = content.replace("color:#94a3b8;'>Velas de Dura", "color:#334155;'>Velas de Dura")
content = content.replace("color:#94a3b8;'>Ponto de Entrada", "color:#334155;'>Ponto de Entrada")
content = content.replace("color:#94a3b8;'>Ponto de Saída", "color:#334155;'>Ponto de Saída")
content = content.replace("color:#94a3b8;'>Motivo da Saída", "color:#334155;'>Motivo da Saída")

# Also for some things I can just replace the hex strings inside the first card HTML block
# Let's just find the first card HTML and do string replace on it.
start_idx = content.find(new_bg1)
if start_idx != -1:
    end_idx = content.find("</div>", start_idx) + 6
    card1_html = content[start_idx:end_idx]
    
    # Text replacements in card1
    card1_html = card1_html.replace("color:#94a3b8;", "color:#334155;")
    card1_html = card1_html.replace("color:#a78bfa;", "color:#0369a1;")
    card1_html = card1_html.replace("color:#f1f5f9;", "color:#0f172a;")
    card1_html = card1_html.replace("rgba(255,255,255,0.08)", "#bae6fd")
    
    content = content[:start_idx] + card1_html + content[end_idx:]


# Replace Card 2 background
old_bg2 = "<div style='background:linear-gradient(90deg,#0f172a,#1e293b,#0f172a); border:1px solid rgba(124,58,237,0.3); border-radius:12px; padding:12px; box-shadow:0 4px 24px rgba(0,0,0,0.4);'>"
new_bg2 = "<div style='background:#e0f2fe; border:1px solid #7dd3fc; border-radius:12px; padding:12px; box-shadow:0 4px 12px rgba(0,0,0,0.1); color:#0f172a;'>"
content = content.replace(old_bg2, new_bg2)

# Card 2 header and body text colors
start_idx2 = content.find(new_bg2)
if start_idx2 != -1:
    end_idx2 = content.find("</table>", start_idx2) + 8
    card2_html = content[start_idx2:end_idx2]
    
    card2_html = card2_html.replace("color:#a78bfa;", "color:#0369a1;")
    card2_html = card2_html.replace("rgba(255,255,255,0.1)", "#bae6fd")
    
    content = content[:start_idx2] + card2_html + content[end_idx2:]

# Replace diff_clr gray logic
content = content.replace('diff_clr = "#10b981" if diff > 0 else ("#ef4444" if diff < 0 else "#94a3b8")', 'diff_clr = "#10b981" if diff > 0 else ("#ef4444" if diff < 0 else "#64748b")')
content = content.replace('diff_clr = "#94a3b8"', 'diff_clr = "#64748b"')

# Replace f"<td style='padding:5px 0; color:#f1f5f9;'>{label}</td>"
content = content.replace("color:#f1f5f9;'>{label}</td>", "color:#334155;'>{label}</td>")


with open('app_ui.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated cards to light blue with black text.")
