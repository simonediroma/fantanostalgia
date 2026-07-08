# Spike 33 — Mercato di riparazione (gennaio)

**Status:** OPEN
**Task bloccato:** 33 — Mercato di riparazione
**Creato da:** /cdp:spec-to-code-update il 2026-07-06

---

## Open question

Il copy del design system menziona un "mercato di riparazione" a gennaio che riassegna anche gli alter ego storici, non solo i giocatori moderni. Non è definito: chi può partecipare (tutti i manager o solo chi ha slot liberi), come si riassegnano gli alter ego (nuovo sorteggio random per ruolo come l'assegnazione iniziale, o scelta manuale), cosa succede ai punteggi già maturati con il vecchio alter ego, e se questa funzionalità va costruita ora o è solo un'idea da roadmap.

## Why it blocks 33

Il mapping alter ego oggi è pensato come "reveal post-asta" one-shot (`backend/engine/mapping.py`, task 03; `docs/architecture.md` — "Reveal post-asta: mapping non visibile fino all'apertura buste"). Riaprire il mapping a gennaio è un cambiamento architetturale non banale sulla stessa tabella/logica usata per l'assegnazione iniziale — senza chiarire la meccanica esatta, il rischio di rompere l'invariante "un alter ego per giocatore per stagione" è alto.

## Hypotheses to verify

- Il mercato di riparazione riguarda solo i giocatori moderni (trasferimenti reali di mercato), e il testo "riassegna anche gli alter ego storici" significa semplicemente che il nuovo giocatore acquistato riceve un nuovo alter ego con lo stesso algoritmo random-per-ruolo usato all'asta iniziale — non un re-mapping generale.
- I punteggi già maturati con il vecchio alter ego restano storicizzati (non si ricalcolano retroattivamente).
- Questa funzionalità potrebbe essere fuori scope per la prima iterazione del restyling e rimandata a una fase successiva.

## Expected output (fill in after investigation)

**Status:** OPEN → change to RESOLVED when complete

**Decision made:**
[TO BE FILLED BY INVESTIGATOR]

**Discarded alternative:**
[TO BE FILLED BY INVESTIGATOR]

**Technical constraints discovered:**
[TO BE FILLED BY INVESTIGATOR]

**Files and patterns found:**

| File / module | What it contains useful for task 33 |
|---------------|----------------------------------|
| [TO BE FILLED] | |

**New acceptance criteria (if emerged):**
[TO BE FILLED BY INVESTIGATOR — or "none"]

**Impact on other tasks:**
[TO BE FILLED BY INVESTIGATOR — or "none"]
