"""Rotas operacionais da portaria (entrada/saída)."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..auth.deps import require_roles
from ..db import get_db
from ..schemas import PortariaEventoOut
from ..services.erros import PlacaNaoReconhecidaError
from ..services.imagem import decodificar, salvar
from ..services.plate_service import resolver_placa
from ..services.ponto_service import obter_planta_por_codigo, obter_ponto
from ..services.visita_service import registrar_entrada, registrar_saida

router = APIRouter(prefix="/portaria", tags=["portaria"])


def _resolver_unidade(db: Session, codigo: str) -> models.Planta:
    planta = obter_planta_por_codigo(db, codigo)
    if planta is None:
        raise HTTPException(
            status_code=404, detail=f"Unidade '{codigo}' não encontrada"
        )
    return planta


def _ponto_para_operacao(db: Session, planta_id: int, operacao: str) -> models.Ponto:
    tipo = "portaria_entrada" if operacao == "entrada" else "portaria_saida"
    ponto = obter_ponto(db, planta_id, tipo)
    if ponto is None:
        raise HTTPException(
            status_code=404,
            detail=f"Ponto do tipo '{tipo}' não encontrado na unidade",
        )
    return ponto


def _processar(
    db: Session,
    *,
    conteudo: bytes,
    operacao: str,
    unidade: str,
    placa: str | None,
) -> models.PortariaMovimentacao:
    try:
        imagem = decodificar(conteudo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Imagem inválida") from exc
    try:
        resolvida = resolver_placa(placa=placa, imagem=imagem)
    except PlacaNaoReconhecidaError as exc:
        raise HTTPException(status_code=422, detail="Placa não reconhecida") from exc
    planta = _resolver_unidade(db, unidade)
    ponto = _ponto_para_operacao(db, planta.id, operacao)
    foto_path = salvar(conteudo)
    if operacao == "entrada":
        return registrar_entrada(
            db,
            resolvida=resolvida,
            planta_id=planta.id,
            ponto_id=ponto.id,
            foto_path=foto_path,
        )
    return registrar_saida(
        db,
        resolvida=resolvida,
        planta_id=planta.id,
        ponto_id=ponto.id,
        foto_path=foto_path,
    )


@router.post(
    "/eventos",
    response_model=PortariaEventoOut,
    status_code=201,
    summary="Registra uma passagem (entrada/saída)",
    responses={
        400: {"description": "Imagem inválida ou operação inválida"},
        404: {"description": "Unidade ou ponto de coleta não encontrado"},
        422: {"description": "Placa inválida ou não reconhecida (e não enviada)"},
    },
)
async def registrar_evento(
    foto: UploadFile = File(..., description="Foto frontal do caminhão"),
    operacao: str = Form(
        ..., description="Operação: 'entrada' ou 'saida'", examples=["entrada"]
    ),
    unidade: str = Form(
        ..., description="Código da unidade (planta)", examples=["PLT001"]
    ),
    placa: str | None = Form(
        None,
        description="Placa explícita (opcional; ignora o OCR)",
        examples=["ABC1D23"],
    ),
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("portaria", "admin")),
) -> models.PortariaMovimentacao:
    """Registra a passagem de um veículo na portaria.

    A placa é reconhecida via ANPR na foto, mas pode ser enviada explicitamente
    no campo `placa`, caso em que o OCR é ignorado. A operação abre (`entrada`)
    ou fecha (`saida`) a visita do veículo na unidade informada.
    """
    if operacao not in ("entrada", "saida"):
        raise HTTPException(status_code=400, detail="Operação inválida")
    conteudo = await foto.read()
    return _processar(
        db, conteudo=conteudo, operacao=operacao, unidade=unidade, placa=placa
    )


@router.get(
    "/eventos",
    response_model=list[PortariaEventoOut],
    summary="Lista as passagens da portaria",
)
def listar_eventos(
    placa: str | None = None,
    operacao: str | None = None,
    visita_id: uuid.UUID | None = None,
    de: datetime | None = None,
    ate: datetime | None = None,
    limite: int = 100,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("portaria", "admin")),
) -> list[models.PortariaMovimentacao]:
    """Lista as passagens com filtros opcionais (`placa`, `operacao`, `visita_id`, `de`/`ate`)."""
    stmt = select(models.PortariaMovimentacao).order_by(
        models.PortariaMovimentacao.capturado_em.desc()
    )
    if placa:
        stmt = stmt.where(models.PortariaMovimentacao.placa == placa.upper())
    if operacao:
        stmt = stmt.where(models.PortariaMovimentacao.operacao == operacao)
    if visita_id is not None:
        stmt = stmt.where(models.PortariaMovimentacao.visita_id == visita_id)
    if de is not None:
        stmt = stmt.where(models.PortariaMovimentacao.capturado_em >= de)
    if ate is not None:
        stmt = stmt.where(models.PortariaMovimentacao.capturado_em <= ate)
    stmt = stmt.limit(min(limite, 200))
    return list(db.scalars(stmt))


@router.get(
    "/abertas",
    response_model=list[PortariaEventoOut],
    summary="Lista as visitas abertas (entrou e não saiu)",
)
def listar_abertas(
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("portaria", "admin")),
) -> list[models.PortariaMovimentacao]:
    """Lista as visitas abertas (entrou e ainda não saiu)."""
    stmt = (
        select(models.PortariaMovimentacao)
        .where(
            models.PortariaMovimentacao.operacao == "entrada",
            models.PortariaMovimentacao.status_visita == "aberta",
        )
        .order_by(models.PortariaMovimentacao.capturado_em)
    )
    return list(db.scalars(stmt))
