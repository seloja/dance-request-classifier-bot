from fastapi.testclient import TestClient

from app.api import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_classify_payment():
    response = client.post("/classify", json={"text": "Сколько стоит абонемент?"})
    assert response.status_code == 200
    assert response.json()["label"] == "payment"


def test_classify_absence():
    response = client.post("/classify", json={"text": "Мы сегодня не придём"})
    assert response.status_code == 200
    assert response.json()["label"] == "absence"


def test_classify_empty_text():
    response = client.post("/classify", json={"text": "   "})
    assert response.status_code == 200
    assert response.json()["label"] == "admin_other"
    assert response.json()["confidence"] == 0.0
