# 13 — Scraper Fantagiaveno.it (Voti Storici 2003+)

## Obiettivo
Scraper per raccogliere voti storici da fantagiaveno.it per stagioni dalla 2003/04 in poi.

## Riferimenti
- `database/schema.sql` — tabelle `player_historic`, `historic_rating`
- `docs/lessons.md` — sezione "Scraping"
- `docs/architecture.md` — sezione "Fonti Dati"

## Output atteso
`backend/scrapers/fantagiaveno.py`

---

## Note preliminari
Prima di implementare, verificare manualmente la struttura HTML di fantagiaveno.it:
- URL base da verificare
- Struttura tabella voti (selettori CSS da aggiornare nel codice)
- Formato nome giocatore e ruolo

## Comportamento

```python
scrape_season(season: str) -> None
# Es: scrape_season("2003/04")
# 1. Scarica lista giocatori per stagione
# 2. Per ogni giocatore: nome, ruolo, squadra → inserisce in player_historic
# 3. Per ogni giornata: voti + bonus/malus → inserisce in historic_rating
# 4. source = "archive"
```

## Regole implementative
- Sleep 2-3 secondi tra richieste
- Idempotente: skip se `player_historic` + `historic_rating` già presenti per stagione
- Loggare progresso: giornata X/34, giocatore Y/Z
- Salvare su db incrementalmente (non aspettare fine scraping)

## Esecuzione
```bash
python -m backend.scrapers.fantagiaveno --season 2003/04
python -m backend.scrapers.fantagiaveno --season 2005/06 --force  # forza re-scraping
```
