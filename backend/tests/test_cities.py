import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "NomadRentals API is running"}

def test_get_cities_unauthorized():
    response = client.get("/cities/")
    assert response.status_code == 401

def test_create_and_get_user():
    # Clean up first in case user exists from previous run
    token = client.post("/auth/login", data={
        "username": "pytest@test.com",
        "password": "testpass123"
    }).json().get("access_token")
    
    if token:
        # Get user id and delete
        me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        user_id = me.json()["id"]
        client.delete(f"/users/{user_id}", headers={"Authorization": f"Bearer {token}"})

    response = client.post("/users/", json={
        "email": "pytest@test.com",
        "name": "Pytest User",
        "password": "testpass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "pytest@test.com"
    assert "id" in data
    assert "password" not in data

def test_login():
    response = client.post("/auth/login", data={
        "username": "pytest@test.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password():
    response = client.post("/auth/login", data={
        "username": "pytest@test.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_get_nonexistent_city():
    token = client.post("/auth/login", data={
        "username": "pytest@test.com",
        "password": "testpass123"
    }).json()["access_token"]
    
    response = client.get("/cities/99999", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 404

def test_recommend_no_preferences():
    token = client.post("/auth/login", data={
        "username": "pytest@test.com",
        "password": "testpass123"
    }).json()["access_token"]

    response = client.get("/cities/recommend?user_id=99999", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 404