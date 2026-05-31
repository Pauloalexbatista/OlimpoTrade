import re

with open('app_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Card 1 Background
content = content.replace(
    "<div style='background:rgba(30,41,59,0.5); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:16px;'>",
    "<div style='background:linear-gradient(90deg,#0f172a,#1e293b,#0f172a); border:1px solid rgba(124,58,237,0.3); border-radius:12px; padding:16px; box-shadow:0 4px 24px rgba(0,0,0,0.4);'>"
)

# 2. Update Card 2 Background
content = content.replace(
    "<div style='background:rgba(30,41,59,0.3); border:1px solid rgba(255,255,255,0.05); border-radius:12px; padding:12px;'>",
    "<div style='background:linear-gradient(90deg,#0f172a,#1e293b,#0f172a); border:1px solid rgba(124,58,237,0.3); border-radius:12px; padding:12px; box-shadow:0 4px 24px rgba(0,0,0,0.4);'>"
)

# 3. Change Selectbox and logic
# Find the exact string for selectbox
selectbox_pattern = r'''(trade_options\s*=\s*\[.*?\]\n\s*)selected_trade_lbl\s*=\s*st\.selectbox\([^)]+\)\n\s*if selected_trade_lbl:\n\s*trade_idx\s*=\s*trade_options\.index\(selected_trade_lbl\)\n\s*tr\s*=\s*st\.session_state\.tg_trades\[trade_idx\]'''

selectbox_replacement = r'''\1
                if "tg_trade_idx" not in st.session_state:
                    st.session_state.tg_trade_idx = 0
                if st.session_state.tg_trade_idx >= len(trade_options):
                    st.session_state.tg_trade_idx = 0

                def on_trade_select():
                    sel = st.session_state.tg_analysis_trade_select_widget
                    if sel in trade_options:
                        st.session_state.tg_trade_idx = trade_options.index(sel)

                trade_idx = st.session_state.tg_trade_idx
                tr = st.session_state.tg_trades[trade_idx]
                if True:
'''
content = re.sub(selectbox_pattern, selectbox_replacement, content, flags=re.DOTALL)


# 4. Insert Controls under Chart
chart_pattern = r'''(st\.plotly_chart\(fig_mini, use_container_width=True, key=f"tg_mini_chart_\{trade_idx\}"\))'''
controls_replacement = r'''\1

                        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
                        cc1, cc2, cc3 = st.columns([1, 8, 1])
                        with cc1:
                            if st.button("⬅️", key="prev_tr", use_container_width=True):
                                if st.session_state.tg_trade_idx > 0:
                                    st.session_state.tg_trade_idx -= 1
                                    st.rerun()
                        with cc2:
                            st.selectbox(
                                "Escolha a Operação:", 
                                trade_options, 
                                index=trade_idx,
                                key="tg_analysis_trade_select_widget",
                                on_change=on_trade_select,
                                label_visibility="collapsed"
                            )
                        with cc3:
                            if st.button("➡️", key="next_tr", use_container_width=True):
                                if st.session_state.tg_trade_idx < len(trade_options) - 1:
                                    st.session_state.tg_trade_idx += 1
                                    st.rerun()
'''
content = re.sub(chart_pattern, controls_replacement, content, flags=re.DOTALL)


with open('app_ui.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated!")
