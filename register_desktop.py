"""Registra (o aggiorna) manolesta come server MCP in Claude Desktop.

Fa un backup timestamped del config e un merge NON distruttivo: tocca soltanto la
voce `mcpServers.manolesta`, lasciando intatti gli altri server e ogni altra chiave.

ATTENZIONE: Claude Desktop riscrive da se' questo file MENTRE e' in esecuzione
(osservato dal vivo: il file cambia tra un backup e la rilettura un istante dopo).
Va quindi lanciato ad app CHIUSA. `Setup-Manolesta.ps1` lo verifica prima di
arrivare qui; se lanci questo script a mano, chiudi prima Claude Desktop.

Uso:
    python register_desktop.py [--python <path-al-python>] [--nome manolesta]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path


def config_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise SystemExit("APPDATA non definita: questo script funziona su Windows.")
    return Path(appdata) / "Claude" / "claude_desktop_config.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="Registra manolesta come server MCP in Claude Desktop.")
    ap.add_argument("--python", default=sys.executable,
                    help="Python che avviera' il server (default: quello che esegue questo script).")
    ap.add_argument("--nome", default="manolesta", help="Nome del server MCP (default: manolesta).")
    args = ap.parse_args()

    cfg_path = config_path()
    if not cfg_path.parent.exists():
        print(f"ATTENZIONE: {cfg_path.parent} non esiste: Claude Desktop non sembra installato.")
        print("Registrazione saltata. Installa Claude Desktop e rilancia questo script.")
        return 0

    cfg: dict = {}
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            print(f"ERRORE: {cfg_path} non contiene JSON valido ({exc}).")
            print("Sistemalo (o rinominalo) e rilancia: non lo sovrascrivo alla cieca.")
            return 2
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = cfg_path.with_name(cfg_path.name + f".bak-manolesta-{stamp}")
        shutil.copy2(cfg_path, backup)
        print(f"Backup del config: {backup.name}")

    if not isinstance(cfg, dict):
        cfg = {}

    servers = cfg.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        print("ERRORE: la chiave 'mcpServers' esiste ma non e' un oggetto. Non tocco nulla.")
        return 2

    servers[args.nome] = {"command": str(args.python), "args": ["-m", "mcp_bdm.server"]}

    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Registrato '{args.nome}' in {cfg_path}")
    print(f"  command : {args.python}")
    print("  args    : -m mcp_bdm.server")
    print(f"Server MCP ora presenti: {', '.join(servers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
