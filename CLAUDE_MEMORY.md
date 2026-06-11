# Stato Corrente
> Versionato nel repo — unica memoria persistente tra sessioni web. Aggiornare a fine ogni task.

**Ultima sessione:** 2026-06-11
**Branch attivo:** `claude/prossimo-task-hyg0j4`
**PR in corso:** task 16 pronto per review — branch `claude/prossimo-task-hyg0j4`

**Convenzione branch:** `task/NN-nome-breve` — un branch per task, PR verso `main`.

---

## Prossima sessione — inizia da qui

1. Mergia PR task 16 (`claude/prossimo-task-hyg0j4`) se approvata
2. Implementa task 12 — DevOps seguendo `prompts/utilities/12-devops.md` (Docker + GH Actions + Cloud Run)
3. Oppure task 13 (scraper fantagiaveno) o task 15 (adattamento Excel reale) secondo priorità
4. Quando disponibile il formato Excel reale delle formazioni, aggiorna il parser in `backend/api/routers/lineups.py` (funzione `_parse_excel`)

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
- [ ] **12** — DevOps (Docker + GH Actions + Cloud Run) → `prompts/utilities/12-devops.md`
- [ ] **13** — Scraper fantagiaveno.it → `prompts/utilities/13-scraper-fantagiaveno.md`
- [ ] **14** — Scraper fbref + motore sintetico → `prompts/utilities/14-scraper-fbref-sintetico.md`
- [ ] **15** — Adattamento formato Excel reale → `prompts/utilities/15-adattamento-excel-reale.md`
- [x] **16** — Redesign estetica 8-bit Sensible Soccer → `prompts/utilities/16-redesign-8bit.md` (branch: `claude/prossimo-task-hyg0j4`)
  - Quando disponibili gli Excel definitivi (formazioni + listone), verificare:
    1. Formato colonne listone reale → aggiornare alias in `backend/api/routers/players.py` (`_find_columns`)
    2. Formato colonne formazioni reale → aggiornare parser in `backend/api/routers/lineups.py` (`_parse_excel`)
    3. Aggiornare `prompts/backend/05-import-formazioni.md` con il formato reale
    4. Aggiungere test con file Excel reale (o campione anonimizzato)

---

## Blockers

- Formato Excel formazioni reale da verificare quando disponibile (aggiornare `prompts/backend/05-import-formazioni.md`)
- Struttura HTML fantagiaveno.it da verificare prima di implementare scraper (task 13)

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
