"""Regras de negócio para registro de eventos de placa."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..anpr.plate import Placa
from . import movimentacao_service


def obter_ou_criar_veiculo(db: Session, placa: str) -> models.Veiculo:
    veiculo = db.execute(
        select(models.Veiculo).where(models.Veiculo.placa == placa)
    ).scalar_one_or_none()
    if veiculo is None:
        veiculo = models.Veiculo(placa=placa)
        db.add(veiculo)
        db.flush()
    return veiculo


def registrar_evento(
    db: Session,
    *,
    placa: Placa,
    confianca: float | None,
    raw: str | None,
    planta_id: int,
    ponto_id: int,
    imagem_path: str | None = None,
    capturado_em: datetime | None = None,
) -> models.EventoPlaca:
    veiculo = obter_ou_criar_veiculo(db, placa.valor)
    evento = models.EventoPlaca(
        placa=placa.valor,
        placa_raw=raw,
        formato=placa.formato,
        confianca=confianca,
        planta_id=planta_id,
        ponto_id=ponto_id,
        veiculo_id=veiculo.id,
        imagem_path=imagem_path,
        capturado_em=capturado_em or datetime.now(timezone.utc),
    )
    db.add(evento)
    db.commit()
    db.refresh(evento)

    # avança a máquina de estados (entrada/saída) automaticamente
    movimentacao_service.processar_evento_placa(db, evento)

    return evento
