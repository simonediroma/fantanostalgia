import os
import sqlite3
import tempfile
import time
from contextlib import contextmanager

from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "development")
GCS_BUCKET = os.getenv("GCS_BUCKET", "fantanostalgia-db")
GCS_BLOB = "fantanostalgia.db"
DB_LOCAL_PATH = os.getenv("DB_LOCAL_PATH", "fantanostalgia.db")

_tmp_db_path: str | None = None
_last_gcs_download: float = 0.0
_GCS_CACHE_TTL = 30.0  # seconds before re-downloading from GCS


def _get_db_path() -> str:
    if ENV == "development":
        return DB_LOCAL_PATH

    global _tmp_db_path
    if _tmp_db_path is None:
        _tmp_db_path = os.path.join(tempfile.gettempdir(), "fantanostalgia.db")
    return _tmp_db_path


def _gcs_blob():
    from google.cloud import storage

    client = storage.Client()
    return client.bucket(GCS_BUCKET).blob(GCS_BLOB)


def _download_db_from_gcs() -> bool:
    """Returns True if the blob existed and was downloaded, False otherwise."""
    global _last_gcs_download
    blob = _gcs_blob()
    if not blob.exists():
        return False
    blob.download_to_filename(_get_db_path())
    _last_gcs_download = time.monotonic()
    return True


def _download_db_from_gcs_if_stale() -> None:
    """Download from GCS only when the local cache is absent or expired."""
    db_path = _get_db_path()
    cache_fresh = (
        os.path.exists(db_path)
        and (time.monotonic() - _last_gcs_download) < _GCS_CACHE_TTL
    )
    if not cache_fresh:
        _download_db_from_gcs()


def _upload_db_to_gcs() -> None:
    global _last_gcs_download
    _gcs_blob().upload_from_filename(_get_db_path())
    _last_gcs_download = time.monotonic()


def init_db() -> None:
    fresh = True
    if ENV != "development":
        try:
            fresh = not _download_db_from_gcs()
        except Exception:
            pass  # errore di rete: procedi con db locale

    schema_path = os.path.join(os.path.dirname(__file__), "..", "..", "database", "schema.sql")
    with open(schema_path) as f:
        schema = f.read()

    with sqlite3.connect(_get_db_path()) as conn:
        conn.executescript(schema)
        for _col, _def in [
            ("cycle", "INTEGER NOT NULL DEFAULT 1"),          # matchday_draw
        ]:
            try:
                conn.execute(f"ALTER TABLE matchday_draw ADD COLUMN {_col} {_def}")
            except sqlite3.OperationalError:
                pass
        for _col, _def in [
            ("team_won", "INTEGER DEFAULT 0"),
            ("minutes", "INTEGER DEFAULT 0"),
        ]:
            try:
                conn.execute(f"ALTER TABLE historic_rating ADD COLUMN {_col} {_def}")
            except sqlite3.OperationalError:
                pass
        for _col, _def in [
            ("user_id", "INTEGER"),
            ("assignments_locked", "INTEGER DEFAULT 0"),
        ]:
            try:
                conn.execute(f"ALTER TABLE manager ADD COLUMN {_col} {_def}")
            except sqlite3.OperationalError:
                pass
        for _col, _def in [
            ("associations_closed", "INTEGER DEFAULT 0"),
            ("associations_closed_at", "TIMESTAMP"),
        ]:
            try:
                conn.execute(f"ALTER TABLE league ADD COLUMN {_col} {_def}")
            except sqlite3.OperationalError:
                pass
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS league_invite (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER REFERENCES league(id),
                manager_id INTEGER REFERENCES manager(id),
                token TEXT NOT NULL UNIQUE,
                used_by_user_id INTEGER REFERENCES user(id),
                used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS manager_nostalgia_pool (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manager_id INTEGER REFERENCES manager(id),
                league_id INTEGER REFERENCES league(id),
                player_historic_id INTEGER REFERENCES player_historic(id),
                assigned_player_current_id INTEGER REFERENCES player_current(id),
                UNIQUE(manager_id, player_historic_id)
            );
            CREATE TABLE IF NOT EXISTS gran_premio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER REFERENCES league(id),
                matchday INTEGER NOT NULL,
                criterion TEXT NOT NULL CHECK(criterion IN
                    ('best_score', 'worst_defense', 'best_player', 'worst_player')),
                prize_player_historic_id INTEGER REFERENCES player_historic(id),
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'resolved')),
                winner_manager_id INTEGER REFERENCES manager(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            );
        """)
        conn.commit()

    if ENV != "development":
        try:
            _upload_db_to_gcs()
        except Exception:
            pass  # non critico: il primo get_db con write lo farà


@contextmanager
def get_db():
    if ENV != "development":
        try:
            _download_db_from_gcs_if_stale()
        except Exception:
            pass  # errore di rete: usa file locale

    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    changed = False
    try:
        yield conn
        changed = conn.total_changes > 0
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    if ENV != "development" and changed:
        try:
            _upload_db_to_gcs()
        except Exception:
            pass  # dati committati localmente; la cache TTL garantisce coerenza
