@echo off
setlocal
title Instalador - Cortes por Lista V4.1

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Instalar_Cortes_por_Lista.ps1"

echo.
pause
