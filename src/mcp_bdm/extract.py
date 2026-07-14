"""Estrazione/formattazione dei metadati BDM.

Gli item di ricerca sono gia' JSON strutturato (id, tipo, numero/anno, ufficio,
data, materia, estratto). Il testo integrale arriva gia' come testo piano dal REST
`provvedimento/{id}/document/testo` (pseudonimizzato all'origine): niente parsing
HTML, solo una normalizzazione leggera degli spazi.
"""

from __future__ import annotations

import html as htmllib
import re
from typing import Any

_META_KEYS = (
    "id", "tipo", "numero_provvedimento", "anno_provvedimento",
    "numero_ruolo", "anno_ruolo", "ufficio", "data", "data_pubblicazione",
    "materia", "riferimento_normativo", "parola_chiave", "estratto",
)


def _clean(v: Any) -> Any:
    return htmllib.unescape(v).strip() if isinstance(v, str) else v


def normalize_text(t: str) -> str:
    if not t:
        return ""
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def estremo(item: dict[str, Any]) -> str:
    """Citazione leggibile: 'Tribunale di Locri, sent. 243/2023'."""
    if not isinstance(item, dict):
        return ""
    uff = _clean(item.get("ufficio")) or ""
    tipo = (_clean(item.get("tipo")) or "").lower()
    tabbr = {"sentenza": "sent.", "ordinanza": "ord.", "decreto": "decr."}.get(tipo, tipo)
    num = _clean(item.get("numero_provvedimento"))
    anno = _clean(item.get("anno_provvedimento"))
    coda = f"{tabbr} {num}/{anno}".strip() if num else ""
    parts = [p for p in (uff.title() if uff.isupper() else uff, coda) if p]
    return ", ".join(parts)


def item_meta(item: dict[str, Any]) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    es = estremo(item)
    if es:
        meta["estremo"] = es
    for k in _META_KEYS:
        v = item.get(k)
        if v in (None, "", []):
            continue
        meta[k] = _clean(v)
    return meta


def default_filename(item: dict[str, Any]) -> str:
    """Nome file intelligibile: preferisce l'estremo, poi l'id troncato."""
    es = estremo(item)
    if es:
        return es
    doc_id = str(item.get("id") or "")
    return f"provvedimento-{doc_id[:12]}" if doc_id else "provvedimento"
