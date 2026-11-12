import httpx

from app.checker import check_url
from app.db import Target


def make_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_check_ok():
    client = make_client(lambda request: httpx.Response(200))
    result = check_url(client, Target(id=1, name="a", url="https://a.test"))
    assert result.ok
    assert result.status_code == 200
    assert result.response_ms is not None


def test_check_server_error():
    client = make_client(lambda request: httpx.Response(503))
    result = check_url(client, Target(id=1, name="a", url="https://a.test"))
    assert not result.ok
    assert result.status_code == 503


def test_check_connection_error():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    result = check_url(make_client(handler), Target(id=1, name="a", url="https://a.test"))
    assert not result.ok
    assert result.status_code is None
    assert "ConnectError" in result.error
