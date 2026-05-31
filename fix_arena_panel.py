import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("app_ui.py", "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

old_start = "        # --- COCKPIT DE CONFIGURACOES ---"
old_end   = "        # --- AUTO-TREINO: movido para o tab Cerebro do Bot (DNA) ---"
idx_start = content.find(old_start)
idx_end   = content.find(old_end)
print(f"Bloco encontrado: {idx_start} -> {idx_end}")

new_panel = open("arena_panel_code.py", "r", encoding="utf-8").read()

if idx_start >= 0 and idx_end > idx_start:
    content = content[:idx_start] + new_panel + content[idx_end + len(old_end):]
    with open("app_ui.py", "w", encoding="utf-8", errors="replace") as f:
        f.write(content)
    print(f"OK. Gravado: {os.path.getsize(chr(39)app_ui.py{chr(39))} bytes")
else:
    print("ERRO: marcadores nao encontrados")
