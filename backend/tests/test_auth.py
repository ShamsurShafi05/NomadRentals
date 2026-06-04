from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def get_auth_token():
    """Helper to login and return token."""
    response = client.post("/auth/login", data={
        "username": "pytest@test.com",
        "password": "testpass123"
    })
    return response.json()["access_token"]

def test_get_me():
    token = get_auth_token()
    response = client.get("/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    assert response.json()["email"] == "pytest@test.com"

def test_invalid_token():
    response = client.get("/cities/", headers={
        "Authorization": "Bearer invalidtoken"
    })
    assert response.status_code == 401

def test_get_cities_authorized():
    token = get_auth_token()
    response = client.get("/cities/", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    assert isinstance(response.json(), list)