from fastapi.testclient import TestClient

from app.main import app


def test_register_then_login():
    with TestClient(app) as client:
        email = "auth-test@example.com"
        password = "password123"

        register = client.post(
            "/api/auth/register",
            json={"email": email, "password": password},
        )
        assert register.status_code == 200, register.text

        login = client.post(
            "/api/auth/login",
            json={"email": email.upper(), "password": password},
        )
        assert login.status_code == 200, login.text
        assert login.json()["user"]["email"] == email

        bad_login = client.post(
            "/api/auth/login",
            json={"email": email, "password": "wrong-password"},
        )
        assert bad_login.status_code == 401
