# 31 — Pagina pubblica "Come Funziona" standalone

## Context
Depends on: task 25 completo (pagine pubbliche già restylate, `base.html` aggiornato con nav e design system disponibile). Branch: `task/31-pagina-come-funziona`.

## Existing modules to read first
1. `backend/templates/home.html` — contiene oggi la spiegazione "come funziona" da estrarre in una pagina dedicata.
2. `backend/templates/base.html` (dopo il task 25) — layout condiviso da riusare per la nuova pagina.
3. `templates/come-funziona/ComeFunziona.dc.html` (cartella `fantanostalgia-design-system/project/`) — riferimento di contenuto e struttura: step spiegati, formula punteggio con esempio numerico, tabella regole, FAQ ad accordion. Attenzione: questo mockup rivela regole di gioco (wildcard storica, mercato di riparazione, tie-break) che **non fanno parte di questo task** — sono gli spike separati (task 32-35). Non includerle nel copy finché non sono risolte.

## Objective
Creare una nuova route pubblica SSR (`/come-funziona` o equivalente) con contenuto step-by-step del meccanismo FantaNostalgia, tabella regole attuali (non quelle ancora da decidere), FAQ ad accordion. Aggiornare la home per linkare alla nuova pagina invece di contenere tutto il testo inline.

## Acceptance criteria
- [ ] Nuova route Jinja2 SSR con template dedicato, che riusa `base.html`.
- [ ] Contenuto copre: come funziona l'asta (invariata), come funziona il mapping alter ego, come si calcolano i punteggi storici (con formula ed esempio, usando solo le regole già confermate — niente wildcard/mercato riparazione/tie-break finché non risolti).
- [ ] FAQ ad accordion (componente nuovo o esteso in `frontend/shared/design-system.js` se non coperto dal task 24) con almeno le domande già note dal mockup che non dipendono dagli spike (piattaforma richiesta, stagioni disponibili, chi può creare una lega).
- [ ] `home.html` aggiornata: la sezione "come funziona" diventa un sommario breve con link alla nuova pagina, non più il contenuto completo.
- [ ] Test: la pagina si carica senza errori, i link di navigazione (#regole, #faq, ecc.) funzionano.
- [ ] Build: nessun errore nel render Jinja2.

## Files that will be created or modified
- `backend/templates/come-funziona.html` — nuovo template
- `backend/api/routers/views.py` (o dove vivono le route SSR pubbliche) — nuova route
- `backend/templates/home.html` — sommario + link, rimozione contenuto duplicato
- `frontend/shared/design-system.js` — componente accordion FAQ, se non già presente

## Notes for Claude Code
- Non citare wildcard storica, mercato di riparazione, tie-break su gol storici o sorteggio manuale finché i task 32-35 non sono risolti — se il copy del mockup li menziona, ometterli o sostituirli con formulazioni generiche già vere oggi.
- Il FAQ "come diventare admin" può ora riferirsi al flusso reale introdotto nel task 30, se già completato — altrimenti ometterla o segnalarla come nota per un secondo passaggio.
- Aggiornare `CLAUDE_MEMORY.md` a fine task: marcare **31** come `[x]`, aggiungere branch e PR.

## Pre-PR Gate
**5-axis code review (frontend):**
- [ ] Correctness: la pagina mostra solo regole confermate, nessuna delle 4 in spike?
- [ ] Accessibility: FAQ accordion navigabile da tastiera, ARIA corretto?
- [ ] Readability: comprensibile in 5 minuti?
- [ ] Performance: nessun peso superfluo?
- [ ] Surgical: ogni riga riconducibile al requisito?
