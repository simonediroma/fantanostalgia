# Design System Brief — FantaNostalgia

> Documento di brief per **Claude design**. Obiettivo: fornire tutto il contesto necessario
> per progettare un **design system formalizzato** per FantaNostalgia, a partire
> dall'estetica 8-bit / Sensible Soccer già esistente.
>
> **Questo documento è un brief, non un'implementazione.** Descrive lo stato attuale,
> le carenze e i requisiti, e propone soluzioni concrete come punto di partenza.
>
> Stato: redatto il 2026-06-24 · Branch: `claude/interface-design-system-analysis-m9zph6`

---

## 1. Obiettivo del brief

FantaNostalgia ha un'identità visiva forte e riconoscibile (arcade anni '80, pixel art,
CRT) ma **non ha un design system formalizzato**. Lo styling vive in tre fogli CSS che
ridefiniscono gli stessi token in modo indipendente, la responsiveness è incompleta, i
componenti non sono catalogati e — soprattutto — **mancano gli elementi informativi ed
esplicativi** che permettano all'utente di capire *a cosa serve* una funzione e *come
eseguirla* (in primis: quali file scaricare e quali caricare).

Il design system richiesto deve:

1. **Unificare i token** in un'unica source of truth, preservando l'estetica 8-bit.
2. **Risolvere le carenze di responsiveness** con un sistema di breakpoint e pattern mobile.
3. **Catalogare i componenti** UI in una libreria documentata.
4. **Introdurre pattern informativi/esplicativi** riusabili: help-box "a cosa serve",
   indicazione esplicita dei file da caricare/scaricare, stati vuoti parlanti, conferme
   con conseguenze chiare.

---

## 2. Identità visiva attuale (8-bit / Sensible Soccer)

Da preservare. È il tratto distintivo del prodotto.

### Palette (token attuali, identici nei 3 CSS)

| Token | Valore | Uso |
|---|---|---|
| `--bg` | `#050510` | Sfondo principale (indaco/nero) |
| `--surface` | `#0d0d2b` | Card, pannelli, topbar |
| `--accent` | `#ffe600` | CTA primarie, titoli, header tabella (giallo neon) |
| `--accent2` | `#00d4ff` | Accento secondario, rank, hover (ciano) |
| `--text` | `#ffffff` | Testo corpo |
| `--muted` | `#7777aa` | Testo secondario/inattivo (viola-grigio) |
| `--green` | `#00ff55` | Positivo, punteggi, vittorie, "fatto" |
| `--red` | `#ff1144` | Pericolo, negativi, operazioni irreversibili |
| `--border` | `#3333aa` | Bordi tabelle/divisori (blu) |

### Tipografia

| Token | Font | Uso |
|---|---|---|
| `--font-pixel` | `Press Start 2P` (Google Fonts) | Titoli, label UI, bottoni, badge — `text-transform: uppercase` |
| `--font-data` | `Courier New`, monospace | Corpo, tabelle, statistiche |

### Cifre stilistiche (firma estetica)

- `border-radius: 0 !important` su tutto (spigoli vivi).
- `box-shadow: 2px 2px 0 #000` → `4px 4px 0 #000` (ombra "pixel" piena, mai sfocata).
- Overlay scanline CRT su ogni pagina via `body::before` (gradiente ripetuto a righe).
- Hover CTA: sfondo da giallo a ciano.

---

## 3. Inventario interfaccia

### Pagine pubbliche — SSR Jinja2 (`backend/templates/`)

| Pagina | File | Scopo |
|---|---|---|
| Home | `home.html` | Landing, "Come funziona", login/registrazione coach, leghe attive |
| Classifica | `classifica.html` | Classifica lega — 4 tab (nostalgia, normale, scontri diretti, calendario) |
| Giornata | `giornata.html` | Dettaglio giornata: risultati, formazioni, Gran Premi |
| Statistiche | `statistiche.html` | Rating giocatori, marcatori, archivio storico |
| Mapping | `mapping.html` | Reveal degli alter ego (bloccata finché le buste non sono aperte) |
| Base | `base.html` | Layout condiviso (header, nav, footer, scanline) |

### Admin — SPA vanilla JS (`frontend/admin/`)

`index.html` + moduli `admin/js/{api,auth,league,listone,mapping,matchday}.js`.
Login + **wizard a 4 step**: `1 Listone → 2 Mapping → 3 Buste → 4 Giornate`.

### Coach — SPA vanilla JS (`frontend/coach/`)

| Pagina | File | Scopo |
|---|---|---|
| Login | `login.html` | Login/registrazione (con token invito) |
| Dashboard | `index.html` | Elenco leghe del coach |
| Rosa | `rosa.html` | Associazione storico→attuale, lock bar, banner Gran Premio |
| Punteggi | `punteggi.html` | Punteggi personali per giornata |

---

## 4. Inventario componenti UI (base per la libreria)

Tutti già presenti nel CSS, da formalizzare con varianti e stati documentati.

| Componente | Varianti / stati | Dove vive oggi |
|---|---|---|
| Bottone | `default` (giallo), `.secondary` (outline), `.danger` (rosso), `:disabled` | tutti i CSS |
| Badge | neutro, `.badge-green`, `.badge-red` | coach.css, style.css |
| Panel / Card | `.panel`, `.league-card` (+ hover) | tutti |
| Tabella | header giallo, righe hover, celle `.rank/.score/.pos/.neg` | tutti |
| Tabs | `.tab-btn` + `.tab-panel.active` | style.css, home.html |
| Wizard step | `.step` + `.done` (verde) + `.active` (giallo) | admin.css |
| Drop-zone | `.drop-zone` + `.drag-over` | admin.css |
| Modal | `.modal-overlay.open` + `.modal-box` | style.css, admin.css |
| Progress bar | `.progress-bar-wrap` + `.progress-bar-fill` | coach.css |
| Messaggio | `.msg.ok` / `.msg.err` (auto-dismiss 5s) | tutti |
| Stato vuoto | `.empty` | tutti |

---

## 5. Carenze e debiti tecnici

### 5a. Token duplicati — nessuna single source of truth

I `:root` sono **copiati in tre file** (`backend/static/style.css`,
`frontend/coach/css/coach.css`, `frontend/admin/css/admin.css`) e sono già **divergenti**:

| Aspetto | style.css | coach.css | admin.css |
|---|---|---|---|
| `body font-size` | `16px` | `15px` | `15px` |
| `.login-card` width | — | `340px` | `320px` |
| hover bottone | →`accent2` | `opacity:0.85` | →`accent2` |
| `.panel` bordo/ombra | — | `1px`, no ombra | `2px` + `3px 3px 0` |

Qualsiasi modifica a un colore va replicata 3 volte: fonte certa di drift.

### 5b. Responsiveness incompleta

- **Mobile senza navigazione**: la sidebar admin/coach va in `display:none` sotto 640px,
  **senza menu hamburger** sostitutivo → la navigazione tra step/sezioni è inaccessibile.
- **Font pixel illeggibili** a misure piccole (label a `0.45–0.55rem`).
- **Tabelle**: solo `overflow-x:auto`, nessun pattern card/stacking su mobile.
- **Scanline CRT** attiva anche su mobile (costo visivo/performance su schermi piccoli).
- **Breakpoint non sistematici**: `768px`, `700px`, `640px` mescolati senza scala.

### 5c. Accessibilità

- Contrasto da verificare per ciano/rosso su sfondo scuro; testo pixel sotto i limiti
  di leggibilità a dimensioni piccole.
- Icone affidate a **emoji** (`⚽ 🏆 → ← ↻ ✓`), prive di alternativa testuale.
- Attributi ARIA quasi assenti (eccetto il modal invito).
- Colore usato come unico veicolo di stato (verde/rosso) senza etichetta/icona ridondante.

### 5d. Coerenza e stili inline

Molti stili sono **inline nelle pagine** (es. `style="background:var(--bg);border:1px..."`
ripetuto sui `<select>` in `admin/index.html`), invece che in classi riusabili.

### 5e. Carenza centrale — elementi informativi ed esplicativi (assenti o disomogenei)

Le funzioni **non spiegano a cosa servono né come si eseguono**:

- **Upload listone / formazioni**: la drop-zone dice solo *"Trascina .xlsx qui"*, ma
  **non indica la struttura attesa** del file (descritta solo in `CLAUDE_MEMORY.md`), non
  offre un **template di esempio** scaricabile, non spiega cosa succede dopo l'upload.
- **Import storico CSV e scraping**: **zero guida in-app**. L'operatore non sa quali file
  scaricare (sitemap, export Web Scraper) né dove caricarli (`POST /admin/historic/import`
  non ha nemmeno una UI).
- **Wizard admin**: alcuni step hanno testo d'aiuto, altri no → esperienza disomogenea;
  manca un "a cosa serve questo step / cosa ottengo".
- **Coach `rosa.html`**: poca spiegazione di cosa significhi "associare l'alter ego" e
  delle conseguenze di *"Conferma e Blocca"* (operazione irreversibile).

---

## 6. Requisito centrale — pattern informativi ed esplicativi

Il design system deve fornire **pattern riusabili** affinché ogni funzionalità dichiari
*a cosa serve* e *come si esegue*. Tre pattern richiesti:

### 6a. Help-box "a cosa serve"

Box informativo standard da anteporre a ogni funzione non banale: una riga su *cosa fa*,
*quando si usa*, *cosa si ottiene*. Proposta di markup (coerente con l'estetica):

```html
<div class="help-box">
  <span class="help-box__icon" aria-hidden="true">i</span>
  <div class="help-box__body">
    <strong>Carica listone</strong>
    <p>Importa la rosa completa della lega da file Excel. Dopo l'import potrai
       assegnare ogni giocatore al manager proprietario.</p>
    <a class="help-box__link" href="#formato-listone">Che file mi serve? →</a>
  </div>
</div>
```

Varianti: `.help-box` (info, ciano), `.help-box--warn` (giallo), `.help-box--danger`
(rosso, per operazioni irreversibili).

### 6b. Tabella completa file da caricare/scaricare

Censimento di **ogni** punto di upload/download dell'app. Il design system deve prevedere
un componente "file-spec" (con formato, struttura, link al template/esempio) da mostrare
accanto a ogni controllo di upload/download.

| # | Funzione | Pagina / Step | Direzione | Formato | Struttura attesa | Esempio / Template | Dove sta oggi |
|---|---|---|---|---|---|---|---|
| 1 | Carica listone (rose) | Admin · Step 1 | Upload | `.xlsx` | Sheet "TutteLeRose", 2 squadre affiancate (col A-D e F-I), header squadra in A/F, colonne `Ruolo \| Calciatore \| Squadra \| Costo`, fine blocco `Crediti Residui: X`. ~10 squadre × 25 giocatori | Manca → da creare `Rose_esempio.xlsx` scaricabile | UI presente (drop-zone), **senza spiegazione formato** |
| 2 | Carica formazioni (risultati) | Admin · Step 4 | Upload | `.xlsx` | Sheet per giornata, 2 match affiancati, header `squadra \| X-Y \| SQUADRA`, colonne `Ruolo \| Calciatore \| _ \| Voto_no_bonus \| Voto_con_bonus`, `Panchina` separa titolari, `TOTALE: XX,YY` fine squadra, `-` = senza voto | Manca → da creare `Formazioni_esempio.xlsx` | UI presente (drop-zone), **senza spiegazione formato** |
| 3 | Import dati storici | `POST /admin/historic/import` | Upload | `.csv` | Colonne obbligatorie: `player_name, role, team, season, matchday, rating, goals, yellow_cards, red_cards, goals_conceded, team_won, minutes` (role ∈ P/D/C/A) | Output di `backend/scrapers/*` o `convert_webscraper.py` | **Nessuna UI** — solo API/CLI |
| 4 | Sitemap stagioni (scraping) | `GET /webscraper/seasons.html` | Download | `.html` / `.json` | File locale con i link fbref di tutte le stagioni; usato da Web Scraper Chrome via sitemap JSON | `docs/webscraper/seasons.html`, `sitemap-*.json` | Fuori app (docs/CLI) |
| 5 | Export Web Scraper → CSV admin | Locale, post-scraping | Download → Upload | `.csv` | Export grezzo di Web Scraper, da convertire con `convert_webscraper.py` nel formato della riga #3 | `backend/scrapers/convert_webscraper.py` | Fuori app (CLI) |
| 6 | Associazione storico→attuale | Coach · Rosa | Form (no file) | — | Select per ruolo P/D/C/A; vincolo: ogni attuale usato una sola volta; blocco finale irreversibile | — | UI presente, **poca spiegazione** |
| 7 | Link invito allenatore | Admin · Step 2 | Download/Share | URL | Link con token da inviare al coach per la registrazione | Modal "Link invito" | UI presente |

> Nota: i punti 3–5 oggi vivono **fuori dall'interfaccia**. Il design system deve almeno
> prevedere, per ognuno, l'help-box e la file-spec che ne spieghino l'esistenza e il flusso,
> anche dove l'azione resta CLI (es. "il CSV va generato così, poi caricato qui").

### 6c. Stati vuoti parlanti e conferme con conseguenze

- **Empty state**: oltre al testo, indicare l'azione successiva (es. *"Nessun manager —
  aggiungine uno per assegnare i giocatori"*, già parzialmente presente).
- **Conferme irreversibili** (`Apri buste`, `Chiudi periodo associazioni`, `Conferma e
  Blocca`): pattern di dialog con descrizione esplicita della conseguenza, non solo
  `confirm()` nativo.

---

## 7. Requisiti del design system + proposte concrete

### 7a. Single source of truth dei token

Un unico file (es. `frontend/shared/tokens.css`) con i `:root`, importato dai tre fogli;
i CSS specifici contengono **solo** le differenze di layout. Eliminare le derive del §5a
allineando i valori (decidere `body` 15 o 16px, `login-card` 320 o 340px, hover bottone unico).

### 7b. Scala tipografica e spaziatura esplicite (proposta)

Sostituire i `clamp()`/rem sparsi con scale nominate:

```
/* Spaziatura — base 4px */
--space-1: 0.25rem;  --space-2: 0.5rem;  --space-3: 0.75rem;
--space-4: 1rem;     --space-6: 1.5rem;  --space-8: 2rem;

/* Tipografia pixel (titoli/UI) */
--fs-pixel-xs: 0.5rem;  --fs-pixel-sm: 0.6rem;
--fs-pixel-md: 0.85rem; --fs-pixel-lg: 1.1rem;

/* Tipografia dati (corpo/tabelle) */
--fs-data-sm: 0.82rem;  --fs-data-md: 0.9rem;  --fs-data-lg: 1rem;
```

Regola di leggibilità: nessuna label pixel sotto `--fs-pixel-xs` su mobile.

### 7c. Sistema di breakpoint (proposta)

```
--bp-sm: 480px;   /* telefoni */
--bp-md: 768px;   /* tablet */
--bp-lg: 1024px;  /* desktop */
```

Sostituire i breakpoint misti (640/700/768) con questi tre. Mobile-first dove possibile.

### 7d. Pattern mobile (abbozzo)

- **Hamburger**: sotto `--bp-md` la sidebar admin/coach diventa un drawer apribile da
  un'icona nella topbar (oggi semplicemente sparisce → navigazione persa).
- **Tabelle**: sotto `--bp-sm`, pattern "stack" (ogni riga diventa una card etichettata)
  in alternativa allo scroll orizzontale per le tabelle dense (classifica, giornata).
- **Scanline**: valutare riduzione opacità o disattivazione sotto `--bp-sm`.
- **Wizard step**: su mobile, indicatore compatto (es. "Step 2/4") + dot invece dei 4 label.

### 7e. Spec componenti (formato libreria)

Per ogni componente del §4, documentare: anatomia, varianti, stati (`hover/active/
disabled/done`), token usati, regole responsive, note accessibilità. Esempio bottone:

| Variante | Sfondo | Bordo | Testo | Hover | Uso |
|---|---|---|---|---|---|
| default | `--accent` | `--accent` | `--bg` | →`--accent2` | CTA primaria |
| secondary | trasparente | `--accent` | `--accent` | inverte | azione secondaria |
| danger | `--red` | `--red` | `#fff` | — | operazioni irreversibili |
| disabled | — | — | — | — | `opacity:0.45` |

### 7f. Accessibilità

- Verificare contrasto WCAG AA per testo su `--bg`/`--surface`; alzare dimensioni minime
  testo pixel.
- Sostituire le emoji-icona con un set icone pixel coerente (o aggiungere `aria-label`).
- Stato mai veicolato dal solo colore: aggiungere icona/etichetta (es. "✓ Fatto").
- Aggiungere ruoli/`aria-*` a tabs, wizard, modal, drop-zone.

### 7g. Pattern esplicativi

Formalizzare i componenti del §6 (`help-box`, `file-spec`, `empty-state`, `confirm-dialog`)
nella libreria, con markup d'esempio e linee guida su *quando* usarli.

---

## 8. Vincoli

- **Mantenere l'estetica 8-bit / Sensible Soccer** (palette, pixel font, spigoli vivi,
  ombre piene, scanline): è l'identità del prodotto.
- **Non modificare** `database/schema.sql`.
- Il deliverable di Claude design è il **design system** (token unificati + libreria
  componenti + pattern responsive ed esplicativi), non la riscrittura funzionale dell'app.
- Lingua dell'interfaccia: **italiano**.

---

## Appendice — File di riferimento

- Token e componenti: `backend/static/style.css`, `frontend/coach/css/coach.css`,
  `frontend/admin/css/admin.css`.
- Wizard, drop-zone, testi d'aiuto esistenti: `frontend/admin/index.html`.
- Flusso associazione e blocco coach: `frontend/coach/rosa.html`.
- Layout pubblico e "Come funziona": `backend/templates/base.html`, `home.html`.
- Flusso file storici (oggi fuori app): `docs/webscraper/README.md`,
  `docs/webscraper/seasons.html`, `backend/api/routers/historic.py`,
  `backend/scrapers/convert_webscraper.py`.
- Formati Excel reali (Rose/Formazioni): `CLAUDE_MEMORY.md`.
