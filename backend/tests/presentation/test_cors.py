from fastapi.testclient import TestClient

from app.main import app


def test_cors_allows_local_hostname_origin():
    client = TestClient(app)

    resp = client.options(
        "/auth/nickname/login",
        headers={
            "Origin": "http://gimjihyeon-ui-noteubug.local:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://gimjihyeon-ui-noteubug.local:5173"


def test_cors_allows_private_network_origin():
    client = TestClient(app)

    resp = client.options(
        "/auth/nickname/login",
        headers={
            "Origin": "http://172.28.111.153:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://172.28.111.153:5173"
