# Spike 32 — Wildcard storica

**Status:** OPEN
**Task bloccato:** 32 — Wildcard storica
**Creato da:** /cdp:spec-to-code-update il 2026-07-06

---

## Open question

Il copy del design system (`templates/come-funziona/ComeFunziona.dc.html`) descrive una "Wildcard storica": il vincitore del miglior scontro diretto storico della giornata riceve un giocatore leggendario extra da schierare per le 3 giornate successive. Simone non ha ancora confermato se questa regola va implementata, e in caso affermativo non è definito: come si sceglie il "giocatore leggendario extra" (pool da cui pescare, criteri), come si integra nel calcolo punteggi esistente, e se è la stessa meccanica dei "Gran Premi" già presenti nell'app (`backend/engine/granpremio.py`) o una regola distinta.

## Why it blocks 32

Senza sapere se questa è una nuova regola o una variazione dei Gran Premi esistenti, non è possibile scrivere un prompt di implementazione: rischio concreto di duplicare logica già presente in `granpremio.py` o di introdurre un sistema parallelo incoerente.

## Hypotheses to verify

- La Wildcard storica è in realtà una descrizione informale del sistema Gran Premi già implementato (`backend/engine/granpremio.py`, tabella `gran_premio`, task 23) e non richiede nuovo codice, solo un aggiornamento del copy pubblico.
- Se è una regola distinta: il "giocatore leggendario" va pescato da un pool di alter ego non ancora assegnati nella stagione storica corrente, con vincolo di ruolo.
- Il beneficio dura esattamente 3 giornate ed è cumulabile con l'alter ego già assegnato al manager (slot extra, non sostituzione).

## Expected output (fill in after investigation)

**Status:** OPEN → change to RESOLVED when complete

**Decision made:**
[TO BE FILLED BY INVESTIGATOR]

**Discarded alternative:**
[TO BE FILLED BY INVESTIGATOR]

**Technical constraints discovered:**
[TO BE FILLED BY INVESTIGATOR]

**Files and patterns found:**

| File / module | What it contains useful for task 32 |
|---------------|----------------------------------|
| [TO BE FILLED] | |

**New acceptance criteria (if emerged):**
[TO BE FILLED BY INVESTIGATOR — or "none"]

**Impact on other tasks:**
[TO BE FILLED BY INVESTIGATOR — or "none"]
