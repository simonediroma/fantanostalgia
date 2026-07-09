# 29 — Gestione multi-lega in Admin

## Context
Depends on: task 26 completo (Admin SPA già restylata, componenti design system disponibili nel wizard). Rischio alzato di un livello (MEDIUM invece di LOW) perché tocca il router lega condiviso. Branch: `task/29-multi-lega-admin`.

## Existing modules to read first
1. `backend/api/routers/league.py` — verificare esattamente quali endpoint espone già (creazione, lista, dettaglio lega). L'architettura attuale (`architecture-context.md`) conferma l'esistenza di questo router ma non il suo contratto API completo — leggerlo per intero prima di aggiungere endpoint, per non duplicare funzionalità già presenti (il task 01-bootstrap ha già coperto "DB + Auth + Gestione Lega").
2. `frontend/admin/js/{api,auth,league}.js` — pattern di chiamata API già in uso lato frontend.
3. `database/schema.sql` — verificare se la tabella lega supporta già multi-tenancy (probabile, dato che `coach.py` referenzia `league_id` nelle query) — **non modificare lo schema in questo task**: se serve una modifica, fermarsi e chiedere approvazione (vedi vincolo in `docs/context.md`).

## Objective
Aggiungere all'Admin SPA un selettore "Lega attiva" e un flusso di creazione nuova lega, riusando gli endpoint già esistenti in `league.py` dove possibile. Se mancano endpoint (es. lista leghe per l'utente admin), aggiungerli seguendo il pattern REST già in uso negli altri router.

## Acceptance criteria
- [ ] L'admin può vedere l'elenco delle leghe esistenti e selezionarne una come "attiva" per il wizard.
- [ ] L'admin può creare una nuova lega (nome, stagione storica, max manager, piattaforma) tramite un form che usa i componenti `Input`/`Button`/`Panel` del design system.
- [ ] Il wizard 4 step (task 26) opera sempre sulla lega attualmente selezionata — nessuna ambiguità su quale lega si sta modificando.
- [ ] Nessuna modifica a `database/schema.sql` senza approvazione esplicita — se il modello dati non supporta già multi-lega pulitamente, fermarsi e riportare il blocco invece di forzare una migrazione.
- [ ] Test: creazione di una seconda lega di prova, switch tra le due, verifica che le operazioni del wizard restino isolate per lega.
- [ ] Build: nessun errore nei test esistenti di `backend/tests/` dopo le modifiche a `league.py`.

## Files that will be created or modified
- `backend/api/routers/league.py` — eventuali nuovi endpoint (solo se mancanti dopo la lettura del file)
- `frontend/admin/index.html` — selettore lega + form creazione lega
- `frontend/admin/js/league.js` — chiamate API per lista/creazione/switch lega

## Implementation — TDD
Scrivi prima il test che fallisce (endpoint mancante o comportamento nuovo) → implementa il minimo per farlo passare → refactor.

## Pre-PR Gate
**5-axis code review:**
- [ ] Correctness: il codice fa quello che dichiara?
- [ ] Security: nessuna vulnerabilità introdotta (es. un admin non deve poter accedere a leghe di un altro admin, se il modello lo prevede)?
- [ ] Readability: comprensibile in 5 minuti?
- [ ] Performance: nessuna regressione evidente?
- [ ] Surgical: ogni riga riconducibile al requisito?

## Notes for Claude Code
- Se `league.py` espone già tutto il necessario, questo task si riduce alla sola parte frontend — verificarlo prima di scrivere codice backend nuovo (regola "cerca prima di implementare" in `CLAUDE.md`).
- Le funzionalità scartate in `project-spec.md` sez. 13 (dashboard KPI, sezione manager standalone, catalogo stagioni esplorabile) **non fanno parte** di questo task.
- Aggiornare `CLAUDE_MEMORY.md` a fine task: marcare **29** come `[x]`, aggiungere branch e PR.
