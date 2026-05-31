import sys, os, textwrap
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Build the panel code programmatically to avoid quoting issues
INDENT = '        '
lines = []
def L(s): lines.append(INDENT + s)
def L0(s): lines.append(s)

L('# ====================================================================')
L('# PAINEL DE LANCAMENTO - premium, sempre visivel, sem expander')
L('# ====================================================================')
L(chr(95)+'strat_d = st.session_state.get(' + chr(39) + 'tg_strategy_type' + chr(39) + ', ' + chr(39) + 'Default (Formulas do Jogo)' + chr(39) + ')')
L(chr(95)+'ref_d   = st.session_state.get(' + chr(39) + 'tg_single_line_ref' + chr(39) + ', ' + chr(39) + 'SMA Rapida (P2)' + chr(39) + ')')
L(chr(95)+'sl_on   = st.session_state.get(' + chr(39) + 'tg_sl_pct_active' + chr(39) + ', st.session_state.get(' + chr(39) + 'tg_sl_active' + chr(39) + ', True))')
L(chr(95)+'tp_on   = st.session_state.get(' + chr(39) + 'tg_tp_pct_active' + chr(39) + ', st.session_state.get(' + chr(39) + 'tg_tp_active' + chr(39) + ', False))')
L(chr(95)+'ts_on   = st.session_state.get(' + chr(39) + 'tg_ts_pct_active' + chr(39) + ', st.session_state.get(' + chr(39) + 'tg_ts_active' + chr(39) + ', False))')
L(chr(95)+'sl_v = st.session_state.get(' + chr(39) + 'tg_sl_pct' + chr(39) + ', 2.0)')
L(chr(95)+'tp_v = st.session_state.get(' + chr(39) + 'tg_tp_pct' + chr(39) + ', 7.0)')
L(chr(95)+'ts_v = st.session_state.get(' + chr(39) + 'tg_ts_pct' + chr(39) + ', 1.5)')
L(chr(95)+'p2 = st.session_state.get(' + chr(39) + 'tg_p2' + chr(39) + ', 5)')
L(chr(95)+'p3 = st.session_state.get(' + chr(39) + 'tg_p3' + chr(39) + ', 13)')
L(chr(95)+'p4 = st.session_state.get(' + chr(39) + 'tg_p4' + chr(39) + ', 21)')
L(chr(95)+'p5 = st.session_state.get(' + chr(39) + 'tg_p5' + chr(39) + ', 55)')
L(chr(95)+'p6 = st.session_state.get(' + chr(39) + 'tg_p6' + chr(39) + ', 144)')
