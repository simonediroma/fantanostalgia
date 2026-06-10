# 14 — Scraper fbref.com + Motore Voti Sintetici (pre-2003)

## Obiettivo
Scraper fbref.com per statistiche match-by-match e motore di calcolo voti sintetici per stagioni pre-2003.

## Riferimenti
- `database/schema.sql` — tabelle `player_historic`, `historic_rating`
- `docs/architecture.md` — sezione "Algoritmo Voti Sintetici"
- `docs/lessons.md` — sezione "Scraping / fbref rate limiting"

## Output atteso
- `backend/scrapers/fbref.py`
- `backend/engine/synthetic_ratings.py`

---

## Scraper fbref (`backend/scrapers/fbref.py`)

```python
scrape_season(season: str) -> None
# Es: scrape_season("1998/99")
# 1. Trova URL stagione Serie A su fbref
# 2. Per ogni giocatore: nome, ruolo, squadra, presenze → player_historic
# 3. Per ogni partita: gol, assist, cartellini, minuti → salva raw in tabella staging
# 4. source = "synthetic"
```

Rate limiting: sleep 3 secondi tra richieste, max 20 richieste/minuto.

---

## Motore voti sintetici (`backend/engine/synthetic_ratings.py`)

```python
calculate_synthetic_ratings(season: str) -> None
```

Prende i dati raw fbref dalla staging e calcola `historic_rating` usando la formula:

```
voto_base:
  se minuti >= 60: 6.0
  se minuti < 60 e > 0: 5.5
  se minuti = 0: NULL (non giocato)

bonus/malus:
  + 3.0 gol (A) / + 3.5 (C) / + 4.0 (D)
  + 1.0 assist
  - 0.5 ammonizione
  - 1.0 espulsione
  - 1.0 autogol
  - 3.0 rigore sbagliato
  + 1.0 rigore parato (P)
  + 1.0 clean sheet P (minuti >= 60)
  + 0.5 clean sheet D (minuti >= 60)
  - 1.0 ogni 2 gol subiti (P)
```

---

## Esecuzione
```bash
python -m backend.scrapers.fbref --season 1998/99
python -m backend.engine.synthetic_ratings --season 1998/99
```
