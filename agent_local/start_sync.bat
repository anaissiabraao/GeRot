@echo off
title GeRot - Sincronizacao de Conhecimento Brudam
cd /d "%~dp0"

echo ========================================================
echo   INICIANDO MOTOR DE SINCRONIZACAO (BRUDAM - GEROT)
echo ========================================================
echo.

:LOOP
echo [%TIME%] Executando sincronizacao...
python sync_engine.py

echo.
echo [%TIME%] Aguardando 10 minutos para a proxima execucao...
timeout /t 600 /nobreak >nul
goto LOOP
