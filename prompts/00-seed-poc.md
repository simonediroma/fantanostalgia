# 00 — Seed dati POC

## Obiettivo
Creare uno script Python che popola il database SQLite con dati di test realistici per validare l'intera pipeline FantaNostalgia senza dipendenze da scraper esterni.

## Riferimenti
- `database/schema.sql` — schema completo
- `docs/architecture.md` — regole di business

## Output atteso
File `database/seed_poc.py` eseguibile con `python database/seed_poc.py`.

## Dati da generare

### Lega
- 1 lega: "Lega Test 2024/25"
- stagione corrente: "2024/25"
- stagione storica: "2002/03"
- budget: 500

### Manager (8)
Nomi inventati: Simone, Marco, Luca, Andrea, Paolo, Matteo, Giorgio, Filippo

### Giocatori attuali (rose da ~25 giocatori per ruolo)
Inventare ~120 giocatori totali distribuiti per ruolo:
- 12 portieri (P)
- 40 difensori (D)
- 40 centrocampisti (C)
- 28 attaccanti (A)

Ogni giocatore ha:
- nome inventato realistico (es. "Rossi M.", "Bianchi A.")
- squadra (usa 20 squadre Serie A inventate: "Milano FC", "Roma United", ecc.)
- quotazione (P: 1-20, D: 1-25, C: 1-30, A: 1-40)
- starts_current_season (0-30, distribuito realisticamente: titolari ~25, riserve ~5)
- manager_id assegnato (ogni manager ha ~15 giocatori: 3P, 8D, 8C, 6A)

### Giocatori storici (stagione "2002/03")
Inventare ~100 giocatori storici distribuiti per ruolo:
- 10 portieri
- 32 difensori
- 32 centrocampisti
- 26 attaccanti

Ogni giocatore ha:
- nome inventato d'epoca (es. "Del Vecchio R.", "Ferretti G.")
- squadra storica inventata
- source: "synthetic"

### Voti storici
Per ogni giocatore storico, generare voti per 34 giornate (stagione corta pre-2003):
- Se titolare (80% probabilità per giornata): voto tra 4.5 e 8.5
- Se non giocato (20%): rating = NULL
- Aggiungere bonus realistici: gol (10% prob per A, 5% per C, 2% per D), assist (15%), ammonizioni (10%), clean sheet per P e D

### Mapping alter ego
Assegnare alter ego seguendo le regole:
- Random per ruolo
- Priorità a giocatori con starts_current_season più alto
- Copertura minima: 1P + 4D + 4C + 3A per manager
- Fallback duplicati se necessario
- is_duplicate = 1 per i duplicati

### Giornate già sorteggiate (simula 5 giornate già giocate)
- giornata corrente 1 → storica 12
- giornata corrente 2 → storica 7
- giornata corrente 3 → storica 28
- giornata corrente 4 → storica 3
- giornata corrente 5 → storica 19

### Formazioni (5 giornate già giocate)
Per ogni manager, per ogni giornata: 11 titolari + 7 riserve dalla sua rosa.

### Punteggi e classifica (calcolati dalle 5 giornate)
Calcolare matchday_score e standings per entrambe le leghe usando i voti generati.

## Note implementative
- Usare `random.seed(42)` per risultati riproducibili
- Stampare riepilogo a fine esecuzione: n giocatori, n alter ego, n duplicati, classifica attuale
- Lo script deve essere idempotente: cancella e ricrea tutto ad ogni esecuzione
- Importare e usare le funzioni di `backend/engine/` dove esistono già (mapping, scoring)
