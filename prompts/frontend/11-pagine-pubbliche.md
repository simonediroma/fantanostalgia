# 11 — Pagine Pubbliche SSR (Jinja2)

## Obiettivo
Implementare le pagine pubbliche renderizzate server-side con Jinja2. URL condivisibili, nessun login richiesto.

## Riferimenti
- `prompts/frontend/09-layout-base.md` — layout base e identità visiva
- `backend/api/routers/standings.py` — dati da usare
- `backend/api/routers/mapping.py` — dati da usare

## Output atteso
- `backend/templates/home.html`
- `backend/templates/classifica.html`
- `backend/templates/mapping.html`
- Route Jinja2 in `backend/api/routers/public.py`

---

## Pagina 1 — Home (`/`)
Lista di tutte le leghe attive con link a classifica e mapping.

```
⚽ FantaNostalgia

Leghe attive:
┌─────────────────────────────────────┐
│ Lega Test 2024/25                   │
│ Stagione storica: 2002/03           │
│ [Classifica] [Mapping]              │
└─────────────────────────────────────┘
```

---

## Pagina 2 — Classifica (`/lega/{league_id}/classifica`)

Due tabelle affiancate (desktop) o in tab (mobile):

**Lega Normale**
| # | Manager | Totale | Ultima |
|---|---------|--------|--------|
| 1 | Simone | 412.5 | 68.5 |

**FantaNostalgia**
| # | Manager | Totale | Ultima |
|---|---------|--------|--------|
| 1 | Marco | 398.0 | 72.0 |

In fondo: "Ultima giornata: G6 corrente → G23 storica (sorteggiata il 14/10/2024)"

URL sharabile es: `/lega/1/classifica`

---

## Pagina 3 — Mapping alter ego (`/lega/{league_id}/mapping`)

Visibile solo se `buste_aperte = 1`, altrimenti pagina "Le buste non sono ancora state aperte".

Raggruppato per manager, ogni card mostra:

```
SIMONE — Team Nostalgia FC
┌──────────────────────────────────────────┐
│ Leao R. (A · Milan)  →  Shevchenko (A · Milan 2002/03) │
│ Theo H. (D · Milan)  →  Maldini P. (D · Milan 2002/03) │
│ ...                                                      │
└──────────────────────────────────────────┘
```

Duplicati evidenziati con badge "dup".

---

## Route da aggiungere (`backend/api/routers/public.py`)

```python
@router.get("/")
def home(request: Request): ...

@router.get("/lega/{league_id}/classifica")
def classifica(request: Request, league_id: int): ...

@router.get("/lega/{league_id}/mapping")
def mapping(request: Request, league_id: int): ...
```

---

## Note implementative
- Le route pubbliche chiamano direttamente il db (non i propri endpoint API) per ridurre latenza SSR
- Meta tag Open Graph per ogni pagina (per sharing su WhatsApp/Telegram con preview)
- `<title>` dinamico: "Lega Test — Classifica FantaNostalgia"
- Nessun JavaScript nelle pagine pubbliche — HTML puro
