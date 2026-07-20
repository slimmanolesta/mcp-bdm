---
name: manolesta
description: >-
  Cerca e recupera il testo integrale di provvedimenti di merito civile
  (sentenze/ordinanze/decreti di Tribunali e Corti d'Appello, dal 2016,
  pseudonimizzati) sulla Banca Dati di Merito pubblica del Ministero
  (bdp.giustizia.it), tramite il connettore `manolesta`.
  USA SEMPRE questa skill quando l'utente vuole cercare/recuperare/"tirare giù"
  giurisprudenza di MERITO su BDM / "Banca Dati di Merito" / "banca dati di
  giustizia" / bdp.giustizia.it — sia per ESTREMI di un provvedimento specifico
  (es. "trovami la sentenza del Tribunale di Verona n. 1234/2024", o incollando un
  estremo trovato altrove), sia per una RICERCA A TEMA più ampia
  (es. "sentenze di merito su usucapione e servitù"). La skill decide DA SÉ se è
  una ricerca per estremi o ampia. NON usare per la Cassazione o la giurisprudenza
  di legittimità/amministrativa/costituzionale (la BDM non le contiene — vanno
  cercate su un'altra banca dati), né per famiglia/minori/stato delle persone
  (esclusi dalla BDM).
---

# Ricerca su Banca Dati di Merito (bdp.giustizia.it)

Recupera il **testo integrale** di provvedimenti di **merito civile** (Tribunali e
Corti d'Appello, dal 1/1/2016, testo **pseudonimizzato** all'origine) dalla Banca
Dati di Merito pubblica del Ministero. È lo step *a valle* del flusso di ricerca:
spesso l'estremo è già stato individuato altrove e qui se ne recupera il testo
ufficiale.

## Gli strumenti

Il connettore espone questi tool. **Usa i tool**: non c'è bisogno di conoscere
percorsi o cartelle d'installazione.

| Tool | A cosa serve |
|---|---|
| `bdm_check_session` | Verifica che la sessione BDM sia valida. |
| `bdm_estremi` | Ricerca per **estremi** (numero, anno, ufficio, tipo) — il caso principale. |
| `bdm_search` | Ricerca **full-text** a tema (testo libero, ufficio, materia). |
| `bdm_get_provvedimento` | Testo integrale per `id`; con `cartella` lo salva come `.md`. |
| `bdm_get_workflow` | Legge le preferenze di flusso dell'utente. |
| `bdm_set_workflow` | Salva le preferenze (fine dell'onboarding). |

> Su Claude Code esiste anche una CLI equivalente (`bdm …`) utile per il lavoro in
> blocco: vedi l'appendice in fondo. Ovunque sia disponibile un tool, **preferisci
> il tool**.

## Cosa contiene (e cosa NO) la BDM — guardia di instradamento

La BDM ha **solo il merito civile**: Tribunali e Corti d'Appello. **Prima di
cercare**, verifica che la richiesta ricada qui:

- **Cassazione / Consiglio di Stato / TAR / Corte Cost. / CGUE-CEDU → NON su BDM.**
  Se l'estremo è di legittimità/amministrativo/costituzionale, **fermati e dillo**:
  non è su BDM, va cercato su una banca dati di legittimità/amministrativa.
- **Famiglia, minori, stato/capacità delle persone → esclusi dalla BDM.** Segnalalo.
- In dubbio sull'organo, chiedi in una riga prima di partire.

## Prerequisito: sessione valida (login CNS)

Il login è **CNS** (chiavetta + PIN) e lo fa sempre l'utente — **non gestire mai
credenziali, non tentare di fare login tu**. La sessione dura ~2h.

Chiama `bdm_check_session`:

- sessione valida → procedi;
- **assente o scaduta** → **fermati** e chiedi all'utente di lanciare
  **`Rinnova-BDM.bat`** (nella cartella dove ha installato manolesta): fa il login
  CNS e salva la sessione da sé, **senza riavviare nulla**. Poi riprendi dal punto
  in cui eri.

## Primo avvio — adatta manolesta al modo di lavorare dell'utente

Manolesta non deve partire con le impostazioni di chi l'ha scritta. All'inizio,
**chiama `bdm_get_workflow`**:

- **Se torna una configurazione** → rispettala in silenzio (dove salvare, come
  nominare, biblioteca sì/no). Ricorda in una riga che si può dire *"riconfigura
  manolesta"* per cambiarla.
- **Se torna `_stato: primo_avvio`** → prima di cercare, fai un **breve
  questionario**, tono piano (l'utente è un giurista, non un informatico):
  - **a) Come organizzi i documenti?** (i) una cartella per pratica/cliente;
    (ii) un unico archivio di giurisprudenza; (iii) altro — fattelo descrivere.
  - **b) Dove salvo i provvedimenti che scarico?** Fatti dare la **cartella
    radice** (es. `C:\Studio\Giurisprudenza`). Se ha scelto "per pratica", spiega
    che di volta in volta indicherà la sottocartella ("salvala nella pratica
    *Rossi c. Bianchi*").
  - **c) Come nomino i file?** Proponi il default — **estremo leggibile**
    (es. `Tribunale di Verona, sent. 1234-2024.md`); accetta una sua convenzione.
  - **d) Vuoi il suggerimento-biblioteca?** Quando un provvedimento afferma un
    principio di portata generale, glielo segnali per un eventuale archivio
    trasversale (sì/no).
- Poi **chiama `bdm_set_workflow`** con le risposte
  (`organizzazione`, `cartella_radice`, `naming`, `biblioteca`) e conferma in una
  riga. Da lì in avanti rispetta quelle scelte senza più chiederle.
- **Se torna `_stato: corrotto`** → il file delle preferenze è illeggibile. Dillo
  e rifai il questionario: `bdm_set_workflow` lo riscrive da capo.

> **Aggiornamenti successivi.** `bdm_set_workflow` fa un aggiornamento *parziale*:
> passa **solo** i campi che stai cambiando. Se l'utente dice "d'ora in poi salva
> in D:\Studio", passa solo `cartella_radice` — se passassi anche gli altri campi
> con valori inventati, cancelleresti le sue scelte precedenti.

Quando l'utente dice "salvala nella pratica X", passa la sottocartella a
`bdm_get_provvedimento`: viene risolta **dentro** la cartella radice configurata.

## Passo 0 — Auto-routing: estremi o ricerca ampia?

Classifica la richiesta dell'utente in **una** delle due modalità:

- **RICERCA PER ESTREMI** (il caso principale) — la richiesta identifica un
  provvedimento **specifico** con: un **numero** (+ tipicamente **anno**), spesso un
  **ufficio** e/o il **tipo** (sentenza/ordinanza/decreto). Indizi: c'è un numero di
  provvedimento; l'utente incolla una citazione ("Trib. Verona, sent. n. 1234/2024");
  chiede "quella sentenza", "questo provvedimento". → **Passo 1**.
- **RICERCA AMPIA / A TEMA** (per parole chiave) — nessun numero specifico: un tema,
  parole, una materia, un ufficio senza numero ("sentenze su usucapione",
  "provvedimenti del Tribunale di Verona in tema di locazione"). → **Passo 2**.

Se la richiesta è mista (tema **+** un ufficio/anno per restringere), usa il Passo 2
passando anche i filtri.

## Passo 1 — Ricerca per estremi

`bdm_estremi(numero, anno, ufficio, tipo, numero_ruolo, anno_ruolo)`

**Due vie d'ingresso.** Guarda cosa l'utente ha davvero in mano:

- **numero di provvedimento** (+ anno/ufficio/tipo) — la via normale, quando la
  citazione dà *"sent. n. 1234/2024"*;
- **numero di RUOLO (R.G.)** + anno di ruolo — quando conosce il **R.G. ma non il
  numero di pubblicazione**. Capita spesso: una sentenza citata in un atto di
  controparte, o un PDF avuto da altra fonte, riportano *"R.G. 1997/2022"* e non il
  numero. R.G. + ufficio è molto selettivo. **È anche il modo per risalire al numero
  di pubblicazione quando manca**, cosa che serve prima di citare in un atto.

Serve almeno una delle due vie; si possono anche combinare.

- **`numero`** oppure **`numero_ruolo`**: almeno uno dei due. **`anno`** quasi sempre necessario per disambiguare.
- **`tipo`**: `SENTENZA` | `ORDINANZA` | `DECRETO` (maiuscolo).
- **`ufficio`**: va scritto **ESATTO** come in BDM (tutto maiuscolo, per esteso):
  es. `TRIBUNALE DI VERONA`, `CORTE DI APPELLO DI VENEZIA`. Normalizza le
  abbreviazioni dell'utente: `Trib.`→`TRIBUNALE DI`, `App.`/`C. App.`/`Corte d'Appello`
  →`CORTE DI APPELLO DI`.

**Disambiguazione (flusso robusto).** Il filtro `ufficio` è a corrispondenza esatta:
se sei incerto sulla dicitura, **cerca prima senza `ufficio`** (solo numero+anno) —
escono i candidati con lo stesso numero tra i vari uffici, con ufficio + data di
deposito + materia. Poi:

- **1 candidato** che combacia → recupera il testo con `bdm_get_provvedimento`.
- **Più candidati** → confronta ufficio/data/materia con ciò che l'utente ha indicato
  e scegli quello giusto; se resta ambiguo, **elenca i candidati** (estremo + ufficio
  + data) e chiedi quale.
- **0 candidati** → verifica numero/anno; prova senza anno per allargare; se ancora
  nulla, riferisci cosa hai provato (magari il provvedimento non è in BDM, o è di
  legittimità).

## Passo 2 — Ricerca ampia / a tema (full-text)

`bdm_search(testo, ufficio, materia, size)`

- Il testo va in full-text sul **testo del provvedimento**. Le **parole sono messe
  in AND** (ogni parola significativa è un criterio): più parole **restringono**
  (es. "usucapione servitù" → provvedimenti che contengono *entrambe*), non
  allargano. I risultati sono **ordinati per rilevanza**, non per data → i primi
  sono i più pertinenti al tema.
- Restituisce il **conteggio totale** + i primi N candidati (id + estremo + materia).
- È una prima setacciatura: leggi gli estremi/materie, individua i provvedimenti
  pertinenti, poi **recupera il testo** di quelli utili.
- Se il conteggio resta enorme, aggiungi parole più specifiche o `materia`; se è
  zero, togli una parola (l'AND può essere troppo stretto) o prova sinonimi.
- **Attenzione**: parole molto corte (meno di 3 caratteri) vengono scartate; se la
  ricerca è fatta *solo* di parole corte, la semantica AND non si applica. Preferisci
  termini pieni.

## Passo 3 — Recupero del testo e salvataggio

`bdm_get_provvedimento(id, cartella, nome)`

- **Con `cartella`** → salva un `.md` con **intestazione di metadati** (estremo,
  ufficio, numero/anno, date, materia) + **testo integrale**, e ti restituisce il
  percorso. È la modalità da preferire: non brucia il contesto.
- **Senza `cartella`** → restituisce il testo in risposta, troncato (tetto 50.000
  caratteri). Per un provvedimento lungo, **salva su file**.
- La `cartella` è confinata alla **radice configurata** nell'onboarding: se passi un
  percorso fuori da lì, il tool rifiuta e te lo dice. Un percorso relativo viene
  risolto dentro la radice.
- Se esiste già un file con quel nome, il tool **non lo sovrascrive**: aggiunge un
  progressivo.
- Il testo è **pseudonimizzato** all'origine (le parti compaiono come `Parte_1`,
  `C.F._1`): è così anche sul portale, non è un difetto del recupero.

## Output da restituire all'utente

1. **Estremo completo** del provvedimento (ufficio, tipo, numero/anno, data) come
   riportato da BDM.
2. Il **percorso del `.md`** salvato.
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
- **Sessione ~2h**: se a metà lavoro un tool torna "sessione scaduta", chiedi il
  `Rinnova-BDM.bat` e riprendi dal punto in cui eri.
- **id = hash sha256**: usalo per il recupero, ma nel nome file usa l'estremo
  leggibile.
- Nessuna ricerca per **frase esatta**: il backend tokenizza sempre il campo.

## Appendice — la CLI (solo su Claude Code)

Su Claude Code, se hai accesso al terminale, la stessa cosa si fa da riga di
comando dalla cartella dove l'utente ha installato manolesta (chiedigliela una
volta; non darla per scontata):

| Tool | Comando equivalente |
|---|---|
| `bdm_check_session` | `bdm.bat check` |
| `bdm_estremi` | `bdm.bat estremi --numero <N> [--anno <A>] [--ufficio "<U>"] [--tipo <T>]`<br>oppure per ruolo: `--numero-ruolo <RG> --anno-ruolo <A> [--ufficio "<U>"]` |
| `bdm_search` | `bdm.bat search "<testo>" [--ufficio "<U>"] [--materia "<M>"] [--size 20]` |
| `bdm_get_provvedimento` | `bdm.bat get <id> --dir "<cartella>" [--name "<nome>"]` |
| `bdm_get_workflow` / `bdm_set_workflow` | *(nessun equivalente CLI)* |

La CLI è comoda per scaricare **più provvedimenti in blocco** senza farli passare
dal contesto. Attenzione: `bdm get --dir` **sovrascrive** un file omonimo e non è
confinato alla cartella radice — quelle protezioni valgono per il tool MCP.
