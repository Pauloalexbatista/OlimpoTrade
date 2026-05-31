import re

with open('app_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Change function signature
content = content.replace(
    "def _build_chart(sub_df, df_full, title_str, show_full_range=False):",
    "def _build_chart(sub_df, df_full, title_str, show_full_range=False, highlight_trade=None):"
)

# 2. Add add_vrect logic at the end of the _build_chart function
return_fig_pattern = r'(\n\s+)return fig'
match = re.search(return_fig_pattern, content)
if match:
    indent = match.group(1)
    
    vrect_code = indent + "# Highlight specific trade se solicitado"
    vrect_code += indent + "if highlight_trade:"
    vrect_code += indent + "    e_time = df_full.iloc[highlight_trade['entry_step']].name"
    vrect_code += indent + "    x_time = df_full.iloc[highlight_trade['exit_step']].name if highlight_trade['exit_step'] < len(df_full) else df_full.index[-1]"
    vrect_code += indent + "    color = 'rgba(16, 185, 129, 0.15)' if highlight_trade['type'] == 'LONG' else 'rgba(239, 68, 68, 0.15)'"
    vrect_code += indent + "    fig.add_vrect("
    vrect_code += indent + "        x0=e_time, x1=x_time,"
    vrect_code += indent + "        fillcolor=color, opacity=1, layer='below', line_width=0,"
    vrect_code += indent + "        annotation_text=f\"{highlight_trade['type']} (PnL: {highlight_trade.get('pnl_pct', 0):+.2f}%)\","
    vrect_code += indent + "        annotation_position='top left', annotation_font_size=10, annotation_font_color='rgba(255,255,255,0.7)'"
    vrect_code += indent + "    )"
    vrect_code += indent + "return fig"
    
    content = content.replace(match.group(0), vrect_code)
    
# 3. Update the call inside the detailed analysis section
# In the detailed analysis section, it uses focus_df and df:
# fig_mini = _build_chart(
#     focus_df, df,
#     title_str=...
#     show_full_range=False
# )
call_pattern = r'(fig_mini\s*=\s*_build_chart\(\s*focus_df,\s*df,\s*title_str=.*?show_full_range=False)(\s*\))'
content = re.sub(call_pattern, r'\1, highlight_trade=tr\2', content, flags=re.DOTALL)

with open('app_ui.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Added highlight region for detailed analysis.")
