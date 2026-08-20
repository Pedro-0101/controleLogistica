"""Testes de integração das rotas operacionais (portaria + balança)."""

import pytest
from fastapi.testclient import TestClient


def test_fluxo_completo_entrada_pesagem_saida(
    client: TestClient, admin_headers: dict[str, str], estrutura: int, foto: bytes
) -> None:
    entrada = client.post(
        "/portaria/eventos",
        data={"operacao": "entrada", "unidade": "PLT001", "placa": "ABC1D23"},
        files={"foto": ("foto.jpg", foto, "image/jpeg")},
        headers=admin_headers,
    )
    assert entrada.status_code == 201
    assert entrada.json()["operacao"] == "entrada"
    assert entrada.json()["status_visita"] == "aberta"

    pesagem = client.post(
        "/pesagens",
        data={"peso": "99.99", "unidade": "PLT001", "placa": "ABC1D23"},
        files={"foto": ("foto.jpg", foto, "image/jpeg")},
        headers=admin_headers,
    )
    assert pesagem.status_code == 201
    assert pesagem.json()["peso"] == 99.99
    assert pesagem.json()["ordem"] == 1

    saida = client.post(
        "/portaria/eventos",
        data={"operacao": "saida", "unidade": "PLT001", "placa": "ABC1D23"},
        files={"foto": ("foto.jpg", foto, "image/jpeg")},
        headers=admin_headers,
    )
    assert saida.status_code == 201
    assert saida.json()["operacao"] == "saida"

    abertas = client.get("/portaria/abertas", headers=admin_headers)
    assert abertas.status_code == 200
    assert abertas.json() == []


def test_pesagem_sem_entrada_retorna_409(
    client: TestClient, admin_headers: dict[str, str], estrutura: int, foto: bytes
) -> None:
    resp = client.post(
        "/pesagens",
        data={"peso": "99.99", "unidade": "PLT001", "placa": "ABC1D23"},
        files={"foto": ("foto.jpg", foto, "image/jpeg")},
        headers=admin_headers,
    )
    assert resp.status_code == 409


def test_pesagem_peso_invalido_retorna_400(
    client: TestClient, admin_headers: dict[str, str], estrutura: int, foto: bytes
) -> None:
    resp = client.post(
        "/pesagens",
        data={"peso": "0", "unidade": "PLT001", "placa": "ABC1D23"},
        files={"foto": ("foto.jpg", foto, "image/jpeg")},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_portaria_sem_placa_e_sem_ocr_retorna_422(
    client: TestClient,
    admin_headers: dict[str, str],
    estrutura: int,
    foto: bytes,
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
        data={"operacao": "entrada", "unidade": "PLT001"},
        files={"foto": ("foto.jpg", foto, "image/jpeg")},
        headers=admin_headers,
    )
    assert resp.status_code == 422
