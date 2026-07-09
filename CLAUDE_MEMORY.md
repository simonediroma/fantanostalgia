# Stato Corrente
> Versionato nel repo — unica memoria persistente tra sessioni web. Aggiornare a fine ogni task.

**Ultima sessione:** 2026-07-09
**Branch attivo:** `claude/task-25-responsive-followup`
**PR in corso:** nessuna — branch pushato, PR non ancora aperta (follow-up al task 25, in attesa di richiesta esplicita). Nota: task 25 (PR #80), task 26 (PR #81) e task 27 (PR #82) sono stati mergiati da Simone direttamente.

**Convenzione branch:** `task/NN-nome-breve` — un branch per task, PR verso `main`.

---

## Prossima sessione — inizia da qui

dobbiamo implementare il design system e alcune dinamiche di gioco con l'epica 4.

### Scraper disponibili (scegli uno)

**Opzione A — calcio-seriea.net (consigliata, no Cloudflare):**
```
pip install -r backend/requirements-scraper.txt
python -m backend.scrapers.calcioseriea --season 2016-2017 --export-csv out.csv
```

**Opzione B — understat (stagioni >= 2014/15, eseguire in locale):**
```
python -m backend.scrapers.understat --season 2015-2016 --export-csv out.csv
```

**Opzione C — fbref con Playwright (qualsiasi stagione, richiede browser locale):**
```
python -m backend.scrapers.fbref_pw --season 2000-2001 --export-csv out.csv
```

**Opzione D — Web Scraper Chrome manuale (fbref, vedi `docs/webscraper/`):**
Scarica sitemap da `GET /webscraper/seasons.html`, importa con Web Scraper Chrome, converti con `convert_webscraper.py`.

### Dopo lo scraping
```
POST /admin/historic/import   # importa CSV con i dati storici
```

### Per modificare pesi senza riscrappare
```
python -m backend.engine.recalculate --dump-weights pesi.json
# edita pesi.json
python -m backend.engine.recalculate --season 2016-2017 --weights-file pesi.json
```

### Coach API attiva
Gli allenatori possono fare login su `/coach/login.html` e vedere la propria rosa nostalgia. L'associazione manuale storico→attuale è disponibile da admin.

Ogni task ha un prompt dedicato in `prompts/`.
Prima di iniziare qualsiasi task: leggi il prompt corrispondente + `docs/architecture.md`.

---

## Task list

### Seed & Setup
- [x] **00** — Seed dati POC → `prompts/00-seed-poc.md` (branch: `task/00-seed-poc`)

### Epica 1 — Backend
- [x] **01** — Bootstrap (DB + Auth + Gestione Lega) → `prompts/backend/01-bootstrap.md` (branch: `task/01-bootstrap`)
- [x] **02** — Import listone Excel → `prompts/backend/02-import-listone.md` (branch: `claude/nice-albattani-4197op`)
- [x] **03** — Algoritmo mapping alter ego → `prompts/backend/03-mapping-alter-ego.md` (branch: `claude/gallant-archimedes-lwbn3i`)
- [x] **04** — Apertura buste → `prompts/backend/04-apertura-buste.md` (branch: `claude/kind-volta-oqq3rf`)
- [x] **05** — Import formazioni Excel → `prompts/backend/05-import-formazioni.md` (branch: `claude/tender-allen-uyaspn`, formato POC)
- [x] **06** — Sorteggio giornata storica → `prompts/backend/06-sorteggio-giornata.md` (branch: `claude/prossimo-task-gztmd8`)
- [x] **07** — Calcolo punteggi → `prompts/backend/07-calcolo-punteggi.md` (branch: `claude/prlssimo-task-fzkcwv`)
- [x] **08** — API classifica pubblica → `prompts/backend/08-api-classifica.md` (branch: `claude/memory-file-review-fecztn`)

### Epica 2 — Frontend
- [x] **09** — Layout base + navigazione → `prompts/frontend/09-layout-base.md` (branch: `claude/task-09-nsvx6j`)
- [x] **10** — Admin pages (setup + listone + mapping + formazioni) → `prompts/frontend/10-admin-pages.md` (branch: `claude/next-steps-ocl3qu`)
- [x] **11** — Pagine pubbliche SSR Jinja2 → `prompts/frontend/11-pagine-pubbliche.md` (branch: `claude/prossimo-task-lo5jxx`)

### Epica 3 — Utilities & DevOps
- [x] **12** — DevOps (Docker + GH Actions + Cloud Run) → `prompts/utilities/12-devops.md` (branch: `claude/task-12-pl3qh8`)
- [ ] **13** — Scraper fantagiaveno.it → `prompts/utilities/13-scraper-fantagiaveno.md` *(deprioritizzato: sostituito da approccio fbref+algoritmo)*
- [x] **14** — Scraper fbref + motore sintetico → branch `claude/data-scraping-approach-jksb5l` (PR #31)
- [x] **15** — Adattamento formato Excel reale → (branch: `claude/gifted-faraday-brf0xr`)
- [x] **16** — Redesign estetica 8-bit Sensible Soccer → `prompts/utilities/16-redesign-8bit.md` (branch: `claude/prossimo-task-hyg0j4`)

### Extra (post-epica)
- [x] **17** — Scraper fbref con Playwright (bypass Cloudflare) → (branch: `task/fbref-playwright`, PR #33)
- [x] **18** — Web Scraper Chrome sitemap + `convert_webscraper.py` → (branch: `task/fbref-webscraper-sitemap`, PR #34)
- [x] **19** — Coach API: auth allenatore, pool nostalgia, associazione manuale storico→attuale → (branch: `claude/nostalgia-player-association-u5semr`, PR #35)
- [x] **20** — Fix CI/CD: switch su Artifact Registry per Cloud Run deploy → (branch: `task/fix-artifact-registry`, PR #36)
- [x] **21** — Guida step-by-step seasons.html per multi-season scraping → (branch: `task/seasons-html-links`, PR #38)
- [x] **22** — Scraper calcio-seriea.net con ruoli reali (fonte alternativa, no Cloudflare) → (branch: `claude/upbeat-fermat-98un5f`, PR #39)
- [x] **23** — Gran Premi di giornata: il presidente attiva max 2 GP/giornata (criterio: best_score/worst_defense/best_player/worst_player) con uno storico libero in palio; alla risoluzione il vincitore riceve lo storico come slot extra nel pool nostalgia e riapre l'associazione (coach) → (branch: `claude/project-analysis-features-4c2s9i`). Backend: `backend/engine/granpremio.py`, router `backend/api/routers/granpremio.py`, tabella `gran_premio` in `db.py`, helper `compute_player_breakdown` in `scoring.py`. Frontend: pannello Step 4 admin + avviso coach in `rosa.html` + sezione "Gran Premi" nella pagina pubblica `giornata.html` (con query in `views.py`). Fix collaterale: rimossa colonna inesistente `hr.penalties_saved` dalla query giornata in `views.py` (causava 500 sulla pagina). Test: `backend/tests/test_granpremio.py`.

### Epica 4 — Design System Restyling
 
- [x] **24** — Libreria design system vanilla JS (porting da `_ds_bundle.js` React, 13 componenti) → `prompts/frontend/24-design-system-vanilla-js.md` (branch: `claude/session-planning-ragfwp`). Creati `frontend/shared/design-system.js` (namespace `window.FantaNostalgiaDS`, 13 factory function: Badge, Button, Panel, Table, EmptyState, HelpBox, Message, ProgressBar, DropZone, Input, WizardSteps, Tabs, Modal), `frontend/shared/design-system.css`, `frontend/shared/tokens/{colors,spacing,typography,effects,fonts}.css` (single source of truth, non ancora adottati dai 3 CSS esistenti — verrà fatto nei task 25-27), `frontend/shared/demo.html` (verifica visiva manuale). Verificato con Playwright headless: zero errori JS, zero riferimenti a React/ReactDOM, tutte le varianti/stati conformi a `_ds_bundle.js` e `project-spec.md` sez. 11.
- [x] **25** — Restyle pagine pubbliche SSR + sezione Hall of Fame (branch: `claude/prossimo-task-1wzl48`, dipende da 24). Nessun prompt scritto in `prompts/` per questo task (gap rispetto agli altri task, segnalato e chiarito con l'utente a inizio sessione con 2 domande: criterio Hall of Fame = top 10 cross-stagione, soglia >=5 giornate min.; migrazione token = sì, subito). Modifiche: `backend/api/main.py` monta `/shared` → `frontend/shared/` come static; `base.html` carica `/shared/design-system.css` prima di `/static/style.css`; `backend/static/style.css` ridotto da 367 a ~180 righe — rimossi `:root`, reset globale, scanline CRT, regole bare `button`/`table`/`.tabs`/`.tab-btn`/`.role-badge`/`.empty`/`.badge`/`.btn-link` (ora tutti provenienti da `frontend/shared/design-system.css`/tokens); le 5 pagine pubbliche (`home.html`, `classifica.html`, `giornata.html`, `statistiche.html`, `mapping.html`) usano ora le classi `ds-*` (ds-button, ds-table, ds-tabs__nav/__tab/__panel, ds-badge, ds-empty-state, ds-message) mantenendo identica la logica JS esistente (tab switching riscritto per usare `hidden` + `aria-selected` invece di classi `.active`). Fix collaterale nel design system condiviso: aggiunta regola `.ds-message[hidden] { display: none; }` in `frontend/shared/design-system.css` — senza, l'attributo `hidden` nativo veniva sovrascritto da `display:flex` del componente (bug latente scoperto verificando la home con Playwright). Hall of Fame: nuova query cross-stagione in `views.py::home()` (`player_historic` JOIN `historic_rating`, `HAVING n >= 5 LIMIT 10`), sezione mostrata solo se `hall_of_fame` non vuoto. Test: `backend/tests/test_home_hall_of_fame.py` (2 test: soglia minima giornate, presenza sezione). Verificato visivamente con Playwright headless (screenshot + interazioni tab/login) su tutte le 5 pagine con dati POC (`database/seed_poc.py`); suite completa 172 passed, 3 fallimenti pre-esistenti non correlati in `test_scoring.py` (confermato con `git stash` su main pulito). **Follow-up 2026-07-09** (branch `claude/task-25-responsive-followup`): dopo che l'utente ha aggiunto `prompts/frontend/25-restyle-pagine-pubbliche.md` a posteriori (commit diretto su `main`), verificati gli acceptance criteria e trovati 3 gap non coperti dalla PR #80: mancava il componente Panel per le card (`league-card`, `step`, `auth-card` in `home.html` ora usano `ds-panel`), mancava la navigazione mobile con hamburger (aggiunto `#navToggle`/`#siteNav` in `base.html` + CSS `.nav-toggle`/`nav.open` sotto 640px), le tabelle dense di classifica/giornata usavano solo `overflow-x:auto` silenzioso invece del pattern stack-a-card richiesto esplicitamente dal prompt (aggiunta classe `.ds-table-stack` con `data-label` sui `<td>`, attiva sotto 480px). Verificato con Playwright a 3 viewport (1200/768/375px), zero errori console, hamburger e stacking tabelle testati via interazione JS.
- [x] **26** — Restyle Admin SPA (wizard 4 step, incl. invito coach esistente) → nessun prompt scritto in `prompts/` (gap segnalato e chiarito con l'utente a inizio sessione: scelto restyle CSS-only, come task 25, invece di componentizzazione JS completa con le factory function di `design-system.js`). Branch: `claude/prossimo-task-vwa0s9` (non `task/26-restyle-admin-spa` come da convenzione — il branch è imposto dall'harness per questa sessione). Modifiche: `frontend/admin/index.html` carica `/shared/design-system.css` prima di `css/admin.css`; tutte le classi custom (`.panel`→`ds-panel ds-panel--default`+`ds-panel__title` su h4, `button`/`.secondary`/`.danger`→`ds-button`+varianti, `.table-wrap`+`table`→`ds-table-wrap`+`ds-table`, `.msg`→`ds-message`, `.empty`→`ds-empty-state`+`ds-empty-state__message`, `.badge`→`ds-badge`, `.drop-zone`→`ds-dropzone`, `.modal-overlay`/`.modal-box`→`ds-modal-overlay`/`ds-modal`, `.steps`/`.step`→`ds-wizard-steps`/`ds-wizard-steps__step`) sostituite sia nel markup statico sia nei template string generati da JS (dashboard leghe, tabella manager, tabella assegnazione giocatori con badge ruolo cyan, stato allenatori, riepiloghi listone/mapping/punteggi, Gran Premi, mapping completo buste). Refactor minimo della logica JS (non della UX): step indicator ora usa `data-state="active"/"done"` invece di classi multiple; drop zone usa `data-dragging="true"` invece di `.drag-over`; modal invito usa l'attributo `hidden` invece di `.open` (stesso pattern già adottato in `home.html` nel task 25). `frontend/admin/css/admin.css` ridotto da 419 a 196 righe — rimosse le regole duplicate (reset, root vars, button, panel, table, messages/empty, wizard steps indicator, drop-zone, modal, badge, h4) ora tutte fornite da `frontend/shared/design-system.css`/tokens; mantenute solo le regole page-shell (login, topbar, aside, content, page routing) e quelle non coperte dal design system (form/label/input/select bare-tag, perché i form dell'admin non sono stati convertiti al componente `ds-input` — restano `<label>`/`<input>` semplici). Verificato con Playwright headless (login → dashboard → tutti e 4 gli step del wizard → modal invito allenatore) su dati POC: zero errori JS/console, visivamente conforme al design system. Suite di test: 172 passed, stessi 3 fallimenti pre-esistenti in `test_scoring.py` (non correlati, già documentati nel task 25) + 3 errori pre-esistenti in `test_fbref_scraper.py` per `pytest-mock` mancante nell'ambiente (non correlato, non toccato da questo task).
- [x] **27** — Restyle Coach SPA → nessun prompt scritto in `prompts/` (gap segnalato e chiarito con l'utente a inizio sessione con 2 domande: confermato approccio CSS-only come 25/26 invece di componentizzazione JS completa; confermato di includere anche `punteggi.html`, non citato nelle note della sessione precedente ma parte della Coach SPA). Branch: `claude/prossimo-task-6xloxn` (non `task/27-restyle-coach-spa` come da convenzione — imposto dall'harness). Modifiche: le 4 pagine (`login.html`, `index.html`, `rosa.html`, `punteggi.html`) caricano `/shared/design-system.css` prima di `css/coach.css`; classi custom sostituite sia nel markup statico sia nei template string JS: `.tabs`/`.tab-btn`/`.tab-panel`→`ds-tabs__nav`/`ds-tabs__tab` (aria-selected) + attributo `hidden` sui pannelli (stesso pattern di `home.html` task 25), `.login-card`→aggiunta `ds-panel ds-panel--default`, `button`/`.secondary`/`.danger`→`ds-button`+varianti, `.msg`→`ds-message`, `.panel`→`ds-panel ds-panel--default`/`ds-panel--accent` (banner Gran Premio vinto), `.badge`/`.badge-green`/`.badge-red`→`ds-badge`+varianti, `.empty`→`ds-empty-state`+`ds-empty-state__message`, tabella punteggi (generata via `innerHTML` in `punteggi.html`, non aveva classe prima)→`ds-table-wrap`+`ds-table`+`ds-table__row`, progress bar del lock-bar in `rosa.html`→`ds-progress-bar__track`/`__fill` al posto di `.progress-bar-wrap`/`.progress-bar-fill` custom. `frontend/coach/css/coach.css` ridotto da 332 a 159 righe — rimossi `:root`, reset globale, scanline CRT, `.badge*`, `.tabs`/`.tab-btn*`/`.tab-panel*`, `button`/`.secondary`/`.danger`, `.msg*`, `.panel*`, `.progress-bar-wrap`/`.progress-bar-fill`, `.empty` (ora tutti forniti da `frontend/shared/design-system.css`/tokens); mantenute solo le regole page-shell (topbar, content, login-wrap/login-card dimensioni) e quelle non coperte dal design system (form/label/input/select bare-tag — stessa scelta di admin/task 26 — e le classi dominio-specifiche `role-section`/`role-header`/`player-row`/`player-card`/`arrow`/`assign-select`/`league-card`/`lock-bar`, non parte del design system condiviso). Verificato end-to-end con Playwright headless su dati POC (`database/seed_poc.py` + invito/registrazione coach + assegnazione pool nostalgia via `/admin/league/{id}/mapping/assign-pools`): login → tab registrati → le mie leghe → rosa (con pool assegnato, panel/badge/progress-bar/player-row visibili) → punteggi (tabella ds-table) — zero errori JS/console (gli unici eventi in console sono `ERR_CONNECTION_RESET` sul fetch dei Google Fonts, dovuto al sandbox di rete, non correlato). Suite di test: 172 passed, stessi 3 fallimenti pre-esistenti in `test_scoring.py` + 3 errori pre-esistenti in `test_fbref_scraper.py` (pytest-mock mancante), entrambi non correlati e già documentati nei task 25/26.
- [x] **28** — Pattern esplicativi (help-box, file-spec, confirm-dialog) → nessun prompt scritto in `prompts/frontend/` (gap segnalato e chiarito con l'utente a inizio sessione con 3 domande: file-spec limitato alle 2 upload già in UI — rose/formazioni Excel, escluso i 3 flussi CLI-only di `docs/design-system-brief.md` §6b; confirm-dialog limitato alle 3 conferme esplicite della spec §6c — Apri buste, Chiudi periodo associazioni, Conferma e Blocca; niente template Excel scaricabili — Rose_esempio.xlsx/Formazioni_esempio.xlsx restano fuori scope, nessuna nuova funzione oltre al restyling). Branch: `claude/prossimo-task-h8zea3` (imposto dall'harness). Aggiunti 2 nuovi componenti alla libreria design system (`frontend/shared/design-system.js`): `FileSpec({format, structure, note})` — box con badge formato file + descrizione struttura attesa, stile analogo a HelpBox ma bordo tratteggiato; `confirmDialog({title, message, consequence, confirmLabel, cancelLabel, danger})` — wrapper Promise-based sopra `Modal`+`Button` già esistenti (risolve `true`/`false`), pensato per sostituire `confirm()` nativo con pattern `if (!await DS.confirmDialog({...})) return;`. CSS in `frontend/shared/design-system.css`: `.ds-file-spec*` e `.ds-confirm-dialog*` (variante `--danger` con bordo/titolo rossi). Demo aggiornato in `frontend/shared/demo.html`. **Prima volta che `design-system.js` viene effettivamente caricato ed eseguito in produzione** (task 24-27 avevano riusato solo le classi CSS, mai le factory JS) — aggiunto `<script src="/shared/design-system.js"></script>` in `frontend/admin/index.html` (prima di `js/api.js`) e in `frontend/coach/rosa.html` (in `<head>`), più `const DS = window.FantaNostalgiaDS;` nei rispettivi script inline. Admin: Step 1 (Carica listone) e Step 4 (Carica formazioni) ora hanno HelpBox + FileSpec con la struttura Excel attesa (da `CLAUDE_MEMORY.md`); i paragrafi statici già esistenti in Step 2 (assegna pool, inviti, chiudi periodo) e Step 3 (apertura buste) sono stati convertiti da `<p style="...">` a `ds-help-box`/`ds-help-box--warn`; le due righe rosse "Operazione irreversibile" separate sono state rimosse a favore del testo `consequence` mostrato nel confirm-dialog al momento del click. I 2 `confirm()` nativi in admin (`closeAssociationsBtn`, `revealBtn`) sostituiti con `DS.confirmDialog(...)`. Coach `rosa.html`: aggiunto nuovo HelpBox statico "Associa l'alter ego" (prima non esisteva alcuna spiegazione del meccanismo di associazione storico→attuale), mostrato/nascosto insieme a `#main`; il `confirm()` nativo di `lockBtn` sostituito con `DS.confirmDialog(...)`. Verificato end-to-end con Playwright headless su dati POC (`database/seed_poc.py` + pool assignment + invito/registrazione coach via API dirette): tutti i 4 step admin (help-box/file-spec visibili, confirm-dialog apre/chiude correttamente su Annulla senza nodi DOM residui), flusso coach completo incluso click reale su "Conferma e Blocca" → dialog → "Blocca" → lock riuscito con badge "Bloccato". Zero errori console/JS (unico evento è `ERR_CONNECTION_RESET` su Google Fonts, dovuto al sandbox di rete, non correlato — già documentato nei task precedenti). Suite di test: 172 passed, stessi 3 fallimenti pre-esistenti in `test_scoring.py` + 3 errori pre-esistenti in `test_fbref_scraper.py` (non correlati, già documentati nei task 25-27).
- [ ] **29** — Gestione multi-lega in Admin → `prompts/frontend/29-multi-lega-admin.md` (branch: `task/29-multi-lega-admin`, dipende da 26)
- [ ] **30** — Elevazione coach → admin → `prompts/backend/30-elevazione-coach-admin.md` (branch: `task/30-elevazione-coach-admin`, dipende da 26, 27 — ⚠️ possibile modifica a `database/schema.sql`, richiede approvazione esplicita di Simone prima di procedere)
- [ ] **31** — Pagina pubblica "Come Funziona" standalone → `prompts/frontend/31-pagina-come-funziona.md` (branch: `task/31-pagina-come-funziona`, dipende da 25)
- ⏳ **32** — Wildcard storica — SPIKE PENDING → `docs/spike-32.md`
- ⏳ **33** — Mercato di riparazione (gennaio) — SPIKE PENDING → `docs/spike-33.md`
- ⏳ **34** — Tie-break su gol storici — SPIKE PENDING → `docs/spike-34.md`
- ⏳ **35** — Sorteggio giornata con override manuale — SPIKE PENDING → `docs/spike-35.md`
---
 
## Prossima sessione — inizia da qui (per questa epica)

Task 24, 25, 26, 27 e 28 completati (vedi task list sopra). Tutti e 3 i CSS applicativi sono migrati ai token/design-system condivisi, e `frontend/shared/design-system.js` è ora effettivamente caricato ed eseguito in produzione (admin + coach), non solo come libreria CSS. Prossimo passo possibile: **task 29** (Gestione multi-lega in Admin, dipende da 26, sbloccato) oppure **task 31** (Pagina pubblica "Come Funziona", dipende da 25, sbloccato) — **task 30** resta HIGH risk (possibile modifica a `schema.sql`, richiede approvazione esplicita di Simone prima di procedere). **Attenzione:** come per 25-28, verificare a inizio sessione se esiste già un prompt in `prompts/frontend/29-multi-lega-admin.md` / `prompts/frontend/31-pagina-come-funziona.md`; se assente, chiarire lo scope con l'utente prima di procedere invece di assumere (è successo per tutti i task 25-28 finora). Nota: il branch task 28 (`claude/prossimo-task-h8zea3`) è pushato ma senza PR aperta.

Ordine di esecuzione: 24 (fatto) → 25 (fatto) → 26 (fatto) → 27 (fatto) → 28 (fatto) → 29 (dopo 26, sbloccato) → 30 (dopo 26+27, HIGH risk, sbloccato ma richiede approvazione su schema.sql) → 31 (dopo 25, sbloccato). Le task 32-35 restano bloccate finché non vengono risolte con `/cdp:spike-integrate` dopo aver riempito i rispettivi `docs/spike-NN.md`.
 
## Decisioni prese epica 4
 
- Modalità: **FEATURE-ADDITION** su repo esistente `fantanostalgia`.
- Scartate esplicitamente (non implementare): dashboard KPI admin, sezione manager standalone, catalogo stagioni esplorabile, coach dashboard doppia classifica, rimozione associazione alter ego pre-lock, import listone via API piattaforme esterne (vedi `project-spec.md` sez. 13 per l'elenco completo).
- Il "link invito coach con token" **esiste già** nell'app — task 26 lo restyla soltanto, non lo ricostruisce.
- Vincolo architetturale: nessuna dipendenza React nel prodotto finale — il design system va portato in vanilla JS (task 24).
- Numerazione continua da dove si era fermata l'epica 3 (ultimo task completato: 23 — Gran Premi di giornata).
 
---

## Formato Excel reale (da Rose_erculotuo.xlsx e Formazioni_erculotuo_36_giornata.xlsx)

### Rose (listone con rose):
- Sheet unico "TutteLeRose", 9 colonne (A-I)
- Due squadre affiancate: left (A-D), separator col E vuota, right (F-I)
- Colonne: Ruolo | Calciatore | Squadra (reale, es. 'Juve') | Costo (prezzo asta)
- Header squadra: col A = nome squadra fanta, col F = nome squadra fanta (right)
- Fine blocco: 'Crediti Residui: X'
- 10 squadre × ~25 giocatori = 250 giocatori totali
- Parser: `_parse_rose_rows` in `backend/api/routers/players.py`
- Auto-assegna giocatori ai manager per `team_name` (case-insensitive)

### Formazioni (risultati giornata):
- Sheet per giornata, es. "Formazioni 36 giornata", 11 colonne (A-K)
- Due match affiancati: left (A-E), col F = risultato (es. '0-1'), right (G-K)
- Header match: col A = squadra sinistra, col F = 'X-Y', col G = squadra destra (UPPERCASE)
- Colonne per ogni squadra: Ruolo | Calciatore | vuota | Voto_no_bonus | Voto_con_bonus
- 'Panchina' separa titolari da panchina (is_starter = 0)
- 'TOTALE: XX,YY' marca fine della squadra
- '-' = giocatore senza voto (sv o non entrato)
- Parser: `_parse_formazioni_rows` in `backend/api/routers/lineups.py`
- Lookup manager per `team_name` (case-insensitive) oltre che per `name`

---

## Coach API

- Router: `backend/api/routers/coach.py`
- Frontend: `frontend/coach/login.html`, `frontend/coach/index.html`, `frontend/coach/rosa.html`
- Endpoint chiave: `GET /coach/league/{id}/rosa` — mostra pool nostalgia del manager con associazioni storico→attuale
- Associazione manuale disponibile da admin panel

---

## Blockers

- Cloudflare su fbref.com può bloccare richieste da datacenter IP (Cloud Run). Usare lo scraper in locale oppure usare `calcio-seriea.net` che non è soggetto a questo blocco.

## PR completate

- [#1](https://github.com/simonediroma/fantanostalgia/pull/1) — task/00-seed-poc ✓ mergiata
- [#2](https://github.com/simonediroma/fantanostalgia/pull/2) — task/01-bootstrap ✓ mergiata
- [#3](https://github.com/simonediroma/fantanostalgia/pull/3) — task/02-import-listone ✓ mergiata
- [#7](https://github.com/simonediroma/fantanostalgia/pull/7) — task/03-mapping-alter-ego (`claude/gallant-archimedes-lwbn3i`) ✓ mergiata
- [#8](https://github.com/simonediroma/fantanostalgia/pull/8) — task/04-apertura-buste (`claude/kind-volta-oqq3rf`) ✓ mergiata
- [#9](https://github.com/simonediroma/fantanostalgia/pull/9) — task/05-import-formazioni (`claude/tender-allen-uyaspn`) ✓ mergiata
- [#10](https://github.com/simonediroma/fantanostalgia/pull/10) — task/06-sorteggio-giornata (`claude/prossimo-task-gztmd8`) ✓ mergiata
- [#11](https://github.com/simonediroma/fantanostalgia/pull/11) — task/07-calcolo-punteggi (`claude/prlssimo-task-fzkcwv`) ✓ mergiata
- [#12](https://github.com/simonediroma/fantanostalgia/pull/12) — task/08-api-classifica (`claude/memory-file-review-fecztn`) ✓ mergiata
- [#13](https://github.com/simonediroma/fantanostalgia/pull/13) — task/09-layout-base (`claude/task-09-nsvx6j`) ✓ mergiata
- [#16](https://github.com/simonediroma/fantanostalgia/pull/16) — task/11-pagine-pubbliche (`claude/prossimo-task-lo5jxx`) ✓ mergiata
- [#17](https://github.com/simonediroma/fantanostalgia/pull/17) — prompt task 16 aggiunto (`claude/8bit-aesthetic-redesign-459mxp`) ✓ mergiata
- [#31](https://github.com/simonediroma/fantanostalgia/pull/31) — scraper fbref + RatingWeights + CSV export/import + understat (`claude/data-scraping-approach-jksb5l`) ✓ mergiata
- [#32](https://github.com/simonediroma/fantanostalgia/pull/32) — requirements-scraper.txt (`task/requirements-scraper`) ✓ mergiata
- [#33](https://github.com/simonediroma/fantanostalgia/pull/33) — scraper fbref con Playwright per bypass Cloudflare (`task/fbref-playwright`) ✓ mergiata
- [#34](https://github.com/simonediroma/fantanostalgia/pull/34) — Web Scraper Chrome sitemap + convert_webscraper.py (`task/fbref-webscraper-sitemap`) ✓ mergiata
- [#35](https://github.com/simonediroma/fantanostalgia/pull/35) — Coach API: auth, nostalgia pool, associazione manuale (`claude/nostalgia-player-association-u5semr`) ✓ mergiata
- [#36](https://github.com/simonediroma/fantanostalgia/pull/36) — Fix CI/CD: Artifact Registry (`task/fix-artifact-registry`) ✓ mergiata
- [#38](https://github.com/simonediroma/fantanostalgia/pull/38) — Guida seasons.html per multi-season scraping (`task/seasons-html-links`) ✓ mergiata
- [#39](https://github.com/simonediroma/fantanostalgia/pull/39) — Scraper calcio-seriea.net con ruoli reali (`claude/upbeat-fermat-98un5f`) ✓ mergiata
- [#80](https://github.com/simonediroma/fantanostalgia/pull/80) — task/25-restyle pagine pubbliche + Hall of Fame (`claude/prossimo-task-1wzl48`) ✓ mergiata
