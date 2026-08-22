"""Testes da máquina de estados da visita (nível de serviço)."""

import uuid

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.services.erros import VisitaAbertaNaoEncontradaError
from app.services.pesagem_service import registrar_pesagem
from app.services.plate_service import PlacaResolvida
from app.services.ponto_service import obter_ponto
from app.services.visita_service import (
    obter_visita_aberta,
    registrar_entrada,
    registrar_saida,
)


def _resolvida(placa: str = "ABC1D23") -> PlacaResolvida:
    return PlacaResolvida(valor=placa, formato="mercosul", confianca=None, raw=None)


def test_entrada_abre_e_saida_fecha_visita(
    session_factory: sessionmaker[Session], estrutura: int
) -> None:
    planta_id = estrutura
    with session_factory() as db:
        entrada_ponto = obter_ponto(db, planta_id, "portaria_entrada")
        saida_ponto = obter_ponto(db, planta_id, "portaria_saida")
        assert entrada_ponto is not None and saida_ponto is not None

        entrada = registrar_entrada(
            db,
            resolvida=_resolvida(),
            planta_id=planta_id,
            ponto_id=entrada_ponto.id,
            foto_path=None,
        )
        assert entrada.status_visita == "aberta"
        assert isinstance(entrada.visita_id, uuid.UUID)

        saida = registrar_saida(
            db,
            resolvida=_resolvida(),
            planta_id=planta_id,
            ponto_id=saida_ponto.id,
            foto_path=None,
        )
        assert saida.visita_id == entrada.visita_id
        assert saida.status_visita == "fechada"

        db.refresh(entrada)
        assert entrada.status_visita == "fechada"


def test_pesagem_sem_visita_aberta_bloqueada(
    session_factory: sessionmaker[Session], estrutura: int
) -> None:
    planta_id = estrutura
    with session_factory() as db:
        balanca = obter_ponto(db, planta_id, "balanca")
        assert balanca is not None
        with pytest.raises(VisitaAbertaNaoEncontradaError):
            registrar_pesagem(
                db,
                resolvida=_resolvida(),
                peso=99.99,
                tipo="tara",
                planta_id=planta_id,
                ponto_id=balanca.id,
                foto_path=None,
            )


def test_carregamento_duas_pesagens(
    session_factory: sessionmaker[Session], estrutura: int
) -> None:
    planta_id = estrutura
    with session_factory() as db:
        entrada_ponto = obter_ponto(db, planta_id, "portaria_entrada")
        saida_ponto = obter_ponto(db, planta_id, "portaria_saida")
        balanca = obter_ponto(db, planta_id, "balanca")
        assert entrada_ponto and saida_ponto and balanca

        registrar_entrada(
            db,
            resolvida=_resolvida(),
            planta_id=planta_id,
            ponto_id=entrada_ponto.id,
            foto_path=None,
        )
        p1 = registrar_pesagem(
            db,
            resolvida=_resolvida(),
            peso=10.0,
            tipo="tara",
            planta_id=planta_id,
            ponto_id=balanca.id,
            foto_path=None,
        )
        p2 = registrar_pesagem(
            db,
            resolvida=_resolvida(),
            peso=25.0,
            tipo="bruto",
            planta_id=planta_id,
            ponto_id=balanca.id,
            foto_path=None,
        )
        assert p1.ordem == 1
        assert p2.ordem == 2

        registrar_saida(
            db,
            resolvida=_resolvida(),
            planta_id=planta_id,
            ponto_id=saida_ponto.id,
            foto_path=None,
        )

        db.refresh(p2)
        assert p2.peso_entrada == 10.0
        assert p2.peso_saida == 25.0
        assert p2.peso_liquido == 15.0
        assert p2.tipo_carregamento == "carregamento"


def test_pesagem_parcial_uma_pesagem(
    session_factory: sessionmaker[Session], estrutura: int
) -> None:
    planta_id = estrutura
    with session_factory() as db:
        entrada_ponto = obter_ponto(db, planta_id, "portaria_entrada")
        saida_ponto = obter_ponto(db, planta_id, "portaria_saida")
        balanca = obter_ponto(db, planta_id, "balanca")
        assert entrada_ponto and saida_ponto and balanca

        registrar_entrada(
            db,
            resolvida=_resolvida(),
            planta_id=planta_id,
            ponto_id=entrada_ponto.id,
            foto_path=None,
        )
        p1 = registrar_pesagem(
            db,
            resolvida=_resolvida(),
            peso=10.0,
            tipo="tara",
            planta_id=planta_id,
            ponto_id=balanca.id,
            foto_path=None,
        )
        registrar_saida(
            db,
            resolvida=_resolvida(),
            planta_id=planta_id,
            ponto_id=saida_ponto.id,
            foto_path=None,
        )

        db.refresh(p1)
        assert p1.tipo_carregamento == "pesagem_parcial"
        assert p1.peso_liquido is None


def test_entradas_reutilizam_visita_aberta(
    session_factory: sessionmaker[Session], estrutura: int
) -> None:
    planta_id = estrutura
    with session_factory() as db:
        entrada_ponto = obter_ponto(db, planta_id, "portaria_entrada")
        assert entrada_ponto is not None

        e1 = registrar_entrada(
            db,
            resolvida=_resolvida(),
            planta_id=planta_id,
            ponto_id=entrada_ponto.id,
            foto_path=None,
        )
        e2 = registrar_entrada(
            db,
            resolvida=_resolvida(),
            planta_id=planta_id,
            ponto_id=entrada_ponto.id,
            foto_path=None,
        )
        assert e2.visita_id == e1.visita_id
        assert e1.veiculo_id is not None
        assert obter_visita_aberta(db, planta_id, e1.veiculo_id) is not None
