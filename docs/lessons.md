# Lezioni Imparate — fantanostalgia

Lezioni operative emerse durante lo sviluppo. Da consultare prima di implementare qualcosa di nuovo.

---

## Generali (universali)

**Ogni unità di lavoro è indipendente**
Un errore su un elemento non deve mai bloccare gli altri. Pattern: `try/except` per elemento nel loop principale, log dell'errore, `continue`.

**Lazy loading per moduli pesanti**
Moduli con import costosi (ML, cloud SDK, scraping) vanno importati solo quando la funzionalità viene effettivamente usata, non al top-level. Evita timeout e startup lenti.

**Batch prima di parallelizzare**
Pre-carica tutti i dati necessari in un unico batch prima di parallelizzare con thread/async. Ogni thread che fa I/O separato moltiplica i costi e i tempi.

**Singleton per client costosi**
Client verso API esterne (DB, cloud) vanno istanziati una volta sola e riusati.

---

## Database (SQLite + GCS)

**Download/upload GCS è costoso**
Ogni operazione di scrittura fa download + upload del db. Raggruppare le scritture in una sola transazione quando possibile. Non aprire connessioni write multiple per operazioni che possono essere batched.

**WAL mode obbligatoria**
SQLite in WAL mode (`PRAGMA journal_mode=WAL`) è necessario per evitare lock in lettura concorrente. Già impostato in `db.py` — non rimuovere.

**Evita query N+1**
Una query per elemento in un loop è sempre un bug di performance. Sostituire con una query batch con `IN (...)`.

---

## Scraping

**fantagiaveno.it — struttura HTML**
Verificare la struttura della pagina prima di finalizzare il parser. Il sito è datato e potrebbe avere markup non standard. Usare `lxml` come parser per robustezza.

**fbref.com — rate limiting**
fbref applica rate limiting aggressivo. Aggiungere sleep di 2-3 secondi tra le richieste. Cachare sempre i risultati su db prima di ri-scrapare.

**Cachare sempre i dati scraping**
I dati storici non cambiano mai. Una volta scraping fatto e salvato su db, non ri-scrapare. Verificare sempre se i dati esistono già prima di fare una nuova richiesta HTTP.

---

## Algoritmo Mapping Alter Ego

**Ordine di assegnazione è critico**
Assegnare prima i giocatori attuali con più titolarità (starts_current_season DESC). Se si assegna in ordine casuale si rischia di sprecare alter ego forti su panchinari.

**Pool alter ego per ruolo**
Costruire il pool di disponibili per ruolo all'inizio, poi estrarre random. Non estrarre uno alla volta con query separate — è N+1 e rompe la casualità uniforme.

**Duplicati come fallback esplicito**
I duplicati vanno calcolati DOPO aver fatto il mapping normale. Calcolare quanti slot rimangono scoperti per ruolo, poi riempire con alter ego già usati estratti random dallo stesso pool.

---

## Specifiche del Progetto

> Aggiungere qui le lezioni emerse durante lo sviluppo di fantanostalgia.
