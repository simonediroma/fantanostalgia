# Stato Corrente
> Versionato nel repo — unica memoria persistente tra sessioni web. Aggiornare a fine ogni task.

**Ultima sessione:** 2026-06-10
**Branch attivo:** `claude/nice-albattani-4197op`
**PR in corso:** [#3](https://github.com/simonediroma/fantanostalgia/pull/3) — task/02-import-listone

**Convenzione branch:** `task/NN-nome-breve` — un branch per task, PR verso `main`.

---

## Prossima sessione — inizia da qui

1. Mergia PR #3 (`claude/nice-albattani-4197op` → `main`) se approvata
2. Crea branch `task/03-mapping-alter-ego` da `main`
3. Implementa task 03 seguendo `prompts/backend/03-mapping-alter-ego.md`
4. Apri PR `task/03-mapping-alter-ego` → `main`

Ogni task ha un prompt dedicato in `prompts/`.
Prima di iniziare qualsiasi task: leggi il prompt corrispondente + `docs/architecture.md`.

---

## Task list

### Seed & Setup
- [x] **00** — Seed dati POC → `prompts/00-seed-poc.md` (branch: `task/00-seed-poc`)

### Epica 1 — Backend
- [x] **01** — Bootstrap (DB + Auth + Gestione Lega) → `prompts/backend/01-bootstrap.md` (branch: `task/01-bootstrap`)
- [x] **02** — Import listone Excel → `prompts/backend/02-import-listone.md` (branch: `claude/nice-albattani-4197op`)
- [ ] **03** — Algoritmo mapping alter ego → `prompts/backend/03-mapping-alter-ego.md`
- [ ] **04** — Apertura buste → `prompts/backend/04-apertura-buste.md`
- [ ] **05** — Import formazioni Excel → `prompts/backend/05-import-formazioni.md`
- [ ] **06** — Sorteggio giornata storica → `prompts/backend/06-sorteggio-giornata.md`
- [ ] **07** — Calcolo punteggi → `prompts/backend/07-calcolo-punteggi.md`
- [ ] **08** — API classifica pubblica → `prompts/backend/08-api-classifica.md`

### Epica 2 — Frontend
- [ ] **09** — Layout base + navigazione → `prompts/frontend/09-layout-base.md`
- [ ] **10** — Admin pages (setup + listone + mapping + formazioni) → `prompts/frontend/10-admin-pages.md`
- [ ] **11** — Pagine pubbliche SSR Jinja2 → `prompts/frontend/11-pagine-pubbliche.md`

### Epica 3 — Utilities & DevOps
- [ ] **12** — DevOps (Docker + GH Actions + Cloud Run) → `prompts/utilities/12-devops.md`
- [ ] **13** — Scraper fantagiaveno.it → `prompts/utilities/13-scraper-fantagiaveno.md`
- [ ] **14** — Scraper fbref + motore sintetico → `prompts/utilities/14-scraper-fbref-sintetico.md`

---

## Blockers

- Formato Excel formazioni reale da verificare quando disponibile (aggiornare `prompts/backend/05-import-formazioni.md`)
- Struttura HTML fantagiaveno.it da verificare prima di implementare scraper (task 13)

## PR completate

- [#1](https://github.com/simonediroma/fantanostalgia/pull/1) — task/00-seed-poc (aperta, da mergiare)
- [#2](https://github.com/simonediroma/fantanostalgia/pull/2) — task/01-bootstrap (aperta, da mergiare)
- [#3](https://github.com/simonediroma/fantanostalgia/pull/3) — task/02-import-listone (aperta, da mergiare)
