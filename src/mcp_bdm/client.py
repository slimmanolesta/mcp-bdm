"""Client REST/GraphQL per la Banca Dati di Merito (bdp.giustizia.it).

Rigioca server-side la sessione catturata al login (cookie JWT httpOnly) via httpx.
Contratto VERIFICATO dal vivo (14.7.2026). Dettagli non ovvi:

- TLS via trust store di Windows (`truststore`): certifi non ha la CA della PA.
- I data-endpoint vogliono una richiesta "da browser": UA Chrome reale + header
  `Sec-Fetch-*`, `Origin` solo sui POST (mai sui GET same-origin), e i soli cookie
  dati (DATA_COOKIE_NAMES). Con la sessione scaduta rispondono 401 (corpo vuoto o
  "jwt non presente"); ci mappiamo BdmAuthError.
- Ricerca = GraphQL `searchProvvedimento`; testo integrale = REST
  `provvedimento/{id}/document/testo` (testo piano, gia' pseudonimizzato).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from . import endpoints
from .config import AREA_DEFAULT, BdmConfig, ssl_context

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


class BdmError(RuntimeError):
    """Errore di comunicazione o di protocollo con la BDM."""


class BdmAuthError(BdmError):
    """Sessione scaduta o assente: serve un nuovo login (CNS)."""


class BdmClient:
    def __init__(self, config: BdmConfig) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None

    async def _ensure(self) -> httpx.AsyncClient:
        if self._client is None:
            self._config.require_auth()
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
                "Cookie": self._config.cookie_header(),
                "Referer": self._config.app_origin + "/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "User-Agent": self._config.user_agent,
                "sec-ch-ua": '"Chromium";v="150", "Google Chrome";v="150", "Not;A=Brand";v="8"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            }
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(40.0, connect=10.0),
                follow_redirects=False,
                verify=ssl_context(),
            )
        return self._client

    def _auth_failed(self, resp: httpx.Response) -> bool:
        if resp.status_code in (401, 403):
            return True
        # alcune risposte 200/500 mascherano la mancanza di sessione nel corpo
        return "jwt non presente" in (resp.text or "")[:60].lower()

    async def _get(self, path: str) -> Any:
        client = await self._ensure()
        try:
            resp = await client.get(self._config.endpoint(path))
        except httpx.HTTPError as exc:
            raise BdmError(f"GET {path} fallita: {exc}") from exc
        if self._auth_failed(resp):
            raise BdmAuthError("sessione BDM scaduta o assente. Esegui: bdm login (o 'Rinnova BDM').")
        if resp.status_code >= 400:
            raise BdmError(f"GET {path} -> HTTP {resp.status_code}: {(resp.text or '')[:200]}")
        return resp

    async def _graphql(self, operation: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        client = await self._ensure()
        payload = {"operationName": operation, "variables": variables, "query": query}
        try:
            resp = await client.post(
                self._config.endpoint(endpoints.EP_GRAPHQL),
                json=payload,
                headers={"Content-Type": "application/json", "Origin": self._config.app_origin},
            )
        except httpx.HTTPError as exc:
            raise BdmError(f"GraphQL {operation} fallita: {exc}") from exc
        if self._auth_failed(resp):
            raise BdmAuthError("sessione BDM scaduta o assente. Esegui: bdm login (o 'Rinnova BDM').")
        if resp.status_code >= 400:
            raise BdmError(f"GraphQL {operation} -> HTTP {resp.status_code}: {(resp.text or '')[:200]}")
        try:
            data = resp.json()
        except ValueError as exc:
            raise BdmError(f"risposta GraphQL non-JSON: {(resp.text or '')[:200]}") from exc
        if data.get("errors"):
            raise BdmError(f"errori GraphQL: {data['errors']}")
        return data.get("data") or {}

    # --- Sessione -------------------------------------------------------------
    async def check_session(self) -> dict[str, Any]:
        """Verifica VERA: una chiamata dati reale (user/current torna 200 anche da
        non loggato, quindi non basta). Usa `materia?area` come sonda leggera."""
        await self._get(endpoints.EP_MATERIA + f"?area={AREA_DEFAULT}")
        return {"ok": True, "utente": self._config.user, "exp": self._config.token_expiration}

    # --- Ricerca --------------------------------------------------------------
    async def search(
        self,
        testo: str = "",
        *,
        numero: str | int | None = None,
        anno: str | int | None = None,
        numero_ruolo: str | int | None = None,
        anno_ruolo: str | int | None = None,
        ufficio: str | None = None,
        tipo: str | None = None,
        materia: str | None = None,
        parola_chiave: str | None = None,
        area: str = AREA_DEFAULT,
        size: int = 10,
        from_: int = 0,
        sort_field: str | None = None,
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        """Cerca provvedimenti. `testo` -> full-text su `anonymized_testo` (parole in
        AND); gli altri vincolano per estremi/faccetta. Ritorna {count, items:[...]}.
        Senza criteri = ultimi depositati.

        Ordinamento: se `sort_field` non e' passato, per una ricerca a TESTO usa la
        RILEVANZA (`_score`, verificato), altrimenti la data di pubblicazione."""
        q = endpoints.build_q_expression(
            testo=testo, numero=numero, anno=anno, numero_ruolo=numero_ruolo,
            anno_ruolo=anno_ruolo, ufficio=ufficio, tipo=tipo, materia=materia,
            parola_chiave=parola_chiave,
        )
        if sort_field is None:
            sort_field = "_score" if testo else "data_pubblicazione"
        variables = {
            "from": max(0, int(from_)), "size": max(1, min(int(size), 50)),
            "area": area, "sort_field": sort_field, "sort_order": sort_order,
        }
        query = endpoints.build_last_query()
        if q:
            variables["q"] = q
            query = endpoints.build_search_query()
        op = "searchProvvedimento" if q else "lastProvvedimento"
        data = await self._graphql(op, query, variables)
        prov = data.get("provvedimento") or {}
        return {"count": prov.get("count"), "items": prov.get("items") or []}

    async def search_estremi(
        self,
        numero: str | int,
        anno: str | int | None = None,
        *,
        ufficio: str | None = None,
        tipo: str | None = None,
        size: int = 20,
    ) -> dict[str, Any]:
        """Ricerca per estremi (il caso d'uso principale): dato numero (+ anno,
        ufficio, tipo) trova il provvedimento specifico. Ordina per data, cosi'
        numero+anno da soli restituiscono i candidati da disambiguare per ufficio."""
        return await self.search(
            numero=numero, anno=anno, ufficio=ufficio, tipo=tipo,
            size=size, sort_field="data", sort_order="desc",
        )

    async def get_text(self, doc_id: str | int) -> str:
        """Testo integrale (piano, pseudonimizzato) del provvedimento."""
        resp = await self._get(endpoints.doc_text_path(doc_id))
        return resp.text or ""

    async def get_meta(self, doc_id: str | int) -> dict[str, Any]:
        """Metadati di un provvedimento per id (per nome file + intestazione)."""
        data = await self._graphql(
            "viewProvvedimento", endpoints.build_view_query(),
            {"id": [str(doc_id)], "area": AREA_DEFAULT},
        )
        items = (data.get("provvedimento") or {}).get("items") or []
        return items[0] if items else {}

    async def taxonomy(self, name: str, area: str = AREA_DEFAULT) -> Any:
        resp = await self._get(f"{name}?area={area}")
        try:
            return resp.json()
        except ValueError:
            return resp.text

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
