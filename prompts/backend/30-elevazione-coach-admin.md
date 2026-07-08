# 30 — Elevazione coach → admin

## Context
Depends on: task 26 e 27 completi (entrambe le SPA restylate — servono per il form di richiesta lato coach e la vista di approvazione lato admin). Rischio HIGH: tocca auth/permessi, superficie di regressione ampia. Branch: `task/30-elevazione-coach-admin`.

## Existing modules to read first
1. `backend/api/routers/coach.py` — meccanismo di autenticazione coach attuale, per capire dove agganciare la richiesta di elevazione.
2. `frontend/coach/index.html` — area personale coach, dove va aggiunto il form di richiesta.
3. `database/schema.sql` — **leggere per intero prima di proporre qualsiasi modifica**. Questo task probabilmente richiede una nuova tabella (es. `admin_elevation_request`) o un nuovo campo di stato — qualsiasi modifica allo schema richiede approvazione esplicita di Simone (vincolo di progetto, vedi `docs/context.md` e `CLAUDE.md` del repo: "File invariati: non toccare mai database/schema.sql senza approvazione esplicita"). Non modificare lo schema senza fermarsi prima a chiedere conferma.

## Objective
Permettere a un coach di richiedere i permessi admin tramite un form nella propria area personale; l'admin esistente vede le richieste pendenti e può approvarle o rifiutarle. Nessuna auto-approvazione: serve sempre un'azione esplicita di un admin già esistente.

## Acceptance criteria
- [ ] Un coach autenticato può inviare una richiesta di elevazione da `frontend/coach/index.html` (form con `HelpBox` che spiega cosa comporta).
- [ ] Un admin autenticato vede le richieste pendenti in una vista dell'Admin SPA e può approvare/rifiutare con conferma esplicita (`Modal`).
- [ ] Un coach approvato ottiene i permessi admin senza dover ricreare un account (transizione di ruolo, non nuova identità).
- [ ] Ogni richiesta approvata/rifiutata è tracciata (chi, quando, esito) per audit minimo.
- [ ] Test: `pytest backend/tests/test_elevation.py` (da creare) copre richiesta → approvazione → verifica permessi, e richiesta → rifiuto → permessi invariati.
- [ ] Build: nessuna regressione nei test di autenticazione esistenti.

## Files that will be created or modified
- `database/schema.sql` — **SOLO dopo approvazione esplicita** — nuova tabella/campo per le richieste di elevazione
- `backend/api/routers/coach.py` — endpoint per inviare la richiesta
- `backend/api/routers/league.py` o nuovo router `admin.py` — endpoint per listare/approvare le richieste (verificare dove vivono oggi le operazioni admin-only prima di crearne uno nuovo)
- `frontend/coach/index.html` — form di richiesta
- `frontend/admin/index.html` — vista richieste pendenti + approvazione

## Doubt-Driven Review — run before writing code
Per ogni decisione non banale in questo task:
1. **CLAIM** — enuncia la decisione come asserzione esplicita
2. **DOUBT** — elenca 2-3 modi in cui potrebbe essere sbagliata
3. **RECONCILE** — verifica o correggi. Se non regge, fermati.

Decisioni che richiedono questo passaggio in questo task:
- Come rappresentare lo stato "richiesta pendente/approvata/rifiutata" senza rompere lo schema esistente (nuova tabella vs campo su tabella coach esistente).
- Se un coach elevato ad admin mantiene anche i permessi coach (probabile: gestisce la propria lega da entrambe le prospettive) o li perde.
- Come autenticare le nuove route admin-only senza duplicare la logica di sessione già in uso altrove nel backend.

## Implementation — TDD
Scrivi il test che fallisce (richiesta senza permessi → nessun accesso admin) → implementa il minimo → refactor.

## Pre-PR Gate
**Security checklist:**
- [ ] Nessun segreto committato o loggato
- [ ] Input validato prima di ogni operazione DB
- [ ] Rate limiting sull'endpoint pubblico di richiesta elevazione (per evitare spam di richieste)
- [ ] OWASP Top 10 verificato per questo task

**5-axis code review:**
- [ ] Correctness: il flusso richiesta→approvazione→permessi funziona esattamente come specificato?
- [ ] Security: un coach non approvato non può in nessun modo accedere a route admin-only?
- [ ] Readability: comprensibile in 5 minuti?
- [ ] Performance: nessuna regressione?
- [ ] Surgical: ogni riga riconducibile al requisito?

## Notes for Claude Code
- Questo è l'unico task di questa epica che tocca potenzialmente `database/schema.sql` — se la modifica sembra necessaria, fermati e chiedi conferma esplicita a Simone prima di scriverla, anche se il resto del task è pronto.
- Non implementare un sistema di ruoli generico/estensibile (RBAC completo) se non richiesto — la minima modifica che risolve "coach può chiedere di diventare admin, un admin approva" è sufficiente (principio di semplicità, vedi `CLAUDE.md`).
- Aggiornare `CLAUDE_MEMORY.md` a fine task: marcare **30** come `[x]`, aggiungere branch e PR, e annotare esplicitamente se lo schema è stato toccato e con quale approvazione.
