"""Testes de integração das rotas operacionais (portaria + balança)."""

import pytest
from fastapi.testclient import TestClient

CAMERA = "http://192.168.11.241/ISAPI/Streaming/channels/101/picture"


def test_fluxo_completo_entrada_pesagem_saida(
    client: TestClient, admin_headers: dict[str, str], estrutura: int
) -> None:
    entrada = client.post(
        "/portaria/eventos",
        data={
            "operacao": "entrada",
            "camera": CAMERA,
            "unidade": "PLT001",
            "placa": "ABC1D23",
        },
        headers=admin_headers,
    )
    assert entrada.status_code == 201
    assert entrada.json()["operacao"] == "entrada"
    assert entrada.json()["status_visita"] == "aberta"

    tara = client.post(
        "/pesagens",
        data={
            "peso": "20.0",
            "tipo": "tara",
            "camera": CAMERA,
            "unidade": "PLT001",
            "placa": "ABC1D23",
        },
        headers=admin_headers,
    )
    assert tara.status_code == 201
    assert tara.json()["tipo"] == "tara"
    assert tara.json()["ordem"] == 1

    bruto = client.post(
        "/pesagens",
        data={
            "peso": "30.0",
            "tipo": "bruto",
            "camera": CAMERA,
            "unidade": "PLT001",
            "placa": "ABC1D23",
        },
        headers=admin_headers,
    )
    assert bruto.status_code == 201
    assert bruto.json()["tipo"] == "bruto"
    assert bruto.json()["ordem"] == 2

    saida = client.post(
        "/portaria/eventos",
        data={
            "operacao": "saida",
            "camera": CAMERA,
            "unidade": "PLT001",
            "placa": "ABC1D23",
        },
        headers=admin_headers,
    )
    assert saida.status_code == 201
    assert saida.json()["operacao"] == "saida"

    abertas = client.get("/portaria/abertas", headers=admin_headers)
    assert abertas.status_code == 200
    assert abertas.json() == []

    carregamentos = client.get("/pesagens/carregamentos", headers=admin_headers)
    assert carregamentos.status_code == 200
    body = carregamentos.json()
    assert len(body) == 1
    assert body[0]["peso_liquido"] == 10.0
    assert body[0]["tipo_carregamento"] == "carregamento"


def test_pesagem_sem_entrada_retorna_409(
    client: TestClient, admin_headers: dict[str, str], estrutura: int
) -> None:
    resp = client.post(
        "/pesagens",
        data={
            "peso": "99.99",
            "tipo": "tara",
            "camera": CAMERA,
            "unidade": "PLT001",
            "placa": "ABC1D23",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 409


def test_pesagem_peso_invalido_retorna_400(
    client: TestClient, admin_headers: dict[str, str], estrutura: int
) -> None:
    resp = client.post(
        "/pesagens",
        data={
            "peso": "0",
            "tipo": "tara",
            "camera": CAMERA,
            "unidade": "PLT001",
            "placa": "ABC1D23",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_pesagem_tipo_invalido_retorna_400(
    client: TestClient, admin_headers: dict[str, str], estrutura: int
) -> None:
    resp = client.post(
        "/pesagens",
        data={
            "peso": "10.0",
            "tipo": "cheio",
            "camera": CAMERA,
            "unidade": "PLT001",
            "placa": "ABC1D23",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_portaria_operacao_invalida_retorna_400(
    client: TestClient, admin_headers: dict[str, str], estrutura: int
) -> None:
    resp = client.post(
        "/portaria/eventos",
        data={
            "operacao": "passagem",
            "camera": CAMERA,
            "unidade": "PLT001",
            "placa": "ABC1D23",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_portaria_unidade_inexistente_retorna_404(
    client: TestClient, admin_headers: dict[str, str], estrutura: int
) -> None:
    resp = client.post(
        "/portaria/eventos",
        data={
            "operacao": "entrada",
            "camera": CAMERA,
            "unidade": "XXX",
            "placa": "ABC1D23",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 404


def test_portaria_sem_placa_e_sem_ocr_retorna_422(
    client: TestClient,
    admin_headers: dict[str, str],
    estrutura: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ReconhecedorVazio:
        def reconhecer_melhor(self, _imagem: object) -> None:
            return None

    monkeypatch.setattr(
        "app.services.plate_service.get_recognizer", lambda: _ReconhecedorVazio()
    )
    resp = client.post(
        "/portaria/eventos",
        data={"operacao": "entrada", "camera": CAMERA, "unidade": "PLT001"},
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_portaria_sem_camera_retorna_422(
    client: TestClient, admin_headers: dict[str, str], estrutura: int
) -> None:
    resp = client.post(
        "/portaria/eventos",
        data={"operacao": "entrada", "unidade": "PLT001", "placa": "ABC1D23"},
        headers=admin_headers,
    )
    assert resp.status_code == 422
