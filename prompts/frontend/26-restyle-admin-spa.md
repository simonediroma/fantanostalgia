# 26 — Restyle Admin SPA

## Context
Depends on: task 24 completo. Il task 25 (pagine pubbliche) può procedere in parallelo, nessuna dipendenza diretta. Branch: `task/26-restyle-admin-spa`.

## Existing modules to read first
1. `frontend/admin/index.html` e `frontend/admin/js/{api,auth,league,listone,mapping,matchday}.js` — struttura wizard 4 step attuale (Listone→Mapping→Buste→Giornate).
2. `frontend/admin/css/admin.css` — foglio da sostituire.
3. `ui_kits/admin/index.html` (cartella `fantanostalgia-design-system/project/`) — riferimento diretto: questo mockup React implementa già il flusso wizard con i componenti del design system, incluso il modal "Link invito" con token — **questa funzionalità esiste già nell'app attuale**, va solo restylata, non ricostruita.
4. `docs/design-system-brief.md` §6b — tabella file da caricare/scaricare (listone, formazioni) da corredare di help-box (rimandato al task 28, non a questo task).

## Objective
Sostituire `frontend/admin/css/admin.css` con i token/componenti unificati, riscrivere il markup del wizard 4 step usando i componenti vanilla JS del task 24 (WizardSteps, Panel, DropZone, Table, Modal, Button, Badge), aggiungere navigazione mobile. Non cambiare la logica del wizard (4 step, ordine, chiamate API) — solo il layer di presentazione.

## Acceptance criteria
- [ ] `frontend/admin/css/admin.css` non definisce più token propri.
- [ ] Wizard 4 step renderizzato con `WizardSteps` del design system; navigazione solo all'indietro sugli step già completati (comportamento invariato).
- [ ] Upload listone/formazioni usa il componente `DropZone`; anteprima mapping usa `Table`.
- [ ] Modal "Link invito" (già esistente) usa il componente `Modal` del design system, stesso comportamento di oggi (genera link con token, copiabile).
- [ ] Step "Apri Buste" mantiene la doppia conferma (bottone + Modal) già presente, ora con `Button` variant danger.
- [ ] Sidebar/navigazione admin accessibile su mobile (hamburger), non più semplicemente nascosta sotto breakpoint.
- [ ] Test: flusso completo dei 4 step eseguito manualmente end-to-end senza errori console, comportamento identico a prima del restyle.
- [ ] Build: nessun errore nelle chiamate API esistenti (`admin/js/api.js` invariato salvo dove strettamente necessario per il nuovo markup).

## Files that will be created or modified
- `frontend/admin/css/admin.css` — sostituito con import token unificati + stili specifici admin
- `frontend/admin/index.html` — markup aggiornato ai componenti design system
- `frontend/admin/js/{listone,mapping,matchday,league}.js` — aggiornati solo per il binding ai nuovi componenti, logica invariata

## Notes for Claude Code
- Cambiamento chirurgico: la logica di business del wizard (validazioni, chiamate API, stato step) non va toccata — solo il rendering.
- Il modello "6 sezioni con dashboard e sidebar permanente" visto in `AdminPanel.dc.html` (l'altro mockup del design system) **non fa parte di questo task** — è stato scartato/rimandato (vedi `project-spec.md` sez. 14.1): l'admin resta il wizard attuale.
- Non introdurre qui la gestione multi-lega (task 29) né l'elevazione admin (task 30) — solo restyle del flusso esistente.
- Aggiornare `CLAUDE_MEMORY.md` a fine task: marcare **26** come `[x]`, aggiungere branch e PR.

## Pre-PR Gate
**5-axis code review (frontend):**
- [ ] Correctness: il wizard si comporta esattamente come prima?
- [ ] Accessibility: nessuna regressione a11y?
- [ ] Readability: comprensibile in 5 minuti?
- [ ] Performance: nessun peso bundle superfluo?
- [ ] Surgical: ogni riga riconducibile al requisito di restyle, nessuna nuova feature introdotta?
