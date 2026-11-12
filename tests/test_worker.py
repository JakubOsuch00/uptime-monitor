import httpx
from sqlalchemy import select

from app import worker
from app.db import Check, SessionLocal, Target


def test_run_once_saves_checks_and_metrics(client):
    with SessionLocal() as s:
        s.add_all(
            [Target(name="up", url="https://up.test"), Target(name="down", url="https://down.test")]
        )
        s.commit()

    def handler(request):
        return httpx.Response(200 if request.url.host == "up.test" else 500)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        assert worker.run_once(http) == 2

    with SessionLocal() as s:
        checks = {c.status_code: c.ok for c in s.scalars(select(Check))}
    assert checks == {200: True, 500: False}
    assert worker.TARGET_UP.labels("up")._value.get() == 1
    assert worker.TARGET_UP.labels("down")._value.get() == 0
