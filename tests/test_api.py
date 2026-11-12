from datetime import UTC, datetime

from app.db import Check, SessionLocal


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_ready(client):
    assert client.get("/ready").status_code == 200


def test_add_list_delete_target(client):
    resp = client.post("/api/targets", json={"name": "example", "url": "https://example.com"})
    assert resp.status_code == 201
    target_id = resp.json()["id"]

    assert [t["name"] for t in client.get("/api/targets").json()] == ["example"]

    assert client.delete(f"/api/targets/{target_id}").status_code == 204
    assert client.get("/api/targets").json() == []


def test_duplicate_target_name(client):
    body = {"name": "example", "url": "https://example.com"}
    client.post("/api/targets", json=body)
    assert client.post("/api/targets", json=body).status_code == 409


def test_invalid_url(client):
    resp = client.post("/api/targets", json={"name": "bad", "url": "not a url"})
    assert resp.status_code == 422


def test_delete_missing_target(client):
    assert client.delete("/api/targets/999").status_code == 404


def test_status_uptime(client):
    target_id = client.post(
        "/api/targets", json={"name": "example", "url": "https://example.com"}
    ).json()["id"]
    with SessionLocal() as s:
        now = datetime.now(UTC)
        for ok in [True, True, True, False]:
            s.add(Check(target_id=target_id, checked_at=now, ok=ok, status_code=200 if ok else 500))
        s.commit()

    status = client.get("/api/status").json()[0]
    assert status["uptime_24h"] == 75.0


def test_status_page_escapes_html(client):
    client.post("/api/targets", json={"name": "<script>x</script>", "url": "https://example.com"})
    page = client.get("/").text
    assert "<script>x</script>" not in page
    assert "&lt;script&gt;" in page


def test_metrics(client):
    client.get("/health")
    body = client.get("/metrics").text
    assert 'http_requests_total{method="GET",path="/health",status="200"}' in body


def test_init_db_retries(monkeypatch):
    from sqlalchemy.exc import OperationalError

    from app import db

    calls = []

    def flaky(_engine):
        calls.append(1)
        if len(calls) < 3:
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(db.Base.metadata, "create_all", flaky)
    db.init_db(attempts=5, delay=0)
    assert len(calls) == 3
