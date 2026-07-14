r"""Login interattivo Banca Dati di Merito: cattura la sessione dopo il login CNS.

Apre un browser (Chrome di preferenza, poi Edge); l'utente fa il login A MANO col
proprio dispositivo CNS (chiavetta + PIN) sul portale del Ministero — le
credenziali NON passano mai dallo script. Il flusso e' OAuth2/OpenID su Azure AD
B2C: dopo l'autenticazione il browser torna su
`/api/bdm/frontoffice/user/auth?code=...`, il backend scambia il codice e deposita
il JWT di sessione in un COOKIE (httpOnly).

Discriminante di "loggato" — robusto e host-agnostico: si interroga da soli
`/api/bdm/frontoffice/user/current`; finche' torna utente nullo la sessione non
c'e'; quando `upn`/`email` diventano non-null il login e' fatto. A quel punto si
fotografa il COOKIE JAR (Playwright vede anche gli httpOnly) e, per sicurezza, un
eventuale header Authorization visto sulle chiamate `/api/bdm/`.

Profilo PERSISTENTE di default: riusa la sessione tra un refresh e l'altro (finche'
il JWT e' valido, niente re-login) e resta isolato dal browser personale; vive in
<app_dir>/.browser-profile. Override via env BDM_LOGIN_PROFILE (un percorso per un
altro profilo; "" per il contesto effimero, re-login ogni volta).

NOTA (recon dal vivo): questo modulo e' cablato sul comportamento OSSERVATO da non
loggato (endpoint, 401 "jwt non presente", user/current con `exp`). Il nome esatto
del cookie del JWT NON e' noto a priori: per questo catturiamo l'INTERO jar, cosi'
il connettore funziona senza doverlo indovinare. Alla prima login vera si conferma
solo la durata reale della sessione (`exp`).
"""

from __future__ import annotations

import base64
import json
import os
import time
from datetime import datetime, timezone

from .config import APP_ORIGIN, LOGIN_URL, app_dir, save_session

_DEBUG = bool(os.environ.get("BDM_LOGIN_DEBUG"))
_profile_env = os.environ.get("BDM_LOGIN_PROFILE")
_PROFILE = str(app_dir() / ".browser-profile") if _profile_env is None else _profile_env.strip()

# JS eseguito nella pagina: interroga user/current con le credenziali (i cookie
# httpOnly viaggiano da soli) e riporta l'utente corrente. {} se non loggato.
_CURRENT_JS = """
async () => {
  try {
    const r = await fetch('/api/bdm/frontoffice/user/current', {credentials:'include'});
    if (!r.ok) return {status:r.status};
    return await r.json();
  } catch(e) { return {error:String(e)}; }
}
"""


class BdmLoginError(RuntimeError):
    pass


def _launch_persistent(p, user_data_dir: str):
    """Contesto persistente (profilo dedicato): Chrome, poi Edge, poi Chromium."""
    last_exc: Exception | None = None
    for ch in ("chrome", "msedge"):
        try:
            return p.chromium.launch_persistent_context(user_data_dir, headless=False, channel=ch)
        except Exception as exc:
            last_exc = exc
    try:
        return p.chromium.launch_persistent_context(user_data_dir, headless=False)
    except Exception as exc:
        raise BdmLoginError(_no_browser_msg(last_exc or exc)) from (last_exc or exc)


def _launch(p):
    """Browser effimero: Chrome, poi Edge, infine il Chromium di Playwright."""
    last_exc: Exception | None = None
    for ch in ("chrome", "msedge"):
        try:
            return p.chromium.launch(headless=False, channel=ch)
        except Exception as exc:
            last_exc = exc
    try:
        return p.chromium.launch(headless=False)
    except Exception as exc:
        raise BdmLoginError(_no_browser_msg(last_exc or exc)) from (last_exc or exc)


def _no_browser_msg(exc) -> str:
    return (
        "Nessun browser disponibile per il login (Chrome/Edge/Chromium). "
        "Installa Google Chrome, oppure (sviluppo) esegui: playwright install chromium. "
        f"Dettaglio: {exc}"
    )


def _user_of(current: dict) -> str:
    """Email/upn se user/current descrive un utente AUTENTICATO, altrimenti ''."""
    if not isinstance(current, dict):
        return ""
    for key in ("upn", "email", "name"):
        v = current.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _exp_of(current: dict) -> str:
    v = current.get("exp") if isinstance(current, dict) else None
    if v in (None, ""):
        return ""
    return str(v)


def _decode_jwt_exp(token: str) -> str:
    """Prova a leggere `exp` da un JWT grezzo (senza verificare la firma). ''."""
    if not token:
        return ""
    raw = token.split(" ", 1)[1] if token.lower().startswith("bearer ") else token
    parts = raw.split(".")
    if len(parts) < 2:
        return ""
    seg = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(seg))
    except Exception:
        return ""
    exp = payload.get("exp") if isinstance(payload, dict) else None
    return str(exp) if exp not in (None, "") else ""


def capture_session(timeout_s: float = 300) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise BdmLoginError(
            "Playwright non installato. Esegui: pip install playwright; playwright install"
        ) from exc

    captured = {"authorization": "", "ua": None}

    with sync_playwright() as p:
        if _PROFILE:
            try:
                ctx = _launch_persistent(p, _PROFILE)
                browser = None
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
            except BdmLoginError:
                print("[login] profilo persistente non disponibile; uso un contesto effimero.", flush=True)
                browser = _launch(p)
                ctx = browser.new_context()
                page = ctx.new_page()
        else:
            browser = _launch(p)
            ctx = browser.new_context()
            page = ctx.new_page()

        def _alive() -> bool:
            if page.is_closed():
                return False
            if browser is not None:
                return browser.is_connected()
            return len(ctx.pages) > 0

        def _close() -> None:
            try:
                (browser or ctx).close()
            except Exception:
                pass

        def on_request(req):
            # Rete di sicurezza: se una chiamata /api/bdm/ porta un header
            # Authorization, lo teniamo (nel caso l'API lo pretenda oltre al cookie).
            try:
                if "/api/bdm/" in req.url:
                    a = req.headers.get("authorization")
                    if a and a.lower() != "bearer":
                        captured["authorization"] = a
                        captured["ua"] = req.headers.get("user-agent")
            except Exception:
                pass

        ctx.on("request", on_request)
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        print(
            ">>> FAI IL LOGIN sulla Banca Dati di Merito nella finestra del browser\n"
            "    (accesso con CNS: inserisci la chiavetta e digita il PIN quando richiesto).\n"
            f"    Attendo il completamento dell'accesso (max {int(timeout_s)}s)...",
            flush=True,
        )

        t0 = time.monotonic()
        deadline = t0 + timeout_s
        current: dict = {}
        user = ""
        while time.monotonic() < deadline:
            if not _alive():
                raise BdmLoginError("Finestra del browser chiusa prima di completare il login.")
            try:
                current = page.evaluate(_CURRENT_JS) or {}
            except Exception:
                current = {}
            user = _user_of(current)
            if _DEBUG:
                print(
                    f"[dbg] +{int(time.monotonic() - t0):>3}s url={page.url[:55]!r} "
                    f"user={user or '-'} exp={_exp_of(current) or '-'} "
                    f"auth_hdr={'Y' if captured['authorization'] else 'N'}",
                    flush=True,
                )
            if user:
                break
            time.sleep(1.5)

        if not user:
            _close()
            raise BdmLoginError(
                "Login autenticato non rilevato entro il timeout (user/current resta "
                "vuoto). Hai completato l'accesso con la CNS?"
            )

        # Fotografa il jar: tutti i cookie del dominio bdp.giustizia.it (incluso
        # il JWT httpOnly). Playwright espone anche gli httpOnly.
        try:
            all_cookies = ctx.cookies()
        except Exception:
            all_cookies = []
        cookies = [
            {
                "name": c.get("name"),
                "value": c.get("value"),
                "domain": c.get("domain"),
                "path": c.get("path", "/"),
            }
            for c in all_cookies
            if isinstance(c, dict) and "giustizia.it" in str(c.get("domain", ""))
        ]

        exp = _exp_of(current) or _decode_jwt_exp(captured["authorization"])
        print(
            f"[login] +{int(time.monotonic() - t0)}s sessione catturata "
            f"(utente: {user}; cookie: {len(cookies)}; exp: {exp or 'n/d'}).",
            flush=True,
        )
        _close()

    return {
        "cookies": cookies,
        "authorization": captured["authorization"],
        "user": user,
        "expiration": exp,
        "ua": captured["ua"],
    }


def login(timeout_s: float = 300) -> dict:
    cap = capture_session(timeout_s)
    now = datetime.now(timezone.utc).isoformat()
    path = save_session(
        cookies=cap["cookies"],
        authorization=cap.get("authorization", ""),
        token_expiration=cap.get("expiration", ""),
        captured_at=now,
        user=cap.get("user", ""),
        user_agent=cap.get("ua", "") or "",
    )
    print(
        f"[login] sessione salvata | utente='{cap.get('user')}' | "
        f"cookie={len(cap['cookies'])} | -> {path}",
        flush=True,
    )
    if cap.get("expiration"):
        print(f"[login] scadenza sessione (exp): {cap['expiration']}", flush=True)
    return {
        "saved_to": str(path),
        "user": cap.get("user", ""),
        "cookies": len(cap["cookies"]),
        "expiration": cap.get("expiration", ""),
    }
