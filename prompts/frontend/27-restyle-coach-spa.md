# 27 — Restyle Coach SPA

## Context
Depends on: task 24 completo. Nessuna dipendenza diretta da 25/26, può procedere in parallelo. Branch: `task/27-restyle-coach-spa`.

## Existing modules to read first
1. `frontend/coach/{login,index,rosa,punteggi}.html` — pagine coach attuali.
2. `frontend/coach/css/coach.css` — foglio da sostituire.
3. `ui_kits/coach/index.html` (cartella `fantanostalgia-design-system/project/`) — riferimento per la vista "Rosa/Alter Ego": usa pool dinamico per ruolo con rimozione associazione — **questo meccanismo è stato scartato** (`project-spec.md` sez. 13/14.2), mantenere il modello a select fisse per slot già presente in `rosa.html`, solo restylato.
4. `docs/design-system-brief.md` §6c — conferme con conseguenze esplicite per "Conferma e Blocca" (irreversibile).

## Objective
Sostituire `frontend/coach/css/coach.css` con i token/componenti unificati, riscrivere le pagine coach con i componenti vanilla JS del task 24 (HelpBox, ProgressBar, Message, Badge, Button, Modal), aggiungere navigazione mobile. Non cambiare la logica di associazione alter ego (select fisse per slot, nessuna rimozione post-assegnazione) né il flusso di lock.

## Acceptance criteria
- [ ] `frontend/coach/css/coach.css` non definisce più token propri.
- [ ] `rosa.html`: assegnazione alter ego con select fisse per slot (comportamento invariato), `ProgressBar` per il conteggio assegnati/totale, `Modal` di conferma per "Conferma e Blocca" con testo esplicito sull'irreversibilità.
- [ ] Lock bar sticky in fondo pagina, sparisce dopo il lock; badge "bloccata" visibile in topbar dopo la conferma.
- [ ] `punteggi.html`: tabella con `Table` del design system.
- [ ] Navigazione coach accessibile su mobile (hamburger).
- [ ] Test: flusso associazione + lock eseguito manualmente end-to-end, comportamento identico a prima del restyle (nessuna funzione di "rimuovi associazione" aggiunta).
- [ ] Build: nessun errore nelle chiamate API esistenti.

## Files that will be created or modified
- `frontend/coach/css/coach.css` — sostituito con import token unificati + stili specifici coach
- `frontend/coach/{login,index,rosa,punteggi}.html` — markup aggiornato ai componenti design system

## Notes for Claude Code
- Cambiamento chirurgico: nessuna nuova funzionalità di associazione/rimozione — solo restyle del comportamento esistente.
- La "dashboard con doppia classifica aggregata" vista in `CoachPortal.dc.html` è stata scartata (`project-spec.md` sez. 13) — non aggiungerla.
- Aggiornare `CLAUDE_MEMORY.md` a fine task: marcare **27** come `[x]`, aggiungere branch e PR.

## Pre-PR Gate
**5-axis code review (frontend):**
- [ ] Correctness: il flusso associazione/lock si comporta esattamente come prima?
- [ ] Accessibility: nessuna regressione a11y?
- [ ] Readability: comprensibile in 5 minuti?
- [ ] Performance: nessun peso bundle superfluo?
- [ ] Surgical: ogni riga riconducibile al requisito di restyle?
