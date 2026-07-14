@echo off
REM Wrapper CLI: "bdm search ..." / "bdm get <id> --dir ..." / "bdm check"
REM Esegui da C:\Tools\mcp-bdm oppure col percorso completo.
set "PY=python"
where python >nul 2>&1 || set "PY=py"
set "PYTHONPATH=%~dp0src"
"%PY%" -m mcp_bdm %*
