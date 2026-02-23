import pytest
from fastapi.testclient import TestClient
from gateway.api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_incoming_message_route(client):
    response = client.post("/webhook/incoming", json={
        "from_number": "573001234567",
        "message": "inventory",
    })
    assert response.status_code == 200


def test_send_message_endpoint(client):
    response = client.post("/api/send", json={
        "to": "573001234567",
        "message": "Test message",
    })
    assert response.status_code == 200


def test_openai_compatible_help(client):
    response = client.post("/v1/chat/completions", json={
        "model": "fba-agent",
        "messages": [{"role": "user", "content": "help"}],
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["choices"]) == 1
    assert "Available commands" in data["choices"][0]["message"]["content"]


def test_openai_compatible_unknown_command(client):
    response = client.post("/v1/chat/completions", json={
        "model": "fba-agent",
        "messages": [{"role": "user", "content": "foobarbaz"}],
    })
    assert response.status_code == 200
    data = response.json()
    assert "not recognized" in data["choices"][0]["message"]["content"]
