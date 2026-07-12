"""Invio email transazionali di gioco ai manager via Resend.

Best-effort: un fallimento di invio non deve mai bloccare l'azione che lo
ha generato (registrazione, sorteggio, ecc.) — va solo loggato. In assenza
di RESEND_API_KEY (es. ambiente dev) le email vengono loggate e non inviate.
"""
import logging
import os

import httpx

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM", "FantaNostalgia <no-reply@fantanostalgia.it>")


def send_email(to: str, subject: str, html: str) -> None:
    if not RESEND_API_KEY:
        logger.info("RESEND_API_KEY non impostata, email non inviata: to=%s subject=%s", to, subject)
        return
    try:
        resp = httpx.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={"from": EMAIL_FROM, "to": [to], "subject": subject, "html": html},
            timeout=10.0,
        )
        resp.raise_for_status()
    except Exception:
        logger.exception("Invio email fallito: to=%s subject=%s", to, subject)


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


def notify_registration(to: str, name: str, league_name: str, base_url: str) -> None:
    html = _layout(
        "Registrazione completata",
        f"<p>Ciao {name}, ti sei registrato con successo e sei entrato nella lega "
        f"<strong>{league_name}</strong>.</p>",
        "Vai alle tue leghe",
        f"{base_url}/coach/",
    )
    send_email(to, f"Benvenuto in FantaNostalgia, {name}!", html)


def notify_league_join(to: str, name: str, league_name: str, base_url: str) -> None:
    html = _layout(
        "Nuova lega",
        f"<p>Ciao {name}, sei entrato nella lega <strong>{league_name}</strong>.</p>",
        "Vai alle tue leghe",
        f"{base_url}/coach/",
    )
    send_email(to, f"Ti sei unito a {league_name}", html)


def notify_matchday_results(to: str, name: str, league_name: str, league_id: int, matchday: int, base_url: str) -> None:
    html = _layout(
        f"Giornata {matchday} conclusa",
        f"<p>Ciao {name}, sono stati calcolati i risultati della giornata {matchday} "
        f"in <strong>{league_name}</strong>.</p>",
        "Vedi i punteggi",
        f"{base_url}/coach/lega/{league_id}/punteggi",
    )
    send_email(to, f"{league_name}: risultati giornata {matchday}", html)


def notify_pool_assignment(to: str, name: str, league_name: str, league_id: int, base_url: str) -> None:
    html = _layout(
        "Rosa nostalgia assegnata",
        f"<p>Ciao {name}, ti è stato assegnato il pool di giocatori storici per "
        f"<strong>{league_name}</strong>. Accedi per associare ogni giocatore storico "
        "al suo alter ego attuale.</p>",
        "Associa gli alter ego",
        f"{base_url}/coach/lega/{league_id}",
    )
    send_email(to, f"{league_name}: la tua rosa nostalgia è pronta", html)


def notify_gran_premio_won(to: str, name: str, league_name: str, league_id: int, prize_player_name: str, base_url: str) -> None:
    html = _layout(
        "Gran Premio vinto!",
        f"<p>Complimenti {name}, hai vinto il Gran Premio in <strong>{league_name}</strong> "
        f"e hai ricevuto <strong>{prize_player_name}</strong> come slot extra nella tua rosa "
        "nostalgia. Accedi per associare il nuovo giocatore al suo alter ego attuale.</p>",
        "Associa il premio",
        f"{base_url}/coach/lega/{league_id}",
    )
    send_email(to, f"Hai vinto un Gran Premio in {league_name}!", html)


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
