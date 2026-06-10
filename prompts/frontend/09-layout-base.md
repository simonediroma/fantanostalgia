# 09 — Layout Base + Navigazione

## Obiettivo
Creare il layout base condiviso tra pagine pubbliche (Jinja2 SSR) e pagina admin (HTML/JS statico). Design coerente, minimal, mobile-friendly.

## Riferimenti
- `docs/architecture.md` — sezione struttura frontend/backend

## Output atteso
- `backend/templates/base.html` — template Jinja2 base (pagine pubbliche)
- `backend/static/style.css` — CSS condiviso
- `frontend/admin/index.html` — shell admin SPA

---

## Identità visiva FantaNostalgia

**Palette:**
- Background: `#0f0f0f` (quasi nero)
- Surface: `#1a1a1a`
- Accent: `#c8a96e` (oro vintage)
- Testo primario: `#f0ece0` (bianco caldo)
- Testo secondario: `#888`
- Verde positivo: `#4caf50`
- Rosso negativo: `#e53935`

**Typography:**
- Display: Georgia serif (titoli, nomi giocatori storici)
- Body: system-ui sans-serif (dati, tabelle)
- Monospace: per punteggi e numeri

**Tono:** retrò-elegante, da "archivio storico" — non sportivo moderno.

---

## Template Jinja2 base (`backend/templates/base.html`)

Struttura:
```html
<!DOCTYPE html>
<html>
<head>
  <title>{% block title %}FantaNostalgia{% endblock %}</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <header>
    <a href="/">⚽ FantaNostalgia</a>
    <nav>
      <!-- link lega corrente se disponibile -->
    </nav>
  </header>
  <main>
    {% block content %}{% endblock %}
  </main>
  <footer>
    FantaNostalgia — La storia incontra il presente
  </footer>
</body>
</html>
```

---

## Pagine pubbliche da creare (solo shell vuota, contenuto nei prompt successivi)

- `backend/templates/home.html` — lista leghe
- `backend/templates/classifica.html` — classifica lega
- `backend/templates/mapping.html` — mapping alter ego

## Route Jinja2 da aggiungere a `backend/api/main.py`

```python
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def home(request: Request):
    # lista leghe
    return templates.TemplateResponse("home.html", {"request": request, "leagues": [...]})
```

---

## Note implementative
- CSS vanilla, nessun framework — max 200 righe
- Responsive: mobile-first, breakpoint unico a 768px
- Aggiungere `jinja2` e `aiofiles` a `backend/requirements.txt`
