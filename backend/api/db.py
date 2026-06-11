import os
import sqlite3
import tempfile
from contextlib import contextmanager

from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "development")
GCS_BUCKET = os.getenv("GCS_BUCKET", "fantanostalgia-db")
GCS_BLOB = "fantanostalgia.db"
DB_LOCAL_PATH = os.getenv("DB_LOCAL_PATH", "fantanostalgia.db")

_tmp_db_path: str | None = None


def _get_db_path() -> str:
    if ENV == "development":
        return DB_LOCAL_PATH

    global _tmp_db_path
    if _tmp_db_path is None:
        _tmp_db_path = os.path.join(tempfile.gettempdir(), "fantanostalgia.db")
    return _tmp_db_path


def _download_db_from_gcs() -> None:
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_BLOB)
    blob.download_to_filename(_get_db_path())


def _upload_db_to_gcs() -> None:
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_BLOB)
    blob.upload_from_filename(_get_db_path())


def init_db() -> None:
    if ENV != "development":
        try:
            _download_db_from_gcs()
        except Exception:
            pass  # primo avvio: db non ancora su GCS

    schema_path = os.path.join(os.path.dirname(__file__), "..", "..", "database", "schema.sql")
    with open(schema_path) as f:
        schema = f.read()

    with sqlite3.connect(_get_db_path()) as conn:
        conn.executescript(schema)
        try:
            conn.execute("ALTER TABLE matchday_draw ADD COLUMN cycle INTEGER NOT NULL DEFAULT 1")
        except sqlite3.OperationalError:
            pass  # colonna già presente
        conn.commit()


@contextmanager
def get_db():
    if ENV != "development":
        try:
            _download_db_from_gcs()
        except Exception:
            pass  # blob non ancora su GCS o errore di rete: usa file locale

    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        changed = conn.total_changes > 0
        conn.commit()
        if ENV != "development" and changed:
            _upload_db_to_gcs()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
