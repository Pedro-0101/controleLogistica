"""Regras de negócio para placas (resolução via corpo ou ANPR)."""

from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..anpr.plate import normalizar_placa
from ..anpr.recognizer import get_recognizer
from .erros import PlacaNaoReconhecidaError


@dataclass(frozen=True)
class PlacaResolvida:
    valor: str
    formato: str | None
    confianca: float | None
    raw: str | None


def obter_ou_criar_veiculo(db: Session, placa: str) -> models.Veiculo:
    """Retorna o veículo da placa, criando-o se ainda não existir."""
    veiculo = db.execute(
        select(models.Veiculo).where(models.Veiculo.placa == placa)
    ).scalar_one_or_none()
    if veiculo is None:
        veiculo = models.Veiculo(placa=placa)
        db.add(veiculo)
        db.flush()
    return veiculo


def resolver_placa(*, placa: str | None, imagem: np.ndarray | None) -> PlacaResolvida:
    """Resolve a placa a partir do campo do corpo ou do OCR da imagem.

    Args:
        placa: Placa informada explicitamente no corpo (opcional).
        imagem: Imagem BGR (numpy) usada pelo OCR quando `placa` não é informada.

    Returns:
        PlacaResolvida com o valor normalizado e metadados do ANPR.

    Raises:
        PlacaNaoReconhecidaError: Se a placa não puder ser determinada.
    """
    if placa:
        normalizada = normalizar_placa(placa)
        if normalizada is None:
            raise PlacaNaoReconhecidaError
        return PlacaResolvida(
            valor=normalizada.valor,
            formato=normalizada.formato,
            confianca=None,
            raw=placa,
        )
    if imagem is None:
        raise PlacaNaoReconhecidaError
    melhor = get_recognizer().reconhecer_melhor(imagem)
    if melhor is None:
        raise PlacaNaoReconhecidaError
    return PlacaResolvida(
        valor=melhor.placa.valor,
        formato=melhor.placa.formato,
        confianca=melhor.confianca,
        raw=melhor.raw,
    )
