# 06 — Sorteggio Giornata Storica

## Obiettivo
Endpoint per sorteggiare la giornata storica corrispondente alla giornata corrente. Eseguito dall'admin (o dal cron GitHub Actions) dopo la chiusura delle formazioni.

## Riferimenti
- `database/schema.sql` — tabella `matchday_draw`
- `docs/architecture.md` — sezione "Regole di Business / Giornate storiche"

## Output atteso
- `backend/engine/draw.py` — logica sorteggio
- Aggiunta endpoints a un nuovo `backend/api/routers/matchday.py`

---

## Regola sorteggio — ciclo infinito
La stagione storica ha N giornate (es. 34 per stagioni pre-2003, 38 per stagioni moderne).
Il sorteggio deve:
1. Caricare tutte le giornate storiche già sorteggiate per questa lega
2. Costruire il pool: tutte le giornate della stagione storica (1..N)
3. Se tutte le giornate sono già state estratte almeno una volta → resettare il contatore e ripartire (ciclo infinito)
4. Estrarre random dal pool delle giornate non ancora estratte nel ciclo corrente
5. Salvare in `matchday_draw`

**Numero giornate stagione storica:**
- Stagioni <= 1987/88: 30 giornate (16 squadre)
- Stagioni 1988/89 - 2003/04: 34 giornate (18 squadre)
- Stagioni >= 2004/05: 38 giornate (20 squadre)

Questa logica va in `backend/engine/draw.py` come funzione `get_season_matchday_count(season: str) -> int`.

---

## Endpoints

### Sorteggia giornata (admin o cron)
```
POST /admin/league/{league_id}/draw/{matchday_current}
Header: Authorization: Bearer {SECRET_KEY}   ← per permettere chiamata da GitHub Actions
```

Response:
```json
{
  "matchday_current": 6,
  "matchday_historic": 23,
  "cycle": 1,
  "drawn_at": "2024-10-14T11:00:00"
}
```

### Lista sorteggi effettuati
```
GET /league/{league_id}/draws
```

Response:
```json
[
  {"matchday_current": 1, "matchday_historic": 12},
  {"matchday_current": 2, "matchday_historic": 7},
  ...
]
```

---

## Note implementative
- Aggiungere colonna `cycle INTEGER DEFAULT 1` a `matchday_draw` per tracciare il ciclo corrente
- L'endpoint è chiamabile sia dall'admin via browser che dal cron GitHub Actions via Bearer token
- Il Bearer token corrisponde a `SECRET_KEY` nelle variabili d'ambiente
- Idempotente per giornata: se la giornata corrente ha già un sorteggio, restituire quello esistente senza ri-sorteggiare
