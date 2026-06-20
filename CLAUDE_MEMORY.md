# Stato Corrente
> Versionato nel repo — unica memoria persistente tra sessioni web. Aggiornare a fine ogni task.

**Ultima sessione:** 2026-06-20
**Branch attivo:** `claude/project-analysis-features-4c2s9i`
**PR in corso:** nessuna (feature Gran Premi pronta, push effettuato — PR non ancora richiesta)

**Convenzione branch:** `task/NN-nome-breve` — un branch per task, PR verso `main`.

---

## Prossima sessione — inizia da qui

L'infrastruttura è completa. Il passo operativo rimanente è **popolare il DB con i dati storici** e giocare la prima lega.

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
- [x] **23** — Gran Premi di giornata: il presidente attiva max 2 GP/giornata (criterio: best_score/worst_defense/best_player/worst_player) con uno storico libero in palio; alla risoluzione il vincitore riceve lo storico come slot extra nel pool nostalgia e riapre l'associazione (coach) → (branch: `claude/project-analysis-features-4c2s9i`). Backend: `backend/engine/granpremio.py`, router `backend/api/routers/granpremio.py`, tabella `gran_premio` in `db.py`, helper `compute_player_breakdown` in `scoring.py`. Frontend: pannello Step 4 admin + avviso coach in `rosa.html`. Test: `backend/tests/test_granpremio.py`.

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
