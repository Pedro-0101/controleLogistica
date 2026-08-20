"""CRUD de pontos de coleta (portarias/balança)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..auth.deps import require_roles
from ..db import get_db
from ..schemas import PontoIn, PontoOut

router = APIRouter(prefix="/pontos", tags=["pontos"])

TIPOS_VALIDOS = {"portaria_entrada", "portaria_saida", "balanca"}


def _obter_ou_404(db: Session, ponto_id: int) -> models.Ponto:
    ponto = db.get(models.Ponto, ponto_id)
    if ponto is None:
        raise HTTPException(status_code=404, detail="Ponto não encontrado")
    return ponto


def _validar_tipo(tipo: str) -> None:
    if tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=422, detail=f"Tipo inválido: {tipo}")


def _validar_planta(db: Session, planta_id: int) -> None:
    if db.get(models.Planta, planta_id) is None:
        raise HTTPException(status_code=422, detail="Planta não encontrada")


def _validar_codigo_unico(
    db: Session, codigo: str, ignorar_id: int | None = None
) -> None:
    stmt = select(models.Ponto).where(models.Ponto.codigo == codigo)
    if ignorar_id is not None:
        stmt = stmt.where(models.Ponto.id != ignorar_id)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Código já cadastrado")


@router.get("", response_model=list[PontoOut])
def listar(
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("admin")),
) -> list[models.Ponto]:
    """Lista os pontos de coleta."""
    return list(db.scalars(select(models.Ponto).order_by(models.Ponto.id)))


@router.get("/{ponto_id}", response_model=PontoOut)
def obter(
    ponto_id: int,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("admin")),
) -> models.Ponto:
    """Retorna um ponto pelo id."""
    return _obter_ou_404(db, ponto_id)


@router.post("", response_model=PontoOut, status_code=201)
def criar(
    body: PontoIn,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("admin")),
) -> models.Ponto:
    """Cria um ponto de coleta."""
    _validar_tipo(body.tipo)
    _validar_planta(db, body.planta_id)
    _validar_codigo_unico(db, body.codigo)
    ponto = models.Ponto(**body.model_dump())
    db.add(ponto)
    db.commit()
    db.refresh(ponto)
    return ponto


@router.put("/{ponto_id}", response_model=PontoOut)
def atualizar(
    ponto_id: int,
    body: PontoIn,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("admin")),
) -> models.Ponto:
    """Atualiza um ponto de coleta."""
    ponto = _obter_ou_404(db, ponto_id)
    _validar_tipo(body.tipo)
    _validar_planta(db, body.planta_id)
    _validar_codigo_unico(db, body.codigo, ignorar_id=ponto_id)
    for campo, valor in body.model_dump().items():
        setattr(ponto, campo, valor)
    db.commit()
    db.refresh(ponto)
    return ponto


@router.delete("/{ponto_id}", status_code=204)
def excluir(
    ponto_id: int,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("admin")),
) -> None:
    """Remove um ponto de coleta."""
    db.delete(_obter_ou_404(db, ponto_id))
    db.commit()
