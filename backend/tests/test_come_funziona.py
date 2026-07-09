def test_come_funziona_loads(client):
    r = client.get("/come-funziona")
    assert r.status_code == 200
    assert "Come funziona" in r.text
    assert 'id="regole"' in r.text
    assert 'id="faq"' in r.text


def test_home_links_to_come_funziona(client):
    r = client.get("/")
    assert r.status_code == 200
    assert 'href="/come-funziona"' in r.text
