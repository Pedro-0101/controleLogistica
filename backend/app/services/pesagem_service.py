"""Regras de negócio para registro de pesagens (vinculadas a uma visita aberta)."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models
from .erros import VisitaAbertaNaoEncontradaError
from .plate_service import PlacaResolvida, obter_ou_criar_veiculo
from .visita_service import obter_visita_aberta


def _proxima_ordem(db: Session, visita_id: uuid.UUID) -> int:
    total = db.scalars(
        select(func.count())
        .select_from(models.Pesagem)
        .where(models.Pesagem.visita_id == visita_id)
    ).one()
    return total + 1


def registrar_pesagem(
    db: Session,
    *,
    resolvida: PlacaResolvida,
    peso: float,
    tipo: str,
    planta_id: int,
    ponto_id: int,
    foto_path: str | None,
) -> models.Pesagem:
    """Registra uma pesagem (em toneladas) vinculada à visita aberta do veículo.

    `tipo` indica se a pesagem é de ``tara`` (caminhão vazio) ou ``bruto``
    (caminhão cheio) — o sistema não consegue inferir isso sozinho.

    Raises:
        VisitaAbertaNaoEncontradaError: Se não houver visita aberta para a placa.
    """
    veiculo = obter_ou_criar_veiculo(db, resolvida.valor)
    aberta = obter_visita_aberta(db, planta_id, veiculo.id)
    if aberta is None:
        raise VisitaAbertaNaoEncontradaError
    pesagem = models.Pesagem(
        visita_id=aberta.visita_id,
        planta_id=planta_id,
        ponto_id=ponto_id,
        veiculo_id=veiculo.id,
        placa=resolvida.valor,
        foto_frontal_path=foto_path,
        peso=peso,
        desvio=None,
        amostras=None,
        ordem=_proxima_ordem(db, aberta.visita_id),
        tipo=tipo,
    )
    db.add(pesagem)
    db.commit()
    db.refresh(pesagem)
    return pesagem
