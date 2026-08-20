"""Testes das rotas de autenticação."""

from fastapi.testclient import TestClient

from .conftest import ADMIN_EMAIL, ADMIN_SENHA


def test_login_e_me(client: TestClient, admin_headers: dict[str, str]) -> None:
    resp = client.get("/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == ADMIN_EMAIL
    assert body["role"] == "admin"
    assert "senha_hash" not in body


def test_login_senha_invalida(client: TestClient, admin_user: int) -> None:
    resp = client.post(
        "/auth/login", data={"username": ADMIN_EMAIL, "password": "errada"}
    )
    assert resp.status_code == 401


def test_refresh_emite_novo_token(client: TestClient, admin_user: int) -> None:
    resp = client.post(
        "/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_SENHA}
    )
    refresh_token = resp.json()["refresh_token"]
    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_sem_token_retorna_401(client: TestClient) -> None:
    resp = client.get("/auth/me")
    assert resp.status_code == 401
