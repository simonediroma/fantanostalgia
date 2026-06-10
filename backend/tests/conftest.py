import os
import tempfile

import pytest
from fastapi.testclient import TestClient

os.environ["ENV"] = "development"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "testpass"
os.environ["SECRET_KEY"] = "test-secret"

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DB_LOCAL_PATH"] = _tmp.name


@pytest.fixture(scope="session")
def client():
    from backend.api.main import app

    with TestClient(app) as c:
        yield c
