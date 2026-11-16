@echo off
REM Windows: dois cliques para abrir o painel. Feche esta janela para desligar o emissor.
cd /d "%~dp0"
if not exist .venv (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar.ps1"
  exit /b
)
where uv >nul 2>nul || set "PATH=%USERPROFILE%\.local\bin;%PATH%"
uv run --quiet emissor painel
pause
