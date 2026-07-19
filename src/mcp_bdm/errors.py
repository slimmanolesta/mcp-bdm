"""Eccezioni del connettore.

Vivono qui, e non in `client.py`, perche' anche `config.py` deve poterle sollevare
senza dipendere dal client (che a sua volta importa la config: sarebbe un ciclo).

Attenzione alla gerarchia: `BdmAuthError` DERIVA da `BdmError`, quindi un
`except BdmError` cattura anche l'errore di sessione. Il contrario non vale: un
`RuntimeError` nudo NON viene catturato da `except BdmError` e arriva all'utente
come traceback. Per questo la mancanza di sessione solleva BdmAuthError.
"""

from __future__ import annotations


class BdmError(RuntimeError):
    """Errore di comunicazione o di protocollo con la BDM."""


class BdmAuthError(BdmError):
    """Sessione scaduta o assente: serve un nuovo login (CNS)."""
