# Manolesta — Guida operativa

*Come far cercare a Claude la giurisprudenza di merito sulla Banca Dati del Ministero, e tirartene giù il testo integrale nella tua cartella.*

---

## Perché stai leggendo questa guida

La giurisprudenza di **merito** — le sentenze e le ordinanze dei Tribunali e delle Corti d'Appello — è spesso ciò che ti serve davvero: è lì che vedi come *quel* giudice, su *quel* tema, decide in concreto. Il Ministero la mette a disposizione gratis, in un portale pubblico. Ma consultarla è scomodo: cerchi, filtri, apri un provvedimento alla volta, copi-incolli. Un lavoro meccanico che ti mangia tempo e attenzione.

**Manolesta** insegna a Claude a farlo per te: gli dici cosa cerchi (un numero di sentenza, oppure un tema), lui la trova sulla banca dati e ti **scarica l'integrale** dove hai deciso tu — pronto da leggere, riassumere o citare.

## Cos'è la Banca Dati di Merito (BDM)

È il portale pubblico del Ministero della Giustizia — `bdp.giustizia.it` — che raccoglie i provvedimenti di **merito civile**: Tribunali e Corti d'Appello, dal 2016 a oggi. I testi sono **pseudonimizzati** all'origine (le parti compaiono come "Parte_1", non coi nomi veri): è così sul portale, non è un limite dello strumento.

Pensala come una biblioteca pubblica delle decisioni di merito: c'è tutto, è gratis, ma prendere un volume alla volta è lento. Manolesta è l'assistente che va a prenderti il volume giusto.

## Cos'è Manolesta — e cosa NON è

Manolesta è **una skill per Claude + un piccolo connettore** che apre un canale verso la BDM. Non inventa nulla: cerca alla fonte e ti riporta il testo ufficiale.

Una cosa detta chiara, senza giri: **non è "scarica e via".** È materiale un po' artigianale. Per accenderlo la prima volta serve un piccolo setup tecnico (lo vedi qui sotto) e, soprattutto, il tuo **login CNS** — la stessa chiavetta/smart card con cui accedi ai servizi della giustizia. Una volta acceso, l'uso di ogni giorno è semplice: parli con Claude in italiano.

Se il setup ti spaventa, tienila così: è un **"ecco come si fa"** che, una volta in piedi, ti fa risparmiare centinaia di clic.

## Cosa ti serve

- **Windows** (il canale sicuro verso la PA usa il magazzino certificati di Windows).
- **Python 3.10 o superiore** installato.
- Una **CNS / SPID con dispositivo** — chiavetta o smart card + PIN + il lettore/driver che già usi per i servizi della giustizia. *Questo è il passaggio non aggirabile: il login lo fai tu, con la tua identità. Nessuno può farlo al posto tuo, e Manolesta non vede mai le tue credenziali.*
- **Claude** su un piano Pro (o superiore): va bene **Claude Desktop** (consigliato) oppure **Claude Code**.
- Una ventina di minuti, la prima volta.

## Preparazione (una volta sola, sul tuo PC)

> Questo è il tratto più tecnico. Lo script di installazione (in arrivo) automatizza quasi tutto; qui trovi comunque i passi, così sai cosa succede.

1. **Scarica** il pacchetto (`manolesta.zip`) e **scompattalo** dove preferisci — per esempio `C:\Tools\manolesta`.
2. **Installa** il connettore e le sue dipendenze (una riga nel terminale; lo script lo farà per te).
3. **Primo login CNS**: lancia `Rinnova-BDM.bat`. Si apre il browser sul portale del Ministero, accedi con la tua CNS come faresti a mano. Fatto il login, la finestra si chiude da sola e la sessione resta valida per circa **2 ore**.
4. **Collega Manolesta a Claude**:
   - su **Claude Desktop**: registri il connettore una volta (di nuovo, lo script lo prepara per te) e carichi la skill da *Personalizza → Competenze*;
   - su **Claude Code**: il connettore è già a portata dalla cartella del progetto.

I dettagli tecnici veri e propri (comandi esatti, registrazione del connettore) stanno nel `README.md` del progetto.

## Il primo avvio: Manolesta ti chiede come lavori

La prima volta che la usi, Manolesta **non parte a testa bassa**: ti fa quattro domande veloci per adattarsi al tuo studio. In sostanza:

- come organizzi i documenti (una cartella per pratica/cliente, oppure un unico archivio di giurisprudenza);
- **dove** vuoi che salvi i provvedimenti che scarica;
- come preferisci che siano **nominati** i file;
- se vuoi che ti segnali i provvedimenti "di principio", buoni da tenere in un archivio trasversale.

Le tue risposte restano salvate: dalla seconda volta non te le richiede più. Se cambi idea, basta dire *"riconfigura Manolesta"*.

È qui la differenza con uno strumento rigido: **si piega al tuo flusso di lavoro**, non il contrario.

## Come si usa — i tre gesti

Una volta accesa, parli in italiano. Tre esempi da copiare e provare:

**1) Hai gli estremi di una sentenza (magari trovata altrove) e vuoi il testo:**
> Cerca sulla Banca Dati di Merito la sentenza del Tribunale di Verona n. 1234/2024 e salvamela nella pratica *Rossi c. Bianchi*.

**2) Vuoi esplorare un tema:**
> Trovami provvedimenti di merito su usucapione e servitù di passaggio: mostrami i primi dieci con il loro estremo e la materia.

**3) Hai individuato il provvedimento e vuoi lavorarci:**
> Scarica l'integrale di quel provvedimento e riassumimi in cinque righe il principio che afferma.

Manolesta capisce da sé se stai cercando **un provvedimento preciso** (per numero/anno/ufficio) o **un tema** (per parole), e sceglie la strada giusta.

## Quando la sessione scade

La sessione dura circa **due ore**. Se a un certo punto Claude ti dice che la sessione è scaduta, rilancia `Rinnova-BDM.bat` (rifai il login CNS) e riprendi da dove eri. Nient'altro da riavviare.

## I limiti (detti onestamente)

- **Solo merito civile** (Tribunali e Corti d'Appello, dal 2016). **Niente** Cassazione, Consiglio di Stato, TAR, Corte Costituzionale: non sono in questa banca dati. Niente famiglia, minori, stato delle persone (esclusi all'origine).
- **Consultazione mirata**, come faresti a mano con la tua sessione: **niente scaricamento massivo**.
- I testi sono **pseudonimizzati** dalla fonte.

## In sintesi: cosa fare adesso

1. Scarica il pacchetto e scompattalo.
2. Fai il setup una volta sola e il primo login con la tua CNS.
3. Collega Manolesta a Claude Desktop.
4. Prova con uno dei tre esempi qui sopra.

## Riferimenti

- Progetto su GitHub: `github.com/slimmanolesta/mcp-bdm`
- Banca Dati di Merito: `bdp.giustizia.it`

---

*Manolesta · connettore + skill per Claude · Avv. Stefano Rossi*
