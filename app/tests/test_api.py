from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}

def test_shorten_requires_api_key():
    response = client.post(
        "/shorten",
        json={"url": "https://example.com"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid or missing API key"

def test_shorten_with_valid_api_key():
    response = client.post(
        "/shorten",
        json={"url": "https://example.com"},
        headers={"X-API-Key": "dev-key-123"},
    )

    assert response.status_code == 200

    body = response.json()

    assert "code" in body
    assert "short_url" in body
    assert body["short_url"].startswith("/")

def test_shorten_with_invalid_api_key():
    response = client.post(
        "/shorten",
        json={"url": "https://example.com"},
        headers={"X-API-Key": "wrong-key"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid or missing API key"

def test_redirect_nonexistent_code():
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json()["detail"] == "short code not found"

def test_redirect_short_url():
    shorten_response = client.post(
        "/shorten",
        json={"url": "https://example.com"},
        headers={"X-API-Key": "dev-key-123"},
    )

    assert shorten_response.status_code == 200

    code = shorten_response.json()["code"]

    response = client.get(
        f"/{code}",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com"

def test_stats_after_redirect():
    shorten_response = client.post(
        "/shorten",
        json={"url": "https://example.com"},
        headers={"X-API-Key": "dev-key-123"},
    )

    assert shorten_response.status_code == 200

    code = shorten_response.json()["code"]

    redirect_response = client.get(
        f"/{code}",
        follow_redirects=False,
    )

    assert redirect_response.status_code == 302

    stats_response = client.get(
        f"/stats/{code}",
        headers={"X-API-Key": "dev-key-123"},
    )

    assert stats_response.status_code == 200
    assert stats_response.json()["code"] == code
    assert stats_response.json()["clicks"] == 1