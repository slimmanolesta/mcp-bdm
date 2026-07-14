---
name: ricerca-bdm
description: >-
  Cerca e recupera il testo integrale di provvedimenti di merito civile
  (sentenze/ordinanze/decreti di Tribunali e Corti d'Appello, dal 2016,
  pseudonimizzati) sulla Banca Dati di Merito pubblica del Ministero
  (bdp.giustizia.it), tramite il connettore casalingo `bdm` (C:\Tools\mcp-bdm).
  USA SEMPRE questa skill quando l'utente vuole cercare/recuperare/"tirare giù"
  giurisprudenza di MERITO su BDM / "Banca Dati di Merito" / "banca dati di
  giustizia" / bdp.giustizia.it — sia per ESTREMI di un provvedimento specifico
  (es. "trovami la sentenza del Tribunale di Verona n. 1234/2024", o incollando un
  estremo trovato su Perplexity/Lexroom), sia per una RICERCA A TEMA più ampia
  (es. "sentenze di merito su usucapione e servitù"). La skill decide DA SÉ se è
  una ricerca per estremi o ampia. NON usare per la Cassazione o la giurisprudenza
  di legittimità/amministrativa/costituzionale (la BDM non le contiene → De Jure o
  OneLegale), né per famiglia/minori/stato delle persone (esclusi dalla BDM).
---

# Ricerca su Banca Dati di Merito (bdp.giustizia.it)

Recupera il **testo integrale** di provvedimenti di **merito civile** (Tribunali e
Corti d'Appello, dal 1/1/2016, testo **pseudonimizzato** all'origine) dalla Banca
Dati di Merito pubblica del Ministero, tramite il connettore `bdm`
(`C:\Tools\mcp-bdm`, gemello di De Jure/WK: login CNS manuale, poi il replay della
sessione gira server-side). È lo step *a valle* del flusso di ricerca: spesso
l'estremo è già stato individuato altrove (Perplexity, Lexroom, altri portali) e
qui se ne recupera il testo ufficiale.

## Cosa contiene (e cosa NO) la BDM — guardia di instradamento

La BDM ha **solo il merito civile**: Tribunali e Corti d'Appello. **Prima di
cercare**, verifica che la richiesta ricada qui:

- **Cassazione / Consiglio di Stato / TAR / Corte Cost. / CGUE-CEDU → NON su BDM.**
  Se l'estremo è di legittimità/amministrativo/costituzionale, **fermati e dillo**:
  quello si recupera con `ricerca-dejure` o `ricerca-onelegale`, non qui.
- **Famiglia, minori, stato/capacità delle persone → esclusi dalla BDM.** Segnalalo.
- In dubbio sull'organo, chiedi in una riga prima di partire.

## Prerequisito: sessione BDM valida (login CNS)

Il login è **CNS** (chiavetta + PIN) e lo fa sempre l'utente — **non gestire mai
credenziali**. La sessione dura ~2h. Prima di operare verifica:

```
C:\Tools\mcp-bdm\bdm.bat check
```

> **Come invocare il connettore.** Usa sempre il wrapper **`bdm.bat`** (in
> `C:\Tools\mcp-bdm`): imposta da sé il `PYTHONPATH` e funziona da qualsiasi shell
> (cmd/PowerShell/Git Bash). NON usare la forma `PYTHONPATH=… python -m mcp_bdm …`:
> è solo-bash e in PowerShell fallisce silenziosamente. Da Git Bash chiama
> `C:/Tools/mcp-bdm/bdm.bat …` (slash) o esegui prima `cd /c/Tools/mcp-bdm`.

- `Sessione OK …` → procedi.
- `Sessione assente/SCADUTA …` → **fermati** e chiedi all'utente di lanciare
  **`Rinnova-BDM.bat`** (in `C:\Tools\mcp-bdm`): fa il login CNS e salva la sessione
  da sé, **senza riavviare** nulla. Poi riprendi. Non tentare login tu.

## Passo 0 — Auto-routing: estremi o ricerca ampia?

Classifica la richiesta dell'utente in **una** delle due modalità:

- **RICERCA PER ESTREMI** (il caso principale) — la richiesta identifica un
  provvedimento **specifico** con: un **numero** (+ tipicamente **anno**), spesso un
  **ufficio** e/o il **tipo** (sentenza/ordinanza/decreto). Indizi: c'è un numero di
  provvedimento; l'utente incolla una citazione ("Trib. Verona, sent. n. 1234/2024");
  chiede "quella sentenza", "questo provvedimento". → **Passo 1**.
- **RICERCA AMPIA / A TEMA** (come su WK/De Jure per parole) — nessun numero
  specifico: un tema, parole, una materia, un ufficio senza numero ("sentenze su
  usucapione", "provvedimenti del Tribunale di Verona in tema di locazione"). →
  **Passo 2**.

> Nota sul portale: BDM offre "Ricerca Classica" (campi separati) e "Ricerca Nuova"
> (una casella unica con suggerimenti, ordinata per rilevanza). Sono la **stessa
> ricerca** sotto: il connettore le copre entrambe. La modalità "ampia" del Passo 2
> corrisponde alla "Ricerca Nuova" full-text.

Se la richiesta è mista (tema **+** un ufficio/anno per restringere), usa il Passo 2
passando anche i filtri di faccetta.

## Passo 1 — Ricerca per estremi

Comando:

```
C:\Tools\mcp-bdm\bdm.bat estremi --numero <N> [--anno <AAAA>] [--ufficio "<UFFICIO ESATTO>"] [--tipo <TIPO>] [--get --dir "<cartella pratica 01_RICEVUTO>"]
```

Dove `<cartella pratica>` è di norma
`C:\...\PRATICHE\<Pratica>\01_RICEVUTO`
(se non sai la pratica, chiedi o risolvila come fa `apri-pratica`).

- **`--numero`** obbligatorio; **`--anno`** quasi sempre necessario per disambiguare.
- **`--tipo`**: `SENTENZA` | `ORDINANZA` | `DECRETO` (maiuscolo).
- **`--ufficio`**: va scritto **ESATTO** come in BDM (tutto maiuscolo, per esteso):
  es. `TRIBUNALE DI VERONA`, `CORTE DI APPELLO DI VENEZIA`. Normalizza le
  abbreviazioni dell'utente: `Trib.`→`TRIBUNALE DI`, `App.`/`C. App.`/`Corte d'Appello`
  →`CORTE DI APPELLO DI`.
- **`--get`**: se il risultato è **univoco**, recupera subito il testo; con `--dir`
  lo salva come `.md` nella pratica (nome file derivato dall'estremo).

**Disambiguazione (flusso robusto).** Il filtro `--ufficio` è a corrispondenza
esatta: se sei incerto sulla dicitura, **cerca prima senza `--ufficio`** (solo
numero+anno) — escono i candidati con lo stesso numero tra i vari uffici, elencati
con ufficio + data di deposito + materia. Poi:

- **1 candidato** che combacia → recupera il testo (`bdm get <id> --dir …` oppure
  rilancia `estremi … --ufficio "<esatto>" --get`).
- **Più candidati** → confronta ufficio/data/materia con ciò che l'utente ha indicato
  e scegli quello giusto; se resta ambiguo, **elenca i candidati** (estremo + ufficio
  + data) e chiedi quale.
- **0 candidati** → verifica numero/anno; prova senza anno per allargare; se ancora
  nulla, riferisci all'utente cosa hai provato (magari il provvedimento non è in BDM,
  o è di legittimità).

## Passo 2 — Ricerca ampia / a tema (full-text)

Comando:

```
C:\Tools\mcp-bdm\bdm.bat search "<testo libero>" [--ufficio "<UFFICIO ESATTO>"] [--materia "<MATERIA>"] [--size 20]
```

- Il testo va in full-text sul **testo del provvedimento** (`anonymized_testo`).
  Le **parole sono messe in AND** (ogni parola significativa è un criterio): più
  parole **restringono** (es. "usucapione servitù" → provvedimenti che contengono
  *entrambe*), non allargano. I risultati sono **ordinati per rilevanza** (`_score`),
  non per data → i primi sono i più pertinenti al tema.
- Restituisce il **conteggio totale** + i primi N candidati (id + estremo + materia).
- È una prima setacciatura: leggi gli estremi/materie, individua i provvedimenti
  pertinenti, poi **recupera il testo** di quelli utili con `bdm get <id> --dir …`.
- Se il conteggio resta enorme, aggiungi parole più specifiche o `--materia`; se è
  zero, togli una parola (l'AND può essere troppo stretto) o prova sinonimi.

## Passo 3 — Recupero del testo e salvataggio in pratica

Per un id specifico:

```
C:\Tools\mcp-bdm\bdm.bat get <id> --dir "<cartella pratica 01_RICEVUTO>" [--name "<nome file>"]
```

- Salva un `.md` con **intestazione di metadati** (estremo, ufficio, numero/anno,
  date, materia) + **testo integrale** pseudonimizzato. Nome file derivato
  dall'estremo (leggibile), non l'id-hash.
- Default = **cartella della pratica** (`01_RICEVUTO`). Non incollare l'intero testo
  in chat: è già nel file.
- Il testo è **pseudonimizzato** all'origine (le parti compaiono come `Parte_1`,
  `C.F._1`): è così anche sul portale, non è un difetto del recupero.

## Output da restituire all'utente

1. **Estremo completo** del provvedimento (ufficio, tipo, numero/anno, data) come
   riportato da BDM.
2. Il **percorso del `.md`** salvato nella pratica, con la dimensione.
3. Una conferma sintetica del contenuto (2-3 righe), non il testo intero.
4. In caso di ricerca ampia: quanti risultati totali e quali candidati hai portato.

## Suggerimento biblioteca (`_KNOWLEDGE`)

Come in `ricerca-dejure`/`ricerca-onelegale`: il provvedimento è salvato **nella
pratica** (default). Se enuncia un **principio/orientamento di merito di portata
generale** su un tema dei pilastri (immobiliare, tributario, concorsuale) — sapere
spendibile in *altri* fascicoli — **proponi** in una riga di versarlo anche in
`_KNOWLEDGE/raw/<area>/` (non versarlo d'iniziativa). Su ok dell'utente copi il testo
(pubblico) in biblioteca e lasci nel fascicolo un rimando; poi `compila-sapere` lo
scheda. Attenzione: gli orientamenti di merito hanno peso diverso dalla legittimità
— segnala che è merito, non un principio nomofilattico.

## Note di robustezza

- **Merito civile soltanto** (2016→oggi). Fuori perimetro (Cassazione, ammin.,
  cost., famiglia/minori) → non è su BDM: devia su De Jure/OneLegale e dillo.
- **`ufficio` esatto**: preferisci il flusso numero+anno → disambigua sui candidati,
  più robusto della stringa esatta al primo colpo.
- **Sessione ~2h**: se a metà lavoro un comando torna "Sessione SCADUTA", chiedi il
  `Rinnova-BDM.bat` e riprendi dal punto in cui eri.
- **id = hash sha256**: usalo per `bdm get`, ma nel nome file usa l'estremo leggibile.
- Il connettore vive in `C:\Tools\mcp-bdm` (dettagli e contratto in `README.md` lì e
  nella memoria `project-connettore-bdm-mcp`).

## Stato della skill (v1.1 — 2026-07-14, dopo revisione)

Costruita sopra il connettore `bdm` **verificato end-to-end in rete**: `check`,
`estremi` (numero+anno+ufficio → 1 esatto; numero+anno → candidati), `search`
full-text, `get` (metadati + testo integrale). **Rifiniti in revisione (verificati
dal vivo):** (a) full-text a **parole in AND** — "usucapione servitù" 152.870→23.909,
prima allargava per OR involontario; (b) **ordinamento per rilevanza** (`_score`)
nella ricerca a tema, non più per data; (c) comandi via wrapper `bdm.bat`
shell-agnostico; encoding UTF-8 del `.md` confermato pulito. **Ancora da rifinire
con l'uso**: normalizzazione automatica delle diciture ufficio (oggi match esatto →
si aggira col flusso numero+anno→disambigua); filtri faccetta `materia`/`ufficio`
nella `search` (full-text verificato; le faccette per stringa esatta sono da
collaudare); nessuna ricerca per **frase esatta** possibile su questo campo (il
backend tokenizza sempre).
