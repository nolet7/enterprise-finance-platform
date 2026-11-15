from fastapi.testclient import TestClient
from app.main import app


def test_response_security_headers_and_correlation():
    response = TestClient(app).get("/healthz")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert len(response.headers["X-Request-ID"]) == 36


def test_request_id_not_reflected_from_untrusted_headers():
    response = TestClient(app).get("/healthz", headers={
        "X-Request-ID": "attacker-controlled",
        "Authorization": "Bearer do-not-log",
    })
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "attacker-controlled"
