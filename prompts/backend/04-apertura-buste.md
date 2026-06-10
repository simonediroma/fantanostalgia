# 04 — Apertura Buste

## Obiettivo
Endpoint per rendere pubblico il mapping alter ego. Azione irreversibile, eseguita dall'admin dopo l'asta.

## Riferimenti
- `database/schema.sql` — tabelle `alter_ego`, `league`
- `backend/api/routers/mapping.py` — aggiungere endpoint qui

## Output atteso
Aggiunta di 2 endpoints a `backend/api/routers/mapping.py`.

---

## Endpoints

### Apri buste (admin, irreversibile)
```
POST /admin/league/{league_id}/mapping/reveal
```
- Imposta `league.buste_aperte = 1`
- Irreversibile — se `buste_aperte` è già 1, restituisce 400 con messaggio "Buste già aperte"
- Restituisce il mapping completo come conferma

### Mapping pubblico (visibile solo dopo apertura buste)
```
GET /league/{league_id}/mapping
```
- Se `buste_aperte = 0`: restituisce 404 con messaggio "Le buste non sono ancora state aperte"
- Se `buste_aperte = 1`: restituisce mapping completo raggruppato per manager

Response formato:
```json
{
  "league": "Lega Test 2024/25",
  "season_historic": "2002/03",
  "buste_aperte_at": "2024-09-01T20:30:00",
  "managers": [
    {
      "name": "Simone",
      "players": [
        {
          "current": {"name": "Leao R.", "role": "A", "team": "Milan"},
          "historic": {"name": "Shevchenko A.", "role": "A", "team": "Milan", "season": "2002/03"},
          "is_duplicate": false
        }
      ]
    }
  ]
}
```

---

## Note implementative
- Aggiungere colonna `buste_aperte_at TIMESTAMP` alla tabella `league` in `schema.sql`
- L'endpoint reveal aggiorna sia `buste_aperte = 1` che `buste_aperte_at = now()`
- Nessuna logica aggiuntiva — la visibilità del mapping è controllata solo da questo flag
