# Guida Web Scraper Chrome — fbref.com Serie A

## Setup

1. Installa l'estensione **Web Scraper** da Chrome Web Store
2. Apri DevTools → tab "Web Scraper"
3. Clicca **"Create new sitemap"** → **"Import sitemap"**
4. Incolla il contenuto di `sitemap-match-reports.json`
5. Sostituisci `[SEASON]` nell'URL con la stagione che vuoi (es. `2005-2006`)

## URL di partenza

```
https://fbref.com/en/comps/11/2005-2006/schedule/2005-2006-Serie-A-Scores-and-Fixtures
```

## Struttura sitemap (2 livelli)

```
_root (fixtures page)
  └── match_link  [SelectorLink — segue ogni "Match Report"]
        └── player_row  [SelectorElement — righe delle due tabelle stats]
              ├── player_name
              ├── position
              ├── minutes
              ├── goals
              ├── yellow_card
              └── red_card
```

## Impostazioni consigliate

- **Request interval:** 4000 ms (rispetta il rate limit fbref)
- **Page load delay:** 3000 ms
- Lascia la finestra Chrome aperta e visibile durante lo scraping

## Scraping

1. Seleziona il selector `match_link`
2. Clicca **"Scrape"**
3. Attendi il completamento (380 partite × ~7 sec ≈ 45 min)
4. Clicca **"Export data as CSV"**

## Conversione CSV

Il CSV di Web Scraper non è nel formato dell'admin. Converti con:

```bash
$env:PYTHONPATH = "."
python -m backend.scrapers.convert_webscraper \
  --input webscraper_export.csv \
  --season 2005-2006 \
  --output fbref_2005-2006.csv
```

## Limitazione importante

Web Scraper **non cattura il risultato della partita** (score home/away).
Di conseguenza nel CSV convertito:
- `team_won = 0` per tutti i giocatori (manca il bonus vittoria +0.5)
- `goals_conceded = 0` per tutti i portieri (manca malus/bonus GK)

Il rating sarà parziale. Per dati completi usa `fbref_pw` (Playwright).

## Alternativa più veloce

Per stagioni dal 2014-2015 in poi usa understat (più semplice):
```bash
python -m backend.scrapers.understat --season 2014-2015 --export-csv out.csv
```
