"""Configurazione del connettore Banca Dati di Merito (bdp.giustizia.it).

Differenza rispetto a De Jure (JWT nell'header Authorization) e al WK (cookie +
CSRF): qui la SPA usa `withCredentials` e i protetti rispondono 401 "jwt non
presente". Il JWT vive quasi certamente in un COOKIE httpOnly depositato da
`/api/bdm/frontoffice/user/auth` dopo lo scambio del codice OAuth (login CNS sul
portale B2C del Ministero). Percio' la sorgente unica di autenticazione qui e' il
COOKIE JAR catturato dal browser al login (Playwright legge anche gli httpOnly).

Come rete di sicurezza salviamo anche un eventuale header Authorization
intercettato (`bearer`), nel caso una parte dell'API lo pretenda: in fase di
recon dal vivo si vedra' quale dei due porta davvero il JWT.

Sorgente unica: un config.json nella cartella dell'app.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

APP_ORIGIN = "https://bdp.giustizia.it"
API_BASE = "https://bdp.giustizia.it/api/bdm/frontoffice"
# Pagina da cui parte il login CNS (redirige sul portale B2C del Ministero).
LOGIN_URL = "https://bdp.giustizia.it/login"
# Macro-area unica della BDM (giurisprudenza civile di merito).
AREA_DEFAULT = "CIVILE"
# I soli cookie che il browser manda ai data-endpoint (esclude i cookie B2C/SSO
# di auth03.giustizia.it, inutili qui e col nome malformato che sporca l'header).
DATA_COOKIE_NAMES = frozenset({
    "jwt_bdm_frontoffice", "cookiesession1", "cookie_accepted",
    "fd2d18de29089600045cac71baad0355", "13f03f665dc4ad927d5708f00b44987b",
})

# UA di un Chrome reale: i data-endpoint vogliono una richiesta "da browser"
# (Sec-Fetch-Site: same-origin + UA credibile), non un client generico.
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
)


def ssl_context():
    """Contesto TLS che usa il trust store di Windows (via truststore): il cert di
    bdp.giustizia.it si ancora a una CA della PA che certifi non ha, ma Windows si'."""
    import ssl
    import truststore
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def app_dir() -> Path:
    """Cartella dove vive config.json. Override con BDM_HOME; in modalita' frozen
    accanto all'eseguibile; altrimenti la radice del progetto."""
    env = os.environ.get("BDM_HOME")
    if env:
        return Path(env)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]  # .../mcp-bdm


def config_path() -> Path:
    return app_dir() / "config.json"


@dataclass
class BdmConfig:
    # Cookie jar catturato al login: lista di dict {name, value, domain, path}.
    # E' qui che vive il JWT di sessione (cookie httpOnly).
    cookies: list[dict[str, Any]] = field(default_factory=list)
    # Rete di sicurezza: header Authorization grezzo, se l'API lo pretende.
    authorization: str = ""
    token_expiration: str = ""  # `exp` letto da user/current (o dal JWT)
    captured_at: str = ""
    user: str = ""  # upn/email dell'account, solo per display
    user_agent: str = _DEFAULT_UA
    api_base: str = API_BASE
    app_origin: str = APP_ORIGIN

    @property
    def is_authenticated(self) -> bool:
        return bool(self.cookies) or bool(self.authorization)

    def require_auth(self) -> None:
        if not self.is_authenticated:
            raise RuntimeError("Sessione BDM assente. Esegui prima: bdm login")

    def cookie_header(self, data_only: bool = True) -> str:
        """Serializza il jar in un header Cookie per httpx. Di default tiene solo i
        cookie che il browser manda ai data-endpoint (DATA_COOKIE_NAMES): esclude i
        cookie B2C/SSO col nome malformato (':') che rompono il parsing lato server."""
        return "; ".join(
            f"{c.get('name')}={c.get('value')}"
            for c in self.cookies
            if c.get("name") and c.get("value") is not None
            and (not data_only or c.get("name") in DATA_COOKIE_NAMES)
        )

    def endpoint(self, path: str) -> str:
        return self.api_base.rstrip("/") + "/" + path.lstrip("/")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def load_config() -> BdmConfig:
    data = _read_json(config_path())

    def pick(key: str, default: str = "") -> str:
        env = os.environ.get("BDM_" + key.upper())
        if env:
            return env
        val = data.get(key)
        return val if isinstance(val, str) and val else default

    cookies = data.get("cookies")
    if not isinstance(cookies, list):
        cookies = []

    return BdmConfig(
        cookies=cookies,
        authorization=pick("authorization"),
        token_expiration=pick("token_expiration"),
        captured_at=pick("captured_at"),
        user=pick("user"),
        user_agent=pick("user_agent", _DEFAULT_UA),
        api_base=pick("api_base", API_BASE),
        app_origin=pick("app_origin", APP_ORIGIN),
    )


def save_session(
    cookies: list[dict[str, Any]],
    authorization: str = "",
    token_expiration: str = "",
    captured_at: str = "",
    user: str = "",
    user_agent: str = "",
) -> Path:
    """Salva la sessione (segreta) in config.json con permessi 0600 dove possibile."""
    path = config_path()
    data = _read_json(path)
    data["cookies"] = cookies
    if authorization:
        data["authorization"] = authorization
    if token_expiration:
        data["token_expiration"] = token_expiration
    if captured_at:
        data["captured_at"] = captured_at
    if user:
        data["user"] = user
    if user_agent:
        data["user_agent"] = user_agent
    data.setdefault("api_base", API_BASE)
    data.setdefault("app_origin", APP_ORIGIN)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


# --- Configurazione di flusso dell'utente (onboarding manolesta) --------------
# Non sono segreti: dove salvare i provvedimenti, come nominarli, ecc. Vivono in un
# file separato dal config.json (che tiene la sessione), accanto ad esso.

def workflow_path() -> Path:
    return app_dir() / "manolesta.workflow.json"


def load_workflow() -> dict[str, Any]:
    """Preferenze di flusso dell'utente (vuoto = primo avvio, va fatto l'onboarding)."""
    return _read_json(workflow_path())


def save_workflow(prefs: dict[str, Any]) -> Path:
    """Salva/aggiorna le preferenze di flusso (merge). Ignora i valori stringa vuoti
    per non sovrascrivere con blank; i booleani vengono sempre scritti."""
    path = workflow_path()
    data = _read_json(path)
    data.update({k: v for k, v in prefs.items() if v != ""})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
