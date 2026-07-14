@echo off
title Rinnova sessione Banca Dati di Merito
cd /d "%~dp0"

echo ============================================================
echo  RINNOVA SESSIONE BANCA DATI DI MERITO (bdp.giustizia.it)
echo ============================================================
echo  Si apre il browser sulla pagina di login della BDM.
echo  ACCEDI con la CNS: inserisci la chiavetta e digita il PIN.
echo  Appena l'accesso e' completo, la sessione viene catturata e
echo  salvata DA SE'. NESSUN riavvio di Claude: il connettore
echo  rilegge la sessione da se'.
echo ------------------------------------------------------------

set "PY=python"
where python >nul 2>&1 || set "PY=py"
set "PYTHONPATH=%~dp0src"

"%PY%" -m mcp_bdm login
if errorlevel 1 goto fail

echo.
echo  Sessione aggiornata. Puoi chiudere questa finestra.
timeout /t 3 /nobreak >nul
exit /b 0

:fail
echo.
echo  ACCESSO NON RIUSCITO: la sessione NON e' stata aggiornata. Riprova.
echo.
pause
exit /b 1
