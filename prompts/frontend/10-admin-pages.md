# 10 — Admin: Setup Lega + Upload Listone + Apertura Buste + Formazioni

## Obiettivo
Implementare le pagine admin (SPA HTML/JS statica) per gestire l'intera pipeline FantaNostalgia.

## Riferimenti
- `backend/api/routers/` — tutti gli endpoint admin già implementati
- `prompts/frontend/09-layout-base.md` — identità visiva e CSS

## Output atteso
`frontend/admin/` con tutti i file necessari.

---

## Struttura pagine admin

```
frontend/admin/
├── index.html        # login + routing SPA
├── js/
│   ├── api.js        # wrapper fetch verso backend API
│   ├── auth.js       # gestione sessione
│   ├── league.js     # setup lega
│   ├── listone.js    # upload listone + visualizza rosa
│   ├── mapping.js    # genera mapping + apertura buste
│   └── matchday.js   # upload formazioni + sorteggio + calcolo
└── css/
    └── admin.css
```

---

## Pagina 1 — Login (`/admin`)
- Form username + password
- POST `/auth/login`
- Redirect a `/admin/dashboard` se successo
- Errore inline se credenziali errate

## Pagina 2 — Dashboard (`/admin/dashboard`)
- Lista leghe esistenti con link a gestione
- Bottone "Nuova lega"

## Pagina 3 — Setup lega (`/admin/league/new` e `/admin/league/{id}`)
- Form: nome lega, stagione corrente, stagione storica, budget
- POST `/admin/league` o PUT `/admin/league/{id}`
- Dopo creazione → redirect a gestione lega

## Pagina 4 — Gestione lega (`/admin/league/{id}/manage`)
Wizard a step con stato visibile:

```
[✓] 1. Listone caricato    [→] 2. Mapping generato    [ ] 3. Buste aperte    [ ] 4. Giornate
```

### Step 1 — Upload listone
- Drag & drop o file picker `.xlsx`
- Preview: conteggio giocatori per ruolo dopo import
- Tabella assegnazione giocatori → manager (dropdown per ogni giocatore)

### Step 2 — Genera mapping
- Bottone "Genera mapping alter ego"
- POST `/admin/league/{id}/mapping/generate`
- Mostra riepilogo: n mappati, n duplicati, copertura per manager

### Step 3 — Apertura buste
- Bottone "Apri buste" con conferma ("Questa azione è irreversibile")
- Dopo apertura: mostra mapping completo raggruppato per manager

### Step 4 — Gestione giornate (ripetuta ogni settimana)
- Upload formazioni Excel
- Bottone "Sorteggia giornata storica" → mostra quale giornata è uscita
- Bottone "Calcola punteggi" → mostra punteggi giornata
- Link "Vedi classifica pubblica"

---

## Note implementative
- Navigazione SPA via `history.pushState` — nessun framework, vanilla JS
- `api.js`: wrapper generico `apiFetch(path, options)` che aggiunge base URL e gestisce 401 → redirect login
- Stato wizard persistito in `sessionStorage` (non localStorage — non supportato in alcuni ambienti)
- CSS admin estende `style.css` del backend — importare via CDN o copiare in `admin/css/`
