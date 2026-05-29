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

    # Terceira Linha: O Cérebro Activo do BOT (Regras de Consenso DNA)
    render_bot_brain_table()

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

def render_bot_brain_table():
    import os
    import json
    
    st.markdown("---")
    st.markdown("##### 🧠 O Cérebro Activo do BOT (Regras de Consenso DNA)")
    
    dna_path = "bot_consensus_dna.json"
    if not os.path.exists(dna_path):
        st.info("ℹ️ Nenhum DNA de Consenso Activo gravado. Vá à aba **Laboratório Matemático** para unificar lições do historial e gravar o cérebro do Bot!")
        return
        
    try:
        with open(dna_path, "r", encoding="utf-8") as f:
            dna = json.load(f)
    except Exception as e:
        st.error(f"Erro ao carregar o cérebro do Bot: {e}")
        return
        
    regimes = ["BULL", "BEAR", "LATERAL", "CAOTICO"]
    table_data = []
    
    for reg in regimes:
        reg_data = dna.get("regimes", {}).get(reg, {})
        if not reg_data or not reg_data.get("active", True):
            table_data.append({
                "Regime (Mercado)": reg,
                "Tipo de Gatilho": "Todos (Inativo)",
                "Stretching": "N/A",
                "Coesão da Mola": "N/A",
                "Disp. Vetorial": "N/A",
                "Aceleração Média": "N/A",
                "Filtros Extra": "Desativado neste regime"
            })
            continue
            
        # 1. BUY Rules (Entrada LONG)
        buy_rules = reg_data.get("buy_rules", {})
        if buy_rules:
            strt = buy_rules.get("stretching", {})
            mola = buy_rules.get("mola", {})
            disp = buy_rules.get("disp", {})
            acc = buy_rules.get("acceleration", {})
            infil = buy_rules.get("infil", {})
            reteste = buy_rules.get("reteste", {})
            
            strt_val = "Instável/Rejeitado"
            if strt.get("stable", False) and strt.get("mean") is not None:
                strt_val = f"{strt['mean']:+.2f}% ({strt.get('min_limit', 0):.2f}% a {strt.get('max_limit', 0):.2f}%)"
                
            mola_val = "Instável/Rejeitado"
            if mola.get("stable", False) and mola.get("mean") is not None:
                mola_val = f"{mola['mean']:.2f}% (Max: {mola.get('max_limit', 0):.2f}%)"
                
            disp_val = "Instável/Rejeitado"
            if disp.get("stable", False) and disp.get("mean") is not None:
                disp_val = f"{disp['mean']:+.2f}% (Max: {disp.get('max_limit', 0):.2f}%)"
                
            acc_val = "Instável/Rejeitado"
            if acc.get("stable", False) and acc.get("mean") is not None:
                symbol = "🔼 Reversão Bull" if acc['mean'] > 0 else "🔽 Reversão Bear"
                acc_val = f"{acc['mean']:+.4f} ({symbol})"
                
            extra_list = []
            if infil.get("active", False):
                extra_list.append(f"Infiltração ({infil.get('rate', 0):.1f}%)")
            if reteste.get("active", False):
                extra_list.append(f"Reteste Fibo ({reteste.get('rate', 0):.1f}%)")
            extra_val = " | ".join(extra_list) if extra_list else "Sem filtros extra"
            
            table_data.append({
                "Regime (Mercado)": f"🔹 {reg}",
                "Tipo de Gatilho": "🟢 Entrada LONG (BUY)",
                "Stretching": strt_val,
                "Coesão da Mola": mola_val,
                "Disp. Vetorial": disp_val,
                "Aceleração Média": acc_val,
                "Filtros Extra": extra_val
            })
        else:
            table_data.append({
                "Regime (Mercado)": f"🔹 {reg}",
                "Tipo de Gatilho": "🟢 Entrada LONG (BUY)",
                "Stretching": "Sem regras de compra",
                "Coesão da Mola": "N/A",
                "Disp. Vetorial": "N/A",
                "Aceleração Média": "N/A",
                "Filtros Extra": "N/A"
            })
            
        # 2. SELL Rules (Saída LONG / Entrada SHORT)
        sell_rules = reg_data.get("sell_rules", {})
        if sell_rules:
            strt = sell_rules.get("stretching", {})
            mola = sell_rules.get("mola", {})
            disp = sell_rules.get("disp", {})
            acc = sell_rules.get("acceleration", {})
            
            strt_val = "Instável/Rejeitado"
            if strt.get("stable", False) and strt.get("mean") is not None:
                strt_val = f"{strt['mean']:+.2f}% ({strt.get('min_limit', 0):.2f}% a {strt.get('max_limit', 0):.2f}%)"
                
            mola_val = "Instável/Rejeitado"
            if mola.get("stable", False) and mola.get("mean") is not None:
                mola_val = f"{mola['mean']:.2f}% (Média)"
                
            disp_val = "Instável/Rejeitado"
            if disp.get("stable", False) and disp.get("mean") is not None:
                disp_val = f"{disp['mean']:+.2f}% (Limit: {disp.get('limit', 0):.2f}%)"
                
            acc_val = "Instável/Rejeitado"
            if acc.get("stable", False) and acc.get("mean") is not None:
                symbol = "🔼 Reversão Bull" if acc['mean'] > 0 else "🔽 Reversão Bear"
                acc_val = f"{acc['mean']:+.4f} ({symbol})"
                
            table_data.append({
                "Regime (Mercado)": f"🔹 {reg}",
                "Tipo de Gatilho": "🔴 Saída LONG / Entrada SHORT (SELL)",
                "Stretching": strt_val,
                "Coesão da Mola": mola_val,
                "Disp. Vetorial": disp_val,
                "Aceleração Média": acc_val,
                "Filtros Extra": "N/A"
            })
        else:
            table_data.append({
                "Regime (Mercado)": f"🔹 {reg}",
                "Tipo de Gatilho": "🔴 Saída LONG / Entrada SHORT (SELL)",
                "Stretching": "Sem regras de venda",
                "Coesão da Mola": "N/A",
                "Disp. Vetorial": "N/A",
                "Aceleração Média": "N/A",
                "Filtros Extra": "N/A"
            })
            
    df_dna = pd.DataFrame(table_data)
    
    # Custom styling for high readability
    def style_gatilhos(val):
        if "Entrada" in str(val):
            return "background-color: rgba(34, 197, 94, 0.1); color: #15803d; font-weight: bold;"
        elif "Saída" in str(val):
            return "background-color: rgba(239, 68, 68, 0.1); color: #b91c1c; font-weight: bold;"
        return ""
        
    styled_df = df_dna.style.map(style_gatilhos, subset=["Tipo de Gatilho"])
    st.dataframe(styled_df, width='stretch', hide_index=True, height=310)
    
    last_up = dna.get("last_updated", "Desconhecido")
    selected = ", ".join(dna.get("selected_tests", []))
    st.markdown(f"<div style='font-size: 11px; color: #64748b; text-align: right; margin-top:-10px;'>🧬 <b>DNA unificado de:</b> {selected} | <b>Última Atualização:</b> {last_up}</div>", unsafe_allow_html=True)

def rebuild_consensus_dna():
    import os
    import json
    
    knowledge_path = "bot_knowledge_base.json"
    dna_path = "bot_consensus_dna.json"
    
    if not os.path.exists(knowledge_path):
        return
        
    try:
        with open(knowledge_path, "r", encoding="utf-8") as f:
            knowledge = json.load(f)
    except Exception as e:
        import streamlit as st
        st.error("Erro ao ler a base de dados de testes para fusão: " + str(e))
        return
        
    if not knowledge:
        return
        
    regimes = ["BULL", "BEAR", "LATERAL", "CAOTICO"]
    consensus_dna = {"smas": [], "regimes": {}, "last_updated": "", "selected_tests": []}
    
    latest_test_name = list(knowledge.keys())[-1]
    consensus_dna["smas"] = knowledge[latest_test_name].get("smas", [5, 13, 21, 55, 144])
    consensus_dna["selected_tests"] = list(knowledge.keys())
    
    for reg in regimes:
        opp_samples = 0
        thr_samples = 0
        
        opp_acc_list, opp_strt_list, opp_mola_list, opp_disp_list = [], [], [], []
        opp_weighted_acc, opp_weighted_strt, opp_weighted_mola, opp_weighted_disp = 0.0, 0.0, 0.0, 0.0
        opp_infil_weighted, opp_reteste_weighted = 0.0, 0.0
        
        thr_acc_list, thr_strt_list, thr_mola_list, thr_disp_list = [], [], [], []
        thr_weighted_acc, thr_weighted_strt, thr_weighted_mola, thr_weighted_disp = 0.0, 0.0, 0.0, 0.0
        thr_infil_weighted, thr_reteste_weighted = 0.0, 0.0
        
        for t_name, t_data in knowledge.items():
            reg_data = t_data.get("regimes", {}).get(reg, {})
            if not reg_data:
                continue
                
            opp_c = reg_data.get("opp_count", 0)
            thr_c = reg_data.get("thr_count", 0)
            
            opp_s = reg_data.get("opp_stats", {})
            if opp_c > 0 and opp_s:
                opp_samples += opp_c
                if "acc_mean" in opp_s: opp_acc_list.append(opp_s["acc_mean"])
                if "strt_mean" in opp_s: opp_strt_list.append(opp_s["strt_mean"])
                if "mola_mean" in opp_s: opp_mola_list.append(opp_s["mola_mean"])
                if "disp_mean" in opp_s: opp_disp_list.append(opp_s["disp_mean"])
                
                opp_weighted_acc += opp_s.get("acc_mean", 0.0) * opp_c
                opp_weighted_strt += opp_s.get("strt_mean", 0.0) * opp_c
                opp_weighted_mola += opp_s.get("mola_mean", 0.0) * opp_c
                opp_weighted_disp += opp_s.get("disp_mean", 0.0) * opp_c
                opp_infil_weighted += opp_s.get("infil_rate", 0.0) * opp_c
                opp_reteste_weighted += opp_s.get("reteste_rate", 0.0) * opp_c
                
            thr_s = reg_data.get("thr_stats", {})
            if thr_c > 0 and thr_s:
                thr_samples += thr_c
                if "acc_mean" in thr_s: thr_acc_list.append(thr_s["acc_mean"])
                if "strt_mean" in thr_s: thr_strt_list.append(thr_s["strt_mean"])
                if "mola_mean" in thr_s: thr_mola_list.append(thr_s["mola_mean"])
                if "disp_mean" in thr_s: thr_disp_list.append(thr_s["disp_mean"])
                
                thr_weighted_acc += thr_s.get("acc_mean", 0.0) * thr_c
                thr_weighted_strt += thr_s.get("strt_mean", 0.0) * thr_c
                thr_weighted_mola += thr_s.get("mola_mean", 0.0) * thr_c
                thr_weighted_disp += thr_s.get("disp_mean", 0.0) * thr_c
                thr_infil_weighted += thr_s.get("infil_rate", 0.0) * thr_c
                thr_reteste_weighted += thr_s.get("reteste_rate", 0.0) * thr_c
                
        opp_final_acc = opp_weighted_acc / opp_samples if opp_samples > 0 else 0.0
        opp_final_strt = opp_weighted_strt / opp_samples if opp_samples > 0 else 0.0
        opp_final_mola = opp_weighted_mola / opp_samples if opp_samples > 0 else 0.0
        opp_final_disp = opp_weighted_disp / opp_samples if opp_samples > 0 else 0.0
        opp_final_infil = opp_infil_weighted / opp_samples if opp_samples > 0 else 0.0
        opp_final_reteste = opp_reteste_weighted / opp_samples if opp_samples > 0 else 0.0
        
        thr_final_acc = thr_weighted_acc / thr_samples if thr_samples > 0 else 0.0
        thr_final_strt = thr_weighted_strt / thr_samples if thr_samples > 0 else 0.0
        thr_final_mola = thr_weighted_mola / thr_samples if thr_samples > 0 else 0.0
        thr_final_disp = thr_weighted_disp / thr_samples if thr_samples > 0 else 0.0
        thr_final_infil = thr_infil_weighted / thr_samples if thr_samples > 0 else 0.0
        thr_final_reteste = thr_reteste_weighted / thr_samples if thr_samples > 0 else 0.0
        
        def check_stability(lst):
            if not lst:
                return True
            has_pos = any(x > 0.0001 for x in lst)
            has_neg = any(x < -0.0001 for x in lst)
            return not (has_pos and has_neg)
            
        opp_acc_stable = check_stability(opp_acc_list)
        opp_strt_stable = check_stability(opp_strt_list)
        opp_mola_stable = check_stability(opp_mola_list)
        opp_disp_stable = check_stability(opp_disp_list)
        
        thr_acc_stable = check_stability(thr_acc_list)
        thr_strt_stable = check_stability(thr_strt_list)
        thr_mola_stable = check_stability(thr_mola_list)
        thr_disp_stable = check_stability(thr_disp_list)
        
        consensus_dna["regimes"][reg] = {
            "active": True,
            "opp_samples": opp_samples,
            "thr_samples": thr_samples,
            "buy_rules": {
                "stretching": {
                    "stable": bool(opp_strt_stable) if opp_samples > 0 else True,
                    "mean": float(opp_final_strt),
                    "min_limit": float(opp_final_strt - 1.5) if opp_strt_stable and opp_samples > 0 else -1.5,
                    "max_limit": float(opp_final_strt + 1.5) if opp_strt_stable and opp_samples > 0 else 1.5
                },
                "mola": {
                    "stable": bool(opp_mola_stable) if opp_samples > 0 else True,
                    "mean": float(opp_final_mola),
                    "max_limit": float(opp_final_mola * 1.3) if opp_mola_stable and opp_samples > 0 else 0.0
                },
                "disp": {
                    "stable": bool(opp_disp_stable) if opp_samples > 0 else True,
                    "mean": float(opp_final_disp),
                    "max_limit": float(opp_final_disp * 1.1) if opp_disp_stable and opp_samples > 0 else 0.0
                },
                "acceleration": {
                    "stable": bool(opp_acc_stable) if opp_samples > 0 else True,
                    "mean": float(opp_final_acc)
                },
                "infil": {
                    "rate": float(opp_final_infil),
                    "active": bool(opp_final_infil > 50.0) if opp_samples > 0 else False
                },
                "reteste": {
                    "rate": float(opp_final_reteste),
                    "active": bool(opp_final_reteste > 50.0) if opp_samples > 0 else False
                }
            },
            "sell_rules": {
                "stretching": {
                    "stable": bool(thr_strt_stable) if thr_samples > 0 else True,
                    "mean": float(thr_final_strt),
                    "min_limit": float(thr_final_strt - 1.5) if thr_strt_stable and thr_samples > 0 else -1.5,
                    "max_limit": float(thr_final_strt + 1.5) if thr_strt_stable and thr_samples > 0 else 1.5
                },
                "mola": {
                    "stable": bool(thr_mola_stable) if thr_samples > 0 else True,
                    "mean": float(thr_final_mola)
                },
                "disp": {
                    "stable": bool(thr_disp_stable) if thr_samples > 0 else True,
                    "mean": float(thr_final_disp),
                    "limit": float(thr_final_disp * 0.9) if thr_disp_stable and thr_samples > 0 else 0.0
                },
                "acceleration": {
                    "stable": bool(thr_acc_stable) if thr_samples > 0 else True,
                    "mean": float(thr_final_acc)
                }
            }
        }
        
    import pandas as pd
    consensus_dna["last_updated"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
    
    try:
        with open(dna_path, "w", encoding="utf-8") as f:
            json.dump(consensus_dna, f, indent=2, ensure_ascii=False)
    except Exception as e:
        import streamlit as st
        st.error("Erro ao gravar o DNA Consensual do Bot: " + str(e))
