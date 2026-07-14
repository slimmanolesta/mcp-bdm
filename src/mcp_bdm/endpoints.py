"""Contratto REST/GraphQL del frontoffice BDM — VERIFICATO dal vivo (14.7.2026).

Recon: la ricerca gira su GraphQL (Apollo, `/api/bdm/frontoffice/graphql`), NON sui
`*/filter` REST (che sono il CRUD dei filtri salvati). Il testo integrale e' un REST
dedicato. Fatti chiave fissati dal traffico reale:

- Ricerca provvedimenti: operazione GraphQL `searchProvvedimento` sul campo
  `provvedimento(from,size,area,q,sort_field,sort_order)`.
- `area` = "CIVILE" (macro-area unica della BDM).
- `q` NON e' testo libero: e' una query-string tipo `campo:"testo"` unita con
  ` AND ` (la SPA la costruisce con `filterExpressionToString`, template
  `${acc} AND ${type}:"${text}"`). Il campo per il full-text sul testo del
  provvedimento e' **`anonymized_testo`** (lowercase, testo tra virgolette):
  `anonymized_testo:"usucapione"` -> count 96387 (verificato).
- Ordinamento visto: sort_field="data_pubblicazione", sort_order="desc".
- Testo integrale: GET `provvedimento/{id}/document/testo` -> testo piano
  (gia' pseudonimizzato all'origine).
"""

from __future__ import annotations

# --- Endpoint REST (path relativi ad api_base) --------------------------------
EP_GRAPHQL = "graphql"
EP_USER_CURRENT = "user/current"
EP_MATERIA = "materia"                 # GET ?area=CIVILE
EP_UFFICIO = "ufficio"
EP_GIUDICE = "giudice"
EP_RIFERIMENTO_NORMATIVO = "riferimento_normativo"
EP_PAROLA_CHIAVE = "parola_chiave"


def doc_text_path(doc_id: str | int) -> str:
    """REST: testo integrale (piano) del provvedimento."""
    return f"provvedimento/{doc_id}/document/testo"


# --- Campi restituiti dagli item di ricerca (fragment minimale, senza gql) ----
PROVV_FIELDS = (
    "id tipo numero_provvedimento anno_provvedimento numero_ruolo anno_ruolo "
    "ufficio data data_pubblicazione materia estratto riferimento_normativo parola_chiave"
)

# Nomi-campo per la query-string `q` — VERIFICATI dal vivo (14.7.2026): tutti
# LOWERCASE e col valore tra virgolette. `UFFICIO` maiuscolo NON filtra.
#   anonymized_testo -> full-text sul testo (count 96387 per "usucapione")
#   numero_provvedimento + anno_provvedimento + ufficio -> per estremi (count 1)
# `tipo` = SENTENZA/ORDINANZA/DECRETO. materia/parola_chiave = stringhe di tassonomia.
Q_FIELDS = {
    "testo": "anonymized_testo",
    "numero": "numero_provvedimento",
    "anno": "anno_provvedimento",
    "numero_ruolo": "numero_ruolo",
    "anno_ruolo": "anno_ruolo",
    "ufficio": "ufficio",
    "tipo": "tipo",
    "materia": "materia",
    "parola_chiave": "parola_chiave",
    "riferimento_normativo": "riferimento_normativo",
}


def _quote(text: str) -> str:
    return '"' + str(text).replace('"', "") + '"'


# Parole vuote da NON trasformare in criterio autonomo nel full-text: da sole
# matcherebbero (quasi) tutto il DB. ES le tratta gia' come stopword, ma evitiamo
# di generare clausole inutili.
_STOPWORDS = frozenset({
    "e", "di", "a", "da", "in", "con", "su", "per", "tra", "fra", "il", "lo", "la",
    "i", "gli", "le", "un", "uno", "una", "del", "dello", "della", "dei", "degli",
    "delle", "al", "allo", "alla", "ai", "agli", "alle", "dal", "dalla", "nel",
    "nella", "che", "chi", "cui", "non", "o", "ed", "od", "come", "se",
})


def _testo_clauses(testo: str) -> list[str]:
    """Full-text: NB il campo `anonymized_testo` tokenizza e va in OR sulle parole
    dentro le virgolette (verificato: "usucapione servitù" -> PIU' risultati). Per
    una ricerca a TEMA che RESTRINGE, ogni parola significativa diventa un criterio
    a se' unito con AND (`anonymized_testo:"w1" AND anonymized_testo:"w2"`)."""
    field = Q_FIELDS["testo"]
    toks = [t for t in str(testo).split() if len(t) >= 3 and t.lower() not in _STOPWORDS]
    if not toks:  # solo stopword/parole cortissime: usa la stringa cosi' com'e'
        s = str(testo).strip()
        return [f"{field}:{_quote(s)}"] if s else []
    return [f"{field}:{_quote(t)}" for t in toks]


def build_q_expression(**criteri: object) -> str:
    """Costruisce la query-string `q` in sintassi BDM (`campo:"valore"` uniti da
    ` AND `). Accetta le chiavi logiche di Q_FIELDS (testo, numero, anno, ufficio,
    tipo, ...). Il `testo` full-text e' spezzato in parole in AND (vedi
    `_testo_clauses`). Vuota se nessun criterio (la ricerca senza `q` = 'ultimi')."""
    parts: list[str] = []
    testo = criteri.get("testo")
    if testo not in (None, ""):
        parts.extend(_testo_clauses(testo))  # type: ignore[arg-type]
    for key, field in Q_FIELDS.items():
        if key == "testo":
            continue
        val = criteri.get(key)
        if val not in (None, ""):
            parts.append(f"{field}:{_quote(val)}")
    return " AND ".join(parts)


def build_search_query() -> str:
    return (
        "query searchProvvedimento($from:Int,$size:Int,$area:String,$q:String,"
        "$sort_field:String,$sort_order:String){"
        " provvedimento(from:$from,size:$size,area:$area,q:$q,"
        "sort_field:$sort_field,sort_order:$sort_order){"
        f" count items {{ {PROVV_FIELDS} }} }} }}"
    )


def build_last_query() -> str:
    return (
        "query lastProvvedimento($from:Int,$size:Int,$area:String,"
        "$sort_field:String,$sort_order:String){"
        " provvedimento(from:$from,size:$size,area:$area,"
        "sort_field:$sort_field,sort_order:$sort_order){"
        f" count items {{ {PROVV_FIELDS} }} }} }}"
    )


def build_view_query() -> str:
    """Metadati di uno o piu' provvedimenti per id (per nome file + intestazione)."""
    return (
        "query viewProvvedimento($id:[String],$area:String){"
        " provvedimento(id:$id,area:$area){"
        f" count items {{ {PROVV_FIELDS} }} }} }}"
    )
