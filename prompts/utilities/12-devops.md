# 12 — DevOps (Dockerfile + GitHub Actions + Cloud Run)

## Obiettivo
Containerizzare il progetto e configurare CI/CD completo su GCP Cloud Run.

## Riferimenti
- `docs/architecture.md` — sezione Infrastruttura e Deploy
- `Dockerfile.backend` e `Dockerfile.frontend` — già presenti, aggiornare
- `cloudbuild.yaml` — già presente, aggiornare
- `.github/workflows/` — già presente, aggiornare

## Output atteso
Aggiornamento di tutti i file di infrastruttura esistenti.

---

## Task 1 — Dockerfile backend

Aggiornare `Dockerfile.backend`:
- Base image: `python:3.11-slim`
- Copiare `backend/`, `database/schema.sql`, `backend/templates/`, `backend/static/`
- Esporre porta 8080
- Health check su `/health`

## Task 2 — Dockerfile frontend (admin)

Aggiornare `Dockerfile.frontend`:
- Base image: `nginx:alpine`
- Copiare `frontend/admin/` in `/usr/share/nginx/html/`
- Config nginx per SPA (tutte le route → `index.html`)
- Porta 8080

`nginx.conf`:
```nginx
server {
    listen 8080;
    root /usr/share/nginx/html;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## Task 3 — docker-compose

Aggiornare `docker-compose.yml`:
- Service `backend`: porta 8080, volume db locale, hot reload
- Service `frontend`: porta 3000, proxy `/api` verso backend
- Variable d'ambiente da `.env`

## Task 4 — GitHub Actions CI/CD

Aggiornare `.github/workflows/deploy.yml`:
- Trigger: push su `main`
- Step: auth GCP → build → push → deploy Cloud Run backend → deploy Cloud Run frontend
- Usare `google-github-actions/auth@v2` con `credentials_json`

## Task 5 — GitHub Actions cron sorteggio

Aggiornare `.github/workflows/weekly-draw.yml`:
- Trigger: ogni lunedì alle 11:00 UTC + workflow_dispatch manuale
- Chiama `POST /admin/league/{league_id}/draw/{matchday}` con Bearer token
- Input manuale: `league_id` e `matchday_current`

## Task 6 — cloudbuild.yaml

Aggiornare `cloudbuild.yaml`:
- Build e deploy backend + frontend
- Substitutions: `_GCS_BUCKET`, `_REGION` (default europe-west1)
- Tag immagini con `$COMMIT_SHA`

---

## Secrets GitHub da configurare (documentare nel README)

| Secret | Valore |
|--------|--------|
| `GCP_SA_KEY` | JSON service account |
| `GCP_PROJECT` | ID progetto |
| `GCS_BUCKET` | Nome bucket db |
| `API_BASE_URL` | URL Cloud Run backend |
| `API_SECRET_KEY` | Uguale a `SECRET_KEY` nel backend |
