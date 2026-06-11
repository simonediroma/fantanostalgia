# 16 — Redesign estetica 8-bit (Sensible Soccer)

## Obiettivo

Allineare tutta la grafica dell'app allo stile 8-bit ispirato a Sensible Soccer (Amiga/DOS, anni '90): pixel font, palette retrò satura su sfondo blu-nero, bordi netti senza border-radius, effetto scanline CRT opzionale.

Nessuna logica backend cambia — solo CSS e template HTML.

## Riferimenti

- `backend/static/style.css` — CSS pagine pubbliche (309 righe circa)
- `frontend/admin/css/admin.css` — CSS admin panel (309 righe circa)
- `backend/templates/base.html` — template base SSR
- `frontend/admin/index.html` — SPA admin
- `docs/architecture.md` — architettura per contesto

## Output atteso

| File | Azione |
|---|---|
| `backend/static/style.css` | Modificato — nuova palette + regole stile 8-bit |
| `frontend/admin/css/admin.css` | Modificato — stessa palette + stile admin 8-bit |
| `backend/templates/base.html` | Modificato — import font pixel nel `<head>` |
| `frontend/admin/index.html` | Modificato — import font pixel nel `<head>` |

---

## Task 1 — Nuova palette CSS e font

Sostituire le variabili CSS in `:root` in **entrambi** i file CSS (`style.css` e `admin.css`) con:

```css
:root {
  --bg: #050510;
  --surface: #0d0d2b;
  --accent: #ffe600;
  --accent2: #00d4ff;
  --text: #ffffff;
  --muted: #7777aa;
  --green: #00ff55;
  --red: #ff1144;
  --border: #3333aa;
  --font-pixel: 'Press Start 2P', monospace;
  --font-data: 'Courier New', monospace;
}
```

Aggiungere in entrambi i template HTML (`base.html` e `admin/index.html`) nel `<head>`, prima del tag `<link>` al CSS locale:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet">
```

---

## Task 2 — Regole stilistiche globali

In entrambi i CSS, applicare come reset/override base:

```css
/* Reset border-radius ovunque */
*, *::before, *::after {
  border-radius: 0 !important;
  box-sizing: border-box;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-data);
  position: relative;
}

/* Scanline overlay — effetto CRT sottile */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background: repeating-linear-gradient(
    to bottom,
    transparent 0px,
    transparent 2px,
    rgba(0, 0, 0, 0.15) 2px,
    rgba(0, 0, 0, 0.15) 4px
  );
  pointer-events: none;
  z-index: 9999;
}

h1, h2, h3, .logo, .site-title {
  font-family: var(--font-pixel);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--accent);
}

/* Dimensioni font pixel per leggibilità */
h1, .logo { font-size: clamp(0.8rem, 2vw, 1.1rem); }
h2 { font-size: clamp(0.65rem, 1.5vw, 0.85rem); }
h3 { font-size: 0.65rem; }

/* Pixel shadow (senza blur) */
.pixel-shadow {
  box-shadow: 2px 2px 0 #000;
}
```

---

## Task 3 — Componenti pubblici (`style.css`)

### Header / nav

```css
header, nav {
  background: var(--surface);
  border-bottom: 2px solid var(--accent);
}
```

Logo e nome sito: `font-family: var(--font-pixel)`, `color: var(--accent)`.

### Bottoni

```css
button, .btn, a.btn-link {
  font-family: var(--font-pixel);
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  background: var(--accent);
  color: var(--bg);
  border: 2px solid var(--accent);
  box-shadow: 2px 2px 0 #000;
  cursor: pointer;
}
button:hover, .btn:hover {
  background: var(--accent2);
  border-color: var(--accent2);
  color: var(--bg);
}
button.secondary {
  background: transparent;
  color: var(--accent);
  border-color: var(--accent);
}
button.secondary:hover {
  background: var(--accent);
  color: var(--bg);
}
button.danger {
  background: var(--red);
  border-color: var(--red);
  color: #fff;
}
```

### Tabelle

```css
table {
  font-family: var(--font-data);
  border-collapse: collapse;
  border: 2px solid var(--border);
}
th {
  background: var(--accent);
  color: var(--bg);
  font-family: var(--font-pixel);
  font-size: 0.55rem;
  text-transform: uppercase;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--bg);
}
td {
  border: 1px solid var(--border);
  padding: 0.4rem 0.75rem;
  color: var(--text);
}
tr:hover td {
  background: rgba(255, 230, 0, 0.07);
}
.score, .total { font-family: var(--font-data); color: var(--green); }
.neg { color: var(--red); }
.rank { font-family: var(--font-pixel); font-size: 0.6rem; color: var(--accent2); }
```

### Card lega

```css
.league-card {
  background: var(--surface);
  border: 2px solid var(--border);
  box-shadow: 3px 3px 0 #000;
  padding: 1rem;
}
.league-card:hover {
  border-color: var(--accent);
  box-shadow: 3px 3px 0 var(--accent);
}
```

### Tabs

```css
.tabs {
  border-bottom: 2px solid var(--border);
}
.tab-btn {
  font-family: var(--font-pixel);
  font-size: 0.55rem;
  text-transform: uppercase;
  padding: 0.5rem 1rem;
  background: transparent;
  color: var(--muted);
  border: none;
  border-bottom: 3px solid transparent;
  cursor: pointer;
}
.tab-btn.active {
  background: var(--accent);
  color: var(--bg);
  border-bottom-color: var(--accent);
}
```

### Badge ruolo (`.role-badge`)

```css
.role-badge {
  font-family: var(--font-pixel);
  font-size: 0.5rem;
  text-transform: uppercase;
  background: var(--accent2);
  color: var(--bg);
  padding: 0.15rem 0.4rem;
  border: 1px solid var(--accent2);
}
```

### Nome storico (`.historic-name`)

```css
.historic-name {
  font-family: var(--font-pixel);
  font-size: 0.65rem;
  color: var(--accent);
  text-transform: uppercase;
}
```

---

## Task 4 — Admin panel (`admin.css`)

### Topbar

```css
.topbar {
  background: var(--surface);
  border-bottom: 2px solid var(--accent);
}
.topbar .logo {
  font-family: var(--font-pixel);
  font-size: 0.75rem;
  color: var(--accent);
  text-transform: uppercase;
}
```

### Sidebar

```css
aside {
  background: var(--surface);
  border-right: 2px solid var(--border);
}
aside nav a {
  font-family: var(--font-pixel);
  font-size: 0.55rem;
  text-transform: uppercase;
  color: var(--muted);
  padding: 0.6rem 1rem;
  display: block;
  border-left: 3px solid transparent;
}
aside nav a:hover, aside nav a.active {
  background: var(--accent);
  color: var(--bg);
  border-left-color: var(--accent2);
}
```

### Panel e form

```css
.panel {
  background: var(--surface);
  border: 2px solid var(--border);
  box-shadow: 3px 3px 0 #000;
  padding: 1.25rem;
}
input, select, textarea {
  background: var(--bg);
  border: 2px solid var(--border);
  color: var(--text);
  font-family: var(--font-data);
  padding: 0.4rem 0.6rem;
}
input:focus, select:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent);
}
label {
  font-family: var(--font-pixel);
  font-size: 0.55rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
}
```

### Wizard step

```css
.step {
  font-family: var(--font-pixel);
  font-size: 0.55rem;
  text-transform: uppercase;
  color: var(--muted);
  padding: 0.4rem 0.75rem;
  border-bottom: 3px solid transparent;
}
.step.active {
  color: var(--bg);
  background: var(--accent);
  border-bottom-color: var(--accent2);
}
.step.done {
  color: var(--green);
  border-bottom-color: var(--green);
}
```

### Drop zone

```css
.drop-zone {
  border: 2px dashed var(--border);
  background: var(--surface);
  text-align: center;
  padding: 2rem;
  font-family: var(--font-pixel);
  font-size: 0.6rem;
  text-transform: uppercase;
  color: var(--muted);
}
.drop-zone.dragover {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(255, 230, 0, 0.05);
}
```

### Messaggi feedback

```css
.msg {
  font-family: var(--font-pixel);
  font-size: 0.6rem;
  text-transform: uppercase;
  padding: 0.6rem 1rem;
  border: 2px solid;
}
.msg.ok {
  border-color: var(--green);
  color: var(--green);
  background: rgba(0, 255, 85, 0.08);
}
.msg.err {
  border-color: var(--red);
  color: var(--red);
  background: rgba(255, 17, 68, 0.08);
}
```

---

## Note implementative

- `Press Start 2P` è un font compatto: non usarlo per il corpo testo o celle di tabella (illeggibile sotto 0.5rem). Usarlo solo per heading, label, badge, bottoni.
- Il `!important` sul reset `border-radius: 0` è necessario per neutralizzare eventuali stili browser default su input/button.
- Lo scanline overlay con `z-index: 9999` non deve bloccare click: `pointer-events: none` è obbligatorio.
- Su mobile (`max-width: 640px`) ridurre ulteriormente i font-size pixel: `h1 { font-size: 0.7rem }`.
- Verificare che i link del navbar nel template `base.html` usino classi già presenti — non aggiungere classi HTML nuove senza motivo.
- I due CSS (`style.css` e `admin.css`) restano file separati: copiare le variabili `:root` in entrambi senza unificarli.
