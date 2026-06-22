"""
Utilità per la normalizzazione delle stagioni — zero dipendenze esterne.

Importabile sia dai router FastAPI sia dagli scraper standalone.
"""


def normalize_season(season: str) -> str:
    """Normalizza qualsiasi formato stagione al formato canonico YYYY/YY.

    Accetta:
        YYYY-YYYY  (es. 2000-2001) → 2000/01
        YYYY-YY    (es. 2000-01)   → 2000/01
        YYYY/YY    (es. 2000/01)   → 2000/01  (già corretto, pass-through)
    """
    s = season.strip()
    if "/" in s:
        return s
    if "-" in s:
        parts = s.split("-")
        if len(parts) == 2 and len(parts[0]) == 4:
            if len(parts[1]) == 4:
                return f"{parts[0]}/{parts[1][2:]}"   # YYYY-YYYY → YYYY/YY
            if len(parts[1]) == 2:
                return f"{parts[0]}/{parts[1]}"        # YYYY-YY   → YYYY/YY
    return s


def season_variants(canonical: str) -> list[str]:
    """Restituisce tutte le rappresentazioni possibili di una stagione.

    Es. "1999/00" → ["1999/00", "1999-00", "1999-2000"]
        "2016/17" → ["2016/17", "2016-17", "2016-2017"]
    """
    parts = canonical.split("/")
    if len(parts) != 2:
        return [canonical]
    y1 = int(parts[0])
    yy = parts[1]
    y2 = y1 + 1
    return [
        canonical,                  # YYYY/YY
        f"{y1}-{yy}",               # YYYY-YY
        f"{y1}-{y2:04d}",           # YYYY-YYYY
    ]
