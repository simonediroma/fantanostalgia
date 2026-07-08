# 24 — Libreria design system in vanilla JS

## Context
Depends on: nessuno (primo task di questa epica). Stato atteso: repo esistente e funzionante, nessuna modifica ancora applicata dal design system. Branch: `task/24-design-system-vanilla-js`.

## Existing modules to read first
1. `frontend/coach/css/coach.css`, `frontend/admin/css/admin.css`, `backend/static/style.css` — capire i 3 `:root` divergenti da sostituire (vedi `docs/design-system-brief.md` §5a).
2. `docs/context.md` — inventario moduli e vincoli di questa epica (Design System Restyling).
3. `project-spec.md` sezione 11 — inventario completo dei 13 componenti (props, varianti, stati) da portare in vanilla JS.

## Objective
Creare `frontend/shared/design-system.js` (namespace globale `window.FantaNostalgiaDS`) con i 13 componenti del design system riscritti in vanilla JS/DOM (nessuna dipendenza React), più `frontend/shared/tokens/*.css` come single source of truth di palette/tipografia/spacing/effetti. Zero regressioni visive rispetto ai mockup React di riferimento.

## Acceptance criteria
- [ ] Tutti i 13 componenti (Badge, Button, Panel, Table, EmptyState, HelpBox, Message, ProgressBar, DropZone, Input, WizardSteps, Tabs, Modal) implementati come funzioni factory vanilla JS che restituiscono un `HTMLElement`, con le stesse props/varianti/stati documentati in `project-spec.md` sez. 11.
- [ ] Nessuna dipendenza da React nel bundle finale (verificare assenza di `React`/`ReactDOM` negli import).
- [ ] Token CSS unificati in `frontend/shared/tokens/` (colors, spacing, typography, effects, fonts) — nessun `:root` duplicato altrove dopo i task 25-27.
- [ ] Estetica identica ai riferimenti: zero border-radius, ombre pixel senza blur, hover accent→accent2 istantaneo (no transition), scanline CRT.
- [ ] Test: apertura manuale di una pagina demo (`frontend/shared/demo.html`, da creare) che monta tutti i componenti e verifica visivamente parità con `fantanostalgia-design-system/project/components/*/*.card.html`.
- [ ] Build: nessun bundler necessario — verificare che il file si carichi con un semplice `<script src="...">` senza errori console.

## Files that will be created or modified
- `frontend/shared/design-system.js` — libreria componenti vanilla JS
- `frontend/shared/tokens/{colors,spacing,typography,effects,fonts}.css` — token unificati
- `frontend/shared/demo.html` — pagina di verifica visiva (non di produzione)

## Notes for Claude Code
- Riferimento 1:1 per comportamento e stile: `_ds_bundle.js` (nella cartella del design system, `fantanostalgia-design-system/project/`) contiene l'implementazione React di tutti i componenti — leggerla come specifica, non come codice da eseguire.
- `Button`, `DropZone`, `Input`, `Tabs`, `WizardSteps`, `TableRow` hanno stato interno (hover, focus, dragging) gestito con `useState` in React — in vanilla JS va rifatto con event listener e classi CSS/attributi (`data-state`), non con un framework reattivo.
- Non introdurre alcuna libreria esterna (niente lit-html, niente virtual DOM) — DOM API pure, coerente col resto dell'app.
- Il file va pensato per essere incluso da tutte e 3 le superfici (pubblica, admin, coach) senza build step, come oggi avviene con i CSS.
- Aggiornare `CLAUDE_MEMORY.md` a fine task: marcare **24** come `[x]`, aggiungere branch e PR.

## Pre-PR Gate
**5-axis code review (frontend):**
- [ ] Correctness: i componenti si comportano come da specifica?
- [ ] Accessibility: nessuna regressione a11y (tastiera, ARIA, contrasto)?
- [ ] Readability: comprensibile in 5 minuti?
- [ ] Performance: nessun peso bundle superfluo?
- [ ] Surgical: ogni riga riconducibile al requisito?
