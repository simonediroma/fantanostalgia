# 05 — Import Formazioni Excel

## Obiettivo
Endpoint per upload del file Excel con le formazioni della giornata. Il sistema legge chi è schierato e costruisce la lineup per il calcolo punteggi.

## Riferimenti
- `database/schema.sql` — tabella `lineup`
- `docs/architecture.md` — sezione Schema I/O

## Output atteso
`backend/api/routers/lineups.py`

---

## Formato Excel atteso
Da definire quando il file reale sarà disponibile. Per ora implementare un formato POC compatibile con `database/seed_poc.py`.

Formato POC:
| Manager | Giocatore | Titolare |
|---------|-----------|----------|
| Simone | Leao R. | 1 |
| Simone | Bianchi M. | 0 |
| Marco | Rossi A. | 1 |

- `Titolare`: 1 = titolare, 0 = riserva
- Il nome giocatore deve matchare esattamente con `player_current.name` nella lega
- Ogni manager deve avere esattamente 11 titolari e max 7 riserve

---

## Endpoints

### Upload formazioni (admin)
```
POST /admin/league/{league_id}/lineups/{matchday}
Content-Type: multipart/form-data
Body: file (.xlsx o .xls)
```

Response:
```json
{
  "matchday": 6,
  "managers_imported": 8,
  "warnings": ["Giocatore 'Verdi G.' non trovato nella rosa di Marco — saltato"]
}
```

### Lista formazioni giornata
```
GET /league/{league_id}/lineups/{matchday}
```

---

## Note implementative
- Idempotente: cancella lineup esistente per quella giornata e reimporta
- Match giocatore: case-insensitive, trim spazi — loggare i non trovati come warning senza bloccare
- `locked_at`: impostare al momento dell'upload (le formazioni si considerano bloccate all'import)
- Aggiungere `__init__.py` vuoti dove mancano nei package Python
