# 08 — API Classifica Pubblica

## Obiettivo
Endpoints pubblici per classifica e storico punteggi. Questi alimentano le pagine SSR Jinja2.

## Riferimenti
- `database/schema.sql` — tabelle `standings`, `matchday_score`, `matchday_draw`

## Output atteso
`backend/api/routers/standings.py`

---

## Endpoints

### Classifica (pubblico)
```
GET /league/{league_id}/standings
```

Response:
```json
{
  "league": {"name": "Lega Test", "season_current": "2024/25", "season_historic": "2002/03"},
  "last_matchday": 6,
  "normal": [
    {"rank": 1, "manager": "Simone", "total": 412.5, "last_matchday": 68.5},
    ...
  ],
  "nostalgia": [
    {"rank": 1, "manager": "Marco", "total": 398.0, "last_matchday": 72.0},
    ...
  ]
}
```

### Storico punteggi per manager (pubblico)
```
GET /league/{league_id}/standings/{manager_name}
```

Response:
```json
{
  "manager": "Simone",
  "matchdays": [
    {"matchday_current": 1, "matchday_historic": 12, "score_normal": 75.0, "score_nostalgia": 68.0},
    ...
  ],
  "total_normal": 412.5,
  "total_nostalgia": 385.0,
  "rank_normal": 1,
  "rank_nostalgia": 3
}
```

### Ultima giornata sorteggiata (pubblico)
```
GET /league/{league_id}/last-draw
```

Response:
```json
{
  "matchday_current": 6,
  "matchday_historic": 23,
  "drawn_at": "2024-10-14T11:00:00"
}
```

---

## Note implementative
- Tutti gli endpoint sono pubblici (nessuna autenticazione)
- Questi endpoint sono chiamati dalle route Jinja2 SSR — ottimizzare per velocità
- Aggiungere indice su `standings(league_id, rank_normal)` e `standings(league_id, rank_nostalgia)` se non presenti in schema.sql
