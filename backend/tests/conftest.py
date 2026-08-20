"""Fixtures e utilitários compartilhados pelos testes."""

from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.auth.security import hash_senha
from app.config import settings
from app.db import Base, get_db
from app.main import app

ADMIN_EMAIL = "admin@test.com"
ADMIN_SENHA = "secret"


def imagem_jpeg() -> bytes:
    """Gera uma imagem JPEG mínima válida para os uploads de teste."""
    arr = np.zeros((16, 16, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", arr)
    assert ok
    return buf.tobytes()


@pytest.fixture()
def foto() -> bytes:
    return imagem_jpeg()


@pytest.fixture()
def db_engine() -> Iterator[Engine]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def session_factory(db_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=db_engine, autoflush=False, autocommit=False)


@pytest.fixture()
def client(db_engine: Engine) -> Iterator[TestClient]:
    factory = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    def override_get_db() -> Iterator[Session]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _imagens_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "imagens_dir", tmp_path)


def _criar_usuario(
    session_factory: sessionmaker[Session],
    email: str,
    senha: str,
    role: str,
) -> int:
    with session_factory() as db:
        usuario = models.Usuario(
            nome=role,
            email=email,
            senha_hash=hash_senha(senha),
            role=role,
            ativo=True,
        )
        db.add(usuario)
        db.commit()
        return usuario.id


@pytest.fixture()
def admin_user(session_factory: sessionmaker[Session]) -> int:
    return _criar_usuario(session_factory, ADMIN_EMAIL, ADMIN_SENHA, "admin")


@pytest.fixture()
def portaria_user(session_factory: sessionmaker[Session]) -> int:
    return _criar_usuario(session_factory, "portaria@test.com", "secret", "portaria")


@pytest.fixture()
def admin_headers(client: TestClient, admin_user: int) -> dict[str, str]:
    resp = client.post(
        "/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_SENHA}
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
def portaria_headers(client: TestClient, portaria_user: int) -> dict[str, str]:
    resp = client.post(
        "/auth/login", data={"username": "portaria@test.com", "password": "secret"}
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
def estrutura(session_factory: sessionmaker[Session]) -> int:
    """Cria uma planta e os três pontos padrão; retorna o id da planta."""
    with session_factory() as db:
        planta = models.Planta(codigo="PLT001", nome="Planta Teste")
        db.add(planta)
        db.flush()
        pontos = [
            ("PORTARIA_ENTRADA", "portaria_entrada"),
            ("PORTARIA_SAIDA", "portaria_saida"),
            ("BALANCA", "balanca"),
        ]
        for codigo, tipo in pontos:
            db.add(models.Ponto(planta_id=planta.id, codigo=codigo, tipo=tipo))
        db.commit()
        return planta.id
