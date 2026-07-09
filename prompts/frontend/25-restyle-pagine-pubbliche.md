# 25 — Restyle pagine pubbliche SSR + sezione Hall of Fame

## Context
Depends on: task 24 completo (`frontend/shared/design-system.js` e token disponibili). Branch: `task/25-restyle-pagine-pubbliche`.

## Existing modules to read first
1. `backend/templates/base.html` — layout condiviso (header, nav, footer, scanline) da aggiornare per usare i nuovi token/font.
2. `backend/templates/{home,classifica,giornata,statistiche,mapping}.html` — pagine da restylare.
3. `backend/static/style.css` — foglio da sostituire con i token unificati del task 24.
4. `docs/design-system-brief.md` §5b — carenze di responsiveness da colmare (niente hamburger, breakpoint non sistematici).

## Objective
Sostituire `backend/static/style.css` con i token/componenti di `frontend/shared/`, applicare il restyle a tutte le pagine pubbliche SSR, aggiungere navigazione mobile funzionante (hamburger) e il pattern di stacking per le tabelle dense (classifica, giornata). Aggiungere alla home la sezione "Top Player · Hall of Fame" (classifica cross-stagione dei voti medi storici più alti).

## Acceptance criteria
- [ ] `backend/static/style.css` non definisce più token propri — importa/usa `frontend/shared/tokens/*.css`.
- [ ] Tutte le pagine pubbliche renderizzano con i componenti del design system dove applicabile (Table per classifica/giornata/statistiche, Panel per card, Badge per stati).
- [ ] Sotto il breakpoint mobile la navigazione resta accessibile tramite menu hamburger (oggi sparisce senza sostituto).
- [ ] Le tabelle dense (classifica, giornata) usano un pattern leggibile su mobile (stack a card o scroll orizzontale esplicito, non solo `overflow-x:auto` silenzioso).
- [ ] Sezione Hall of Fame in home: nuova query backend (sola lettura) che estrae i N giocatori con media voto storico più alta cross-stagione, renderizzata con il componente Table.
- [ ] Test: caricamento di ciascuna pagina pubblica senza errori console, verifica manuale a 3 viewport (desktop, tablet, mobile).
- [ ] Build: nessun errore server-side nel render Jinja2 delle pagine modificate.

## Files that will be created or modified
- `backend/static/style.css` — sostituito con import dei token unificati + stili specifici pagine pubbliche
- `backend/templates/base.html` — nav mobile, include design-system.js
- `backend/templates/home.html` — restyle + sezione Hall of Fame
- `backend/templates/{classifica,giornata,statistiche,mapping}.html` — restyle
- Query Hall of Fame: nuovo helper in `backend/api/routers/standings.py` o `views.py` (verificare dove vivono già le query di rendering SSR prima di aggiungerne una nuova)

## Notes for Claude Code
- Non toccare la logica di calcolo punteggi (`backend/engine/scoring.py`) — la query Hall of Fame è una semplice aggregazione di lettura sui dati storici già presenti, non richiede nuova logica di business.
- Il form di login/registrazione in home ha un punto aperto: nel mockup del design system il campo si chiama `email` ma il flusso reale usa solo username + codice invito (vedi `project-spec.md` sez. 14.3) — non aggiungere un campo email reale, mantieni il comportamento attuale (solo username), il naming `email` nel mockup è fuorviante.
- Copertura scanline CRT: valutare riduzione opacità sotto il breakpoint mobile per performance, come suggerito in `docs/design-system-brief.md` §7d — non è un requisito bloccante, solo un miglioramento se semplice.
- Aggiornare `CLAUDE_MEMORY.md` a fine task: marcare **25** come `[x]`, aggiungere branch e PR.

## Pre-PR Gate
**5-axis code review (frontend):**
- [ ] Correctness: le pagine si comportano come da specifica?
- [ ] Accessibility: nessuna regressione a11y (tastiera, ARIA, contrasto)?
- [ ] Readability: comprensibile in 5 minuti?
- [ ] Performance: nessun re-render/peso bundle superfluo?
- [ ] Surgical: ogni riga riconducibile al requisito?
