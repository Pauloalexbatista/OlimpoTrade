@echo off
title OlimpoTrade - Algorithmic Trading Lab
cd /d "%~dp0"
echo ===================================================
echo   OLIMPOTRADE - Algorithmic Trading Lab
echo ===================================================
echo.
echo A iniciar a interface grafica interativa...
echo.
if exist "C:\Users\paulo\AppData\Local\Programs\Python\Python312\python.exe" (
    "C:\Users\paulo\AppData\Local\Programs\Python\Python312\python.exe" -m streamlit run app_ui.py
) else (
    streamlit run app_ui.py
)
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Ocorreu uma falha ao iniciar o Streamlit.
    echo Verifique se as dependencias estao corretamente instaladas.
    echo.
    pause
)
