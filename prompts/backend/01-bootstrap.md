# 01 — Backend Bootstrap (DB + Auth + Gestione Lega)

## Obiettivo
Implementare il core del backend: inizializzazione DB, autenticazione admin, CRUD lega. È il fondamento su cui si appoggiano tutti gli altri moduli.

## Riferimenti
- `database/schema.sql`
- `docs/architecture.md`
- `backend/api/db.py` — già presente, non modificare
- `backend/api/main.py` — già presente, aggiungere i router

## Output atteso
Tutti i file sotto `backend/api/` necessari per:
1. Inizializzare il db allo startup
2. Login/logout admin con sessione
3. CRUD lega

---

## Task 1 — Inizializzazione DB

`backend/api/db.py` è già implementato. Aggiungere chiamata a `init_db()` nello startup di FastAPI in `main.py`:

```python
@app.on_event("startup")
def startup():
    init_db()
```

---

## Task 2 — Auth Admin

File: `backend/api/routers/auth.py`

### Requisiti
- Login con username e password (hardcoded in variabile d'ambiente, no tabella utenti)
- Sessione via cookie firmato (usare `itsdangerous` o `python-jose`)
- Middleware che protegge tutte le route `/admin/*`
- Dependency FastAPI `get_current_admin` riutilizzabile nei router

### Variabili d'ambiente necessarie
```
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme
SECRET_KEY=your-secret-key
SESSION_EXPIRE_HOURS=24
```

### Endpoints
```
POST /auth/login     body: {username, password} → set cookie sessione → redirect /admin
POST /auth/logout    → cancella cookie → redirect /
GET  /auth/me        → {username} se autenticato, 401 altrimenti
```

---

## Task 3 — Gestione Lega

File: `backend/api/routers/league.py`

### Endpoints admin (protetti)
```
POST   /admin/league              body: {name, season_current, season_historic, budget}
PUT    /admin/league/{id}         body: campi aggiornabili
DELETE /admin/league/{id}
```

### Endpoints pubblici
```
GET /league                       lista tutte le leghe (id, name, season_*)
GET /league/{id}                  dettaglio lega
```

### Validazioni
- `season_current` e `season_historic` formato "YYYY/YY" (es. "2024/25")
- `season_historic` deve essere diversa da `season_current`
- `budget` >= 100

---

## Note implementative
- Usare `pydantic` per tutti i modelli request/response
- Gestione errori con HTTPException e messaggi in italiano
- Nessuna dipendenza esterna oltre a quanto già in `requirements.txt` — aggiungere solo `itsdangerous` e `python-jose[cryptography]`
- Aggiornare `requirements.txt` con le nuove dipendenze
