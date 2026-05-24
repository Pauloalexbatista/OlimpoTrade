@echo off
title OlimpoTrade - Algorithmic Trading Lab
echo ===================================================
echo   OLIMPOTRADE - Algorithmic Trading Lab
echo ===================================================
echo.
echo A iniciar a interface grafica interativa...
echo.
streamlit run app_ui.py
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Ocorreu uma falha ao iniciar o Streamlit.
    echo Verifique se as dependencias estao corretamente instaladas.
    echo.
    pause
)
