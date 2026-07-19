@echo off
REM Installatore di manolesta per Claude Desktop. Fai doppio click su questo file.
REM Serve Python 3.10+ installato. Chiudi Claude Desktop prima di lanciarlo.
title Setup Manolesta
cd /d "%~dp0"

REM Cerchiamo un Python che FUNZIONI davvero, non che risulti "presente":
REM su Windows 11 c'e' uno stub del Microsoft Store di nome python.exe che sta nel
REM PATH (quindi "where python" lo trova) ma non esegue nulla: apre lo Store. Per
REM questo proviamo a eseguire un comando vero invece di limitarci a cercarlo.
set "PY="
py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys" >nul 2>&1 && set "PY=python"

if not defined PY goto nopython

%PY% "%~dp0setup_manolesta.py"
echo.
pause
exit /b %errorlevel%

:nopython
echo.
echo  ============================================================
echo   MANCA PYTHON
echo  ============================================================
echo.
echo   Manolesta ha bisogno di Python 3.10 o superiore, che su questo
echo   computer non risulta installato (oppure c'e' solo il segnaposto
echo   del Microsoft Store, che non funziona).
echo.
echo   Cosa fare:
echo    1. Vai su   https://www.python.org/downloads/
echo    2. Scarica l'ultima versione per Windows e installala.
echo    3. IMPORTANTE: nella prima schermata dell'installazione, spunta
echo       "Add Python to PATH" (o "Aggiungi Python al PATH").
echo    4. Chiudi questa finestra e rilancia Setup-Manolesta.
echo.
pause
exit /b 1
