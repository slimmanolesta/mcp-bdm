@echo off
REM Wrapper CLI: "bdm search ..." / "bdm estremi ..." / "bdm get <id> --dir ..." / "bdm check"
REM Esegui dalla cartella del connettore oppure col percorso completo.
REM Usa l'ambiente isolato creato da Setup-Manolesta se c'e'; altrimenti ripiega
REM sul Python di sistema + PYTHONPATH (installazione "a mano").
setlocal
if exist "%~dp0.venv\Scripts\python.exe" goto venv

set "PY=python"
where python >nul 2>&1 || set "PY=py"
set "PYTHONPATH=%~dp0src"
goto run

:venv
set "PY=%~dp0.venv\Scripts\python.exe"
set "PYTHONPATH="

:run
"%PY%" -m mcp_bdm %*
