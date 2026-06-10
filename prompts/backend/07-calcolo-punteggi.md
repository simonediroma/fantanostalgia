# 07 — Calcolo Punteggi FantaNostalgia

## Obiettivo
Implementare il motore di calcolo punteggi per entrambe le leghe (normale e nostalgia) per ogni giornata.

## Riferimenti
- `database/schema.sql` — tabelle `lineup`, `alter_ego`, `historic_rating`, `matchday_score`, `standings`
- `docs/architecture.md` — sezione "Algoritmo Voti Sintetici" (formula bonus/malus)
- `docs/lessons.md` — sezione "Database / Evita query N+1"

## Output atteso
- `backend/engine/scoring.py` — logica calcolo
- Aggiunta endpoint a `backend/api/routers/matchday.py`

---

## Logica calcolo per giornata

### Per ogni manager, per ogni giocatore in formazione:

**Punteggio Normale** (lega standard):
- Usa il voto reale del giocatore nella giornata corrente
- Il voto reale NON è nel nostro db — viene passato nel body dell'endpoint o importato insieme alle formazioni
- Bonus/malus standard Gazzetta applicati

**Punteggio FantaNostalgia:**
- Cerca l'alter ego del giocatore in `alter_ego`
- Se alter ego esiste → usa `historic_rating` per la giornata storica sorteggiata
- Se alter ego NON esiste → usa il voto reale del giocatore corrente SENZA bonus, solo malus
- Se alter ego esiste ma non è andato a voto in quella giornata (`rating = NULL`) → voto 6.0 (sv)

### Formula bonus/malus (da `docs/architecture.md`):
```
voto_base (da historic_rating.rating o voto reale)
+ 3.0 gol A / + 3.5 gol C / + 4.0 gol D
+ 1.0 assist
- 0.5 ammonizione
- 1.0 espulsione
- 1.0 autogol
- 3.0 rigore sbagliato
+ 1.0 rigore parato (P)
+ 1.0 clean sheet P (se minuti >= 60)
+ 0.5 clean sheet D (se minuti >= 60)
- 1.0 ogni 2 gol subiti (P)
```

### Aggiornamento standings
Dopo il calcolo della giornata:
1. Aggiornare `matchday_score` per ogni manager
2. Ricalcolare `standings` sommando tutti i `matchday_score`
3. Aggiornare `rank_normal` e `rank_nostalgia`

---

## Endpoints

### Calcola punteggi giornata (admin)
```
POST /admin/league/{league_id}/scores/{matchday}
Body: {
  "real_ratings": [
    {"player_name": "Leao R.", "rating": 7.5, "goals": 1, "assists": 0, ...}
  ]
}
```

Response:
```json
{
  "matchday": 6,
  "matchday_historic": 23,
  "scores": [
    {"manager": "Simone", "score_normal": 68.5, "score_nostalgia": 72.0}
  ]
}
```

### Punteggi giornata (pubblico)
```
GET /league/{league_id}/scores/{matchday}
```

---

## Note implementative
- Tutta la logica di calcolo in `backend/engine/scoring.py`, nessuna logica nel router
- Caricare tutti i dati necessari in batch prima del calcolo (no query N+1)
- Il calcolo è idempotente: ricalcola e sovrascrive se chiamato più volte sulla stessa giornata
- I voti reali (`real_ratings`) sono opzionali nel body: se non forniti, il punteggio normale non viene calcolato
