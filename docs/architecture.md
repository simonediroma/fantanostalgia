# fantanostalgia — Architettura e Riferimenti Tecnici

## Progetto

**fantanostalgia** — Modalità parallela al fantacalcio tradizionale.

**Obiettivo:** Gestire una lega FantaNostalgia dove ogni giocatore acquistato all'asta ha un alter ego storico assegnato in modo random per ruolo. I voti della stagione corrente alimentano la lega normale; i voti dell'alter ego nella stagione storica alimentano la lega FantaNostalgia. Due classifiche parallele, 100€ di montepremi dedicato.

---

## Stack Tecnico

| Layer | Tecnologia |
|-------|-----------|
| Frontend | HTML / Vanilla JS |
| Backend | Python 3.11 + FastAPI |
| Database | SQLite su GCS (Cloud Storage) |
| Deploy | GCP Cloud Run (backend + frontend nginx) |
| Task automatici | GitHub Actions (CI/CD) + Cloud Scheduler (cron settimanale) |
| Secrets | GCP Secret Manager |

---

## Architettura

Pattern: **monorepo** con backend Python e frontend statico, due Cloud Run separati.

```
fantanostalgia/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── db.py                # SQLite + GCS connection manager
│   │   └── routers/
│   │       ├── league.py        # CRUD lega e manager
│   │       ├── players.py       # Upload listone Excel + gestione rosa
│   │       ├── mapping.py       # Algoritmo alter ego + apertura buste
│   │       ├── matchday.py      # Sorteggio giornata + calcolo punteggi
│   │       └── standings.py     # Classifiche normale e nostalgia
│   ├── scrapers/
│   │   ├── fbref.py             # Statistiche match-by-match da fbref.com (con varianti fbref_pw.py Playwright)
│   │   └── calcioseriea.py      # Statistiche con ruoli reali da calcio-seriea.net
│   └── engine/
│       ├── rating.py            # Algoritmo interno voti sintetici (RatingWeights) da statistiche
│       ├── mapping.py           # Algoritmo mapping alter ego
│       └── scoring.py           # Calcolo punteggi entrambe le leghe
├── frontend/
│   ├── src/
│   │   ├── components/          # Componenti UI riutilizzabili
│   │   └── pages/               # Pagine app
│   └── public/
│       └── index.html
├── database/
│   └── schema.sql               # Schema SQLite — NON MODIFICARE senza approvazione
├── .github/
│   └── workflows/
│       ├── deploy.yml           # CI/CD → Cloud Run on push to main
│       └── weekly-draw.yml      # Cron sorteggio giornata (ogni lunedì)
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
└── cloudbuild.yaml
```

---

## Infrastruttura

| Risorsa | Valore |
|---------|--------|
| GCP Project | da configurare |
| Cloud Run Backend | fantanostalgia-api |
| Cloud Run Frontend | fantanostalgia-web |
| GCS Bucket | fantanostalgia-db |
| GCS DB Blob | fantanostalgia.db |
| Region | europe-west1 |

---

## Fonti Dati

| Fonte | Cosa contiene | Stagioni |
|-------|--------------|---------|
| fbref.com | Statistiche match-by-match (gol, assist, cartellini, minuti) | 1990 → oggi |
| calcio-seriea.net | Statistiche match-by-match con ruoli reali (no Cloudflare) | dipende dal sito |

**Regola:** per ogni stagione storica i voti sono calcolati dall'algoritmo interno di FantaNostalgia (`backend/engine/rating.py`) a partire dalle statistiche scrapate — non esistono "voti reali" importati da nessuna fonte, nemmeno per le stagioni più recenti.

---

## Algoritmo Voti Sintetici (tutte le stagioni)

Formula standard Gazzetta dello Sport applicata alle statistiche scrapate:

```
voto_base = 6.0  (se minuti >= 60) | 5.5 (se minuti < 60) | None (se non giocato)
+ 3.0 per gol segnato (attaccante)
+ 3.5 per gol segnato (centrocampista)
+ 4.0 per gol segnato (difensore)
+ 1.0 per assist
- 0.5 per ammonizione
- 1.0 per espulsione
- 1.0 per autogol
- 3.0 per rigore sbagliato
+ 1.0 per rigore parato (portiere)
+ 1.0 per clean sheet (portiere, se minuti >= 60)
+ 0.5 per clean sheet (difensore, se minuti >= 60)
- 1.0 ogni 2 gol subiti (portiere)
```

---

## Regole di Business FantaNostalgia

### Mapping alter ego
- Random per ruolo (P→P, D→D, C→C, A→A)
- Nessun criterio di valore — pippa da 5cr può avere Ronaldo il Fenomeno
- Priorità assegnazione: titolari attuali prima (ordinati per `starts_current_season` DESC)
- Copertura minima per rosa: 1P + 4D + 4C + 3A con alter ego
- Fallback duplicati: se giocatori storici insufficienti, stesso alter ego a più giocatori reali
- Reveal post-asta: mapping non visibile fino all'apertura buste

### Giornate storiche
- Sorteggio settimanale alla chiusura formazioni
- Ciclo infinito: finite le giornate storiche si riparte dall'inizio
- La stessa giornata storica può uscire più volte

### Giocatori senza alter ego
- Voto reale della giornata corrente senza bonus
- Solo malus applicati

---

## Schema I/O

**Upload listone Excel:**
```
Input: file .xlsx formato Gazzetta/Fantagazzetta
Colonne attese: nome, ruolo (P/D/C/A), squadra, quotazione
Output: player_current popolato per league_id
```

**Mapping alter ego:**
```
Input: league_id, season_historic
Output: alter_ego table popolata, mapping visibile solo dopo apertura buste
```

**Calcolo punteggi giornata:**
```
Input: league_id, matchday_current, matchday_historic (sorteggiata)
Output: matchday_score aggiornato, standings aggiornate
```

---

## Deploy

```bash
# Build e push su Cloud Run
gcloud builds submit --config cloudbuild.yaml

# Solo backend
gcloud run deploy fantanostalgia-api --source ./backend --region europe-west1

# Solo frontend
gcloud run deploy fantanostalgia-web --source ./frontend --region europe-west1
```

---

## Comandi Utili

```bash
# Sviluppo locale
docker-compose up                          # avvia backend + frontend
uvicorn backend.api.main:app --reload      # solo backend

# Database
sqlite3 fantanostalgia.db < database/schema.sql   # inizializza schema
sqlite3 fantanostalgia.db ".tables"               # verifica tabelle

# Test
cd backend && pytest                       # tutti i test
```

---

## Variabili d'Ambiente

```env
ENV=production                  # development | production
GCS_BUCKET=fantanostalgia-db    # bucket GCS per il db
GCP_PROJECT=your-project-id
SECRET_KEY=your-secret-key
DB_LOCAL_PATH=fantanostalgia.db # solo in development
```
