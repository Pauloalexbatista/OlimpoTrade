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
    # Se for toggleable (ex: Stop Loss, Take Profit), desenhar toggle and slider
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
    import pandas as pd
    import numpy as np
    import streamlit as st
    
    st.markdown("---")
    st.markdown("##### 🧠 O Cérebro Activo do BOT (Regras de Consenso DNA - 12 Variáveis Quantitativas)")
    
    dna_path = "bot_consensus_dna.json"
    if not os.path.exists(dna_path):
        st.info("🧠 Nenhum DNA de Consenso Activo gravado. Vá à aba **Laboratório Matemático** ou **Arena** para treinar e gravar o cérebro!")
        return
        
    try:
        with open(dna_path, "r", encoding="utf-8") as f:
            dna = json.load(f)
    except Exception as e:
        st.error(f"Erro ao carregar o cérebro do Bot: {e}")
        return
        
    vars_def = [
        {
            "id": 1,
            "name": "Compressão da Mola",
            "json": "mola_mean",
            "math": "std(SMAs) / mean(SMAs) * 100",
            "meaning": "Mede o quão comprimidas estão as médias. Valores baixos indicam consolidação estreita (mola comprimida pronta a explodir).",
            "key": "mola",
            "key_exit": "mola_exit",
            "fmt": "{:.2f}%"
        },
        {
            "id": 2,
            "name": "Estiramento (Stretching)",
            "json": "strt_mean",
            "math": "mean(|SMA_i - SMA_med|) / SMA_med * 100",
            "meaning": "Mede o afastamento médio das médias em relação à média central do feixe. Indica sobrecompra/sobrevenda local.",
            "key": "stretching",
            "key_exit": "stretching_exit",
            "fmt": "{:.2f}%"
        },
        {
            "id": 3,
            "name": "Dispersão Vetorial",
            "json": "disp_mean",
            "math": "(SMA_5 - SMA_144) / SMA_144 * 100",
            "meaning": "Mede a abertura máxima macro e alinhamento direcional. Positivo = alta (Bull); Negativo = baixa (Bear).",
            "key": "disp",
            "key_exit": "disp_exit",
            "fmt": "{:+.2f}%"
        },
        {
            "id": 4,
            "name": "Velocidade",
            "json": "vel_mean",
            "math": "SMA_5 - SMA_5 (atrás 2 velas)",
            "meaning": "Mede o momentum ou velocidade da tendência rápida de curto prazo.",
            "key": "velocity",
            "key_exit": "velocity_exit",
            "fmt": "{:+.4f}"
        },
        {
            "id": 5,
            "name": "Aceleração",
            "json": "acc_mean",
            "math": "Velocidade - Velocidade (atrás 2 velas)",
            "meaning": "Mede a aceleração/desaceleração rápida. Crucial para identificar a exaustão de um movimento e reversão iminente.",
            "key": "acceleration",
            "key_exit": "acceleration_exit",
            "fmt": "{:+.4f}"
        },
        {
            "id": 6,
            "name": "Volatilidade",
            "json": "vol_mean",
            "math": "std(Fechos, 20 velas)",
            "meaning": "Mede o ruído do mercado. Permite rejeitar operações se a volatilidade for caótica para o regime.",
            "key": "volatility",
            "key_exit": "volatility_exit",
            "fmt": "{:.4f}"
        },
        {
            "id": 7,
            "name": "Taxa de Infiltração",
            "json": "infil_rate",
            "math": "% gatilhos com SMA 5>13>21 e 55<144",
            "meaning": "Mede a percentagem de operações de contra-tendência profunda onde o curto prazo infiltra o longo prazo.",
            "key": "infil",
            "key_exit": "infil_exit",
            "fmt": "{:.1f}%",
            "is_rate": True
        },
        {
            "id": 8,
            "name": "Taxa de Reteste",
            "json": "reteste_rate",
            "math": "% fechos a menos de 0.8% da SMA 55 ou 144",
            "meaning": "Mede a precisão das entradas em pullback nos suportes ou resistências de Fibonacci macro.",
            "key": "reteste",
            "key_exit": "reteste_exit",
            "fmt": "{:.1f}%",
            "is_rate": True
        },
        {
            "id": 9,
            "name": "Momentum de Força (RSI 14)",
            "json": "rsi_mean",
            "math": "100 - (100 / (1 + RS)) [14 velas]",
            "meaning": "Oscilador clássico de força de momentum. Evita comprar topos (sobrecompra >70) e vender fundos (sobrevenda <30).",
            "key": "rsi",
            "key_exit": "rsi_exit",
            "fmt": "{:.2f}"
        },
        {
            "id": 10,
            "name": "Fronteira Estatística (BB %)",
            "json": "bb_dist_mean",
            "math": "(Price - Lower) / (Upper - Lower) * 100",
            "meaning": "Mede a posição do preço em relação às bandas. >100% indica rompimento de alta; <0% indica rompimento de baixa.",
            "key": "bb",
            "key_exit": "bb_exit",
            "fmt": "{:.2f}%"
        },
        {
            "id": 11,
            "name": "Aceleração Macro (MACD Hist)",
            "json": "macd_mean",
            "math": "MACD_Line - MACD_Signal [12, 26, 9]",
            "meaning": "Mede a força de aceleração da tendência de longo prazo. Evita operar contra marés macro fortes.",
            "key": "macd",
            "key_exit": "macd_exit",
            "fmt": "{:+.4f}"
        },
        {
            "id": 12,
            "name": "Respiração do Mercado (ATR 14)",
            "json": "atr_mean",
            "math": "rolling_mean(True_Range, 14)",
            "meaning": "Mede a volatilidade real de cada vela. Excelente para stop-loss dinâmico e exaustão do regime.",
            "key": "atr",
            "key_exit": "atr_exit",
            "fmt": "{:.4f}"
        }
    ]
    
    columns = pd.MultiIndex.from_tuples([
        ("#", "", ""),
        ("Variável", "", ""),
        ("Nome Técnico", "", ""),
        ("Cálculo Matemático", "", ""),
        ("Significado / Objetivo no Cérebro", "", ""),
        
        ("BULL (Alta)", "LONG (Compra)", "Entrada"),
        ("BULL (Alta)", "LONG (Compra)", "Saída"),
        ("BULL (Alta)", "SHORT (Venda)", "Entrada"),
        ("BULL (Alta)", "SHORT (Venda)", "Saída"),
        
        ("BEAR (Baixa)", "LONG (Compra)", "Entrada"),
        ("BEAR (Baixa)", "LONG (Compra)", "Saída"),
        ("BEAR (Baixa)", "SHORT (Venda)", "Entrada"),
        ("BEAR (Baixa)", "SHORT (Venda)", "Saída"),
        
        ("LATERAL (Consolidação)", "LONG (Compra)", "Entrada"),
        ("LATERAL (Consolidação)", "LONG (Compra)", "Saída"),
        ("LATERAL (Consolidação)", "SHORT (Venda)", "Entrada"),
        ("LATERAL (Consolidação)", "SHORT (Venda)", "Saída"),
        
        ("CAÓTICO (Ruído)", "LONG (Compra)", "Entrada"),
        ("CAÓTICO (Ruído)", "LONG (Compra)", "Saída"),
        ("CAÓTICO (Ruído)", "SHORT (Venda)", "Entrada"),
        ("CAÓTICO (Ruído)", "SHORT (Venda)", "Saída")
    ])
    
    table_rows = []
    for v in vars_def:
        row = [
            v["id"],
            v["name"],
            v["json"],
            v["math"],
            v["meaning"]
        ]
        for reg in ["BULL", "BEAR", "LATERAL", "CAOTICO"]:
            reg_rules = dna.get("regimes", {}).get(reg, {})
            buy = reg_rules.get("buy_rules", {})
            sell = reg_rules.get("sell_rules", {})
            
            if v.get("is_rate"):
                val_long_in = buy.get(v['key'], {}).get("rate")
                val_long_out = buy.get(v['key_exit'], {}).get("rate")
                val_short_in = sell.get(v['key'], {}).get("rate")
                val_short_out = sell.get(v['key_exit'], {}).get("rate")
            else:
                val_long_in = buy.get(v['key'], {}).get("mean")
                val_long_out = buy.get(v['key_exit'], {}).get("mean")
                val_short_in = sell.get(v['key'], {}).get("mean")
                val_short_out = sell.get(v['key_exit'], {}).get("mean")
                
            def fmt_val(val):
                if val is None or pd.isna(val) or val == 0.0:
                    return "-"
                return v['fmt'].format(val)
                
            row.append(fmt_val(val_long_in))
            row.append(fmt_val(val_long_out))
            row.append(fmt_val(val_short_in))
            row.append(fmt_val(val_short_out))
            
        table_rows.append(row)
        
    df_dna = pd.DataFrame(table_rows, columns=columns)
    
    st.dataframe(df_dna, width='stretch', hide_index=True, height=550)

def rebuild_consensus_dna():
    import os
    import json
    import pandas as pd
    import numpy as np
    
    dna_path = "bot_consensus_dna.json"
    knowledge_path = "bot_knowledge_base.json"
    
    if not os.path.exists(knowledge_path):
        return
        
    try:
        with open(knowledge_path, "r", encoding="utf-8") as f:
            knowledge = json.load(f)
    except Exception:
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
        
        opp_weighted = {
            "stretching": 0.0, "stretching_exit": 0.0,
            "mola": 0.0, "mola_exit": 0.0,
            "disp": 0.0, "disp_exit": 0.0,
            "velocity": 0.0, "velocity_exit": 0.0,
            "acceleration": 0.0, "acceleration_exit": 0.0,
            "volatility": 0.0, "volatility_exit": 0.0,
            "infil": 0.0, "infil_exit": 0.0,
            "reteste": 0.0, "reteste_exit": 0.0,
            "rsi": 0.0, "rsi_exit": 0.0,
            "bb": 0.0, "bb_exit": 0.0,
            "macd": 0.0, "macd_exit": 0.0,
            "atr": 0.0, "atr_exit": 0.0
        }
        
        thr_weighted = {
            "stretching": 0.0, "stretching_exit": 0.0,
            "mola": 0.0, "mola_exit": 0.0,
            "disp": 0.0, "disp_exit": 0.0,
            "velocity": 0.0, "velocity_exit": 0.0,
            "acceleration": 0.0, "acceleration_exit": 0.0,
            "volatility": 0.0, "volatility_exit": 0.0,
            "infil": 0.0, "infil_exit": 0.0,
            "reteste": 0.0, "reteste_exit": 0.0,
            "rsi": 0.0, "rsi_exit": 0.0,
            "bb": 0.0, "bb_exit": 0.0,
            "macd": 0.0, "macd_exit": 0.0,
            "atr": 0.0, "atr_exit": 0.0
        }
        
        for t_name, t_data in knowledge.items():
            reg_data = t_data.get("regimes", {}).get(reg, {})
            if not reg_data:
                continue
                
            opp_c = reg_data.get("opp_count", 0)
            thr_c = reg_data.get("thr_count", 0)
            
            opp_s = reg_data.get("opp_stats", {})
            if opp_c > 0 and opp_s:
                opp_samples += opp_c
                opp_weighted["stretching"] += opp_s.get("strt_mean", 0.0) * opp_c
                opp_weighted["stretching_exit"] += opp_s.get("strt_exit_mean", opp_s.get("strt_mean", 0.0)) * opp_c
                opp_weighted["mola"] += opp_s.get("mola_mean", 0.0) * opp_c
                opp_weighted["mola_exit"] += opp_s.get("mola_exit_mean", opp_s.get("mola_mean", 0.0)) * opp_c
                opp_weighted["disp"] += opp_s.get("disp_mean", 0.0) * opp_c
                opp_weighted["disp_exit"] += opp_s.get("disp_exit_mean", opp_s.get("disp_mean", 0.0)) * opp_c
                opp_weighted["velocity"] += opp_s.get("vel_mean", 0.0) * opp_c
                opp_weighted["velocity_exit"] += opp_s.get("vel_exit_mean", opp_s.get("vel_mean", 0.0)) * opp_c
                opp_weighted["acceleration"] += opp_s.get("acc_mean", 0.0) * opp_c
                opp_weighted["acceleration_exit"] += opp_s.get("acc_exit_mean", opp_s.get("acc_mean", 0.0)) * opp_c
                opp_weighted["volatility"] += opp_s.get("vol_mean", 0.0) * opp_c
                opp_weighted["volatility_exit"] += opp_s.get("vol_exit_mean", opp_s.get("vol_mean", 0.0)) * opp_c
                opp_weighted["infil"] += opp_s.get("infil_rate", 0.0) * opp_c
                opp_weighted["infil_exit"] += opp_s.get("infil_exit_rate", opp_s.get("infil_rate", 0.0)) * opp_c
                opp_weighted["reteste"] += opp_s.get("reteste_rate", 0.0) * opp_c
                opp_weighted["reteste_exit"] += opp_s.get("reteste_exit_rate", opp_s.get("reteste_rate", 0.0)) * opp_c
                opp_weighted["rsi"] += opp_s.get("rsi_mean", 50.0) * opp_c
                opp_weighted["rsi_exit"] += opp_s.get("rsi_exit_mean", opp_s.get("rsi_mean", 50.0)) * opp_c
                opp_weighted["bb"] += opp_s.get("bb_dist_mean", 50.0) * opp_c
                opp_weighted["bb_exit"] += opp_s.get("bb_dist_exit_mean", opp_s.get("bb_dist_mean", 50.0)) * opp_c
                opp_weighted["macd"] += opp_s.get("macd_mean", 0.0) * opp_c
                opp_weighted["macd_exit"] += opp_s.get("macd_exit_mean", opp_s.get("macd_mean", 0.0)) * opp_c
                opp_weighted["atr"] += opp_s.get("atr_mean", 0.0) * opp_c
                opp_weighted["atr_exit"] += opp_s.get("atr_exit_mean", opp_s.get("atr_mean", 0.0)) * opp_c
                
            thr_s = reg_data.get("thr_stats", {})
            if thr_c > 0 and thr_s:
                thr_samples += thr_c
                thr_weighted["stretching"] += thr_s.get("strt_mean", 0.0) * thr_c
                thr_weighted["stretching_exit"] += thr_s.get("strt_exit_mean", thr_s.get("strt_mean", 0.0)) * thr_c
                thr_weighted["mola"] += thr_s.get("mola_mean", 0.0) * thr_c
                thr_weighted["mola_exit"] += thr_s.get("mola_exit_mean", thr_s.get("mola_mean", 0.0)) * thr_c
                thr_weighted["disp"] += thr_s.get("disp_mean", 0.0) * thr_c
                thr_weighted["disp_exit"] += thr_s.get("disp_exit_mean", thr_s.get("disp_mean", 0.0)) * thr_c
                thr_weighted["velocity"] += thr_s.get("vel_mean", 0.0) * thr_c
                thr_weighted["velocity_exit"] += thr_s.get("vel_exit_mean", thr_s.get("vel_mean", 0.0)) * thr_c
                thr_weighted["acceleration"] += thr_s.get("acc_mean", 0.0) * thr_c
                thr_weighted["acceleration_exit"] += thr_s.get("acc_exit_mean", thr_s.get("acc_mean", 0.0)) * thr_c
                thr_weighted["volatility"] += thr_s.get("vol_mean", 0.0) * thr_c
                thr_weighted["volatility_exit"] += thr_s.get("vol_exit_mean", thr_s.get("vol_mean", 0.0)) * thr_c
                thr_weighted["infil"] += thr_s.get("infil_rate", 0.0) * thr_c
                thr_weighted["infil_exit"] += thr_s.get("infil_exit_rate", thr_s.get("infil_rate", 0.0)) * thr_c
                thr_weighted["reteste"] += thr_s.get("reteste_rate", 0.0) * thr_c
                thr_weighted["reteste_exit"] += thr_s.get("reteste_exit_rate", thr_s.get("reteste_rate", 0.0)) * thr_c
                thr_weighted["rsi"] += thr_s.get("rsi_mean", 50.0) * thr_c
                thr_weighted["rsi_exit"] += thr_s.get("rsi_exit_mean", thr_s.get("rsi_mean", 50.0)) * thr_c
                thr_weighted["bb"] += thr_s.get("bb_dist_mean", 50.0) * thr_c
                thr_weighted["bb_exit"] += thr_s.get("bb_dist_exit_mean", thr_s.get("bb_dist_mean", 50.0)) * thr_c
                thr_weighted["macd"] += thr_s.get("macd_mean", 0.0) * thr_c
                thr_weighted["macd_exit"] += thr_s.get("macd_exit_mean", thr_s.get("macd_mean", 0.0)) * thr_c
                thr_weighted["atr"] += thr_s.get("atr_mean", 0.0) * thr_c
                thr_weighted["atr_exit"] += thr_s.get("atr_exit_mean", thr_s.get("atr_mean", 0.0)) * thr_c
                
        buy_rules = {}
        sell_rules = {}
        
        keys = ["stretching", "stretching_exit", "mola", "mola_exit", "disp", "disp_exit", 
                "velocity", "velocity_exit", "acceleration", "acceleration_exit", 
                "volatility", "volatility_exit", "infil", "infil_exit", 
                "reteste", "reteste_exit", "rsi", "rsi_exit", 
                "bb", "bb_exit", "macd", "macd_exit", "atr", "atr_exit"]
                
        for k in keys:
            val_buy = opp_weighted[k] / opp_samples if opp_samples > 0 else (50.0 if k in ["rsi", "rsi_exit", "bb", "bb_exit"] else 0.0)
            if k.endswith("exit"):
                buy_rules[k] = {"mean": float(val_buy)}
            elif k in ["infil", "reteste"]:
                buy_rules[k] = {"rate": float(val_buy), "active": bool(val_buy > 50.0) if opp_samples > 0 else False}
            else:
                buy_rules[k] = {"mean": float(val_buy)}
                
            val_sell = thr_weighted[k] / thr_samples if thr_samples > 0 else (50.0 if k in ["rsi", "rsi_exit", "bb", "bb_exit"] else 0.0)
            if k.endswith("exit"):
                sell_rules[k] = {"mean": float(val_sell)}
            elif k in ["infil", "reteste"]:
                sell_rules[k] = {"rate": float(val_sell), "active": bool(val_sell > 50.0) if thr_samples > 0 else False}
            else:
                sell_rules[k] = {"mean": float(val_sell)}
                
        consensus_dna["regimes"][reg] = {
            "active": True,
            "opp_samples": opp_samples,
            "thr_samples": thr_samples,
            "buy_rules": buy_rules,
            "sell_rules": sell_rules
        }
        
    consensus_dna["last_updated"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
    
    try:
        with open(dna_path, "w", encoding="utf-8") as f:
            json.dump(consensus_dna, f, indent=2, ensure_ascii=False)
    except Exception as e:
        import streamlit as st
        st.error("Erro ao gravar o DNA Consensual do Bot: " + str(e))
