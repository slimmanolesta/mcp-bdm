"""Server MCP sottile per la Banca Dati di Merito (bdp.giustizia.it).

Espone tre tool (ricerca, recupero testo, verifica sessione) sopra lo stesso motore
della CLI. Per il bulk usare la CLI (`bdm get/search`), che scrive su disco senza
bruciare contesto.

Avvio stdio per Claude Desktop:  python -m mcp_bdm.server
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import extract
from .client import BdmAuthError, BdmClient, BdmError
from .config import load_config


def _fmt(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(value)


def create_server() -> FastMCP:
    mcp = FastMCP(
        name="mcp_bdm",
        instructions=(
            "Connettore Banca Dati di Merito (bdp.giustizia.it): giurisprudenza di "
            "merito civile (sentenze/ordinanze/decreti dal 2016), pseudonimizzata. "
            "Ricerca full-text e testo integrale dei provvedimenti. Il login e' CNS "
            "(lo fa l'utente, sessione breve); per scaricare in massa nella cartella "
            "di una pratica usa la CLI 'bdm'."
        ),
    )

    @mcp.tool()
    async def bdm_check_session() -> str:
        """Verifica che la sessione BDM sia valida (chiamata dati reale)."""
        cfg = load_config()
        if not cfg.is_authenticated:
            return "Sessione assente. Esegui 'bdm login' (scorciatoia 'Rinnova BDM')."
        client = BdmClient(cfg)
        try:
            info = await client.check_session()
            return _fmt({"ok": True, "utente": info.get("utente"), "exp": info.get("exp")})
        except BdmAuthError as exc:
            return _fmt({"ok": False, "errore": str(exc)})
        except BdmError as exc:
            return f"ERRORE: {exc}"
        finally:
            await client.aclose()

    @mcp.tool()
    async def bdm_search(testo: str = "", ufficio: str = "", materia: str = "", size: int = 10) -> str:
        """Cerca provvedimenti di merito civile.

        Args:
            testo: testo libero (ricerca full-text sul testo del provvedimento).
            ufficio: filtro per ufficio giudiziario (vuoto = tutti).
            materia: filtro per materia (vuoto = tutte).
            size: massimo risultati.
        """
        client = BdmClient(load_config())
        try:
            res = await client.search(testo=testo, ufficio=ufficio or None,
                                      materia=materia or None, size=size)
            items = res.get("items") or []
            compact = [{"id": it.get("id"), "estremo": extract.estremo(it),
                        "materia": it.get("materia"), "data": it.get("data"),
                        "estratto": it.get("estratto")} for it in items]
            return _fmt({"count": res.get("count"), "mostrati": len(compact), "risultati": compact})
        except (BdmAuthError, BdmError) as exc:
            return f"ERRORE: {exc}"
        finally:
            await client.aclose()

    @mcp.tool()
    async def bdm_get_provvedimento(id: str, max_chars: int = 20000) -> str:
        """Recupera il testo integrale (pseudonimizzato) di un provvedimento per id.

        Restituisce metadati (estremo, ufficio, date, materia) + testo pulito.
        """
        client = BdmClient(load_config())
        try:
            meta_item = await client.get_meta(id)
            meta = extract.item_meta(meta_item) if meta_item else {"id": id}
            text = extract.normalize_text(await client.get_text(id))
            return _fmt({
                "meta": meta,
                "testo": text[: max(1000, int(max_chars))],
                "troncato": len(text) > max_chars,
                "char_totali": len(text),
            })
        except (BdmAuthError, BdmError) as exc:
            return f"ERRORE: {exc}"
        finally:
            await client.aclose()

    return mcp


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
