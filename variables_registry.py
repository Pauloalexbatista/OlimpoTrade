import streamlit as st
import pandas as pd

class QuantVariable:
    def __init__(self, key, name, category, description, formula, default_value, min_val=None, max_val=None, step=None, is_toggleable=False):
        self.key = key
        self.name = name
        self.category = category
        self.description = description
        self.formula = formula
        self.default_value = default_value
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.is_toggleable = is_toggleable

# Registo central das variáveis do sistema
VARIABLES = [
    # Médias Móveis (Fibonacci & Clássicas)
    QuantVariable("tg_p2", "Período SMA Rápida (P2)", "Médias Móveis (Lab/Jogo)", "Média móvel rápida imediata (cabeça do feixe). Representa a velocidade do momentum curto.", "SMA(Close, P2)", 5, 2, 20, 1),
    QuantVariable("tg_p3", "Período SMA Sinal (P3)", "Médias Móveis (Lab/Jogo)", "Média móvel usada para cruzamentos rápidos com P2 para gatilho.", "SMA(Close, P3)", 13, 3, 50, 1),
    QuantVariable("tg_p4", "Período SMA Intermédia (P4)", "Médias Móveis (Lab/Jogo)", "Média intermédia que define o alinhamento de curto/médio prazo.", "SMA(Close, P4)", 21, 5, 100, 1),
    QuantVariable("tg_p5", "Período SMA Lenta 1 (P5)", "Médias Móveis (Lab/Jogo)", "Média institucional lenta. Atua como primeiro trampolim de suporte.", "SMA(Close, P5)", 55, 10, 200, 1),
    QuantVariable("tg_p6", "Período SMA Lenta 2 (P6)", "Médias Móveis (Lab/Jogo)", "Média institucional profunda. Atua como o suporte gravitacional final.", "SMA(Close, P6)", 144, 20, 500, 1),
    
    # Médias Móveis Clássicas (PAULO_GOLD & Cruzamentos)
    QuantVariable("short_window_val", "Janela Curta Clássica (Rápida)", "Estratégias Clássicas", "Número de candles para a média curta móvel das estratégias clássicas.", "SMA(Close, Short)", 9, 2, 100, 1),
    QuantVariable("long_window_val", "Janela Longa Clássica (Lenta)", "Estratégias Clássicas", "Número de candles para a média longa móvel das estratégias clássicas.", "SMA(Close, Long)", 21, 5, 200, 1),
    QuantVariable("paulo_gold_min_dist_pct_val", "PG: Distância Mínima de Médias (%)", "Estratégias Clássicas", "Distância mínima exigida em % entre as médias rápidas/lentas na estratégia PAULO_GOLD.", "SMA_Rápida > SMA_Lenta * (1 + Dist%)", 0.0, 0.0, 2.0, 0.05),
    
    # Indicadores do Cockpit e Gatilhos
    QuantVariable("tg_bot_compress_thresh", "Compressão Mola (Limite)", "Indicadores Cockpit", "Limite máximo de Stretching (esticamento) para detetar compressão extrema da mola (consolidação).", "Stretching < Limite", 0.6, 0.1, 5.0, 0.1),
    QuantVariable("tg_min_confidence_pct", "Confiança Mínima de Entrada (%)", "Filtros e Decisão", "Percentagem mínima de regras que têm de estar válidas (verdes) para o Bot autorizar o trade.", "Regras Válidas / Total >= Confiança", 80.0, 50.0, 100.0, 5.0),
    
    # Gestão de Risco
    QuantVariable("tg_sl_pct", "Stop Loss (SL) %", "Gestão de Risco", "Limite máximo de perda percentual admitida por operação.", "Preço de Entrada * (1 - SL%)", 2.0, 0.5, 10.0, 0.1, is_toggleable=True),
    QuantVariable("tg_tp_pct", "Take Profit (TP) %", "Gestão de Risco", "Alvo de lucro percentual definido para saída automática.", "Preço de Entrada * (1 + TP%)", 7.0, 1.0, 25.0, 0.1, is_toggleable=True),
    QuantVariable("tg_ts_pct", "Trailing Stop (TS) %", "Gestão de Risco", "Trailing Stop para acompanhamento de ganhos acumulados.", "Stop dinâmico a partir do máximo", 1.5, 0.5, 5.0, 0.1, is_toggleable=True),
    
    # Fricções e Custos de Mercado
    QuantVariable("fee_pct_val", "Taxa Operacional API (%)", "Custos de Mercado", "Comissão cobrada pela exchange em cada compra e venda.", "Valor da Ordem * Taxa%", 0.1, 0.0, 1.0, 0.01),
    QuantVariable("tax_pct_val", "Imposto Mais-Valias (%)", "Custos de Mercado", "Percentagem de imposto deduzida automaticamente sobre lucros líquidos pós-jogo.", "Lucro Líquido * Imposto%", 28.0, 0.0, 50.0, 1.0),
    QuantVariable("slippage_pct_val", "Deslizamento (Slippage) (%)", "Custos de Mercado", "Fricção que simula pior preço de execução por atraso ou liquidez.", "Compra + Slippage%, Venda - Slippage%", 0.05, 0.0, 0.5, 0.01)
]

def initialize_variables_registry():
    """Garante que todas as variáveis quantitativas estão presentes no st.session_state."""
    for var in VARIABLES:
        # Inicializar ativação (se for toggleable)
        if var.is_toggleable:
            toggle_key = f"{var.key}_active"
            if toggle_key not in st.session_state:
                if var.key == "tg_sl_pct":
                    st.session_state[toggle_key] = st.session_state.get("tg_sl_active", True)
                elif var.key == "tg_tp_pct":
                    st.session_state[toggle_key] = st.session_state.get("tg_tp_active", False)
                elif var.key == "tg_ts_pct":
                    st.session_state[toggle_key] = st.session_state.get("tg_ts_active", False)
                else:
                    st.session_state[toggle_key] = True
                    
        # Inicializar valor principal
        if var.key not in st.session_state:
            if var.key == "tg_p2": st.session_state[var.key] = st.session_state.get("p2_window_val", var.default_value)
            elif var.key == "tg_p3": st.session_state[var.key] = st.session_state.get("p3_window_val", var.default_value)
            elif var.key == "tg_p4": st.session_state[var.key] = st.session_state.get("p4_window_val", var.default_value)
            elif var.key == "tg_p5": st.session_state[var.key] = st.session_state.get("p5_window_val", var.default_value)
            elif var.key == "tg_p6": st.session_state[var.key] = st.session_state.get("p6_window_val", var.default_value)
            else:
                st.session_state[var.key] = var.default_value
                
    # Variáveis booleanas manuais adicionais
    if "paulo_gold_trend_filter_val" not in st.session_state:
        st.session_state.paulo_gold_trend_filter_val = False
    if "allow_reentry_val" not in st.session_state:
        st.session_state.allow_reentry_val = True

def render_variable_widget(var):
    # Se for toggleable (ex: Stop Loss, Take Profit), desenhar toggle e slider
    if var.is_toggleable:
        toggle_key = f"{var.key}_active"
        st.session_state[toggle_key] = st.toggle(
            f"Ativar {var.name.split(' ')[0]}", 
            value=st.session_state.get(toggle_key, True), 
            key=f"tg_toggle_{var.key}"
        )
        # Sincronizar com variáveis antigas do jogo
        if var.key == "tg_sl_pct":
            st.session_state.tg_sl_active = st.session_state[toggle_key]
        elif var.key == "tg_tp_pct":
            st.session_state.tg_tp_active = st.session_state[toggle_key]
        elif var.key == "tg_ts_pct":
            st.session_state.tg_ts_active = st.session_state[toggle_key]
            
        if st.session_state[toggle_key]:
            st.session_state[var.key] = st.slider(
                var.name, 
                min_value=var.min_val, 
                max_value=var.max_val, 
                value=float(st.session_state.get(var.key, var.default_value)), 
                step=var.step,
                key=f"tg_slide_{var.key}"
            )
            # Sincronizar valor com jogo
            if var.key == "tg_sl_pct": st.session_state.tg_sl_pct = st.session_state[var.key]
            elif var.key == "tg_tp_pct": st.session_state.tg_tp_pct = st.session_state[var.key]
            elif var.key == "tg_ts_pct": st.session_state.tg_ts_pct = st.session_state[var.key]
        else:
            st.markdown(f"<p style='color:#64748b; font-style:italic; font-size:12px;'>{var.name} desativado.</p>", unsafe_allow_html=True)
    else:
        # Variável numérica padrão
        if var.step is not None:
            st.session_state[var.key] = st.slider(
                var.name, 
                min_value=var.min_val, 
                max_value=var.max_val, 
                value=float(st.session_state.get(var.key, var.default_value)) if isinstance(var.default_value, float) else int(st.session_state.get(var.key, var.default_value)), 
                step=var.step,
                key=f"tg_slide_{var.key}"
            )
        else:
            st.session_state[var.key] = st.number_input(
                var.name,
                value=st.session_state.get(var.key, var.default_value),
                key=f"tg_num_{var.key}"
            )

def render_variables_dashboard(compact=False):
    """Desenha a Central & Dicionário de Variáveis. Suporta compact=True para ecrãs de topo."""
    initialize_variables_registry()
    
    if not compact:
        st.markdown("<h2 style='text-align: center; color: #7c3aed;'>🔧 Central & Dicionário de Variáveis</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b;'>A fonte única de verdade e painel de comando quantitativo do OlimpoTrade.</p>", unsafe_allow_html=True)
        st.markdown("---")

    # Renderizar os ajustadores divididos em 4 Colunas horizontais
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    
    with col1:
        st.markdown("##### 📏 Médias Móveis")
        mavg_vars = [v for v in VARIABLES if v.category == "Médias Móveis (Lab/Jogo)"]
        for var in mavg_vars:
            render_variable_widget(var)
            
    with col2:
        st.markdown("##### ⚙️ Estratégias & Cockpit")
        # Checkboxes extras para Estratégias Clássicas
        st.session_state.paulo_gold_trend_filter_val = st.checkbox(
            "PG: Filtro Macro", 
            value=st.session_state.paulo_gold_trend_filter_val,
            key="tg_chk_pg_filter"
        )
        st.session_state.allow_reentry_val = st.checkbox(
            "Re-Entrada Tendência", 
            value=st.session_state.allow_reentry_val,
            key="tg_chk_reentry"
        )
        
        # Variáveis de Estratégias Clássicas e Indicadores Cockpit
        class_vars = [v for v in VARIABLES if v.category in ["Estratégias Clássicas", "Indicadores Cockpit"]]
        for var in class_vars:
            render_variable_widget(var)
            
    with col3:
        st.markdown("##### 🛡️ Decisão & Risco")
        risk_vars = [v for v in VARIABLES if v.category in ["Filtros e Decisão", "Gestão de Risco"]]
        for var in risk_vars:
            render_variable_widget(var)
            
    with col4:
        st.markdown("##### 💸 Custos & Operações")
        cost_vars = [v for v in VARIABLES if v.category == "Custos de Mercado"]
        for var in cost_vars:
            render_variable_widget(var)
            
        st.markdown("<div style='height:25px;'></div>", unsafe_allow_html=True)
        # Botão para repor padrões
        if st.button("🔄 Repor Padrões (Reset)", width='stretch', type="secondary", key="tg_btn_reset_global"):
            for var in VARIABLES:
                st.session_state[var.key] = var.default_value
                if var.is_toggleable:
                    st.session_state[f"{var.key}_active"] = (var.key == "tg_sl_pct")
                    if var.key == "tg_sl_pct": st.session_state.tg_sl_active = True
                    elif var.key == "tg_tp_pct": st.session_state.tg_tp_active = False
                    elif var.key == "tg_ts_pct": st.session_state.tg_ts_active = False
            st.session_state.paulo_gold_trend_filter_val = False
            st.session_state.allow_reentry_val = True
            st.toast("Valores de fábrica repostos com sucesso!")
            st.rerun()

    # Segunda Linha: O Dicionário de Conceitos a ocupar toda a largura (100% de ecrã)
    st.markdown("---")
    st.markdown("##### 📖 Dicionário de Conceitos & Fórmulas (Consulta)")
    
    table_data = []
    for var in VARIABLES:
        status = "Ativo"
        if var.is_toggleable:
            status = "LIGADO" if st.session_state.get(f"{var.key}_active", True) else "DESLIGADO"
        
        table_data.append({
            "Categoria": var.category,
            "Nome": var.name,
            "Conceito/Fórmula": var.formula,
            "Descrição/Finalidade": var.description,
            "Valor Ativo (Estado)": f"{st.session_state.get(var.key)} ({status})"
        })
        
    df_vars = pd.DataFrame(table_data)
    st.dataframe(df_vars, width='stretch', hide_index=True, height=350)
