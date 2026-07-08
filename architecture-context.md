# Architecture Context — FantaNostalgia

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Frontend | HTML / Vanilla JS — Jinja2 SSR per le pagine pubbliche + 2 SPA vanilla JS (admin, coach) |
| Backend | Python 3.11 + FastAPI |
| Database | SQLite su GCS (Google Cloud Storage) |
| Auth | Sessione/token custom — login admin + login coach con token d'invito (dettagli implementativi non documentati) |
| Deploy | GCP Cloud Run (backend + frontend nginx separati), GitHub Actions (CI/CD), Cloud Scheduler (cron settimanale), Secret Manager |

## Repository Structure
- `backend/api/` — FastAPI app (`main.py`, `db.py`) + `routers/` (league, players, mapping, matchday, standings, coach, historic, granpremio)
- `backend/engine/` — logica di business: mapping alter ego, scoring, synthetic ratings, recalculate
- `backend/scrapers/` — ingestion dati storici (fbref, fbref_pw/Playwright, understat, calcio-seriea, convert_webscraper)
- `backend/templates/` — pagine pubbliche SSR Jinja2 (home, classifica, giornata, statistiche, mapping, base)
- `backend/static/style.css` — CSS pagine pubbliche (uno dei 3 fogli da unificare)
- `backend/tests/` — test pytest
- `frontend/admin/` — SPA admin: wizard 4 step (Listone→Mapping→Buste→Giornate), `js/{api,auth,league,listone,mapping,matchday}.js`, `css/admin.css`
- `frontend/coach/` — SPA coach: login, dashboard, rosa (associazione alter ego + lock), punteggi; `css/coach.css`
- `database/schema.sql` — schema SQLite (protetto, vedi sotto)
- `docs/` — `architecture.md`, `design-system-brief.md`, `webscraper/`
- `prompts/` — prompt per-task (backend/, frontend/, utilities/)
- `scripts/`, `.github/workflows/` (deploy.yml, weekly-draw.yml)

> Nota: l'albero in `docs/architecture.md` (che ipotizza `frontend/src/components`, `frontend/public/`) è superato/aspirazionale. La struttura reale confermata è quella sopra, con `frontend/admin/` e `frontend/coach/` come SPA separate.

## Key Modules
| Module | Path | Responsibility |
|--------|------|----------------|
| API entry | `backend/api/main.py` | FastAPI app entry point |
| DB layer | `backend/api/db.py` | Connessione SQLite + sync su GCS |
| Routers | `backend/api/routers/*.py` | Endpoint per dominio (lega, listone, mapping, giornate, classifiche, coach, storico, gran premi) |
| Engine | `backend/engine/*.py` | Algoritmo mapping alter ego, calcolo punteggi, voti sintetici |
| Scrapers | `backend/scrapers/*.py` | Import dati storici da fonti esterne |
| Admin SPA | `frontend/admin/` | Wizard operativo lega (upload listone/formazioni, mapping, buste) |
| Coach SPA | `frontend/coach/` | Associazione storico→attuale, lock rosa, punteggi personali |
| Schema DB | `database/schema.sql` | Schema SQLite — **non modificare senza approvazione** |

## Conventions
- Testing: pytest, test in `backend/tests/`
- Branching: `task/NN-nome-breve`, un branch per sessione/task, PR verso `main`, mai push diretto su `main`
- Naming: PEP8 per Python, camelCase per JS (nessuna eccezione segnalata)
- Error handling: nessun pattern esplicito documentato — seguire lo stile già presente per router/modulo toccato
- Memoria di sessione: `CLAUDE_MEMORY.md` (gitignored) tiene lo stato tra sessioni; `CLAUDE.md` contiene le istruzioni operative
- Lingua: tutta la UI in italiano

## Design System
- Component library: custom, namespace `FantaNostalgiaDesignSystem_90de16` (consegnato localmente in questo progetto Cowork, non ancora nel repo)
- Key components: Button, Badge, Panel, Table, Message, HelpBox, EmptyState, ProgressBar, DropZone, Input, WizardSteps, Tabs, Modal
- Naming conventions: PascalCase, namespace unico su `window`
- Docs: `docs/design-system-brief.md` nel repo (brief con gap analysis); i file sorgente completi del nuovo design system (`tokens/*.css`, `components/*.jsx`, `guidelines/*.html`, `ui_kits/*.html`) sono referenziati nel manifest ma **non ancora caricati** nella cartella di progetto — solo readme/manifest/bundle/styles.css sono presenti
- Stato attuale pre-restyling: 3 fogli CSS divergenti (`backend/static/style.css`, `frontend/coach/css/coach.css`, `frontend/admin/css/admin.css`) con token duplicati e già disallineati — è il debito che il nuovo design system deve risolvere

## What NOT to touch
- `database/schema.sql` — mai modificare senza approvazione esplicita
- Mai push diretto su `main` — workflow one-branch-per-task con PR
- Nessun altro vincolo segnalato
