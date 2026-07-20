"""Email transazionali di gioco ai manager via Resend, accodate su DB.

Il pattern è coda + scodamento schedulato (non invio sincrono): il backend
gira su Cloud Run senza CPU always-allocated, quindi un invio HTTP eseguito
dopo che la risposta è già stata inviata al client rischierebbe di essere
affamato di CPU e non completarsi mai. `enqueue_email` scrive una riga sulla
stessa transazione DB dell'azione che l'ha generata (nessun round-trip GCS
aggiuntivo); `process_email_queue`, invocato periodicamente da
`POST /admin/process-email-queue` (cron GitHub Actions), scoda e invia
davvero, dentro la sua propria richiesta HTTP.
"""
import json
import logging
import os
import sqlite3
from typing import Callable

import httpx

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM", "FantaNostalgia <no-reply@fantanostalgia.it>")

DEFAULT_BATCH_SIZE = 20
MAX_EMAIL_ATTEMPTS = 5


def send_email(to: str, subject: str, html: str) -> None:
    """Invia una email via Resend. Solleva se l'invio fallisce (errore di
    rete o risposta non-2xx) — il chiamante (process_email_queue) ne ha
    bisogno per decidere retry/dead-letter. Se RESEND_API_KEY non è
    impostata (dev/test) non invia nulla e non solleva: no-op loggato."""
    if not RESEND_API_KEY:
        logger.info("RESEND_API_KEY non impostata, email non inviata: to=%s subject=%s", to, subject)
        return
    resp = httpx.post(
        RESEND_API_URL,
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={"from": EMAIL_FROM, "to": [to], "subject": subject, "html": html},
        timeout=10.0,
    )
    resp.raise_for_status()


def _layout(title: str, body_html: str, cta_label: str, cta_url: str) -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;padding:24px;color:#222;">
      <h2 style="color:#1a7a3c;">{title}</h2>
      {body_html}
      <p style="margin:24px 0;">
        <a href="{cta_url}" style="background:#1a7a3c;color:#fff;padding:12px 20px;
           text-decoration:none;border-radius:4px;font-weight:bold;">{cta_label}</a>
      </p>
      <p style="margin-top:32px;font-size:12px;color:#888;">FantaNostalgia</p>
    </div>
    """


def _render_registration(params: dict, base_url: str) -> tuple[str, str]:
    name, league_name = params["name"], params["league_name"]
    html = _layout(
        "Registrazione completata",
        f"<p>Ciao {name}, ti sei registrato con successo e sei entrato nella lega "
        f"<strong>{league_name}</strong>.</p>",
        "Vai alle tue leghe",
        f"{base_url}/coach/",
    )
    return f"Benvenuto in FantaNostalgia, {name}!", html


def _render_league_join(params: dict, base_url: str) -> tuple[str, str]:
    name, league_name = params["name"], params["league_name"]
    html = _layout(
        "Nuova lega",
        f"<p>Ciao {name}, sei entrato nella lega <strong>{league_name}</strong>.</p>",
        "Vai alle tue leghe",
        f"{base_url}/coach/",
    )
    return f"Ti sei unito a {league_name}", html


def _render_matchday_results(params: dict, base_url: str) -> tuple[str, str]:
    name, league_name = params["name"], params["league_name"]
    league_id, matchday = params["league_id"], params["matchday"]
    html = _layout(
        f"Giornata {matchday} conclusa",
        f"<p>Ciao {name}, sono stati calcolati i risultati della giornata {matchday} "
        f"in <strong>{league_name}</strong>.</p>",
        "Vedi i punteggi",
        f"{base_url}/coach/lega/{league_id}/punteggi",
    )
    return f"{league_name}: risultati giornata {matchday}", html


def _render_pool_assignment(params: dict, base_url: str) -> tuple[str, str]:
    name, league_name, league_id = params["name"], params["league_name"], params["league_id"]
    html = _layout(
        "Rosa nostalgia assegnata",
        f"<p>Ciao {name}, ti è stato assegnato il pool di giocatori storici per "
        f"<strong>{league_name}</strong>. Accedi per associare ogni giocatore storico "
        "al suo alter ego attuale.</p>",
        "Associa gli alter ego",
        f"{base_url}/coach/lega/{league_id}",
    )
    return f"{league_name}: la tua rosa nostalgia è pronta", html


def _render_gran_premio_won(params: dict, base_url: str) -> tuple[str, str]:
    name, league_name, league_id = params["name"], params["league_name"], params["league_id"]
    prize_player_name = params["prize_player_name"]
    html = _layout(
        "Gran Premio vinto!",
        f"<p>Complimenti {name}, hai vinto il Gran Premio in <strong>{league_name}</strong> "
        f"e hai ricevuto <strong>{prize_player_name}</strong> come slot extra nella tua rosa "
        "nostalgia. Accedi per associare il nuovo giocatore al suo alter ego attuale.</p>",
        "Associa il premio",
        f"{base_url}/coach/lega/{league_id}",
    )
    return f"Hai vinto un Gran Premio in {league_name}!", html


def _render_market_won(params: dict, base_url: str) -> tuple[str, str]:
    name, league_name, league_id = params["name"], params["league_name"], params["league_id"]
    won_players_names = params["won_players_names"]
    players_list = ", ".join(won_players_names)
    html = _layout(
        "Mercato: giocatori aggiudicati!",
        f"<p>Complimenti {name}, hai vinto le offerte sul mercato di <strong>{league_name}</strong> "
        f"per: <strong>{players_list}</strong>. Accedi per associarli ai giocatori della tua rosa.</p>",
        "Associa i nuovi acquisti",
        f"{base_url}/coach/lega/{league_id}",
    )
    return f"Mercato {league_name}: hai aggiudicato {len(won_players_names)} giocatore/i", html


def _render_password_reset(params: dict, base_url: str) -> tuple[str, str]:
    name, new_password = params["name"], params["new_password"]
    html = _layout(
        "Password reimpostata",
        f"<p>Ciao {name}, la tua password è stata reimpostata dall'amministratore. "
        f"La tua nuova password è: <strong>{new_password}</strong></p>",
        "Vai al login",
        f"{base_url}/coach/login.html",
    )
    return "La tua password è stata reimpostata", html


TEMPLATES: dict[str, Callable[[dict, str], tuple[str, str]]] = {
    "registration": _render_registration,
    "league_join": _render_league_join,
    "matchday_results": _render_matchday_results,
    "pool_assignment": _render_pool_assignment,
    "gran_premio_won": _render_gran_premio_won,
    "market_won": _render_market_won,
    "password_reset": _render_password_reset,
}


def render_email(template: str, params: dict, base_url: str) -> tuple[str, str]:
    return TEMPLATES[template](params, base_url)


def league_manager_emails(conn, league_id: int) -> list[tuple[str, str]]:
    """Ritorna (nome, email) per i manager della lega che hanno un utente collegato."""
    rows = conn.execute(
        """
        SELECT m.name AS manager_name, u.email
        FROM manager m
        JOIN user u ON u.id = m.user_id
        WHERE m.league_id = ?
        """,
        (league_id,),
    ).fetchall()
    return [(r["manager_name"], r["email"]) for r in rows]


def enqueue_email(conn: sqlite3.Connection, template: str, to: str, params: dict) -> int:
    """Accoda un'email da inviare al prossimo giro di /admin/process-email-queue.
    Nessun commit qui: fa parte della transazione già aperta dal chiamante
    (blocco `with get_db()` esistente al trigger point)."""
    if template not in TEMPLATES:
        raise ValueError(f"Template email sconosciuto: {template}")
    cur = conn.execute(
        "INSERT INTO email_queue (template, to_email, params) VALUES (?, ?, ?)",
        (template, to, json.dumps(params)),
    )
    return cur.lastrowid


def process_email_queue(
    conn: sqlite3.Connection,
    base_url: str,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_attempts: int = MAX_EMAIL_ATTEMPTS,
) -> dict:
    """Elabora fino a batch_size righe 'pending' in ordine FIFO, sulla
    connessione già aperta dal chiamante (un solo commit/upload GCS per
    l'intero batch)."""
    rows = conn.execute(
        "SELECT id, template, to_email, params, attempts FROM email_queue"
        " WHERE status = 'pending' ORDER BY id LIMIT ?",
        (batch_size,),
    ).fetchall()

    sent = failed = retrying = 0
    for row in rows:
        try:
            params = json.loads(row["params"])
            subject, html = render_email(row["template"], params, base_url)
            send_email(row["to_email"], subject, html)
        except Exception as exc:
            attempts = row["attempts"] + 1
            new_status = "failed" if attempts >= max_attempts else "pending"
            conn.execute(
                "UPDATE email_queue SET attempts = ?, last_error = ?, status = ? WHERE id = ?",
                (attempts, str(exc)[:2000], new_status, row["id"]),
            )
            logger.exception(
                "Invio email in coda fallito (tentativo %s/%s): id=%s template=%s to=%s",
                attempts, max_attempts, row["id"], row["template"], row["to_email"],
            )
            if new_status == "failed":
                failed += 1
            else:
                retrying += 1
            continue
        if row["template"] == "password_reset":
            # La password in chiaro non deve restare indefinitamente nel DB
            # una volta inviata: la riga resta come traccia dell'evento
            # (template/to_email/sent_at), solo il contenuto sensibile viene redatto.
            conn.execute(
                "UPDATE email_queue SET status = 'sent', sent_at = CURRENT_TIMESTAMP, params = ? WHERE id = ?",
                (json.dumps({"redacted": True}), row["id"]),
            )
        else:
            conn.execute(
                "UPDATE email_queue SET status = 'sent', sent_at = CURRENT_TIMESTAMP WHERE id = ?",
                (row["id"],),
            )
        sent += 1

    remaining_pending = conn.execute(
        "SELECT COUNT(*) AS c FROM email_queue WHERE status = 'pending'"
    ).fetchone()["c"]
    return {
        "processed": len(rows),
        "sent": sent,
        "retrying": retrying,
        "failed": failed,
        "remaining_pending": remaining_pending,
    }
