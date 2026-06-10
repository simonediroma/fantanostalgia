# 02 — Import Listone Excel

## Obiettivo
Endpoint per upload del listone Excel della lega. Parsing rosa attuale con ruoli, quotazioni e calcolo indice titolarità.

## Riferimenti
- `database/schema.sql` — tabella `player_current`
- `docs/architecture.md` — sezione Schema I/O
- `backend/api/routers/players.py` — già presente, completare e correggere

## Output atteso
`backend/api/routers/players.py` completo e funzionante.

---

## Formato Excel atteso
Il listone standard Fantacalcio (Gazzetta/Fantagazzetta) ha questo layout:

| Ruolo | Nome | Squadra | Quotazione Attuale | ... |
|-------|------|---------|-------------------|-----|
| P | Buffon G. | Juventus | 15 | ... |

Colonne obbligatorie (ricerca case-insensitive, nomi alternativi accettati):
- **Ruolo**: "R", "Ruolo", "Ruo" — valori: P, D, C, A (o Por/Dif/Cen/Att)
- **Nome**: "Nome", "Calciatore", "Giocatore"
- **Squadra**: "Squadra", "Sq", "Team"
- **Quotazione**: "Qt A", "Quotazione", "Q.A.", "Quota"

Colonne opzionali:
- **Presenze**: "Pv", "Presenze" → usato come `starts_current_season`

---

## Endpoints

### Upload listone (admin)
```
POST /admin/league/{league_id}/listone
Content-Type: multipart/form-data
Body: file (.xlsx o .xls)
```

Response:
```json
{
  "imported": 450,
  "by_role": {"P": 45, "D": 135, "C": 135, "A": 135},
  "warnings": ["Colonna presenze non trovata, starts=0 per tutti"]
}
```

### Assegna giocatori a manager (admin, post-asta)
```
POST /admin/league/{league_id}/assign
Body: [{player_id: 1, manager_id: 2}, ...]
```

### Lista giocatori
```
GET /league/{league_id}/players?role=A&manager_id=3
```

---

## Note implementative
- Prima dell'import: cancellare tutti i `player_current` della lega (idempotente)
- Se `starts_current_season` non disponibile nel file: default 0, aggiungere warning nella response
- Saltare righe con ruolo non valido o nome vuoto, contarle nei warnings
- Il file POC di test è in `database/seed_poc.py` — verificare compatibilità del parser con i dati generati lì
