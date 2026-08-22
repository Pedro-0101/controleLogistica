"""Resolução de unidades (plantas) e pontos de coleta."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models


def obter_planta_por_codigo(db: Session, codigo: str) -> models.Planta | None:
    """Retorna a unidade (planta) pelo código (ou None)."""
    return db.execute(
        select(models.Planta).where(models.Planta.codigo == codigo)
    ).scalar_one_or_none()


def obter_ponto(db: Session, planta_id: int, tipo: str) -> models.Ponto | None:
    """Retorna o ponto de coleta do tipo informado na planta (ou None)."""
    return (
        db.execute(
            select(models.Ponto)
            .where(models.Ponto.planta_id == planta_id, models.Ponto.tipo == tipo)
            .order_by(models.Ponto.id)
        )
        .scalars()
        .first()
    )


def obter_ponto_por_codigo(db: Session, codigo: str) -> models.Ponto | None:
    """Retorna o ponto de coleta pelo código (ou None)."""
    return db.execute(
        select(models.Ponto).where(models.Ponto.codigo == codigo)
    ).scalar_one_or_none()
