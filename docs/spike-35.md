# Spike 35 — Sorteggio giornata con override manuale

**Status:** OPEN
**Task bloccato:** 35 — Sorteggio giornata con override manuale
**Creato da:** /cdp:spec-to-code-update il 2026-07-06

---

## Open question

Il mockup `ui_kits/admin/index.html` mostra un pulsante "Sorteggia manualmente" nello step Giornate, che lascia intendere che l'admin possa forzare il sorteggio della giornata storica oltre al processo automatico esistente (task 06 — sorteggio alla chiusura formazioni, descritto in `docs/architecture.md`). Non è chiaro se questo è: (a) solo un pulsante per rieseguire manualmente il sorteggio automatico già esistente quando serve, oppure (b) un meccanismo per scegliere manualmente QUALE giornata storica uscirà, bypassando la casualità.

## Why it blocks 35

Le due interpretazioni hanno impatti molto diversi: (a) è un piccolo wrapper su una funzione già esistente (basso rischio); (b) introduce la possibilità per l'admin di "pilotare" l'esito, il che cambia le garanzie di equità del gioco e potrebbe richiedere una discussione con Simone su chi può usarlo e se va tracciato/loggato.

## Hypotheses to verify

- Il sorteggio automatico (task 06) esiste già come funzione richiamabile (verificare `backend/engine/` per il modulo di sorteggio) e "sorteggia manualmente" è solo un trigger admin della stessa funzione, utile ad esempio se il cron settimanale fallisce.
- Non è richiesta la scelta manuale della giornata specifica — resta comunque casuale, solo il *quando* è manuale non il *risultato*.
- Se invece serve scelta manuale del risultato, questo va esplicitamente confermato da Simone prima di implementarlo, per le implicazioni sull'equità percepita del gioco.

## Expected output (fill in after investigation)

**Status:** OPEN → change to RESOLVED when complete

**Decision made:**
[TO BE FILLED BY INVESTIGATOR]

**Discarded alternative:**
[TO BE FILLED BY INVESTIGATOR]

**Technical constraints discovered:**
[TO BE FILLED BY INVESTIGATOR]

**Files and patterns found:**

| File / module | What it contains useful for task 35 |
|---------------|----------------------------------|
| [TO BE FILLED] | |

**New acceptance criteria (if emerged):**
[TO BE FILLED BY INVESTIGATOR — or "none"]

**Impact on other tasks:**
[TO BE FILLED BY INVESTIGATOR — or "none"]
