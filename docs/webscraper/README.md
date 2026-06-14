# Guida Web Scraper Chrome — fbref.com Serie A

## Opzione A — Tutte le stagioni storiche in un colpo (consigliata)

Usa `sitemap-all-seasons.json` + `seasons.html`.
La sitemap parte da un file HTML locale che contiene tutti i link alle stagioni fbref,
senza placeholder da sostituire.

### Setup

1. Installa l'estensione **Web Scraper** da Chrome Web Store
2. Abilita "Allow access to file URLs" in `chrome://extensions` → Web Scraper
3. Apri `docs/webscraper/seasons.html` in Chrome
4. Copia l'URL dalla barra indirizzi (sarà tipo `file:///C:/path/to/seasons.html`)
5. Apri `sitemap-all-seasons.json`, sostituisci `SOSTITUISCI_CON_URL_FILE_LOCALE` con quell'URL
6. DevTools → Web Scraper → "Create new sitemap" → "Import sitemap" → incolla il JSON

### Struttura sitemap (3 livelli)

```
_root (seasons.html — file locale)
  └── season_link  [SelectorLink — ogni stagione fbref]
        └── match_link  [SelectorLink — ogni "Match Report"]
              ├── home_score   [SelectorText]
              ├── away_score   [SelectorText]
              └── player_row  [SelectorElement]
                    ├── player_name
                    ├── position
                    ├── minutes
                    ├── goals
                    ├── yellow_card
                    └── red_card
```

### Stagioni incluse in seasons.html

2000-01 → 2013-14 (14 stagioni, ~5320 partite)

Per aggiungere stagioni: modifica `seasons.html` aggiungendo un `<li><a href="...">` con l'URL fbref corrispondente.

### Scraping

1. Seleziona il selector `player_row` (non `season_link` o `match_link`)
2. Clicca **"Scrape"**
3. Attendi il completamento — stima ~45 min per stagione × 14 stagioni ≈ **10 ore**
   (puoi fare stagioni separate usando le sitemap per singola stagione)
4. Clicca **"Export data as CSV"**

---

## Opzione B — Stagione singola

Usa le sitemap `sitemap-2000-2001.json`, `sitemap-2010-2011.json`, ecc.
(URL già compilati, niente da sostituire).

Oppure `sitemap-match-reports.json` (generico, con `[SEASON]` da sostituire).

---

## Conversione CSV

Il CSV di Web Scraper non è nel formato dell'admin. Converti con:

```bash
# Windows PowerShell
$env:PYTHONPATH = "."
python -m backend.scrapers.convert_webscraper `
  --input webscraper_export.csv `
  --season 2005-2006 `
  --output fbref_2005-2006.csv

# Linux/Mac
PYTHONPATH=. python -m backend.scrapers.convert_webscraper \
  --input webscraper_export.csv \
  --season 2005-2006 \
  --output fbref_2005-2006.csv
```

Il convertitore legge `home_score` e `away_score` dal CSV per calcolare
`team_won` e `goals_conceded`. Se mancano, produce un warning e usa 0 come fallback.

---

## Impostazioni consigliate

- **Request interval:** 4000 ms (rispetta il rate limit fbref)
- **Page load delay:** 3000 ms
- Lascia la finestra Chrome aperta e visibile durante lo scraping

---

## Alternativa per stagioni 2014-15 in poi

```bash
python -m backend.scrapers.understat --season 2014-2015 --export-csv out.csv
```
