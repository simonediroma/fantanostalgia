"""Foto dei giocatori storici da Wikidata/Wikimedia Commons.

Flusso per un giocatore: ricerca per nome su Wikidata → primo candidato che è un
calciatore (P106 = Q937857), ha un'immagine (P18) e un'età plausibile nella stagione
storica (P569) → miniatura e crediti (autore, licenza) da Commons.
Le immagini Commons sono CC-BY-SA o simili: i crediti vanno mostrati con la foto.
"""
import re
import time

import requests

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia rifiuta le richieste senza User-Agent descrittivo.
USER_AGENT = "fantanostalgia/1.0 (https://fantanostalgia.it)"
FOOTBALLER = "Q937857"
THUMB_WIDTH = 300
MIN_INTERVAL = 0.2
TIMEOUT = 15

_last_call = 0.0


def _get(url: str, params: dict) -> dict:
    global _last_call
    wait = MIN_INTERVAL - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()
    resp = requests.get(url, params={**params, "format": "json"},
                        headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def search_query(name: str) -> str:
    """'BAGGIO R.' → 'Baggio': via le iniziali, maiuscolo → capitalizzato."""
    q = re.sub(r"(\s+[A-Za-z]\.)+$", "", name.strip())
    return q.title() if q.isupper() else q


def _claim_values(entity: dict, prop: str) -> list:
    out = []
    for c in entity.get("claims", {}).get(prop, []):
        dv = c.get("mainsnak", {}).get("datavalue")
        if dv:
            out.append(dv["value"])
    return out


def pick_candidate(entities: list[dict], season: str) -> tuple[str, str] | None:
    """(wikidata_id, file Commons) del primo calciatore con foto ed età 15-45 nella stagione."""
    try:
        season_year = int(season[:4])
    except ValueError:
        season_year = None
    for e in entities:
        if not any(v.get("id") == FOOTBALLER for v in _claim_values(e, "P106")):
            continue
        images = _claim_values(e, "P18")
        if not images:
            continue
        births = _claim_values(e, "P569")
        if season_year and births:
            age = season_year - int(births[0]["time"][1:5])
            if not 15 <= age <= 45:
                continue
        return e["id"], images[0]
    return None


def parse_imageinfo(data: dict) -> dict | None:
    for page in data.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [None])[0]
        if not info:
            continue
        meta = info.get("extmetadata", {})
        artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()
        license_ = meta.get("LicenseShortName", {}).get("value", "").strip()
        return {
            "photo_url": info.get("thumburl") or info.get("url"),
            "photo_credit": ", ".join(p for p in (artist, license_) if p) or "Wikimedia Commons",
            "photo_source_url": info.get("descriptionurl"),
        }
    return None


def find_photo(name: str, season: str) -> dict | None:
    """Foto del giocatore o None. Errori di rete/HTTP vengono propagati."""
    found = _get(WIKIDATA_API, {
        "action": "wbsearchentities", "search": search_query(name),
        "language": "it", "uselang": "it", "type": "item", "limit": 10,
    }).get("search", [])
    ids = [r["id"] for r in found]
    if not ids:
        return None
    entities = _get(WIKIDATA_API, {
        "action": "wbgetentities", "ids": "|".join(ids), "props": "claims",
    }).get("entities", {})
    pick = pick_candidate([entities[i] for i in ids if i in entities], season)
    if pick is None:
        return None
    wikidata_id, filename = pick
    info = parse_imageinfo(_get(COMMONS_API, {
        "action": "query", "titles": f"File:{filename}", "prop": "imageinfo",
        "iiprop": "url|extmetadata", "iiurlwidth": THUMB_WIDTH,
    }))
    if info is None:
        return None
    return {"wikidata_id": wikidata_id, **info}
