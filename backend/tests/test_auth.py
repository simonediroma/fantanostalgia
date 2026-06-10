def test_me_unauthenticated(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_login_wrong_credentials(client):
    r = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_login_success(client):
    r = client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    assert r.status_code == 200
    assert "session" in r.cookies


def test_me_authenticated(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    r = client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["username"] == "admin"


def test_logout(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    r = client.post("/auth/logout")
    assert r.status_code == 200
    r2 = client.get("/auth/me")
    assert r2.status_code == 401
