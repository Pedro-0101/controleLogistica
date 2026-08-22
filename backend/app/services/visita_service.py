"""Máquina de estados da visita: entrada -> pesagens -> saída.

A placa é a chave natural. Cada visita é agrupada por um ``visita_id`` (UUID)
compartilhado entre a movimentação da portaria (entrada/saída) e as pesagens.
Ao fechar a visita (saída), calcula-se o peso líquido e o tipo de carregamento.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from .plate_service import PlacaResolvida, obter_ou_criar_veiculo


def obter_visita_aberta(
    db: Session, planta_id: int, veiculo_id: int
) -> models.PortariaMovimentacao | None:
    """Retorna a entrada aberta mais recente do veículo na planta (ou None)."""
    return (
        db.execute(
            select(models.PortariaMovimentacao)
            .where(
                models.PortariaMovimentacao.planta_id == planta_id,
                models.PortariaMovimentacao.veiculo_id == veiculo_id,
                models.PortariaMovimentacao.operacao == "entrada",
                models.PortariaMovimentacao.status_visita == "aberta",
            )
            .order_by(models.PortariaMovimentacao.id.desc())
        )
        .scalars()
        .first()
    )


def _finalizar_carregamento(db: Session, visita_id: uuid.UUID) -> None:
    """Preenche pesos (tara/bruto) e tipo na última pesagem da visita.

    O peso líquido é ``bruto - tara``. O sistema não sabe, sozinho, se uma
    pesagem é de caminhão vazio ou cheio — essa informação vem do front no campo
    ``tipo`` de cada pesagem.
    """
    pesagens = list(
        db.scalars(
            select(models.Pesagem)
            .where(models.Pesagem.visita_id == visita_id)
            .order_by(models.Pesagem.ordem)
        )
    )
    if not pesagens:
        return
    ultima = pesagens[-1]
    taras = [p for p in pesagens if p.tipo == "tara"]
    brutos = [p for p in pesagens if p.tipo == "bruto"]
    tara = taras[-1].peso if taras else None
    bruto = brutos[-1].peso if brutos else None
    ultima.peso_entrada = tara
    ultima.peso_saida = bruto
    if tara is not None and bruto is not None:
        ultima.peso_liquido = round(bruto - tara, 1)
        ultima.tipo_carregamento = "carregamento" if bruto > tara else "descarregamento"
    elif tara is not None or bruto is not None:
        ultima.peso_liquido = None
        ultima.tipo_carregamento = "pesagem_parcial"
    else:
        ultima.peso_liquido = None
        ultima.tipo_carregamento = "sem_pesagem"


def registrar_entrada(
    db: Session,
    *,
    resolvida: PlacaResolvida,
    planta_id: int,
    ponto_id: int,
    foto_path: str | None,
) -> models.PortariaMovimentacao:
    """Registra a passagem de entrada e abre (ou reutiliza) uma visita."""
    veiculo = obter_ou_criar_veiculo(db, resolvida.valor)
    aberta = obter_visita_aberta(db, planta_id, veiculo.id)
    visita_id = aberta.visita_id if aberta is not None else uuid.uuid4()
    mov = models.PortariaMovimentacao(
        visita_id=visita_id,
        planta_id=planta_id,
        ponto_id=ponto_id,
        veiculo_id=veiculo.id,
        placa=resolvida.valor,
        placa_raw=resolvida.raw,
        formato=resolvida.formato,
        confianca=resolvida.confianca,
        operacao="entrada",
        foto_frontal_path=foto_path,
        status_visita="aberta",
    )
    db.add(mov)
    db.commit()
    db.refresh(mov)
    return mov


def registrar_saida(
    db: Session,
    *,
    resolvida: PlacaResolvida,
    planta_id: int,
    ponto_id: int,
    foto_path: str | None,
) -> models.PortariaMovimentacao:
    """Registra a passagem de saída e fecha a visita, finalizando o carregamento."""
    veiculo = obter_ou_criar_veiculo(db, resolvida.valor)
    aberta = obter_visita_aberta(db, planta_id, veiculo.id)
    visita_id = aberta.visita_id if aberta is not None else uuid.uuid4()
    if aberta is not None:
        aberta.status_visita = "fechada"
    _finalizar_carregamento(db, visita_id)
    mov = models.PortariaMovimentacao(
        visita_id=visita_id,
        planta_id=planta_id,
        ponto_id=ponto_id,
        veiculo_id=veiculo.id,
        placa=resolvida.valor,
        placa_raw=resolvida.raw,
        formato=resolvida.formato,
        confianca=resolvida.confianca,
        operacao="saida",
        foto_frontal_path=foto_path,
        status_visita="fechada",
    )
    db.add(mov)
    db.commit()
    db.refresh(mov)
    return mov
