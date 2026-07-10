def test_admin_js_no_cache_header(client):
    r = client.get("/admin/js/matchday.js")
    assert r.status_code == 200
    assert r.headers.get("cache-control") == "no-cache"


def test_shared_no_cache_header(client):
    r = client.get("/shared/design-system.js")
    assert r.status_code == 200
    assert r.headers.get("cache-control") == "no-cache"


def test_static_dir_unaffected(client):
    r = client.get("/static/style.css")
    assert r.status_code == 200
    assert r.headers.get("cache-control") != "no-cache"
