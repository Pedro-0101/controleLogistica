"""Testes dos CRUDs de entidades."""

from fastapi.testclient import TestClient


def test_criar_e_listar_planta(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/plantas",
        json={"codigo": "PLT002", "nome": "Unidade 2"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["codigo"] == "PLT002"

    resp = client.get("/plantas", headers=admin_headers)
    assert resp.status_code == 200
    assert any(p["codigo"] == "PLT002" for p in resp.json())


def test_codigo_duplicado_retorna_409(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    client.post(
        "/plantas", json={"codigo": "PLT003", "nome": "X"}, headers=admin_headers
    )
    resp = client.post(
        "/plantas", json={"codigo": "PLT003", "nome": "Y"}, headers=admin_headers
    )
    assert resp.status_code == 409


def test_excluir_planta_com_ponto_retorna_409(
    client: TestClient, admin_headers: dict[str, str], estrutura: int
) -> None:
    resp = client.delete(f"/plantas/{estrutura}", headers=admin_headers)
    assert resp.status_code == 409


def test_criar_planta_sem_permissao(
    client: TestClient, portaria_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/plantas", json={"codigo": "PLT004", "nome": "X"}, headers=portaria_headers
    )
    assert resp.status_code == 403


def test_criar_veiculo_placa_invalida(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    resp = client.post("/veiculos", json={"placa": "inválida!"}, headers=admin_headers)
    assert resp.status_code == 422


def test_criar_usuario_nao_retorna_senha(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/usuarios",
        json={
            "nome": "Balanca 1",
            "email": "balanca@test.com",
            "senha": "segredo",
            "role": "balanca",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert "senha_hash" not in resp.json()
    assert resp.json()["role"] == "balanca"
