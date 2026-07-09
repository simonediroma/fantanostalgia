# 28 — Pattern esplicativi (help-box, file-spec, confirm-dialog)

## Context
Depends on: task 26 e 27 completi (admin e coach già restylati con i componenti del design system). Branch: `task/28-pattern-esplicativi`.

## Existing modules to read first
1. `docs/design-system-brief.md` §6a-6c — specifica dei 3 pattern richiesti (help-box, file-spec, empty-state/confirm-dialog) e tabella completa dei punti di upload/download (§6b).
2. `frontend/admin/index.html` (dopo il task 26) — punti dove aggiungere help-box: upload listone (step 1), upload formazioni (step 4).
3. `frontend/coach/rosa.html` (dopo il task 27) — punto dove aggiungere help-box su cosa significa "associare l'alter ego" e conferma con conseguenze per "Conferma e Blocca" (già presente dal task 27, qui si arricchisce solo il testo esplicativo).

## Objective
Aggiungere il componente `HelpBox` prima di ogni funzione non banale (upload listone, upload formazioni, mapping, apertura buste, associazione alter ego), con testo su cosa fa/quando si usa/cosa si ottiene. Aggiungere un componente "file-spec" (tabella formato atteso + link a esempio) accanto a ogni upload/download secondo la tabella in `docs/design-system-brief.md` §6b.

## Acceptance criteria
- [ ] Ogni punto di upload (listone, formazioni) ha un `HelpBox` che spiega formato atteso e cosa succede dopo l'import.
- [ ] Componente file-spec (nuovo, da aggiungere a `frontend/shared/design-system.js` se non già presente dal task 24) mostra: formato, struttura attesa, link a un file di esempio scaricabile — per listone e formazioni (righe 1-2 della tabella §6b).
- [ ] Import dati storici via CSV (`POST /admin/historic/import`, oggi senza UI) ha almeno un `HelpBox` che ne spiega l'esistenza e il flusso (anche restando un'azione CLI, come indicato nella nota della tabella §6b).
- [ ] Empty state parlanti: dove oggi c'è solo un messaggio (`.empty`), aggiungere indicazione dell'azione successiva usando `EmptyState` con CTA dove sensato.
- [ ] Test: verifica manuale che ogni help-box/file-spec compaia nel punto corretto e col testo corretto (italiano, tono coerente).
- [ ] Build: nessun errore console nelle pagine modificate.

## Files that will be created or modified
- `frontend/shared/design-system.js` — eventuale componente file-spec aggiuntivo (se non coperto dal task 24)
- `frontend/admin/index.html` — help-box su step 1 (listone) e step 4 (formazioni)
- `frontend/coach/rosa.html` — help-box su associazione alter ego (arricchimento testo)
- `backend/templates/mapping.html` — eventuale help-box su reveal alter ego, se applicabile

## Notes for Claude Code
- Non creare ancora i file di esempio scaricabili (`Rose_esempio.xlsx`, `Formazioni_esempio.xlsx`) se non esistono — se il tempo lo consente aggiungerli come file statici in `backend/static/`, altrimenti lasciare un link placeholder e segnalarlo come nota di follow-up in `CLAUDE_MEMORY.md`.
- I testi devono seguire il tono di voce già definito: italiano, informale da gaming, 2ª persona per il coach, 3ª tecnica per l'admin (vedi `project-spec.md` sez. 6).
- Aggiornare `CLAUDE_MEMORY.md` a fine task: marcare **28** come `[x]`, aggiungere branch e PR.

## Pre-PR Gate
**5-axis code review (frontend):**
- [ ] Correctness: help-box e file-spec compaiono nei punti corretti con testo corretto?
- [ ] Accessibility: nessuna regressione a11y?
- [ ] Readability: comprensibile in 5 minuti?
- [ ] Performance: nessun peso bundle superfluo?
- [ ] Surgical: ogni riga riconducibile al requisito?
