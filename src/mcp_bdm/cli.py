"""CLI Banca Dati di Merito: login, ricerca, recupero testo, verifica sessione.

Caso d'uso principale: `bdm get <id> --dir <pratica>` scrive il provvedimento come
.md pulito su disco; `bdm search "..."` elenca i candidati.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from . import extract
from .client import BdmAuthError, BdmClient, BdmError
from .config import load_config


def _force_utf8_stdio() -> None:
    """Forza UTF-8 su stdout/stderr.

    Su Windows, quando l'output e' rediretto o in pipe (e' cosi' che ci invoca un
    agente), Python NON usa la console ma ripiega sul code page ANSI (cp1252):
    stampare un testo che contiene caratteri fuori da cp1252 - p.es. le legature
    fi/fl tipiche dei PDF - fa fallire il comando a meta' documento con
    UnicodeEncodeError. A console non si vede mai, in pipe si'.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


async def _get(args) -> int:
    client = BdmClient(load_config())
    try:
        meta_item = await client.get_meta(args.id)
        meta = extract.item_meta(meta_item) if meta_item else {"id": args.id}
        text = extract.normalize_text(await client.get_text(args.id))
        fname = extract.safe_filename(args.name or extract.default_filename(meta_item or {"id": args.id}))
        if args.dir:
            destdir = Path(args.dir)
            destdir.mkdir(parents=True, exist_ok=True)
            out = destdir / (fname + ".md")
            out.write_text(extract.provvedimento_md(meta, text), encoding="utf-8")
            print(f"SALVATO {out}  ({len(text)} char)")
        else:
            print(extract.md_header(meta))
            print()
            print(text[: args.max_chars])
        return 0
    except (BdmAuthError, BdmError) as exc:
        print(f"ERRORE: {exc}", file=sys.stderr)
        return 2
    finally:
        await client.aclose()


async def _search(args) -> int:
    client = BdmClient(load_config())
    try:
        res = await client.search(
            testo=args.text, ufficio=args.ufficio or None, materia=args.materia or None,
            size=args.size,
        )
        items = res.get("items") or []
        print(f"count totale: {res.get('count')} — mostro {len(items)}:")
        for i, it in enumerate(items, 1):
            print(f"  [{i}] id={it.get('id')}")
            print(f"       {extract.estremo(it)}  [{it.get('materia') or ''}]")
        if not items:
            print("(nessun risultato)")
            return 1
        return 0
    except (BdmAuthError, BdmError) as exc:
        print(f"ERRORE: {exc}", file=sys.stderr)
        return 2
    finally:
        await client.aclose()


async def _estremi(args) -> int:
    client = BdmClient(load_config())
    try:
        res = await client.search_estremi(
            numero=args.numero, anno=args.anno or None,
            ufficio=args.ufficio or None, tipo=args.tipo or None, size=args.size,
        )
        items = res.get("items") or []
        print(f"count totale: {res.get('count')} — mostro {len(items)}:")
        for i, it in enumerate(items, 1):
            print(f"  [{i}] id={it.get('id')}")
            print(f"       {extract.estremo(it)}  (del {it.get('data') or ''}, pubbl. {it.get('data_pubblicazione') or ''})  [{it.get('materia') or ''}]")
        if not items:
            print("(nessun risultato per gli estremi indicati)")
            return 1
        if (args.get or args.dir) and len(items) == 1:
            print("-> un solo risultato: ne recupero il testo.")
            it = items[0]
            text = extract.normalize_text(await client.get_text(it["id"]))
            fname = extract.safe_filename(args.name or extract.default_filename(it))
            if args.dir:
                destdir = Path(args.dir); destdir.mkdir(parents=True, exist_ok=True)
                out = destdir / (fname + ".md")
                out.write_text(extract.provvedimento_md(extract.item_meta(it), text), encoding="utf-8")
                print(f"SALVATO {out}  ({len(text)} char)")
            else:
                print(); print(extract.md_header(extract.item_meta(it))); print(); print(text[: args.max_chars])
        elif (args.get or args.dir):
            print("Più di un risultato: affina con --ufficio/--tipo, poi 'bdm get <id>'.")
        return 0
    except (BdmAuthError, BdmError) as exc:
        print(f"ERRORE: {exc}", file=sys.stderr)
        return 2
    finally:
        await client.aclose()


def _login(args) -> int:
    from .auth import BdmLoginError, login
    try:
        login(timeout_s=args.timeout)
    except BdmLoginError as exc:
        print(f"ERRORE login: {exc}", file=sys.stderr)
        return 2
    return 0


async def _check(args) -> int:
    cfg = load_config()
    if not cfg.is_authenticated:
        print("Sessione assente. Esegui: bdm login")
        return 1
    client = BdmClient(cfg)
    try:
        info = await client.check_session()
        print(f"Sessione OK — utente: {info.get('utente')} | exp: {info.get('exp')}")
        inviati = info.get("cookie_inviati") or []
        print(f"Cookie inviati ({len(inviati)}): {', '.join(inviati) or '(nessuno)'}")
        return 0
    except BdmAuthError as exc:
        print(f"Sessione SCADUTA: {exc}")
        # Diagnosi: se i cookie partiti sono pochi o manca il JWT, il problema non e'
        # la scadenza ma la selezione dei cookie (forzabile con BDM_COOKIE_NAMES).
        inviati = cfg.data_cookie_names()
        print(f"Cookie inviati ({len(inviati)}): {', '.join(inviati) or '(nessuno)'}")
        if not any("jwt" in n.lower() for n in inviati):
            print("ATTENZIONE: tra i cookie inviati non c'e' un JWT: rifai il login.")
        return 1
    except BdmError as exc:
        print(f"Errore: {exc}")
        return 2
    finally:
        await client.aclose()


def main(argv=None) -> int:
    _force_utf8_stdio()
    parser = argparse.ArgumentParser(prog="bdm", description="Connettore Banca Dati di Merito (bdp.giustizia.it).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_login = sub.add_parser("login", help="Login da browser (CNS) e cattura della sessione.")
    p_login.add_argument("--timeout", type=int, default=300)
    p_login.set_defaults(func=_login)

    p_search = sub.add_parser("search", help="Ricerca full-text (campo ampio, su anonymized_testo).")
    p_search.add_argument("text", nargs="?", default="", help="Testo libero (full-text su anonymized_testo).")
    p_search.add_argument("--ufficio", default="")
    p_search.add_argument("--materia", default="")
    p_search.add_argument("--size", type=int, default=10)
    p_search.set_defaults(func=lambda a: asyncio.run(_search(a)))

    p_est = sub.add_parser("estremi", help="Ricerca per estremi (numero/anno/ufficio/tipo) — caso principale.")
    p_est.add_argument("--numero", required=True, help="Numero del provvedimento, es. 941.")
    p_est.add_argument("--anno", default="", help="Anno del provvedimento, es. 2026.")
    p_est.add_argument("--ufficio", default="", help="Ufficio esatto, es. 'TRIBUNALE DI VERONA'.")
    p_est.add_argument("--tipo", default="", help="SENTENZA | ORDINANZA | DECRETO.")
    p_est.add_argument("--size", type=int, default=20)
    p_est.add_argument("--dir", default="", help="Se univoco, salva il .md qui.")
    p_est.add_argument("--name", default="")
    p_est.add_argument("--max-chars", type=int, default=20000, dest="max_chars")
    p_est.add_argument("--get", action="store_true", help="Se univoco, recupera subito il testo.")
    p_est.set_defaults(func=lambda a: asyncio.run(_estremi(a)))

    p_get = sub.add_parser("get", help="Recupera il testo integrale di un provvedimento per id.")
    p_get.add_argument("id")
    p_get.add_argument("--dir", default="", help="Cartella di destinazione (.md). Vuoto = stampa a video.")
    p_get.add_argument("--name", default="", help="Nome file senza estensione (default: dall'estremo).")
    p_get.add_argument("--max-chars", type=int, default=20000, dest="max_chars")
    p_get.set_defaults(func=lambda a: asyncio.run(_get(a)))

    p_check = sub.add_parser("check", help="Verifica la sessione (chiamata dati reale).")
    p_check.set_defaults(func=lambda a: asyncio.run(_check(a)))

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
