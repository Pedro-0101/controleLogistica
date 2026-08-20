"""CRUD de unidades (plantas)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..auth.deps import get_current_user, require_roles
from ..db import get_db
from ..schemas import PlantaIn, PlantaOut

router = APIRouter(prefix="/plantas", tags=["plantas"])


def _obter_ou_404(db: Session, planta_id: int) -> models.Planta:
    planta = db.get(models.Planta, planta_id)
    if planta is None:
        raise HTTPException(status_code=404, detail="Planta não encontrada")
    return planta


def _validar_codigo_unico(
    db: Session, codigo: str, ignorar_id: int | None = None
) -> None:
    stmt = select(models.Planta).where(models.Planta.codigo == codigo)
    if ignorar_id is not None:
        stmt = stmt.where(models.Planta.id != ignorar_id)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Código já cadastrado")


@router.get("", response_model=list[PlantaOut])
def listar(
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(get_current_user),
) -> list[models.Planta]:
    """Lista as unidades."""
    return list(db.scalars(select(models.Planta).order_by(models.Planta.id)))


@router.get("/{planta_id}", response_model=PlantaOut)
def obter(
    planta_id: int,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(get_current_user),
) -> models.Planta:
    """Retorna uma unidade pelo id."""
    return _obter_ou_404(db, planta_id)


@router.post("", response_model=PlantaOut, status_code=201)
def criar(
    body: PlantaIn,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("admin")),
) -> models.Planta:
    """Cria uma unidade."""
    _validar_codigo_unico(db, body.codigo)
    planta = models.Planta(**body.model_dump())
    db.add(planta)
    db.commit()
    db.refresh(planta)
    return planta


@router.put("/{planta_id}", response_model=PlantaOut)
def atualizar(
    planta_id: int,
    body: PlantaIn,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("admin")),
) -> models.Planta:
    """Atualiza uma unidade."""
    planta = _obter_ou_404(db, planta_id)
    _validar_codigo_unico(db, body.codigo, ignorar_id=planta_id)
    for campo, valor in body.model_dump().items():
        setattr(planta, campo, valor)
    db.commit()
    db.refresh(planta)
    return planta


@router.delete("/{planta_id}", status_code=204)
def excluir(
    planta_id: int,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("admin")),
) -> None:
    """Remove uma unidade (bloqueado se houver pontos vinculados)."""
    planta = _obter_ou_404(db, planta_id)
    tem_ponto = db.execute(
        select(models.Ponto).where(models.Ponto.planta_id == planta_id).limit(1)
    ).scalar_one_or_none()
    if tem_ponto is not None:
        raise HTTPException(status_code=409, detail="Planta possui pontos vinculados")
    db.delete(planta)
    db.commit()
