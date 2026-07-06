# FantaNostalgia Design System

> **GitHub:** https://github.com/simonediroma/fantanostalgia
> Explore the full codebase for deeper design context: frontend CSS, HTML templates, and the design-system brief at `docs/design-system-brief.md`.

FantaNostalgia è un'app italiana di fantacalcio con una **classifica parallela nostalgia**. Ad ogni giocatore acquistato all'asta viene assegnato un alter ego storico casuale da una stagione passata — rivelato solo dopo la chiusura dell'asta ("apertura buste"). Ogni settimana viene sorteggiata una giornata storica e i punteggi vengono calcolati su due classifiche in parallelo.

**Superfici principali:**
- **Pagine pubbliche** — classifica, giornata, statistiche, mapping (Jinja2 SSR, `backend/templates/`)
- **Admin panel** — SPA vanilla JS con wizard a 4 step (Listone → Mapping → Buste → Giornate)
- **Coach portal** — SPA vanilla JS per associazione storico→attuale + lock definitivo

---

## CONTENT FUNDAMENTALS

**Lingua:** italiano. Tutta l'interfaccia è in italiano — titoli, label, messaggi, placeholder, conferme.

**Tono:** informale e da gaming. L'app è tra amici in una lega privata. Niente linguaggio corporate; si parla come tra vecchi compagni di lega.

**Casing:** UPPERCASE per tutto il testo in pixel font (label, bottoni, badge, intestazioni). Mixed case per corpo testo in data font (descrizioni, valori, placeholder).

**Persona:** 2ª persona singolare per il coach ("la tua rosa", "il tuo budget", "assegna"). 3ª tecnica per le funzioni admin ("la lega", "il mapping", "i giocatori").

**Emoji:** usati con parsimonia. Solo nel logo (⚽) e occasionalmente nei titoli di sezione. Mai nelle label dei bottoni o nelle tabelle.

**Numeri:** punteggi con una decimale (98.5, −1.0). Budget come interi (500, 47). Giornate come interi ordinati (Giornata 22).

**Esempi di copy autentico:**
- Drop zone: "Trascina il listone Excel qui"
- Lock: "Conferma e Blocca"
- Reveal: "Apertura Buste"
- Progress: "7/12 assegnati"
- Loading: "Caricamento…"
- Empty: "Nessun manager ancora."
- Success: "Listone importato — 250 giocatori caricati."
- Danger: "Questa operazione è irreversibile."

---

## VISUAL FOUNDATIONS

### Palette
Cinque token base + quattro semantici. Vedere `tokens/colors.css`.

| Token | Valore | Uso |
|---|---|---|
| `--bg` | `#050510` | Sfondo principale — indaco/nero |
| `--surface` | `#0d0d2b` | Pannelli, card, topbar — blu scuro |
| `--border` | `#3333aa` | Bordi tabelle e divisori — blu medio |
| `--text` | `#ffffff` | Corpo testo |
| `--muted` | `#7777aa` | Testo secondario/inattivo — viola-grigio |
| `--accent` | `#ffe600` | CTA, titoli, header tabelle — giallo neon |
| `--accent2` | `#00d4ff` | Hover, rank, accenti secondari — ciano |
| `--green` | `#00ff55` | Positivo, punteggi, "done" — verde neon |
| `--red` | `#ff1144` | Danger, negativi, irreversibile — rosso caldo |

### Tipografia
Due font soltanto. Vedere `tokens/typography.css`.
- **Press Start 2P** (`--font-pixel`): headings, label, bottoni, badge, wizard steps. Sempre UPPERCASE. Min 0.45rem. Caricato da Google Fonts CDN.
- **Courier New** (`--font-data`): corpo testo, tabelle, statistiche, valori numerici. Mixed case.

### Spacing
Scala base 4px (`--space-1` = 4px … `--space-12` = 48px). Vedere `tokens/spacing.css`.

### Effetti visivi (firma estetica)
- **Zero border-radius**: `border-radius: 0 !important` su tutto. Spigoli vivi, nessun arrotondamento.
- **Pixel shadows**: box-shadow senza blur (`2px 2px 0 #000` sm, `3px 3px 0` md, `4px 4px 0` lg). Mai `blur-radius > 0`.
- **CRT scanline overlay**: `body::before` con `repeating-linear-gradient` a righe sottili opache (0.15 alpha). Su tutte le pagine.
- **Hover bottone**: da giallo neon a ciano (istantaneo, senza `transition`). 8-bit — no easing.
- **Hover riga tabella**: `rgba(255,230,0,0.07)` — sottile giallo trasparente.
- **Transizioni**: nessuna sui colori/bordi; solo `transition: width 0.3s` per la progress bar.
- **Immagini**: non usate nell'app. Nessuna texture di sfondo.
- **Gradients**: nessuno (eccetto scanline CRT).

### Layout shell
- Topbar: sticky, 50px, `--surface` + bordo inferiore `--accent`.
- Sidebar: 200px, `--surface` + bordo destro `--border`.
- Contenuto: `flex: 1`, padding `1.75rem 2rem`.
- Lock bar: sticky bottom, `--surface` + bordo superiore `--accent` (coach only).

---

## ICONOGRAPHY

**Nessun icon set esterno.** L'app usa:
- **Emoji** (sparso): `⚽` nel logo, `→` `←` come frecce.
- **Caratteri Unicode** come pseudo-icone: `×` per dismiss, `✓` per confirm, `→` per arrows.
- **Testo come icona**: badge con lettere di ruolo (P / D / C / A) in `--font-pixel`.

**Non è presente** un icon font, sprite SVG, o libreria (Lucide, Heroicons, etc.). Se in futuro si aggiunge iconografia, mantenere lo stile pixel-art coerente con il font.

---

## COMPONENT LIBRARY

Tutti i componenti in `components/`. Namespace: `window.FantaNostalgiaDesignSystem_90de16`.

### Core (`components/core/`)
| Componente | Varianti |
|---|---|
| `Button` | default, secondary, danger, ghost; disabled; fullWidth |
| `Badge` | default, accent, cyan, green, red, outline |
| `Panel` | default, accent, danger, plain |

### Feedback (`components/feedback/`)
| Componente | Varianti |
|---|---|
| `Message` | ok, err, info, warn; onDismiss |
| `HelpBox` | info, warn, danger; title, link |
| `EmptyState` | message + optional action CTA |
| `ProgressBar` | value/max, label, showPercent |

### Data (`components/data/`)
| Componente | Note |
|---|---|
| `Table` | columns con align/pixel/color/nowrap; row click |

### Navigation (`components/navigation/`)
| Componente | Note |
|---|---|
| `Tabs` | tabs array; render function children |

### Forms (`components/forms/`)
| Componente | Varianti |
|---|---|
| `Input` | text/number/password; error; helpText; disabled |
| `DropZone` | accept; label/sublabel; fileName |
| `WizardSteps` | steps array; current (1-indexed); onNavigate |

### Overlay (`components/overlay/`)
| Componente | Note |
|---|---|
| `Modal` | open/onClose; title; actions (flex row) |

---

## UI KITS

- **`ui_kits/admin/index.html`** — Admin panel completo con login, sidebar, wizard a 4 step. Interattivo.
- **`ui_kits/coach/index.html`** — Coach portal: associazione storico→attuale, progress bar, lock definitivo.

---

## FILE INDEX

```
styles.css                    Entry point — solo @import
tokens/
  colors.css                  Palette (9 token + alias)
  typography.css              Font stacks + scale pixel/data
  spacing.css                 Scale 4px + layout constants
  effects.css                 Shadows, resets globali, CRT scanline
  fonts.css                   @import Google Fonts (Press Start 2P)
components/
  core/                       Button · Badge · Panel
  feedback/                   Message · HelpBox · EmptyState · ProgressBar
  data/                       Table
  navigation/                 Tabs
  forms/                      Input · DropZone · WizardSteps
  overlay/                    Modal
guidelines/
  colors-base.card.html       Palette superfici
  colors-semantic.card.html   Palette accenti
  type-pixel.card.html        Scala pixel font
  type-data.card.html         Scala data font
  spacing.card.html           Scala spaziatura
  effects.card.html           Sistema ombre
ui_kits/
  admin/index.html            Admin panel SPA
  coach/index.html            Coach portal SPA
docs/
  design-system-brief.md      Brief originale completo (dal repo)
  architecture.md             Architettura tecnica backend/frontend
readme.md                     Questo file
SKILL.md                      Skill agent config
```

---

## NOTE E CAVEATS

- **Press Start 2P** è caricato da Google Fonts CDN. In ambienti offline, scaricare il TTF da https://fonts.google.com/specimen/Press+Start+2P e aggiornare `tokens/fonts.css`.
- **Bundle**: il file `_ds_bundle.js` è generato automaticamente dal compilatore. Non modificarlo.
- **Pagine pubbliche SSR** (Jinja2 templates in `backend/templates/`) non sono incluse nel kit: usano `backend/static/style.css` separato. Per design context completo, leggere i template HTML nel repo GitHub.
