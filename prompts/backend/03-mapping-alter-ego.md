# 03 — Algoritmo Mapping Alter Ego

## Obiettivo
Implementare l'algoritmo che assegna un alter ego storico a ogni giocatore attuale della lega. È il cuore di FantaNostalgia.

## Riferimenti
- `database/schema.sql` — tabelle `player_current`, `player_historic`, `alter_ego`
- `docs/architecture.md` — sezione "Regole di Business / Mapping alter ego"
- `docs/lessons.md` — sezione "Algoritmo Mapping Alter Ego"

## Output atteso
- `backend/engine/mapping.py` — logica algoritmo
- `backend/api/routers/mapping.py` — endpoints

---

## Regole algoritmo (implementare nell'ordine esatto)

### Step 1 — Costruisci pool per ruolo
Per ogni ruolo (P, D, C, A):
- Carica tutti i `player_historic` della stagione storica della lega con quel ruolo
- Questo è il pool disponibile per il ruolo

### Step 2 — Ordina giocatori attuali per titolarità
Per ogni ruolo, ordina `player_current` per `starts_current_season DESC`.
I titolari ricevono l'alter ego per primi.

### Step 3 — Assegnazione random
Per ogni giocatore attuale (in ordine di titolarità):
- Estrai random dal pool del suo ruolo (senza reinserimento)
- Salva in `alter_ego` con `is_duplicate = 0`
- Rimuovi il giocatore storico dal pool

### Step 4 — Verifica copertura minima per manager
Per ogni manager, controlla che abbia almeno: 1P + 4D + 4C + 3A con alter ego.
Se un manager non raggiunge il minimo per un ruolo → vai allo Step 5.

### Step 5 — Fallback duplicati
Se pool esaurito ma mancano coperture:
- Ricostruisci il pool completo per quel ruolo
- Estrai random e assegna con `is_duplicate = 1`
- Stesso alter ego può apparire più volte nella lega

### Step 6 — Salva mapping (buste chiuse)
Il mapping viene salvato su db ma NON è visibile pubblicamente fino all'apertura buste.
`league.buste_aperte = 0`

---

## Endpoints

### Genera mapping (admin)
```
POST /admin/league/{league_id}/mapping/generate
```
- Richiede che il listone sia stato caricato (`player_current` popolato)
- Richiede che i giocatori storici siano presenti (`player_historic` popolato)
- Idempotente: cancella mapping esistente e rigenera
- Usa `random.seed()` con seed casuale, salva il seed nel db per audit

Response:
```json
{
  "mapped": 120,
  "duplicates": 8,
  "coverage_by_manager": [
    {"manager": "Simone", "P": 3, "D": 8, "C": 8, "A": 6}
  ]
}
```

### Stato mapping (admin, buste chiuse)
```
GET /admin/league/{league_id}/mapping
```
Restituisce il mapping completo (visibile solo all'admin prima dell'apertura buste).

---

## Note implementative
- Tutto il codice dell'algoritmo va in `backend/engine/mapping.py`
- Il router importa e chiama le funzioni dell'engine — nessuna logica nel router
- Usare una singola transazione db per l'intera operazione
- Aggiungere alla tabella `league` una colonna `mapping_seed TEXT` per salvare il seed usato (aggiornare schema.sql)
