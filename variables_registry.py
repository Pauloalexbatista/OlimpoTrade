import os
import json
import streamlit as st
import pandas as pd


class QuantVariable:
    def __init__(
    self,
    key,
    name,
    category,
    description,
    formula,
    default_value,
    min_val=None,
    max_val=None,
    step=None,
     is_toggleable=False):
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
    QuantVariable(
    "tg_p2",
    "Período SMA Rápida (P2)",
    "Médias Móveis (Lab/Jogo)",
    "Média móvel rápida imediata (cabeça do feixe). Representa a velocidade do momentum curto.",
    "SMA(Close, P2)",
    9,
    1,
    999,
     1),
    QuantVariable(
    "tg_p3",
    "Período SMA Sinal (P3)",
    "Médias Móveis (Lab/Jogo)",
    "Média móvel usada para cruzamentos rápidos com P2 para gatilho.",
    "SMA(Close, P3)",
    21,
    1,
    999,
     1),
    QuantVariable(
    "tg_p4",
    "Período SMA Intermédia (P4)",
    "Médias Móveis (Lab/Jogo)",
    "Média intermédia que define o alinhamento de curto/médio prazo.",
    "SMA(Close, P4)",
    50,
    1,
    999,
     1),
    QuantVariable(
    "tg_p5",
    "Período SMA Lenta 1 (P5)",
    "Médias Móveis (Lab/Jogo)",
    "Média institucional lenta. Atua como primeiro trampolim de suporte.",
    "SMA(Close, P5)",
    100,
    1,
    999,
     1),
    QuantVariable(
    "tg_p6",
    "Período SMA Lenta 2 (P6)",
    "Médias Móveis (Lab/Jogo)",
    "Média institucional profunda. Atua como o suporte gravitacional final.",
    "SMA(Close, P6)",
    200,
    1,
    999,
     1),

    # Médias Móveis Clássicas (PAULO_GOLD & Cruzamentos)
    QuantVariable(
    "short_window_val",
    "Janela Curta Clássica (Rápida)",
    "Estratégias Clássicas",
    "Número de candles para a média curta móvel das estratégias clássicas.",
    "SMA(Close, Short)",
    9,
    1,
    999,
     1),
    QuantVariable(
    "long_window_val",
    "Janela Longa Clássica (Lenta)",
    "Estratégias Clássicas",
    "Número de candles para a média longa móvel das estratégias clássicas.",
    "SMA(Close, Long)",
    21,
    1,
    999,
     1),
    QuantVariable(
    "paulo_gold_min_dist_pct_val",
    "PG: Distância Mínima de Médias (%)",
    "Estratégias Clássicas",
    "Distância mínima exigida em % entre as médias rápidas/lentas na estratégia PAULO_GOLD.",
    "SMA_Rápida > SMA_Lenta * (1 + Dist%)",
    0.0,
    0.0,
    2.0,
     0.05),

    # Indicadores do Cockpit e Gatilhos
    QuantVariable(
    "tg_bot_compress_thresh",
    "Compressão Mola (Limite)",
    "Indicadores Cockpit",
    "Limite máximo de Stretching (esticamento) para detetar compressão extrema da mola (consolidação).",
    "Stretching < Limite",
    0.6,
    0.1,
    5.0,
     0.1),
    QuantVariable(
    "tg_min_confidence_pct",
    "Confiança Mínima de Entrada (%)",
    "Filtros e Decisão",
    "Percentagem mínima de regras que têm de estar válidas (verdes) para o Bot autorizar o trade.",
    "Regras Válidas / Total >= Confiança",
    80.0,
    50.0,
    100.0,
     5.0),

    # Gestão de Risco
    QuantVariable(
    "tg_sl_pct",
    "Stop Loss (SL) %",
    "Gestão de Risco",
    "Limite máximo de perda percentual admitida por operação.",
    "Preço de Entrada * (1 - SL%)",
    2.0,
    0.0,
    10.0,
    0.1,
     is_toggleable=False),
    QuantVariable(
    "tg_tp_pct",
    "Take Profit (TP) %",
    "Gestão de Risco",
    "Alvo de lucro percentual definido para saída automática.",
    "Preço de Entrada * (1 + TP%)",
    7.0,
    0.0,
    25.0,
    0.1,
     is_toggleable=False),
    QuantVariable(
    "tg_ts_pct",
    "Trailing Stop (TS) %",
    "Gestão de Risco",
    "Trailing Stop para acompanhamento de ganhos acumulados.",
    "Stop dinâmico a partir do máximo",
    1.5,
    0.0,
    5.0,
    0.1,
     is_toggleable=False),

    # Fricções e Custos de Mercado
    QuantVariable(
    "fee_pct_val",
    "Taxa Operacional API (%)",
    "Custos de Mercado",
    "Comissão cobrada pela exchange em cada compra e venda.",
    "Valor da Ordem * Taxa%",
    0.1,
    0.0,
    1.0,
     0.01),
    QuantVariable(
    "tax_pct_val",
    "Imposto Mais-Valias (%)",
    "Custos de Mercado",
    "Percentagem de imposto deduzida automaticamente sobre lucros líquidos pós-jogo.",
    "Lucro Líquido * Imposto%",
    28.0,
    0.0,
    50.0,
     1.0),
    QuantVariable(
    "slippage_pct_val",
    "Deslizamento (Slippage) (%)",
    "Custos de Mercado",
    "Fricção que simula pior preço de execução por atraso ou liquidez.",
    "Compra + Slippage%, Venda - Slippage%",
    0.05,
    0.0,
    0.5,
     0.01)
]


def load_user_preferences():
    import json
    import os
    pref_file = "user_preferences.json"
    if os.path.exists(pref_file):
        try:
            with open(pref_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_user_preferences(prefs):
    import json
    with open("user_preferences.json", "w", encoding="utf-8") as f:
        json.dump(prefs, f, indent=4)


def initialize_variables_registry():
    """Garante que todas as variáveis quantitativas estão presentes no st.session_state."""
    import streamlit as st
    prefs = load_user_preferences()
    for var in VARIABLES:
        # Inicializar ativação (se for toggleable)
        if var.is_toggleable:
            toggle_key = f"{var.key}_active"
            if toggle_key not in st.session_state:
                if var.key == "tg_sl_pct":
                    st.session_state[toggle_key] = prefs.get(
                        toggle_key, st.session_state.get("tg_sl_active", True))
                elif var.key == "tg_tp_pct":
                    st.session_state[toggle_key] = prefs.get(
                        toggle_key, st.session_state.get("tg_tp_active", False))
                elif var.key == "tg_ts_pct":
                    st.session_state[toggle_key] = prefs.get(
                        toggle_key, st.session_state.get("tg_ts_active", False))
                else:
                    st.session_state[toggle_key] = prefs.get(toggle_key, True)

        # Inicializar valor principal
        if var.key not in st.session_state:
            if var.key == "tg_p2": st.session_state[var.key] = prefs.get(var.key, st.session_state.get("p2_window_val", var.default_value))
            elif var.key == "tg_p3": st.session_state[var.key] = prefs.get(var.key, st.session_state.get("p3_window_val", var.default_value))
            elif var.key == "tg_p4": st.session_state[var.key] = prefs.get(var.key, st.session_state.get("p4_window_val", var.default_value))
            elif var.key == "tg_p5": st.session_state[var.key] = prefs.get(var.key, st.session_state.get("p5_window_val", var.default_value))
            elif var.key == "tg_p6": st.session_state[var.key] = prefs.get(var.key, st.session_state.get("p6_window_val", var.default_value))
            else:
                st.session_state[var.key] = prefs.get(
                    var.key, var.default_value)

    # Variáveis booleanas manuais adicionais
    if "paulo_gold_trend_filter_val" not in st.session_state:
        st.session_state.paulo_gold_trend_filter_val = prefs.get(
            'paulo_gold_trend_filter_val', False)
    if "tg_filter_momentum_active" not in st.session_state:
        st.session_state.tg_filter_momentum_active = prefs.get(
            'tg_filter_momentum_active', False)
        
        st.session_state.tg_filter_macd_active = prefs.get('tg_filter_macd_active', False)
        
        for k, v in [('tg_macd_long_entry', 0.1), ('tg_macd_long_exit', 0.1), ('tg_macd_short_entry', -0.1), ('tg_macd_short_exit', -0.1)]:
            if k not in st.session_state:
                st.session_state[k] = prefs.get(k, v)
    if "tg_filter_squeeze_active" not in st.session_state:
        st.session_state.tg_filter_squeeze_active = prefs.get(
            'tg_filter_squeeze_active', False)
    if "tg_subchart_type" not in st.session_state:
        st.session_state.tg_subchart_type = prefs.get(
            'tg_subchart_type', 'Heatmap (Vel/Acel)')
    if "allow_reentry_val" not in st.session_state:
        st.session_state.allow_reentry_val = prefs.get(
            'allow_reentry_val', True)
    if "tg_only_one_move_per_candle" not in st.session_state:
        st.session_state.tg_only_one_move_per_candle = prefs.get(
            'tg_only_one_move_per_candle', True)


def render_variable_widget(var):
    # Se for toggleable (ex: Stop Loss, Take Profit), desenhar toggle and
    # slider
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
            st.markdown(
    f"<p style='color:#64748b; font-style:italic; font-size:12px;'>{var.name} desativado.</p>",
     unsafe_allow_html=True)
    else:
        # Variável numérica padrão
        if var.step is not None:
            st.session_state[var.key] = st.slider(
                var.name,
                min_value=var.min_val,
                max_value=var.max_val,
                value=float(
    st.session_state.get(
        var.key,
        var.default_value)) if isinstance(
            var.default_value,
            float) else int(
                st.session_state.get(
                    var.key,
                     var.default_value)),
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
    import os
    import json
    initialize_variables_registry()

    if not compact:
        st.markdown(
    "<h2 style='text-align: center; color: #7c3aed;'>🔧 Central & Dicionário de Variáveis</h2>",
     unsafe_allow_html=True)
        st.markdown(
    "<p style='text-align: center; color: #64748b;'>A fonte única de verdade e painel de comando quantitativo do OlimpoTrade.</p>",
     unsafe_allow_html=True)
        st.markdown("---")

    # Renderizar os ajustadores divididos em 5 Colunas horizontais
    col1, col2, col3, col4, col5 = st.columns([1.2, 1.2, 1.2, 1.2, 1.2])

    # 🌏 COLUNA 1: Mercado & Ativo
    with col1:
        st.markdown("##### 🌏 Mercado & Ativo")

        options_list = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
     "🧪 Cenário Didático (Fictício)"]
        symbol_val = st.session_state.get(
    'symbol_val', '🧪 Cenário Didático (Fictício)')
        if symbol_val not in options_list:
            symbol_val = '🧪 Cenário Didático (Fictício)'

        selected_symbol = st.selectbox(
            "Par de Trading",
            options_list,
            index=options_list.index(symbol_val),
            help="Selecione o par de trading real para carregar dados da Binance API, ou use o Cenário Didático para simulações fictícias controladas.",
            key="cc_global_symbol"
        )
        if selected_symbol != st.session_state.get('symbol_val'):
            st.session_state.symbol_val = selected_symbol
            st.rerun()

        # Exibição dinâmica de sliders didáticos
        if st.session_state.symbol_val == "🧪 Cenário Didático (Fictício)":
            st.markdown(
    "<div style='margin-top:10px;'></div>",
     unsafe_allow_html=True)

            # 1. Cenário Didático
            scenarios = [
    "Didatico Classico",
    "Montanha Russa",
    "Flash Crash",
    "Lateralizacao Eterna",
     "Tendencia Saudavel (Bull)"]
            current_scenario = st.session_state.get(
                'math_scenario', 'Didatico Classico')
            if current_scenario not in scenarios:
                current_scenario = 'Didatico Classico'
            selected_scenario = st.selectbox(
                "Cenário Didático",
                scenarios,
                index=scenarios.index(current_scenario),
                key="cc_math_scenario"
            )
            if selected_scenario != st.session_state.get('math_scenario'):
                st.session_state.math_scenario = selected_scenario

            # 2. Ruído do Mercado
            current_noise = float(st.session_state.get('math_noise', 1.0))
            selected_noise = st.slider(
                "Ruído do Mercado",
                0.1, 5.0,
                current_noise,
                step=0.1,
                key="cc_math_noise"
            )
            if selected_noise != st.session_state.get('math_noise'):
                st.session_state.math_noise = selected_noise

            # 3. Tamanho da Série
            current_size = int(st.session_state.get('math_size', 500))
            selected_size = st.slider(
                "Tamanho da Série",
                100, 2000,
                current_size,
                step=100,
                key="cc_math_size"
            )
            if selected_size != st.session_state.get('math_size'):
                st.session_state.math_size = selected_size

        # Seletor do Sub-grafico
        st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
        subchart_options = [
            'Heatmap (Vel/Acel)',
            'Histograma MACD',
            'Volume',
            'ADX (Tendência)'
        ]
        
        current_subcharts = st.session_state.get('tg_subchart_type', ['Heatmap (Vel/Acel)'])
        if isinstance(current_subcharts, str):
            if current_subcharts == "Ambos": current_subcharts = ["Heatmap (Vel/Acel)", "Histograma MACD"]
            elif current_subcharts == "Nenhum": current_subcharts = []
            else: current_subcharts = [current_subcharts]
            
        current_subcharts = [c for c in current_subcharts if c in subchart_options]

        selected_subcharts = st.multiselect(
            "📊 Painel do Sub-gráfico",
            options=subchart_options,
            default=current_subcharts,
            key="cc_subchart_type",
            help="Selecione os indicadores secundários exibidos abaixo do gráfico principal."
        )
        if selected_subcharts != st.session_state.get('tg_subchart_type'):
            st.session_state.tg_subchart_type = selected_subcharts
            st.rerun()


    # 🎯 COLUNA 2: Algoritmo & Gatilhos
    with col2:
        st.markdown("##### 🧠 Algoritmo & Gatilhos")

        # Inicializar tg_strategy_type se necessario
        if 'tg_strategy_type' not in st.session_state:
            st.session_state.tg_strategy_type = 'Default (Manual)'

        _arena_strategies = [
            'Default (Manual)',
            'Cérebro de Consenso (IA)',
            'Momentum Puro',
            'Momentum & MACD',
            'Lagarta (Todas as Linhas)',
            'Linha Solitária',
            'Média Camadas (Duas Linhas)',
            '🤖 Claude — Pirâmide Fibonacci'
        ]
        _arena_current = st.session_state.get(
            'tg_strategy_type', 'Default (Manual)')
        if _arena_current not in _arena_strategies:
            _arena_current = 'Default (Manual)'

        _arena_selected = st.selectbox(
            'Modelo de Decisão:',
            _arena_strategies,
            index=_arena_strategies.index(_arena_current),
            key='cc_arena_strategy'
        )

        # Sync old variables to avoid breaking other parts immediately
        st.session_state.strategy_type_val = _arena_selected

        if _arena_selected != st.session_state.get('tg_strategy_type'):
          st.session_state.tg_strategy_type = _arena_selected

          # Auto-configurar risco e modo do bot por estratégia
          if 'Lagarta' in _arena_selected or 'Cruzamento' in _arena_selected or 'Linha Solitária' in _arena_selected:
              st.session_state.tg_sl_pct_active = True
              st.session_state.tg_sl_active = True
              st.session_state.tg_sl_pct = 1.0
              st.session_state.tg_ts_pct_active = True
              st.session_state.tg_ts_active = True
              st.session_state.tg_ts_pct = 1.0
              st.session_state.tg_tp_pct_active = False
              st.session_state.tg_tp_active = False
              st.session_state.tg_bot_mode = "Bot Autonomo"
              st.session_state.tg_lagarta_min_disp = 0.3  # filtro recomendado para Lagarta
              st.toast('Lagarta: SL=1% TS=1% Dispersão≥0.30 — Bot Autónomo ligado!')
          elif 'Momentum & MACD' in _arena_selected:
              st.session_state.tg_sl_pct_active = True
              st.session_state.tg_sl_active = True
              st.session_state.tg_sl_pct = 0.5
              st.session_state.tg_ts_pct_active = True
              st.session_state.tg_ts_active = True
              st.session_state.tg_tp_active = False
              st.session_state.tg_bot_mode = "Bot Autonomo"
              st.session_state.tg_lagarta_min_disp = 0.0
              st.toast('Momentum & MACD: SL=0.5% TS=0.5% - Usa Heatmap e MACD!')
          elif 'Momentum Puro' in _arena_selected:
              st.session_state.tg_sl_pct_active = True
              st.session_state.tg_sl_active = True
              st.session_state.tg_sl_pct = 0.5
              st.session_state.tg_ts_pct_active = True
              st.session_state.tg_ts_active = True
              st.session_state.tg_ts_pct = 0.5
              st.session_state.tg_tp_pct_active = False
              st.session_state.tg_tp_active = False
              st.session_state.tg_bot_mode = "Bot Autonomo"
              st.session_state.tg_lagarta_min_disp = 0.0
              st.toast('Momentum Puro: SL=0.5% TS=0.5% - Só entra com Vel 1:1 Acel 1!')
          elif 'Camadas' in _arena_selected or 'Esmigalhador' in _arena_selected:
              st.session_state.tg_sl_pct_active = True
              st.session_state.tg_sl_active = True
              st.session_state.tg_sl_pct = 1.0
              st.session_state.tg_ts_pct_active = True
              st.session_state.tg_ts_active = True
              st.session_state.tg_ts_pct = 0.5
              st.session_state.tg_tp_pct_active = False
              st.session_state.tg_tp_active = False
              st.session_state.tg_bot_mode = "Bot Autonomo"
              st.session_state.tg_lagarta_min_disp = 0.0  # desativado por defeito (ajustar manualmente)
              st.toast('Média Camadas: SL=1% TS=0.5% — Bot Autónomo ligado!')
          elif 'Cérebro' in _arena_selected:
              st.session_state.tg_bot_mode = "Bot Autonomo"
              st.session_state.tg_lagarta_min_disp = 0.0  # desativado por defeito
              if os.path.exists('bot_consensus_dna.json'):
                  try:
                      with open('bot_consensus_dna.json', 'r', encoding='utf-8') as _f_dna:
                          _dna = json.load(_f_dna)
                      _smas = _dna.get('smas', [5, 13, 21, 55, 144])
                      st.session_state.tg_p2 = _smas[0]
                      st.session_state.tg_p3 = _smas[1]
                      st.session_state.tg_p4 = _smas[2]
                      st.session_state.tg_p5 = _smas[3]
                      st.session_state.tg_p6 = _smas[4]
                      st.toast('Cérebro: Médias sincronizadas. Bot Autónomo ligado!')
                  except Exception:
                      st.toast('Cérebro: Bot Autónomo ligado!')
          elif 'Claude' in _arena_selected:
              # Claude v4: Pirâmide FLAT EXIT — SMAs rápidas, SL/TS tight
              st.session_state.tg_p2 = 2
              st.session_state.tg_p3 = 3
              st.session_state.tg_p4 = 5
              st.session_state.tg_p5 = 8
              st.session_state.tg_p6 = 13
              st.session_state.tg_sl_pct_active = True
              st.session_state.tg_sl_active = True
              st.session_state.tg_sl_pct = 0.5
              st.session_state.tg_ts_pct_active = True
              st.session_state.tg_ts_active = True
              st.session_state.tg_ts_pct = 0.5
              st.session_state.tg_tp_pct_active = False
              st.session_state.tg_tp_active = False
              st.session_state.tg_lagarta_min_disp = 0.0
              st.session_state.tg_bot_mode = "Bot Autonomo"
              st.toast('🤖 Claude v4: [2,3,5,8,13] SL=0.5% TS=0.5% FLAT EXIT — Vamos bater o recorde!')
          elif 'Default' in _arena_selected or 'Manual' in _arena_selected:
              st.session_state.tg_bot_mode = "Manual"
              st.toast('Modo Manual ativado.')
          st.rerun()

        with st.expander("📖 Ler as Regras das Estratégias", expanded=False):
            # Painel Dinâmico de Explicação Estética da Estratégia Selecionada
            _strategy_styles = {
                'Default (Manual)': {
                    'gradient': 'linear-gradient(135deg, rgba(100,116,139,0.15) 0%, rgba(51,65,85,0.3) 100%)',
                    'border': 'rgba(100,116,139,0.2)',
                    'icon': '🎮',
                    'color': '#94a3b8',
                    'title': 'Modo Manual (Default)',
                    'desc': '<b>🎮 Funcionamento:</b><br>'
                            '• Nenhuma regra automatizada ativa. O Bot autónomo permanecerá em inação completa.<br>'
                            '• O utilizador é 100% responsável por executar e gerir as ordens manualmente através dos botões da consola (COMPRA, VENDA e FECHAR).'
                },
                'Cérebro de Consenso (IA)': {
                    'gradient': 'linear-gradient(135deg, rgba(139,92,246,0.15) 0%, rgba(109,40,217,0.3) 100%)',
                    'border': 'rgba(139,92,246,0.2)',
                    'icon': '🧠',
                    'color': '#a78bfa',
                    'title': 'Cérebro de Consenso (Consensus Engine)',
                    'desc': '<b>🧠 Funcionamento:</b><br>'
                            '• Combina o sinal de 6 sensores quantitativos: <b>Tendência</b>, <b>Aceleração</b>, <b>Volatilidade</b>, <b>Canal Desvio Padrão</b>, <b>Saturação (RSI)</b> e <b>Stop Loss Dinâmico</b>.<br>'
                            '• O bot só executa uma ordem quando o consenso ponderado dos sensores ultrapassa **80%** de confiança.<br><br>'
                            '<b>⚠️ Configuração Importante:</b> As médias móveis (P2 a P6) são configuradas de forma automática pelo sistema com base no DNA gerado no Laboratório Matemático (`bot_consensus_dna.json`).'
                },
                'Momentum & MACD': {
                    'gradient': 'linear-gradient(135deg, rgba(139,92,246,0.15) 0%, rgba(109,40,217,0.3) 100%)',
                    'border': 'rgba(139,92,246,0.2)',
                    'icon': '📊',
                    'color': '#8b5cf6',
                    'title': 'Estratégia Momentum & MACD',
                    'desc': '<b>🔥 Funcionamento:</b><br>'
                            '  Combina a física de mercado (HeatMap) com Histograma MACD.<br>'
                            '  <b>Gatilho LONG:</b> Entra quando Heatmap 1:1 e Histograma Positivo.<br>'
                            '  <b>Saída LONG:</b> Sai quando Histograma fica Negativo.<br>'
                            '  <b>Gatilho SHORT:</b> Entra quando Heatmap -1:-1 e Histograma Negativo.<br>'
                            '  <b>Saída SHORT:</b> Sai quando Histograma fica Positivo.<br>'
                },
                'Momentum Puro': {
                    'gradient': 'linear-gradient(135deg, rgba(239,68,68,0.15) 0%, rgba(185,28,28,0.3) 100%)',
                    'border': 'rgba(239,68,68,0.2)',
                    'icon': '⚡',
                    'color': '#ef4444',
                    'title': 'Estratégia Momentum Puro',
                    'desc': '<b>🔥 Funcionamento:</b><br>'
                            '  Ignora as linhas e usa apenas a física de mercado (Aceleração e Velocidade).<br>'
                            '  <b>Gatilho LONG:</b> Entra APENAS quando Velocidade > 0 e Aceleração > 0.<br>'
                            '  <b>Saída LONG:</b> Sai quando a Velocidade inverte para negativo.<br>'
                            '  <b>Gatilho SHORT:</b> Entra APENAS quando Velocidade < 0 e Aceleração < 0.<br>'
                            '  <b>Saída SHORT:</b> Sai quando a Velocidade inverte para positivo.'
                },
                'Lagarta (Todas as Linhas)': {
                    'gradient': 'linear-gradient(135deg, rgba(16,185,129,0.15) 0%, rgba(4,120,87,0.3) 100%)',
                    'border': 'rgba(16,185,129,0.2)',
                    'icon': '🐛',
                    'color': '#34d399',
                    'title': 'Estratégia da Lagarta (Todas as Linhas)',
                    'desc': '<b>🐛 Funcionamento:</b><br>'
                            '• Utiliza o feixe completo das 5 médias configuradas (P2, P3, P4, P5 e P6) para avaliar a tendência do fluxo.<br>'
                            '• <b>Gatilho LONG (Compra):</b> Entra quando o preço cruza as linhas do feixe de médias para cima.<br>'
                            '• <b>Gatilho SHORT (Venda):</b> Entra quando o preço cruza as linhas do feixe de médias para baixo.<br>'
                            '• <b>Teimosia:</b> O robô ignora cruzamentos na direção contrária após estar posicionado. Só sai ao atingir o Stop Loss (1.0%) ou Trailing Stop (1.0%). Reentra instantaneamente caso saia por SL e o alinhamento da direção oposta seja válido.'
                },
                'Linha Solitária': {
                    'gradient': 'linear-gradient(135deg, rgba(245,158,11,0.15) 0%, rgba(180,83,9,0.3) 100%)',
                    'border': 'rgba(245,158,11,0.2)',
                    'icon': '🎯',
                    'color': '#fbbf24',
                    'title': 'Linha Solitária',
                    'desc': '<b>🎯 Funcionamento:</b><br>'
                            '• O preço é avaliado exclusivamente contra uma única linha de referência (selecionada no menu abaixo deste painel, ex: P2, P3, avg_sma).<br>'
                            '• <b>Gatilho LONG (Compra):</b> Entra quando o preço cruza a linha de referência para cima.<br>'
                            '• <b>Gatilho SHORT (Venda):</b> Entra quando o preço cruza a linha de referência para baixo.<br>'
                            '• <b>Saída:</b> Encerra o trade por cruzamento contrário na mesma linha, Stop Loss ou Trailing Stop.'
                },
                'Média Camadas (Duas Linhas)': {
                    'gradient': 'linear-gradient(135deg, rgba(59,130,246,0.15) 0%, rgba(29,78,216,0.3) 100%)',
                    'border': 'rgba(59,130,246,0.2)',
                    'icon': '📊',
                    'color': '#60a5fa',
                    'title': 'Média Camadas (Duas Linhas)',
                    'desc': '<b>⚠️ Configuração Importante (Linhas P2/P1 e P4):</b> O utilizador deve configurar os valores de <b>P2 (a primeira linha rápida/preço)</b>, <b>P3 (linha intermediária)</b> e <b>P4 (Pivot Meio / Equador)</b> na Central de Variáveis acima. As linhas P5 e P6 são ignoradas nesta estratégia.<br><br>'
                            '<b>📊 Regras de Funcionamento:</b><br>'
                            '• <b>Inversão (Entrada Principal):</b> Entra LONG quando a linha rápida P2 cruza o Equador (P4) para cima; entra SHORT quando P2 cruza P4 para baixo.<br>'
                            '• <b>Pullback (Reentrada):</b> Se o preço estiver acima de P4, reentra LONG sempre que P2 corrigir e voltar a cruzar P3 para cima. Se estiver abaixo de P4, reentra SHORT sempre que P2 corrigir e cruzar P3 para baixo.<br><br>'
                            '<b>Gestão de Risco:</b> SL automático de 1.0% e TS de 0.5%.'
                },
                '🤖 Claude — Pirâmide Fibonacci': {
                    'gradient': 'linear-gradient(135deg, rgba(236,72,153,0.15) 0%, rgba(190,24,93,0.3) 100%)',
                    'border': 'rgba(236,72,153,0.2)',
                    'icon': '🤖',
                    'color': '#f472b6',
                    'title': 'Claude — Pirâmide Fibonacci (Modo Pirâmide de 2 Linhas)',
                    'desc': '<b>🤖 Regras de Funcionamento:</b><br>'
                            '• Utiliza a proporção harmónica de Fibonacci: P2=3 (rápida), P3=5 (confirmadora) e P4=8 (filtro lento).<br>'
                            '• <b>Gatilho LONG (Compra):</b> P2 cruza P3 para cima, contanto que P2 já esteja acima de P4 (pirâmide alinhada) E a velocidade/momentum de P2 seja positiva ($> 0$).<br>'
                            '• <b>Gatilho SHORT (Venda):</b> P2 cruza P3 para baixo, contanto que P2 já esteja abaixo de P4 (pirâmide alinhada) E a velocidade/momentum de P2 seja negativa ($< 0$).<br>'
                            '• <b>Saída Rápida:</b> O trade fecha imediatamente se a pirâmide se desalinhar (P2 cruza P3 na direção contrária), ou por SL (0.5%) ou Trailing Stop (0.5%).'
                }
            }

            _info = _strategy_styles.get(_arena_selected, _strategy_styles['Default (Manual)'])
            
            st.markdown(f"""
            <div style="
                background: {_info['gradient']};
                border: 1px solid {_info['border']};
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
                color: #e2e8f0;
                box-shadow: 0 4px 6px -1px rgba(0,0,0,0.15), 0 2px 4px -1px rgba(0,0,0,0.06);
            ">
                <h4 style="color: {_info['color']}; margin-top: 0; font-weight: 700; display: flex; align-items: center; gap: 8px;">
                    <span>{_info['icon']}</span> {_info['title']}
                </h4>
                <p style="font-size: 13.5px; line-height: 1.6; color: #cbd5e1; margin-bottom: 0;">
                    {_info['desc']}
                </p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown('''
### 📖 Referência Rápida de Regras

**1. Estratégia da Lagarta (Linha Única)**
* **Entrada:** Compra (LONG) quando o Preço cruza a linha para cima. Vende (SHORT) quando cruza para baixo.
* **Teimosia:** Ignora cruzamentos opostos! Só sai ao bater no Stop Loss (0.5%) ou Trailing Stop.
* **Agilidade Extrema:** Se sair por SL e a tendência oposta for válida, entra instantaneamente na nova direção.

**2. Estratégia Média Camadas**
* **Inversão:** Entra LONG quando P2 rompe o Equador (P4) para cima.
* **Pullback:** Tenta reentrar quando o mercado corrige, mas P2 volta a cruzar a Média P3 para cima.

**3. Cérebro de Consenso (Lab)**
* **DNA de 6 Sensores:** Usa Tendência, Aceleração, Volatilidade, Distância ao Chão, Saturação e Stop Loss.
* **Consenso:** Só ataca se a confiança coletiva dos sensores passar os 80%.

**4. 🤖 Claude — Pirâmide Fibonacci**
* **Médias:** Fibonacci [P2=3, P3=5, P4=8, P5=13, P6=21] — cobrem velocidades naturais do mercado.
* **Entrada LONG:** P2 cruza P3 para cima E P2 já está acima de P4 (pirâmide alinhada) E velocidade positiva.
* **Entrada SHORT:** P2 cruza P3 para baixo E P2 já está abaixo de P4 E velocidade negativa.
* **Seletividade:** Só entra quando os 3 primeiros SMAs estão em ordem — confirma tendência antes de agir.
* **Saída:** Quando a pirâmide parte na direção oposta (P2 cruza P3 de volta), TS ou SL.

**5. Default (Fórmula do Jogo)**
* Modo puramente Manual.
''')

        # Sub-opcao: Linha de Referencia (so para Lagarta)
        if 'Linha Solitária' in st.session_state.get('tg_strategy_type', ''):
            _ref_options = [
                'SMA Rápida (P2)', 'SMA Sinal (P3)', 'SMA Intermédia (P4)',
                'SMA Lenta 1 (P5)', 'SMA Lenta 2 (P6)',
                'Média do Vetor (avg_sma)', 'Desvio Padrão (sma_std)'
            ]
            # Apenas linhas específicas são válidas para a Linha Solitária
            _smart_default = 'SMA Sinal (P3)'
            _current_ref = st.session_state.get('tg_single_line_ref', _smart_default)
            if _current_ref not in _ref_options:
                _current_ref = _smart_default
            st.selectbox(
                'Linha de Referência (Linha Solitária):',
                _ref_options,
                index=_ref_options.index(_current_ref),
                key='tg_single_line_ref',
                help='Escolha a linha única contra a qual o preço será avaliado.'
            )
    # 🧬 COLUNA 3: Vetor de Médias Móveis
    with col3:
        st.markdown("##### 🧬 Vetor de Médias Móveis")
        mavg_vars = [v for v in VARIABLES if v.category == "Médias Móveis (Lab/Jogo)"]
        for var in mavg_vars:
            render_variable_widget(var)

    # 🛡️ COLUNA 4: Risco & Gatilhos
    with col4:
        st.markdown("##### 🛡️ Risco & Gatilhos")
        
        # Confiança mínima
        conf_var = [v for v in VARIABLES if v.key == "tg_min_confidence_pct"][0]
        render_variable_widget(conf_var)
        
        # Stop Loss, Take Profit, Trailing Stop
        # Filtro universal de dispersão (todas as estratégias)
        if 'tg_lagarta_min_disp' not in st.session_state:
            st.session_state.tg_lagarta_min_disp = 0.0
        st.slider(
            '📐 Dispersão Mínima das SMAs',
            min_value=0.0, max_value=2.0,
            step=0.05,
            key='tg_lagarta_min_disp',
            help='Suspende entradas de QUALQUER estratégia quando as SMAs estão demasiado comprimidas. 0 = sem filtro (desativado). Recomendado: 0.30 para Lagarta.'
        )
        st.markdown("<p style='font-size:11px;color:#64748b;margin-top:-8px;'>0 = desativado | 0.30 = recomendado | 0.50 = conservador</p>", unsafe_allow_html=True)

        risk_vars = [v for v in VARIABLES if v.key in ["tg_sl_pct", "tg_tp_pct"]]
        for var in risk_vars:
            render_variable_widget(var)

        st.markdown("##### 🌊 Trailing Stop Dinâmico (Efeito Garrafão)")
        st.session_state.tg_ts_active = st.checkbox("Ativar Efeito Garrafão (TS Baseado em ATR)", value=st.session_state.get("tg_ts_active", False))
        
        col_ts1, col_ts2, col_ts3 = st.columns(3)
        with col_ts1:
            st.session_state.tg_ts_atr_start = st.number_input("Torneira Aberta (xATR)", min_value=0.0, step=0.1, value=st.session_state.get("tg_ts_atr_start", 1.5))
        with col_ts2:
            st.session_state.tg_ts_atr_end = st.number_input("Torneira Fechada (xATR)", min_value=0.0, step=0.1, value=st.session_state.get("tg_ts_atr_end", 0.2))
        with col_ts3:
            st.session_state.tg_ts_weakness_bars = st.number_input("Velas Exaustão (MACD)", min_value=1, step=1, value=int(st.session_state.get("tg_ts_weakness_bars", 2)))

        st.session_state.tg_only_one_move_per_candle = st.checkbox(
            "Apenas 1 Movimento por Vela",
            value=st.session_state.get("tg_only_one_move_per_candle", True),
            key="tg_chk_only_one_move",
            help="Impede o robô de entrar numa nova posição na mesma vela após fechar uma anterior. Se desativado, permite até 2 movimentos (reversão automática)."
        )


        st.session_state.tg_filter_momentum_active = st.checkbox(
            "⚡ Ativar Filtro de Momentum",
            value=st.session_state.get("tg_filter_momentum_active", False),
            key="tg_chk_filter_momentum",
            help="LONG só entra se for (1, 1) [subida acelerada]. Bloqueia entradas LONG se for (-1, -1) [queda acelerada] ou (1, -1) [subida a travar]. E o inverso para SHORT."
        )

        st.session_state.tg_filter_macd_active = st.checkbox(
            "🔴 Ativar Filtro MACD",
            value=st.session_state.get("tg_filter_macd_active", False),
            key="tg_chk_filter_macd",
            help="Força todas as estratégias a respeitarem os limites do MACD Histograma definidos abaixo."
        )

        st.markdown("###### Limites Histograma MACD (0 = desativado)")
        c_long1, c_long2 = st.columns(2)
        with c_long1:
            st.session_state.tg_macd_long_entry = st.number_input("MACD Long Entry (ex: 0.1)", value=st.session_state.get("tg_macd_long_entry", 0.1), step=0.01)
        with c_long2:
            st.session_state.tg_macd_long_exit = st.number_input("MACD Long Exit (ex: 0.01)", value=st.session_state.get("tg_macd_long_exit", 0.1), step=0.01)

        c_short1, c_short2 = st.columns(2)
        with c_short1:
            st.session_state.tg_macd_short_entry = st.number_input("MACD Short Entry (ex: -0.1)", value=st.session_state.get("tg_macd_short_entry", -0.1), step=0.01)
        with c_short2:
            st.session_state.tg_macd_short_exit = st.number_input("MACD Short Exit (ex: -0.01)", value=st.session_state.get("tg_macd_short_exit", -0.1), step=0.01)

        st.session_state.tg_filter_squeeze_active = st.checkbox(
            "⏳ Ativar Filtro de Squeeze",
            value=st.session_state.get("tg_filter_squeeze_active", False),
            key="tg_chk_filter_squeeze",
            help="Bloqueia entradas quando as SMAs estão muito comprimidas (lateralização) e só permite entrada no 1º ponto de afastamento (rompimento)."
        )
        # Custos & Fricções de Mercado
        cost_vars = [v for v in VARIABLES if v.category == "Custos de Mercado"]
        for var in cost_vars:
            render_variable_widget(var)

    # 💾 COLUNA 5: Memória & Padrões
    with col5:
        st.markdown("##### 💾 Memória & Padrões")
        st.markdown("<p style='font-size:12px; color:#64748b; margin-bottom:15px;'>Configure e guarde as suas variáveis favoritas ou reponha os valores padrões.</p>", unsafe_allow_html=True)
        
        # Botão Guardar DNA Consenso (💾 Guardar)
        if st.button("💾 Guardar", width='stretch', key="tg_btn_save_global"):
            rebuild_consensus_dna()
            # Guardar preferências do utilizador
            prefs_to_save = {}
            for v in VARIABLES:
                if v.key in st.session_state:
                    prefs_to_save[v.key] = st.session_state[v.key]
                t_key = f"{v.key}_active"
                if t_key in st.session_state:
                    prefs_to_save[t_key] = st.session_state[t_key]
            if "paulo_gold_trend_filter_val" in st.session_state:
                prefs_to_save["paulo_gold_trend_filter_val"] = st.session_state["paulo_gold_trend_filter_val"]
            if "allow_reentry_val" in st.session_state:
                prefs_to_save["allow_reentry_val"] = st.session_state["allow_reentry_val"]
            if "tg_only_one_move_per_candle" in st.session_state:
                prefs_to_save["tg_only_one_move_per_candle"] = st.session_state["tg_only_one_move_per_candle"]
            if "tg_filter_momentum_active" in st.session_state:
                prefs_to_save["tg_filter_momentum_active"] = st.session_state["tg_filter_momentum_active"]
            if "tg_filter_macd_active" in st.session_state:
                prefs_to_save["tg_filter_macd_active"] = st.session_state["tg_filter_macd_active"]
            for k in ['tg_macd_long_entry', 'tg_macd_long_exit', 'tg_macd_short_entry', 'tg_macd_short_exit']:
                if k in st.session_state:
                    prefs_to_save[k] = st.session_state[k]
            if "tg_filter_squeeze_active" in st.session_state:
                prefs_to_save["tg_filter_squeeze_active"] = st.session_state["tg_filter_squeeze_active"]
            if "tg_subchart_type" in st.session_state:
                prefs_to_save["tg_subchart_type"] = st.session_state["tg_subchart_type"]
            save_user_preferences(prefs_to_save)
            st.success("Configurações do painel e Cérebro guardadas com sucesso na memória local!")
            
        # Botão Repor Padrões (🔁 Repor Padrões)
        if st.button("🔁 Repor Padrões", width='stretch', key="tg_btn_reset_global"):
            if os.path.exists("user_preferences.json"):
                os.remove("user_preferences.json")
            for var in VARIABLES:
                st.session_state[var.key] = var.default_value
                if var.is_toggleable:
                    st.session_state[f"{var.key}_active"] = (var.key == "tg_sl_pct")
                    if var.key == "tg_sl_pct": st.session_state.tg_sl_active = True
                    elif var.key == "tg_tp_pct": st.session_state.tg_tp_active = False
                    elif var.key == "tg_ts_pct": st.session_state.tg_ts_active = False
            st.session_state.paulo_gold_trend_filter_val = False
            st.session_state.allow_reentry_val = True
            st.session_state.tg_only_one_move_per_candle = True
            st.session_state.tg_filter_momentum_active = False
            st.session_state.tg_filter_macd_active = False
            st.session_state.tg_filter_volume_active = False
            st.session_state.tg_volume_threshold_pct = 0.0
            for k, v in [('tg_macd_long_entry', 0.1), ('tg_macd_long_exit', 0.1), ('tg_macd_short_entry', -0.1), ('tg_macd_short_exit', -0.1)]:
                st.session_state[k] = v
            st.session_state.tg_filter_squeeze_active = False
            st.session_state.tg_subchart_type = ['Heatmap (Vel/Acel)']
            st.session_state.symbol_val = "🧪 Cenário Didático (Fictício)"
            st.toast("Valores padrões repostos com sucesso!")
            st.rerun()

            
        # Botão extra para ver valores do Cérebro Ativo
        if os.path.exists("bot_consensus_dna.json"):
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            if st.button("🧠 Carregar Cérebro", width='stretch', key="tg_btn_load_dna_global"):
                try:
                    with open("bot_consensus_dna.json", "r", encoding="utf-8") as f_dna:
                        dna = json.load(f_dna)
                    smas = dna.get("smas", [5, 13, 21, 55, 144])
                    st.session_state.tg_p2 = smas[0]
                    st.session_state.tg_p3 = smas[1]
                    st.session_state.tg_p4 = smas[2]
                    st.session_state.tg_p5 = smas[3]
                    st.session_state.tg_p6 = smas[4]
                    st.toast("Médias sincronizadas com o Cérebro de Consenso!")
                    st.rerun()

                except Exception as e_dna:
                    st.error(f"Erro: {e_dna}")



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
            "math": "% gatilhos cruzamento P2>P3>P4 e P5<P6",
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
            "math": "% fechos a menos de 0.8% da SMA P5 ou P6",
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
    
    # Nota Teórica e Explicativa sobre o Consenso de Regimes (Matemática Pura)
    st.markdown("""<div style="background: linear-gradient(135deg, rgba(15,23,42,0.9) 0%, rgba(30,41,59,0.95) 100%);
padding: 20px; border-radius: 14px; border: 1px solid rgba(124,58,237,0.3);
box-shadow: 0 8px 32px rgba(0,0,0,0.3); margin-top: 20px;">
<h5 style="color: #a78bfa; margin-top: 0; font-weight: 800; display: flex; align-items: center; gap: 8px;">
🎓 Nota Científica: A Simetria Cruzada dos Regimes Extremos
</h5>
<p style="font-size: 13.5px; color: #cbd5e1; line-height: 1.6; margin-bottom: 12px;">
Notou que as colunas de <b>BULL / LONG</b> e <b>BEAR / SHORT</b> estão vazias, enquanto <b>BULL / SHORT</b> e <b>BEAR / LONG</b> estão preenchidas? 
Isto não é um erro, mas sim uma <b>consequência matemática pura e brilhante</b> da estrutura geométrica do mercado:
</p>
<ul style="font-size: 13px; color: #cbd5e1; line-height: 1.6; padding-left: 20px; margin-bottom: 0;">
<li style="margin-bottom: 8px;">
<b>Porquê BULL / LONG está vazio?</b> Um <i>Fundo Estrutural</i> (ponto ideal de compra) é por definição um <b>mínimo local</b>. Para o preço formar um vale, ele teve de cair nos últimos períodos, o que faz com que as médias curtas (<code style="color:#f472b6;">sma_5</code>, <code style="color:#f472b6;">sma_13</code>) apontem para baixo e cruzem. Por isso, na vela exata do fundo, as médias <b>nunca</b> estarão alinhadas em alta pura (<code style="color:#4ade80;">BULL</code>). O regime no fundo é classificado como <code style="color:#ef4444;">BEAR</code> ou <code style="color:#60a5fa;">LATERAL</code>.
</li>
<li style="margin-bottom: 8px;">
<b>Porquê BEAR / SHORT está vazio?</b> Um <i>Topo Estrutural</i> (ponto ideal de venda) é um <b>máximo local</b>. Para o preço formar um pico, ele teve de subir recentemente, alinhando as médias curtas para cima. Na vela exata do topo, é matematicamente impossível as médias estarem alinhadas em baixa pura (<code style="color:#ef4444;">BEAR</code>). O regime no topo é classificado como <code style="color:#4ade80;">BULL</code> ou <code style="color:#60a5fa;">LATERAL</code>.
</li>
<li>
<b>Conclusão Científica:</b> O Bot é estatisticamente consistente. Ele aprende regras de <b>LONG (Compra)</b> nos regimes <code style="color:#ef4444;">BEAR</code> (pullbacks extremos nos suportes), <code style="color:#60a5fa;">LATERAL</code> e <code style="color:#818cf8;">CAÓTICO</code>, e regras de <b>SHORT (Venda)</b> nos regimes <code style="color:#4ade80;">BULL</code> (picos de euforia e resistências), <code style="color:#60a5fa;">LATERAL</code> e <code style="color:#818cf8;">CAÓTICO</code>.
</li>
</ul>
</div>""", unsafe_allow_html=True)

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
            if k in ["infil", "reteste", "infil_exit", "reteste_exit"]:
                buy_rules[k] = {"rate": float(val_buy), "active": bool(val_buy > 50.0) if opp_samples > 0 else False}
            elif k.endswith("exit"):
                buy_rules[k] = {"mean": float(val_buy)}
            else:
                buy_rules[k] = {"mean": float(val_buy)}
                
            val_sell = thr_weighted[k] / thr_samples if thr_samples > 0 else (50.0 if k in ["rsi", "rsi_exit", "bb", "bb_exit"] else 0.0)
            if k in ["infil", "reteste", "infil_exit", "reteste_exit"]:
                sell_rules[k] = {"rate": float(val_sell), "active": bool(val_sell > 50.0) if thr_samples > 0 else False}
            elif k.endswith("exit"):
                sell_rules[k] = {"mean": float(val_sell)}
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
