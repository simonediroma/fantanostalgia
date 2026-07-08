# Context — FantaNostalgia Restyling (Design System Installation)

## Existing stack
| Layer | Technology |
|-------|-----------|
| Frontend | HTML / Vanilla JS — Jinja2 SSR per le pagine pubbliche + 2 SPA vanilla JS (admin, coach) |
| Backend | Python 3.11 + FastAPI |
| Database | SQLite su GCS (Google Cloud Storage) |
| Auth | Sessione/token custom — login admin + login coach con token d'invito |
| Deploy | GCP Cloud Run (backend + frontend nginx separati), GitHub Actions, Cloud Scheduler, Secret Manager |

## Modules involved in questa feature
| Module | Path | Ruolo nella feature |
|--------|------|----------------------|
| Design system (nuovo) | `frontend/shared/design-system.js` (da creare) | Libreria vanilla JS dei 13 componenti, porting da `_ds_bundle.js` React |
| Token CSS (nuovo) | `frontend/shared/tokens/*.css` (da creare) | Single source of truth palette/tipografia/spacing/effetti, sostituisce i 3 `:root` duplicati |
| Pagine pubbliche | `backend/templates/*.html`, `backend/static/style.css` | Da restylare (M2), aggiunta sezione Hall of Fame e pagina Come Funziona (M8) |
| Admin SPA | `frontend/admin/index.html`, `frontend/admin/js/{api,auth,league,listone,mapping,matchday}.js`, `frontend/admin/css/admin.css` | Da restylare (M3), estesa con multi-lega (M6) ed elevazione admin (M7) |
| Coach SPA | `frontend/coach/{login,index,rosa,punteggi}.html`, `frontend/coach/css/coach.css` | Da restylare (M4), estesa con richiesta elevazione (M7) |
| Router lega | `backend/api/routers/league.py` | Punto di estensione per multi-lega (M6) — verificare cosa espone già prima di aggiungere endpoint |
| Auth/coach router | `backend/api/routers/coach.py` | Punto di estensione per elevazione coach→admin (M7) |
| Engine scoring | `backend/engine/scoring.py`, `backend/engine/granpremio.py`, `backend/engine/mapping.py` | Coinvolti solo dagli spike M9-M12 (regole di gioco), non toccare finché gli spike non sono risolti |
| Schema DB | `database/schema.sql` | **Protetto** — M7 (e potenzialmente gli spike) potrebbero richiedere una nuova tabella/campo: serve approvazione esplicita di Simone prima di modificarlo |

## Pattern esistenti da seguire
- I 3 fogli CSS attuali (`backend/static/style.css`, `frontend/coach/css/coach.css`, `frontend/admin/css/admin.css`) definiscono `:root` con gli stessi token, oggi già divergenti (`docs/design-system-brief.md` §5a) — vanno sostituiti, non semplicemente affiancati.
- Tutte le viste sono già in italiano, 2ª persona per il coach, 3ª tecnica per l'admin — il design system rispetta questa convenzione, mantenerla nei nuovi copy (help-box, empty-state, FAQ).
- Zero border-radius, ombre pixel senza blur, scanline CRT: vincolo estetico non negoziabile su ogni superficie.
- I componenti del design system sono forniti in React (`_ds_bundle.js`) — vanno riscritti in vanilla JS mantenendo identici props/varianti/stati (vedi `project-spec.md` sez. 11 per l'inventario completo).

## Conventions
- Branching: `task/NN-nome-breve`, un branch per task, PR verso `main`, mai push diretto.
- Testing: pytest in `backend/tests/` per il backend; nessun framework di test frontend esistente oggi (da introdurre solo se necessario per M1).
- Naming: PEP8 Python, camelCase JS.
- Lingua: tutta la UI in italiano, sempre.

## Do not touch
- `database/schema.sql` senza approvazione esplicita di Simone.
- `backend/engine/scoring.py`, `granpremio.py`, `mapping.py` — riservati agli spike M9-M12, non modificare nel restyling puro (M1-M8).
- Non push diretto su `main`.
