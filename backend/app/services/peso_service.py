"""Regras de negócio para registro de pesagens (ligadas a uma movimentação)."""

from sqlalchemy.orm import Session

from .. import models
from . import movimentacao_service
from .plate_service import obter_ou_criar_veiculo


def registrar_pesagem(
    db: Session,
    *,
    placa: str,
    peso: float,
    desvio: float | None,
    amostras: int | None,
    planta_id: int,
    ponto_id: int,
) -> models.Pesagem:
    veiculo = obter_ou_criar_veiculo(db, placa)

    mov = movimentacao_service.obter_aberta(db, planta_id, veiculo.id)
    if mov is None:
        mov = models.Movimentacao(
            planta_id=planta_id, veiculo_id=veiculo.id, status="aberta"
        )
        db.add(mov)
        db.flush()

    pesagem = models.Pesagem(
        peso=peso,
        desvio=desvio,
        amostras=amostras,
        planta_id=planta_id,
        ponto_id=ponto_id,
        veiculo_id=veiculo.id,
        movimentacao_id=mov.id,
    )
    db.add(pesagem)
    db.flush()
    movimentacao_service.atualizar_pesos(db, mov)
    db.commit()
    db.refresh(pesagem)
    return pesagem
