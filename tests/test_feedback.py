HEADERS = {"X-API-Key": "test-key"}

VALID = {
    "type": "complaint",
    "message": "Урок 5 не відкривається",
    "rating": 2,
    "user_id": "u_42",
    "platform": "android",
    "app_version": "1.3.0",
}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rejects_missing_api_key(client, notifier):
    response = client.post("/api/v1/feedback", json=VALID)
    assert response.status_code == 401
    assert notifier.sent == []


def test_rejects_wrong_api_key(client):
    response = client.post("/api/v1/feedback", json=VALID, headers={"X-API-Key": "nope"})
    assert response.status_code == 401


def test_accepts_valid_feedback(client, notifier):
    response = client.post("/api/v1/feedback", json=VALID, headers=HEADERS)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "accepted"
    assert len(notifier.sent) == 1
    assert "Скарга" in notifier.sent[0]
    assert "#complaint" in notifier.sent[0]
    assert body["id"] in notifier.sent[0]


def test_rejects_invalid_type(client):
    response = client.post(
        "/api/v1/feedback", json={**VALID, "type": "spam"}, headers=HEADERS
    )
    assert response.status_code == 422


def test_rejects_unknown_field(client):
    response = client.post(
        "/api/v1/feedback", json={**VALID, "hack": 1}, headers=HEADERS
    )
    assert response.status_code == 422


def test_escapes_html(client, notifier):
    payload = {**VALID, "message": "<script>alert(1)</script>"}
    response = client.post("/api/v1/feedback", json=payload, headers=HEADERS)
    assert response.status_code == 201
    assert "&lt;script&gt;" in notifier.sent[0]
    assert "<script>" not in notifier.sent[0]


def test_demo_page(client):
    response = client.get("/demo/")
    assert response.status_code == 200
    assert "Feedback Bot" in response.text
    assert "/api/v1/feedback" in response.text