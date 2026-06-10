# FantaNostalgia

Modalità parallela al fantacalcio. Stessa asta, due classifiche: una normale e una con i voti di una stagione storica. Il mapping alter ego è random — non sai cosa hai preso fino all'apertura buste.

## Regole in breve

- Ogni giocatore acquistato riceve un alter ego storico **random per ruolo** (nessun criterio di valore)
- Il mapping viene rivelato **post-asta** (apertura buste pubblica)
- Ogni settimana, alla chiusura formazioni, viene **sorteggiata la giornata storica** corrispondente
- Ciclo infinito: finite le giornate storiche si riparte dall'inizio
- **100€ di montepremi** separato per il vincitore FantaNostalgia
- Giocatori senza alter ego: voto reale senza bonus, solo malus

## Stack

| Layer | Tecnologia |
|-------|-----------|
| Backend | Python 3.11 + FastAPI |
| Frontend | HTML / Vanilla JS |
| Database | SQLite su GCP Cloud Storage |
| Deploy | GCP Cloud Run |
| CI/CD | GitHub Actions |
| Cron | GitHub Actions (sorteggio settimanale) |

## Setup

```bash
chmod +x setup.sh
./setup.sh
```

## Sviluppo locale

```bash
pip install -r backend/requirements.txt
docker-compose up
```

- Backend API: http://localhost:8080
- Frontend: http://localhost:3000
- Docs API: http://localhost:8080/docs

## Deploy

```bash
gcloud builds submit --config cloudbuild.yaml
```

## Secrets GitHub

| Secret | Valore |
|--------|--------|
| `GCP_SA_KEY` | JSON service account (Cloud Run Admin + Storage Admin) |
| `GCP_PROJECT` | ID progetto GCP |
| `GCS_BUCKET` | Nome bucket GCS per il db |
| `API_BASE_URL` | URL Cloud Run backend |
| `API_SECRET_KEY` | Secret key per autenticazione cron |
