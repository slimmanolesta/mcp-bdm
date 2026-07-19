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


# Tetto ai caratteri restituiti in chat: oltre, si salva su file. Serve a impedire
# che il modello si spari in contesto una sentenza di 150 pagine chiedendo un
# max_chars enorme (i parametri dei tool li sceglie lui).
MAX_CHARS_CEILING = 50_000


def _resolve_dest(cartella: str) -> tuple[Path | None, str]:
    """Risolve la cartella di destinazione, confinandola alla radice configurata
    nell'onboarding (`cartella_radice`), se c'e'.

    I parametri dei tool arrivano da un modello: senza confinamento una cartella
    allucinata puo' far scrivere ovunque sul disco. Un percorso relativo viene
    risolto DENTRO la radice, cosi' "Rossi c. Bianchi" finisce dove deve.
    """
    wf = load_workflow() or {}
    root = wf.get("cartella_radice") or ""
    dest = Path(cartella).expanduser()
    if not root:
        return dest, ""
    try:
        root_p = Path(root).expanduser().resolve()
        dest_p = dest.resolve() if dest.is_absolute() else (root_p / dest).resolve()
    except (OSError, ValueError):
        return None, f"percorso non valido: {cartella!r}"
    if dest_p != root_p and root_p not in dest_p.parents:
        return None, (f"la cartella richiesta ({dest_p}) e' fuori dalla radice configurata "
                      f"({root_p}). Indica una sottocartella della radice, oppure cambia "
                      f"la radice con bdm_set_workflow.")
    return dest_p, ""


def _unique_path(destdir: Path, fname: str) -> Path:
    """Percorso .md che non calpesta un file esistente.

    Senza questo, un nome allucinato dal modello (es. "_SCHEDA") sovrascriverebbe in
    silenzio un file dell'utente, per giunta su una cartella sincronizzata.
    """
    out = destdir / (fname + ".md")
    n = 2
    while out.exists():
        out = destdir / f"{fname} ({n}).md"
        n += 1
    return out


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
            max_chars: caratteri restituiti in chat quando NON si salva
                (tetto massimo 50000: per testi piu' lunghi usa `cartella`).
        """
        destdir = None
        if cartella:
            destdir, errore = _resolve_dest(cartella)
            if errore:
                return f"ERRORE: {errore}"
        client = BdmClient(load_config())
        try:
            meta_item = await client.get_meta(id)
            meta = extract.item_meta(meta_item) if meta_item else {"id": id}
            text = extract.normalize_text(await client.get_text(id))
            if destdir is not None:
                destdir.mkdir(parents=True, exist_ok=True)
                fname = extract.safe_filename(nome or extract.default_filename(meta_item or {"id": id}))
                out = _unique_path(destdir, fname)
                out.write_text(extract.provvedimento_md(meta, text), encoding="utf-8")
                return _fmt({"salvato": str(out), "char": len(text), "estremo": meta.get("estremo")})
            limite = min(max(1000, int(max_chars)), MAX_CHARS_CEILING)
            return _fmt({
                "meta": meta,
                "testo": text[:limite],
                "troncato": len(text) > limite,
                "limite_applicato": limite,
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
    async def bdm_set_workflow(organizzazione: str | None = None,
                               cartella_radice: str | None = None,
                               naming: str | None = None,
                               biblioteca: bool | None = None) -> str:
        """Salva la configurazione di flusso dell'utente (fine dell'onboarding).

        Aggiornamento PARZIALE: passa solo i campi da cambiare, gli altri restano
        come sono. NON passare valori "di comodo" per i campi che non stai
        cambiando, altrimenti sovrascrivi le scelte gia' fatte dall'utente.

        Args:
            organizzazione: "per_pratica" | "archivio_unico" | descrizione libera.
            cartella_radice: cartella radice dove salvare i provvedimenti. Vincola
                anche dove `bdm_get_provvedimento` puo' scrivere.
            naming: convenzione per i nomi file ("estremo" = default leggibile).
            biblioteca: se segnalare i provvedimenti di principio generale.
        """
        prefs = {
            "organizzazione": organizzazione,
            "cartella_radice": cartella_radice,
            "naming": naming,
            "biblioteca": biblioteca,
        }
        path = save_workflow(prefs)
        return _fmt({"salvato": str(path), "config": load_workflow()})

    return mcp


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
