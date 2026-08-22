"""Rotas operacionais da balança (pesagens)."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..auth.deps import require_roles
from ..db import get_db
from ..schemas import CarregamentoOut, PesagemOut
from ..services import camera as camera_service
from ..services.erros import (
    CameraNaoConfiguradaError,
    CameraSnapshotError,
    PlacaNaoReconhecidaError,
    VisitaAbertaNaoEncontradaError,
)
from ..services.imagem import decodificar, salvar
from ..services.pesagem_service import registrar_pesagem
from ..services.plate_service import resolver_placa
from ..services.ponto_service import obter_planta_por_codigo, obter_ponto

router = APIRouter(prefix="/pesagens", tags=["pesagens"])


def _resolver_unidade(db: Session, codigo: str) -> models.Planta:
    planta = obter_planta_por_codigo(db, codigo)
    if planta is None:
        raise HTTPException(
            status_code=404, detail=f"Unidade '{codigo}' não encontrada"
        )
    return planta


def _ponto_balanca(db: Session, planta_id: int) -> models.Ponto:
    ponto = obter_ponto(db, planta_id, "balanca")
    if ponto is None:
        raise HTTPException(
            status_code=404, detail="Ponto do tipo 'balanca' não encontrado na unidade"
        )
    return ponto


@router.post(
    "",
    response_model=PesagemOut,
    status_code=201,
    summary="Registra a pesagem de um veículo",
    responses={
        400: {"description": "Imagem inválida, peso <= 0 ou tipo inválido"},
        404: {"description": "Unidade ou ponto de coleta não encontrado"},
        409: {"description": "Nenhuma visita aberta para a placa"},
        422: {"description": "Placa inválida ou não reconhecida (e não enviada)"},
        502: {"description": "Falha ao capturar imagem da câmera"},
    },
)
async def criar_pesagem(
    peso: float = Form(..., description="Peso em toneladas", examples=[99.99]),
    tipo: str = Form(
        ..., description="Tipo da pesagem: 'tara' (vazio) ou 'bruto' (cheio)"
    ),
    camera: str = Form(
        ...,
        description="URL de snapshot da câmera",
        examples=["http://192.168.11.241/ISAPI/Streaming/channels/101/picture"],
    ),
    unidade: str = Form(
        ..., description="Código da unidade (planta)", examples=["SAO_JOAO"]
    ),
    placa: str | None = Form(
        None,
        description="Placa explícita (opcional; ignora o OCR)",
        examples=["ABC1D23"],
    ),
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("balanca", "admin")),
) -> models.Pesagem:
    """Registra a pesagem de um veículo na balança da unidade informada.

    O front envia a URL de snapshot da câmera e o `tipo` da pesagem (``tara``
    para caminhão vazio ou ``bruto`` para cheio). O peso líquido é calculado
    como ``bruto - tara`` no fechamento da visita.
    """
    if peso <= 0:
        raise HTTPException(status_code=400, detail="Peso deve ser maior que zero")
    if tipo not in ("tara", "bruto"):
        raise HTTPException(status_code=400, detail="Tipo deve ser 'tara' ou 'bruto'")
    planta = _resolver_unidade(db, unidade)
    ponto = _ponto_balanca(db, planta.id)
    try:
        conteudo = await camera_service.capturar_snapshot(camera)
    except CameraNaoConfiguradaError as exc:
        raise HTTPException(status_code=400, detail="Câmera não informada") from exc
    except CameraSnapshotError as exc:
        raise HTTPException(
            status_code=502, detail="Falha ao capturar imagem da câmera"
        ) from exc
    try:
        imagem = decodificar(conteudo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Imagem inválida") from exc
    try:
        resolvida = resolver_placa(placa=placa, imagem=imagem)
    except PlacaNaoReconhecidaError as exc:
        raise HTTPException(status_code=422, detail="Placa não reconhecida") from exc
    foto_path = salvar(conteudo)
    try:
        return registrar_pesagem(
            db,
            resolvida=resolvida,
            peso=peso,
            tipo=tipo,
            planta_id=planta.id,
            ponto_id=ponto.id,
            foto_path=foto_path,
        )
    except VisitaAbertaNaoEncontradaError as exc:
        raise HTTPException(
            status_code=409, detail="Nenhuma visita aberta para esta placa"
        ) from exc


@router.get(
    "",
    response_model=list[PesagemOut],
    summary="Lista as pesagens",
)
def listar_pesagens(
    placa: str | None = None,
    visita_id: uuid.UUID | None = None,
    de: datetime | None = None,
    ate: datetime | None = None,
    limite: int = 100,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("balanca", "admin")),
) -> list[models.Pesagem]:
    """Lista as pesagens com filtros opcionais (`placa`, `visita_id`, `de`/`ate`)."""
    stmt = select(models.Pesagem).order_by(models.Pesagem.capturado_em.desc())
    if placa:
        stmt = stmt.where(models.Pesagem.placa == placa.upper())
    if visita_id is not None:
        stmt = stmt.where(models.Pesagem.visita_id == visita_id)
    if de is not None:
        stmt = stmt.where(models.Pesagem.capturado_em >= de)
    if ate is not None:
        stmt = stmt.where(models.Pesagem.capturado_em <= ate)
    stmt = stmt.limit(min(limite, 200))
    return list(db.scalars(stmt))


@router.get(
    "/carregamentos",
    response_model=list[CarregamentoOut],
    summary="Lista os carregamentos concluídos",
)
def listar_carregamentos(
    placa: str | None = None,
    de: datetime | None = None,
    ate: datetime | None = None,
    limite: int = 100,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("balanca", "admin")),
) -> list[models.Pesagem]:
    """Lista os carregamentos concluídos (com peso líquido e tipo)."""
    stmt = (
        select(models.Pesagem)
        .where(models.Pesagem.tipo_carregamento.is_not(None))
        .order_by(models.Pesagem.capturado_em.desc())
    )
    if placa:
        stmt = stmt.where(models.Pesagem.placa == placa.upper())
    if de is not None:
        stmt = stmt.where(models.Pesagem.capturado_em >= de)
    if ate is not None:
        stmt = stmt.where(models.Pesagem.capturado_em <= ate)
    stmt = stmt.limit(min(limite, 200))
    return list(db.scalars(stmt))
