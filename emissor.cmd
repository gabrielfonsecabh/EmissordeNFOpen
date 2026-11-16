@echo off
REM Atalho: emissor <comando>. Ex.: emissor painel, emissor status
cd /d "%~dp0"
where uv >nul 2>nul || set "PATH=%USERPROFILE%\.local\bin;%PATH%"
uv run --quiet emissor %*
