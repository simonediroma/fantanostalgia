# Spike 34 — Tie-break su gol storici

**Status:** OPEN
**Task bloccato:** 34 — Tie-break su gol storici
**Creato da:** /cdp:spec-to-code-update il 2026-07-06

---

## Open question

Il copy del design system descrive un tie-break basato sui gol storici in caso di parità esatta di punteggio in uno scontro diretto. Non è chiaro: quali gol contano (solo dei giocatori con alter ego assegnato, o dell'intera rosa storica schierata), come si comporta il tie-break se anche i gol sono pari (serve un secondo criterio?), e se questa regola si applica solo alla classifica nostalgia o anche a quella normale.

## Why it blocks 34

`backend/engine/scoring.py` (task 07) calcola oggi i punteggi ma il comportamento in caso di parità esatta non è documentato in `docs/architecture.md` — probabile che oggi un pareggio resti tale senza tie-break. Aggiungere un criterio di spareggio richiede sapere esattamente quale campo dati usare (i gol storici sono già disponibili per giocatore/giornata?) prima di poter scrivere un prompt implementativo preciso.

## Hypotheses to verify

- I dati dei gol storici sono già presenti nel dataset scrapato (fbref/calcio-seriea, task 14/22) e quindi disponibili senza nuovo scraping — verificare lo schema in `database/schema.sql` (tabella dei risultati storici).
- Il tie-break si applica solo alla classifica nostalgia (scontri diretti), non a quella normale/reale.
- In caso di parità anche sui gol, il pareggio resta ufficiale (nessun terzo criterio necessario, a meno che Simone non lo richieda esplicitamente).

## Expected output (fill in after investigation)

**Status:** OPEN → change to RESOLVED when complete

**Decision made:**
[TO BE FILLED BY INVESTIGATOR]

**Discarded alternative:**
[TO BE FILLED BY INVESTIGATOR]

**Technical constraints discovered:**
[TO BE FILLED BY INVESTIGATOR]

**Files and patterns found:**

| File / module | What it contains useful for task 34 |
|---------------|----------------------------------|
| [TO BE FILLED] | |

**New acceptance criteria (if emerged):**
[TO BE FILLED BY INVESTIGATOR — or "none"]

**Impact on other tasks:**
[TO BE FILLED BY INVESTIGATOR — or "none"]
