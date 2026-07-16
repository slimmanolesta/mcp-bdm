@echo off
REM Installatore di manolesta per Claude Desktop. Fai doppio click su questo file.
REM Serve Python 3.10+ installato. Chiudi Claude Desktop prima di lanciarlo.
title Setup Manolesta
cd /d "%~dp0"

set "PY=python"
where python >nul 2>&1 || set "PY=py"

"%PY%" "%~dp0setup_manolesta.py"

echo.
pause
