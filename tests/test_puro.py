"""Test delle funzioni pure: niente rete, niente CNS, niente sessione.

Perche' esistono: ognuno di questi test corrisponde a un bug REALE trovato in
revisione. Sono la rete di sicurezza per le modifiche future (spesso fatte con
l'aiuto dell'AI): se una di queste proprieta' si rompe, la rottura si vede qui
invece che sul PC di un collega.

    python -m pytest tests/ -q
"""

from __future__ import annotations

import os
import tempfile

import pytest

from mcp_bdm import config as cfg
from mcp_bdm import extract as ex
from mcp_bdm.client import BdmAuthError, BdmError


@pytest.fixture(autouse=True)
def _isola(monkeypatch):
    """Ogni test in una cartella dati sua: mai toccare la config vera."""
    monkeypatch.setenv("BDM_HOME", tempfile.mkdtemp())


# --- eccezioni ---------------------------------------------------------------

def test_sessione_assente_e_un_errore_gestibile():
    """BUG: era un RuntimeError nudo -> non catturato da `except BdmError`,
    l'utente vedeva un traceback al primo comando."""
    with pytest.raises(BdmAuthError):
        cfg.BdmConfig().require_auth()
    assert issubclass(BdmAuthError, BdmError)


# --- citazione e nome file ---------------------------------------------------

@pytest.mark.parametrize("ufficio, atteso", [
    ("CORTE DI APPELLO DI BARI", "Corte di Appello di Bari"),
    ("TRIBUNALE DI VERONA", "Tribunale di Verona"),
    ("CORTE D'APPELLO DI BARI", "Corte d'Appello di Bari"),
])
def test_estremo_e_una_citazione_forense(ufficio, atteso):
    """BUG: str.title() produceva 'Corte Di Appello Di Bari' (preposizioni
    maiuscole) in una stringa che e' una CITAZIONE mostrata a un avvocato."""
    item = {"ufficio": ufficio, "tipo": "SENTENZA",
            "numero_provvedimento": "941", "anno_provvedimento": "2026"}
    assert ex.estremo(item) == f"{atteso}, sent. 941/2026"


def test_nome_file_non_maciulla_il_numero():
    """BUG: la barra di 1234/2024 diventava '_' -> '1234_2024', che sembra un refuso."""
    item = {"ufficio": "TRIBUNALE DI VERONA", "tipo": "SENTENZA",
            "numero_provvedimento": "1234", "anno_provvedimento": "2024"}
    nome = ex.safe_filename(ex.default_filename(item))
    assert "1234-2024" in nome and "1234_2024" not in nome


@pytest.mark.parametrize("cattivo", ["..\\..\\evil", "C:/x/y", "../../etc/passwd"])
def test_safe_filename_neutralizza_la_traversal(cattivo):
    """Il nome file puo' arrivare da un modello: non deve poter uscire dalla cartella."""
    pulito = ex.safe_filename(cattivo)
    assert "/" not in pulito and "\\" not in pulito


# --- preferenze di flusso ----------------------------------------------------

def test_aggiornamento_parziale_non_azzera_le_altre_preferenze():
    """BUG: `biblioteca` tornava a False a ogni aggiornamento parziale, in silenzio."""
    cfg.save_workflow({"organizzazione": "per_pratica",
                       "cartella_radice": r"C:\Studio", "biblioteca": True})
    cfg.save_workflow({"cartella_radice": r"D:\Studio2"})  # cambio solo la cartella
    dopo = cfg.load_workflow()
    assert dopo["biblioteca"] is True
    assert dopo["organizzazione"] == "per_pratica"
    assert dopo["cartella_radice"] == r"D:\Studio2"


def test_primo_avvio_e_file_corrotto_non_si_confondono():
    """BUG: un file troncato leggeva come {} = 'primo avvio', e l'onboarding
    sovrascriveva quel che restava."""
    assert cfg.load_workflow() == {}                      # davvero primo avvio
    p = cfg.workflow_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"organizzazione": "per_prat', encoding="utf-8")  # troncato
    assert cfg.load_workflow().get("_stato") == "corrotto"


def test_le_chiavi_di_servizio_non_finiscono_nel_file():
    cfg.save_workflow({"organizzazione": "archivio_unico"})
    assert "_stato" not in cfg.load_workflow()


# --- confinamento della scrittura --------------------------------------------

def test_scrittura_confinata_alla_radice_configurata():
    """BUG: `cartella` arriva dal modello e non era vincolata: una cartella
    allucinata poteva far scrivere ovunque (es. sopra un _SCHEDA.md)."""
    from mcp_bdm import server

    radice = tempfile.mkdtemp()
    cfg.save_workflow({"cartella_radice": radice})

    dentro, err = server._resolve_dest(os.path.join(radice, "Rossi c. Bianchi"))
    assert err == "" and dentro is not None

    relativa, err = server._resolve_dest("Rossi c. Bianchi")   # risolta nella radice
    assert err == "" and str(relativa).startswith(str(radice))

    _, err = server._resolve_dest(r"C:\Windows\System32")      # fuori: rifiutata
    assert err != ""

    _, err = server._resolve_dest(os.path.join(radice, "..", "altrove"))
    assert err != ""


def test_non_sovrascrive_un_file_esistente():
    """BUG: un nome allucinato (es. '_SCHEDA') calpestava un file dell'utente."""
    from pathlib import Path

    from mcp_bdm import server

    d = Path(tempfile.mkdtemp())
    (d / "_SCHEDA.md").write_text("contenuto dell'utente", encoding="utf-8")
    scelto = server._unique_path(d, "_SCHEDA")
    assert scelto.name == "_SCHEDA (2).md"
    assert (d / "_SCHEDA.md").read_text(encoding="utf-8") == "contenuto dell'utente"


# --- costruzione della query -------------------------------------------------

def test_full_text_mette_le_parole_in_AND():
    """Piu' parole devono RESTRINGERE. In OR la ricerca allargava (152.870 vs 23.909)."""
    from mcp_bdm import endpoints

    q = endpoints.build_q_expression(testo="usucapione servitu")
    assert q.count("anonymized_testo") == 2 and " AND " in q


def test_le_virgolette_non_possono_iniettare_criteri():
    from mcp_bdm import endpoints

    q = endpoints.build_q_expression(testo='foo" OR ufficio:"X')
    assert q.count('"') % 2 == 0


# --- selezione dei cookie ----------------------------------------------------

def _jar():
    """Jar realistico, modellato su una cattura vera + un cookie NUOVO del
    bilanciatore (il caso che faceva morire la vecchia allowlist)."""
    return [
        {"name": "jwt_bdm_frontoffice", "value": "x", "domain": ".bdp.giustizia.it"},
        {"name": "cookiesession1", "value": "x", "domain": "bdp.giustizia.it"},
        {"name": "cookie_accepted", "value": "x", "domain": "bdp.giustizia.it"},
        {"name": "fd2d18de29089600045cac71baad0355", "value": "x", "domain": "bdp.giustizia.it"},
        {"name": "13f03f665dc4ad927d5708f00b44987b", "value": "x", "domain": "bdp.giustizia.it"},
        {"name": "a1b2c3d4e5f60718293a4b5c6d7e8f90", "value": "x", "domain": "bdp.giustizia.it"},
        {"name": "x-ms-cpim-sso:b2c_0", "value": "x", "domain": ".auth03.giustizia.it"},
        {"name": "x-ms-cpim-csrf", "value": "x", "domain": ".auth03.giustizia.it"},
        {"name": "_pk_id.abc.123", "value": "x", "domain": "auth03.giustizia.it"},
        {"name": "estraneo", "value": "x", "domain": "altro-sito.it"},
    ]


def test_nessuna_regressione_rispetto_alla_vecchia_allowlist():
    """La denylist deve mandare ALMENO quel che mandava l'allowlist: e' la garanzia
    che il cambio non rompa un'autenticazione che funzionava."""
    inviati = set(cfg.BdmConfig(cookies=_jar()).data_cookie_names())
    presenti = {c["name"] for c in _jar()} & cfg.LEGACY_ALLOWLIST
    assert presenti <= inviati


def test_manda_anche_i_cookie_nuovi_del_dominio_dati():
    """BUG: l'allowlist veniva da UNA cattura. Un cookie aggiunto o rinominato dal
    sito veniva scartato in silenzio -> 401 subito dopo un login riuscito, in loop,
    non diagnosticabile. Il cookie nuovo deve partire."""
    inviati = cfg.BdmConfig(cookies=_jar()).data_cookie_names()
    assert "a1b2c3d4e5f60718293a4b5c6d7e8f90" in inviati


@pytest.mark.parametrize("scartato", [
    "x-ms-cpim-sso:b2c_0",   # nome malformato: romperebbe l'header
    "x-ms-cpim-csrf",        # roba del portale di autenticazione
    "_pk_id.abc.123",        # dominio diverso (auth03, non bdp)
    "estraneo",              # tutt'altro sito
])
def test_scarta_cio_che_non_va_ai_data_endpoint(scartato):
    assert scartato not in cfg.BdmConfig(cookies=_jar()).data_cookie_names()


def test_l_header_non_contiene_mai_nomi_malformati():
    header = cfg.BdmConfig(cookies=_jar()).cookie_header()
    assert "x-ms-cpim" not in header


def test_override_di_emergenza(monkeypatch):
    """Via di fuga se un giorno servisse forzare la selezione a mano."""
    monkeypatch.setenv("BDM_COOKIE_NAMES", "jwt_bdm_frontoffice")
    assert cfg.BdmConfig(cookies=_jar()).data_cookie_names() == ["jwt_bdm_frontoffice"]


def test_bdm_home_esplicito_non_migra_i_dati(monkeypatch, tmp_path):
    """BUG (colpito dal vivo): la migrazione scattava anche con BDM_HOME impostato,
    e una cartella temporanea di prova si portava via la sessione vera."""
    monkeypatch.setenv("BDM_HOME", str(tmp_path))
    legacy = cfg._legacy_app_dir() / "config.json"
    esisteva = legacy.exists()
    cfg.config_path()
    assert legacy.exists() == esisteva
