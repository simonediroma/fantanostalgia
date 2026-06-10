# fantanostalgia — Claude Code Configuration

---

## ⚡ ISTRUZIONI OPERATIVE PER CLAUDE — LEGGERE SEMPRE

1. **Inizio sessione:** leggi `@CLAUDE_MEMORY.md` per lo stato corrente. Quella è la tua partenza.
2. **Fine sessione:** prima del commit finale, aggiorna obbligatoriamente `CLAUDE_MEMORY.md` (gitignored — non committare):
   - Marca i task completati con `[x]`
   - Aggiorna `Ultima sessione` con la data odierna
   - Scrivi `Prossima sessione — inizia da qui` in modo esplicito e actionable
   - Aggiorna `PR corrente` e `Branch` se cambiati
3. **Branch:** crea un branch dedicato per ogni task, con naming `task/NN-nome-breve` (es. `task/01-bootstrap`). Parti sempre da `main` aggiornato. Mai push diretto su `main`.
4. **PR:** una PR per task. Ogni PR dal branch del task verso `main`. Ogni PR deve essere indipendente e reviewable. Aggiorna `CLAUDE_MEMORY.md` con il link alla PR aperta.
5. **File invariati:** non toccare mai `database/schema.sql` senza approvazione esplicita.

---

## Linee Guida Comportamentali (Karpathy Rules)

> Regole per ridurre gli errori comuni nell'assistenza al codice. In caso di contrasto, le istruzioni operative sopra hanno precedenza.

### 1. Pensa Prima di Scrivere Codice

**Non assumere. Non nascondere confusione. Porta a galla i trade-off.**

Prima di implementare:
- Enuncia esplicitamente le tue assunzioni. Se incerto, chiedi.
- Se esistono interpretazioni multiple, presentale — non scegliere in silenzio.
- Se esiste un approccio più semplice, dillo. Spingi back quando è giustificato.
- Se qualcosa non è chiaro, fermati. Nomina cosa non è chiaro. Chiedi.

### 2. Semplicità Prima di Tutto

**Il minimo codice che risolve il problema. Niente di speculativo.**

- Nessuna feature oltre a quanto richiesto.
- Nessuna astrazione per codice usato una sola volta.
- Nessuna "flessibilità" o "configurabilità" non richiesta.
- Nessuna gestione di errori per scenari impossibili.
- Se scrivi 200 righe e basterebbero 50, riscrivilo.

Test: "Un senior engineer direbbe che è sovra-complicato?" Se sì, semplifica.

### 3. Cambiamenti Chirurgici

**Tocca solo quello che devi. Pulisci solo il tuo stesso disordine.**

Quando modifichi codice esistente:
- Non "migliorare" codice, commenti o formattazione adiacente.
- Non refactorare cose che non sono rotte.
- Mantieni lo stile esistente, anche se lo faresti diversamente.
- Se noti codice morto non correlato, menzionalo — non eliminarlo.

### 4. Esecuzione Goal-Driven

**Definisci criteri di successo. Itera fino a verifica.**

Trasforma i task in obiettivi verificabili:
- "Aggiungi validazione" → "Scrivi test per input non validi, poi falli passare"
- "Correggi il bug" → "Scrivi un test che lo riproduce, poi fallo passare"

### 5. Cerca Prima di Implementare

**Non reimplementare mai qualcosa che esiste già.**

Prima di scrivere qualsiasi funzione nuova:
1. Cerca nel codebase se esiste già una funzionalità equivalente.
2. Se esiste: riusa o estendi. Non duplicare.

---

## Riferimenti Tecnici

Prima di ogni scelta architetturale o di implementazione, leggi @docs/architecture.md.

Prima di implementare qualcosa di nuovo o non banale, leggi @docs/lessons.md.

---

# 📍 Stato Corrente e Memoria di Sessione

@CLAUDE_MEMORY.md
