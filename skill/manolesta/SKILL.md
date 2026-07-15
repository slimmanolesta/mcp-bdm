---
name: manolesta
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
  di legittimità/amministrativa/costituzionale (la BDM non le contiene — vanno
  cercate su un'altra banca dati), né per famiglia/minori/stato delle persone
  (esclusi dalla BDM).
---

# Ricerca su Banca Dati di Merito (bdp.giustizia.it)

Recupera il **testo integrale** di provvedimenti di **merito civile** (Tribunali e
Corti d'Appello, dal 1/1/2016, testo **pseudonimizzato** all'origine) dalla Banca
Dati di Merito pubblica del Ministero, tramite il connettore `bdm`
(`C:\Tools\mcp-bdm`: login CNS manuale, poi il replay della sessione gira
server-side). È lo step *a valle* del flusso di ricerca: spesso l'estremo è già
stato individuato altrove (Perplexity, Lexroom, altri portali) e qui se ne
recupera il testo ufficiale.

## Cosa contiene (e cosa NO) la BDM — guardia di instradamento

La BDM ha **solo il merito civile**: Tribunali e Corti d'Appello. **Prima di
cercare**, verifica che la richiesta ricada qui:

- **Cassazione / Consiglio di Stato / TAR / Corte Cost. / CGUE-CEDU → NON su BDM.**
  Se l'estremo è di legittimità/amministrativo/costituzionale, **fermati e dillo**:
  non è su BDM, va cercato su una banca dati di legittimità/amministrativa.
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

## Come guidi il connettore: Claude Desktop (tool MCP) o Claude Code (CLI)

Le istruzioni operative qui sotto usano i **comandi CLI** (`bdm …`). Su **Claude
Desktop** il connettore gira come **server MCP** e si guida con i tool equivalenti:

| Gesto | Claude Code — CLI | Claude Desktop — tool MCP |
|---|---|---|
| Verifica sessione | `bdm.bat check` | `bdm_check_session` |
| Ricerca per estremi | `bdm.bat estremi --numero … --anno …` | `bdm_estremi(numero, anno, ufficio, tipo)` |
| Ricerca a tema | `bdm.bat search "…"` | `bdm_search(testo, ufficio, materia, size)` |
| Testo integrale + salvataggio | `bdm.bat get <id> --dir "<cartella>"` | `bdm_get_provvedimento(id, cartella)` |

Su Desktop non c'è terminale: il salvataggio nella cartella dell'utente avviene
passando `cartella` a `bdm_get_provvedimento`. Il login CNS resta comunque un passo
locale (`Rinnova-BDM.bat`): nessun host lo evita.

## Primo avvio — adatta manolesta al modo di lavorare dell'utente

Manolesta non deve partire con le impostazioni di chi l'ha scritta: la **prima
volta** si adatta a chi la usa. All'inizio di una sessione:

1. Verifica se esiste già la **configurazione di flusso** dell'utente
   (`manolesta.workflow.json`, accanto al `config.json` del connettore).
2. **Se esiste** → leggila e rispettala in silenzio (dove salvare, come nominare,
   biblioteca sì/no). Ricorda in una riga che si può dire *"riconfigura manolesta"*
   per cambiarla.
3. **Se NON esiste** (primo avvio) → prima di cercare, fai un **breve questionario**,
   tono piano (l'utente è un giurista, non un informatico). Quattro domande:
   - **a) Come organizzi i documenti?** (i) una cartella per pratica/cliente;
     (ii) un unico archivio di giurisprudenza; (iii) altro — fattelo descrivere.
   - **b) Dove salvo i provvedimenti che scarico?** Fatti dare la cartella radice
     (es. `C:\Studio\...`). Se ha scelto "per pratica", spiega che di volta in volta
     indicherà la sottocartella ("salvala nella pratica *Rossi c. Bianchi*").
   - **c) Come nomino i file?** Proponi il default — **estremo leggibile**
     (es. `Trib_Verona_sent_1234-2024.md`); accetta una sua convenzione.
   - **d) Vuoi il suggerimento-biblioteca?** Quando un provvedimento afferma un
     principio di portata generale, glielo segnali per un eventuale archivio
     trasversale (sì/no).
4. **Salva** le risposte in `manolesta.workflow.json` e conferma in una riga. Da lì
   in avanti rispetta quelle scelte senza più chiederle.

Quando poi l'utente dice "salvala nella pratica X", combina la **cartella radice**
configurata con la sottocartella indicata e passala a `bdm_get_provvedimento`
(o `bdm get --dir` su Code).

## Passo 0 — Auto-routing: estremi o ricerca ampia?

Classifica la richiesta dell'utente in **una** delle due modalità:

- **RICERCA PER ESTREMI** (il caso principale) — la richiesta identifica un
  provvedimento **specifico** con: un **numero** (+ tipicamente **anno**), spesso un
  **ufficio** e/o il **tipo** (sentenza/ordinanza/decreto). Indizi: c'è un numero di
  provvedimento; l'utente incolla una citazione ("Trib. Verona, sent. n. 1234/2024");
  chiede "quella sentenza", "questo provvedimento". → **Passo 1**.
- **RICERCA AMPIA / A TEMA** (per parole chiave) — nessun numero
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
C:\Tools\mcp-bdm\bdm.bat estremi --numero <N> [--anno <AAAA>] [--ufficio "<UFFICIO ESATTO>"] [--tipo <TIPO>] [--get --dir "<cartella di destinazione>"]
```

Dove `<cartella di destinazione>` è la cartella in cui salvare il provvedimento
(se non è indicata, chiedila).

- **`--numero`** obbligatorio; **`--anno`** quasi sempre necessario per disambiguare.
- **`--tipo`**: `SENTENZA` | `ORDINANZA` | `DECRETO` (maiuscolo).
- **`--ufficio`**: va scritto **ESATTO** come in BDM (tutto maiuscolo, per esteso):
  es. `TRIBUNALE DI VERONA`, `CORTE DI APPELLO DI VENEZIA`. Normalizza le
  abbreviazioni dell'utente: `Trib.`→`TRIBUNALE DI`, `App.`/`C. App.`/`Corte d'Appello`
  →`CORTE DI APPELLO DI`.
- **`--get`**: se il risultato è **univoco**, recupera subito il testo; con `--dir`
  lo salva come `.md` (nome file derivato dall'estremo).

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

## Passo 3 — Recupero del testo e salvataggio

Per un id specifico:

```
C:\Tools\mcp-bdm\bdm.bat get <id> --dir "<cartella di destinazione>" [--name "<nome file>"]
```

- Salva un `.md` con **intestazione di metadati** (estremo, ufficio, numero/anno,
  date, materia) + **testo integrale** pseudonimizzato. Nome file derivato
  dall'estremo (leggibile), non l'id-hash.
- Non incollare l'intero testo in chat: è già nel file.
- Il testo è **pseudonimizzato** all'origine (le parti compaiono come `Parte_1`,
  `C.F._1`): è così anche sul portale, non è un difetto del recupero.

## Output da restituire all'utente

1. **Estremo completo** del provvedimento (ufficio, tipo, numero/anno, data) come
   riportato da BDM.
2. Il **percorso del `.md`** salvato, con la dimensione.
3. Una conferma sintetica del contenuto (2-3 righe), non il testo intero.
4. In caso di ricerca ampia: quanti risultati totali e quali candidati hai portato.

## Nota sul valore del merito

Gli orientamenti di **merito** hanno un peso diverso dalla legittimità: se un
provvedimento enuncia un principio di portata generale, ricorda che è
**giurisprudenza di merito**, non nomofilattica. Segnalalo quando lo riporti.

## Note di robustezza

- **Merito civile soltanto** (2016→oggi). Fuori perimetro (Cassazione, ammin.,
  cost., famiglia/minori) → non è su BDM: dillo (va cercato su un'altra banca dati).
- **`ufficio` esatto**: preferisci il flusso numero+anno → disambigua sui candidati,
  più robusto della stringa esatta al primo colpo.
- **Sessione ~2h**: se a metà lavoro un comando torna "Sessione SCADUTA", chiedi il
  `Rinnova-BDM.bat` e riprendi dal punto in cui eri.
- **id = hash sha256**: usalo per `bdm get`, ma nel nome file usa l'estremo leggibile.
- Il connettore vive in `C:\Tools\mcp-bdm` (dettagli e contratto nel `README.md` del
  repo).

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
