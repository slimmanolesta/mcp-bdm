# mcp-bdm

Connettore casalingo per la **Banca Dati di Merito** pubblica del Ministero
(`bdp.giustizia.it`), pensato per essere pilotato da un assistente AI (Claude).

> **Skill inclusa.** Questo repo contiene la skill Claude **manolesta**
> (in `skill/manolesta/`), che pilota il connettore `bdm` per cercare e
> recuperare provvedimenti dalla BDM.
Backend **REST + GraphQL** (`/api/bdm/frontoffice/...`), autenticazione con **JWT
di sessione in cookie httpOnly**, depositato dopo il login **CNS** (chiavetta +
PIN) sul portale B2C del Ministero. La chiavetta serve solo a *ottenere* la
sessione: le ricerche girano poi server-side rigiocando la sessione via httpx.

Forma **ibrida**: un solo motore, due facce.

- **CLI** (`bdm …`) — tirare giù un provvedimento come `.md` pulito in una
  cartella, senza bruciare il contesto del modello.
- **MCP sottile** (`bdm-mcp`) — `bdm_search` / `bdm_get_provvedimento` /
  `bdm_check_session` per la consultazione rapida inline.

## ⚠️ Non è plug-and-play — è un riferimento «ecco come si fa»

Questo repo è pubblicato come **riferimento** per chi vuole capire *come* si
interroga la BDM da codice, non come tool pronto all'uso. Per farlo girare serve:

- **Windows** (il TLS verso la PA usa il trust store di sistema via `truststore`;
  su Linux/macOS va adattato);
- **Python 3.10+**;
- un **login CNS proprio** (chiavetta + PIN): l'autenticazione è personale e non è
  automatizzabile né condivisibile;
- **adattare i path** e le variabili d'ambiente al proprio ambiente.

Aspettati di dover mettere le mani nel codice. È materiale di studio, non un
prodotto.

## Stato — funzionante (nucleo verificato end-to-end in rete)

Nucleo CLI verificato **end-to-end in rete** (`check`, `search`, `get`, `estremi`).

**Contratto verificato dal vivo:**
- **Auth = replay del cookie** (`jwt_bdm_frontoffice` + cookie di sessione), via
  httpx. Nessun header Authorization: i data-endpoint vogliono una richiesta "da
  browser" — UA Chrome reale + `Sec-Fetch-Site: same-origin`, `Origin` solo sui
  POST. TLS via **trust store di Windows** (`truststore`): certifi non ha la CA
  della PA. Con la sessione scaduta i protetti danno `401` → `BdmAuthError`.
- **Ricerca = GraphQL** (`/api/bdm/frontoffice/graphql`, operazione
  `searchProvvedimento`) su `provvedimento(from,size,area,q,sort_field,sort_order)`.
  `area="CIVILE"`. **`q` NON è testo libero**: è una query-string `campo:"testo"`
  unita con ` AND ` (come `filterExpressionToString` della SPA); il full-text sul
  testo del provvedimento è **`anonymized_testo:"..."`**. I `*/filter` REST NON
  sono la ricerca: sono il CRUD dei filtri salvati.
- **Testo integrale = REST** `GET provvedimento/{id}/document/testo` → testo piano,
  **pseudonimizzato** all'origine (le parti diventano `Parte_1`, `C.F._1`…).
- **Tassonomie**: `GET materia?area=CIVILE`, `ufficio`, `giudice`, ecc.
- **Durata sessione ~120 min**: captured_at→exp = 2 ore. Il replay regge per tutta
  la finestra; a scadenza serve il re-login CNS (`Rinnova-BDM.bat`).

**Residui (follow-up, non bloccanti):**
- Registrazione MCP in `claude_desktop_config.json` + allowlist. Il **CLI funziona
  già** senza registrazione.
- Rifinire i nomi-campo delle faccette in `q` (`UFFICIO`/`MATERIA` maiuscoli sono
  ipotesi da confermare; il full-text `anonymized_testo` è verificato).

## Uso

```
# login (apre il browser; l'accesso CNS è manuale, le credenziali non passano dallo script)
python -m mcp_bdm login          # oppure: Rinnova-BDM.bat

# verifica sessione (chiamata dati reale)
python -m mcp_bdm check

# ricerca full-text
python -m mcp_bdm search "usucapione" --size 10

# ricerca per estremi (numero + anno + eventuale ufficio)
python -m mcp_bdm estremi --numero 1234 --anno 2024 --ufficio "TRIBUNALE DI VERONA"

# recupero testo integrale per id, salvato in una cartella
python -m mcp_bdm get <id> --dir "C:\percorso\alla\cartella"
```

(con `pip install -e .` i comandi diventano `bdm …` / `bdm-mcp`.)

## Config

La sessione vive in `config.json` (fuori da git, permessi 0600), creato da `login`:
il **cookie jar** catturato (col JWT httpOnly), `exp`, l'utente (per display). Il
client manda ai data-endpoint solo i cookie utili (`DATA_COOKIE_NAMES`), non i
cookie B2C/SSO. Override via `BDM_API_BASE`, `BDM_HOME`, ecc.; profilo di login via
`BDM_LOGIN_PROFILE`, debug con `BDM_LOGIN_DEBUG=1`. Parti da `config.example.json`.

## Dipendenze runtime

`httpx`, `truststore` (TLS via store di Windows). Per il login: `playwright`.
Per l'MCP: `mcp`.

## Note di sicurezza e di uso

Il JWT è un segreto (file 0600, mai stampato per intero). La BDM è pubblica e
gratuita, i testi sono **pseudonimizzati** all'origine. Uso previsto =
**consultazione mirata con la propria sessione**, come farebbe un umano: **niente
scraping massivo**. Copre la sola giurisprudenza **civile di merito** (Tribunali e
Corti d'Appello, dal 2016; esclude Cassazione/amministrativo/costituzionale e
famiglia/minori/stato delle persone).

## Licenza

[MIT](LICENSE).
