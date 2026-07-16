"""Setup di manolesta per Claude Desktop (Windows).

Fa, nell'ordine: verifica che Claude Desktop sia CHIUSO, controlla la versione di
Python, crea un ambiente isolato (.venv), installa le dipendenze + il browser per
il login CNS, e registra manolesta come server MCP in Claude Desktop.

Non gestisce MAI credenziali: il login CNS lo fa l'utente, a parte, col browser.

Uso: doppio click su `Setup-Manolesta.bat` (oppure: `python setup_manolesta.py`).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
VENV_PY = VENV_DIR / "Scripts" / "python.exe"


def rule() -> None:
    print("=" * 60)


def fail(msg: str, *extra: str) -> None:
    print()
    print(f"  STOP: {msg}")
    for line in extra:
        print(f"  {line}")
    print()
    raise SystemExit(1)


def run(cmd: list, desc: str, cwd: Path | None = None) -> None:
    result = subprocess.run([str(c) for c in cmd], cwd=str(cwd) if cwd else None)
    if result.returncode != 0:
        fail(f"{desc} non riuscito.",
             "Sei connesso a internet? Un proxy o un antivirus puo' bloccare il download.")


def claude_desktop_running() -> bool | None:
    """True/False; None se non riusciamo a stabilirlo."""
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq claude.exe", "/NH"],
                             capture_output=True, text=True, timeout=20)
        return "claude.exe" in (out.stdout or "").lower()
    except Exception:
        return None


def step_claude_chiuso() -> None:
    # Non e' pignoleria: Claude Desktop riscrive da se' il proprio file di
    # configurazione mentre e' in esecuzione, quindi scrivere ad app aperta puo'
    # far perdere la registrazione o rovinare il file.
    stato = claude_desktop_running()
    if stato is True:
        fail("Claude Desktop e' APERTO.",
             "",
             "Mentre e' in esecuzione riscrive da se' il file di configurazione:",
             "se scrivessi adesso, la registrazione andrebbe persa.",
             "",
             "ESCI del tutto da Claude Desktop (menu Esci, oppure tasto destro",
             "sull'icona vicino all'orologio -> Esci: non basta la X), poi",
             "rilancia questo setup.")
    if stato is None:
        print("  [1/5] Non riesco a verificare se Claude Desktop e' aperto.")
        input("        Assicurati che sia CHIUSO, poi premi INVIO per proseguire...")
        return
    print("  [1/5] Claude Desktop chiuso: ok.")


def step_python() -> None:
    if sys.version_info < (3, 10):
        v = f"{sys.version_info.major}.{sys.version_info.minor}"
        fail(f"serve Python 3.10 o superiore (questo e' {v}).",
             "Installa una versione recente da https://www.python.org/downloads/",
             "(spunta 'Add Python to PATH'), poi rilancia questo setup.")
    print(f"  [2/5] Python {sys.version_info.major}.{sys.version_info.minor}: ok.")


def step_venv() -> None:
    if VENV_PY.exists():
        print("  [3/5] Ambiente isolato gia' presente: ok.")
        return
    print("  [3/5] Creo l'ambiente isolato (.venv)...")
    run([sys.executable, "-m", "venv", VENV_DIR], "creazione dell'ambiente isolato")
    if not VENV_PY.exists():
        fail("l'ambiente isolato non risulta creato.")


def step_dipendenze() -> None:
    print("  [4/5] Installo le dipendenze e il browser per il login CNS.")
    print("        (la prima volta puo' richiedere qualche minuto)")
    subprocess.run([str(VENV_PY), "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
    run([VENV_PY, "-m", "pip", "install", "-e", ".[login,mcp]", "--quiet"],
        "installazione delle dipendenze", cwd=ROOT)
    run([VENV_PY, "-m", "playwright", "install", "chromium"],
        "download del browser per il login", cwd=ROOT)
    print("        dipendenze e browser: ok.")


def step_registra() -> None:
    print("  [5/5] Registro manolesta in Claude Desktop...")
    run([VENV_PY, ROOT / "register_desktop.py", "--python", VENV_PY],
        "registrazione in Claude Desktop", cwd=ROOT)


def main() -> int:
    print()
    rule()
    print("  SETUP MANOLESTA")
    print("  Banca Dati di Merito (bdp.giustizia.it) per Claude Desktop")
    rule()
    print()

    step_claude_chiuso()
    step_python()
    step_venv()
    step_dipendenze()
    step_registra()

    print()
    rule()
    print("  FATTO. Adesso, nell'ordine:")
    rule()
    print()
    print("  1. Lancia  Rinnova-BDM.bat  e accedi con la CNS (chiavetta + PIN).")
    print("     La sessione dura circa 2 ore: quando scade, rilancialo.")
    print()
    print("  2. Apri Claude Desktop.")
    print()
    print("  3. Carica la skill: Personalizza -> Competenze -> carica la")
    print("     cartella  skill\\manolesta  (oppure il suo .zip).")
    print()
    print('  4. Prova a chiedere: "con manolesta, cerca sulla Banca Dati di')
    print('     Merito la sentenza n. 941/2026".')
    print()
    print("  Guida completa: GUIDA.md")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
