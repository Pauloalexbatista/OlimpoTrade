# -*- coding: utf-8 -*-
import sys

with open("app_ui.py", "r", encoding="utf-8") as f:
    content = f.read()

t1 = '''                if st.session_state.get('tg_filter_squeeze_active', False):
                    # Squeeze ativo: exige que estejamos na primeira vela de rompimento
                    if _disp_now < _disp_min:
                        return "HOLD", 0.0, {
                            "Squeeze (Compressǜo)": f"Mola: {_disp_now:.3f}% < {_disp_min:.2f}%",
                            "Estado": "? Em compressǜo - aguardar rompimento"
                        }
                    elif _disp_prev >= _disp_min:
                        return "HOLD", 0.0, {
                            "Squeeze (Rompimento)": f"Mola prev ({_disp_prev:.3f}%) jǭ acima do mnimo ({_disp_min:.2f}%)",
                            "Estado": "?O Fora do ponto de partida da explosǜo"
                        }
                else:
                    # Filtro de dispersǜo normal
                    if _disp_now < _disp_min:
                        return "HOLD", 0.0, {
                            "Dispersǜo Mola": f"{_disp_now:.3f}%",
                            f"Mnimo ({_disp_min:.2f}%)": ">" SMAs comprimidas ? aguardar expansǜo",
                        }'''

# Substituindo por lógica correta, onde o checkbox apenas liga o escudo de compressão e não bloqueia trades pós-rompimento.
r1 = '''                if st.session_state.get('tg_filter_squeeze_active', False):
                    # Filtro de Squeeze Ativo: Atua como ESCUDO. 
                    # Se as médias estão muito juntas (compressão), não deixa entrar de todo.
                    if _disp_now < _disp_min:
                        return "HOLD", 0.0, {
                            "Filtro Squeeze Ativo": f"Mola: {_disp_now:.3f}% < Mínimo: {_disp_min:.2f}%",
                            "Estado": "⏸️ Em compressão. Sinais da estratégia bloqueados."
                        }
                else:
                    # Antes o slider sozinho ativava. Agora, se a checkbox estiver desligada, 
                    # o slider não bloqueia nada (para evitar confusões).
                    pass'''

# Vamos ter cuidado com a codificação do target
target_to_replace = []
lines = content.split('\n')
in_block = False
for i, line in enumerate(lines):
    if "if st.session_state.get('tg_filter_squeeze_active', False):" in line and "Squeeze ativo" in lines[i+1]:
        # Encontramos o bloco
        target_to_replace = lines[i:i+17]
        break

if target_to_replace:
    t_str = '\n'.join(target_to_replace)
    content = content.replace(t_str, r1)
    with open("app_ui.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Filtro corrigido com sucesso!")
else:
    print("Bloco não encontrado.")
