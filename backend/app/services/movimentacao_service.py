"""Máquina de estados do pareamento: entrada -> pesagens -> saída.

A placa é a chave natural. Cada "visita" de um veículo vira uma Movimentacao
(aberta na portaria de entrada, fechada na de saída). As pesagens da balança
são anexadas a essa movimentação e, ao fechar, calcula-se o peso líquido e o
tipo (carregamento/descarregamento). Veículo que entra e sai sem pesar resulta
em tipo "sem_pesagem".
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models


def _pesagens_do_mov(db: Session, mov: models.Movimentacao) -> list[models.Pesagem]:
    return list(
        db.scalars(
            select(models.Pesagem)
            .where(models.Pesagem.movimentacao_id == mov.id)
            .order_by(models.Pesagem.id)
        )
    )


def obter_aberta(
    db: Session, planta_id: int, veiculo_id: int
) -> models.Movimentacao | None:
    return db.execute(
        select(models.Movimentacao).where(
            models.Movimentacao.planta_id == planta_id,
            models.Movimentacao.veiculo_id == veiculo_id,
            models.Movimentacao.status == "aberta",
        )
    ).scalar_one_or_none()


def atualizar_pesos(db: Session, mov: models.Movimentacao) -> None:
    """Preenche peso_entrada/saida/liquido e tipo a partir das pesagens."""
    pesagens = _pesagens_do_mov(db, mov)
    mov.peso_entrada = None
    mov.peso_saida = None
    mov.peso_liquido = None
    if len(pesagens) >= 1:
        mov.peso_entrada = pesagens[0].peso
    if len(pesagens) >= 2:
        mov.peso_saida = pesagens[1].peso
        mov.peso_liquido = round(abs(pesagens[1].peso - pesagens[0].peso), 1)
        mov.tipo = (
            "carregamento" if pesagens[1].peso > pesagens[0].peso else "descarregamento"
        )


def processar_evento_placa(
    db: Session, evento: models.EventoPlaca
) -> models.Movimentacao | None:
    """Avança o estado a partir de um evento de placa (entrada/saída)."""
    ponto = evento.ponto
    if ponto is None or ponto.tipo not in ("portaria_entrada", "portaria_saida"):
        return None
    if evento.veiculo is None:
        return None

    if ponto.tipo == "portaria_entrada":
        mov = obter_aberta(db, evento.planta_id, evento.veiculo.id)
        if mov is None:
            mov = models.Movimentacao(
                planta_id=evento.planta_id,
                veiculo_id=evento.veiculo.id,
                status="aberta",
                entrada_evento_id=evento.id,
            )
            db.add(mov)
            db.commit()
            db.refresh(mov)
        return mov

    # portaria_saida
    mov = obter_aberta(db, evento.planta_id, evento.veiculo.id)
    if mov is None:
        mov = models.Movimentacao(
            planta_id=evento.planta_id,
            veiculo_id=evento.veiculo.id,
            status="fechada",
            saida_evento_id=evento.id,
            tipo="sem_pesagem",
            fechado_em=datetime.now(timezone.utc),
        )
        db.add(mov)
        db.commit()
        db.refresh(mov)
        return mov

    atualizar_pesos(db, mov)
    if len(_pesagens_do_mov(db, mov)) == 0:
        mov.tipo = "sem_pesagem"
    elif mov.peso_saida is None:
        mov.tipo = "pesagem_parcial"
    mov.status = "fechada"
    mov.saida_evento_id = evento.id
    mov.fechado_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(mov)
    return mov


def listar_abertas(
    db: Session, planta_id: int | None = None
) -> list[models.Movimentacao]:
    stmt = select(models.Movimentacao).where(models.Movimentacao.status == "aberta")
    if planta_id is not None:
        stmt = stmt.where(models.Movimentacao.planta_id == planta_id)
    return list(db.scalars(stmt.order_by(models.Movimentacao.criado_em)))
