"""Server MCP sottile per la Banca Dati di Merito (bdp.giustizia.it).

Espone tre tool (ricerca, recupero testo, verifica sessione) sopra lo stesso motore
della CLI. Per il bulk usare la CLI (`bdm get/search`), che scrive su disco senza
bruciare contesto.

Avvio stdio per Claude Desktop:  python -m mcp_bdm.server
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import extract
from .client import BdmAuthError, BdmClient, BdmError
from .config import load_config, load_workflow, save_workflow


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
    async def bdm_estremi(numero: str, anno: str = "", ufficio: str = "",
                          tipo: str = "", size: int = 20) -> str:
        """Ricerca per ESTREMI (uso principale): dato il numero (+ anno, ufficio,
        tipo) trova il provvedimento specifico. Con numero+anno soli puo' restituire
        piu' candidati tra uffici diversi, da disambiguare.

        Args:
            numero: numero del provvedimento (es. "941"). Obbligatorio.
            anno: anno (es. "2026"); quasi sempre necessario per disambiguare.
            ufficio: ufficio ESATTO in maiuscolo (es. "TRIBUNALE DI VERONA").
            tipo: SENTENZA | ORDINANZA | DECRETO.
            size: massimo candidati.
        """
        client = BdmClient(load_config())
        try:
            res = await client.search_estremi(
                numero=numero, anno=anno or None, ufficio=ufficio or None,
                tipo=tipo or None, size=size,
            )
            items = res.get("items") or []
            compact = [{"id": it.get("id"), "estremo": extract.estremo(it),
                        "materia": it.get("materia"), "data": it.get("data"),
                        "data_pubblicazione": it.get("data_pubblicazione")} for it in items]
            return _fmt({"count": res.get("count"), "mostrati": len(compact), "risultati": compact})
        except (BdmAuthError, BdmError) as exc:
            return f"ERRORE: {exc}"
        finally:
            await client.aclose()

    @mcp.tool()
    async def bdm_get_provvedimento(id: str, cartella: str = "", nome: str = "",
                                    max_chars: int = 20000) -> str:
        """Recupera il testo integrale (pseudonimizzato) di un provvedimento per id.

        Se `cartella` e' indicata, salva un .md pulito (metadati + testo integrale)
        in quella cartella e restituisce il percorso; altrimenti restituisce metadati
        + testo (troncato a `max_chars`) nella risposta.

        Args:
            id: id (hash) del provvedimento.
            cartella: cartella di destinazione; se valorizzata, salva il .md su disco.
            nome: nome file senza estensione (default: derivato dall'estremo).
            max_chars: massimo caratteri restituiti in chat quando NON si salva.
        """
        client = BdmClient(load_config())
        try:
            meta_item = await client.get_meta(id)
            meta = extract.item_meta(meta_item) if meta_item else {"id": id}
            text = extract.normalize_text(await client.get_text(id))
            if cartella:
                destdir = Path(cartella)
                destdir.mkdir(parents=True, exist_ok=True)
                fname = extract.safe_filename(nome or extract.default_filename(meta_item or {"id": id}))
                out = destdir / (fname + ".md")
                out.write_text(extract.provvedimento_md(meta, text), encoding="utf-8")
                return _fmt({"salvato": str(out), "char": len(text), "estremo": meta.get("estremo")})
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

    @mcp.tool()
    async def bdm_get_workflow() -> str:
        """Legge la configurazione di flusso dell'utente (dove salvare, come nominare,
        biblioteca si'/no). Vuota al PRIMO AVVIO: in quel caso conduci l'onboarding
        (fai le domande) e poi chiama `bdm_set_workflow`."""
        wf = load_workflow()
        if not wf:
            return _fmt({"_stato": "primo_avvio",
                         "_nota": "Configurazione assente: conduci l'onboarding, poi salva con bdm_set_workflow."})
        return _fmt(wf)

    @mcp.tool()
    async def bdm_set_workflow(organizzazione: str = "", cartella_radice: str = "",
                               naming: str = "", biblioteca: bool = False) -> str:
        """Salva la configurazione di flusso dell'utente (fine dell'onboarding).

        Args:
            organizzazione: "per_pratica" | "archivio_unico" | descrizione libera.
            cartella_radice: cartella dove salvare i provvedimenti scaricati.
            naming: convenzione per i nomi file ("" = estremo leggibile di default).
            biblioteca: se segnalare i provvedimenti di principio generale.
        """
        prefs = {
            "organizzazione": organizzazione,
            "cartella_radice": cartella_radice,
            "naming": naming,
            "biblioteca": bool(biblioteca),
        }
        path = save_workflow(prefs)
        return _fmt({"salvato": str(path), "config": prefs})

    return mcp


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
