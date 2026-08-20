"""CRUD de caminhões (veículos)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..anpr.plate import normalizar_placa
from ..auth.deps import get_current_user, require_roles
from ..db import get_db
from ..schemas import VeiculoIn, VeiculoOut

router = APIRouter(prefix="/veiculos", tags=["veiculos"])


def _obter_ou_404(db: Session, veiculo_id: int) -> models.Veiculo:
    veiculo = db.get(models.Veiculo, veiculo_id)
    if veiculo is None:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    return veiculo


def _validar_placa(placa: str) -> str:
    normalizada = normalizar_placa(placa)
    if normalizada is None:
        raise HTTPException(status_code=422, detail="Placa inválida")
    return normalizada.valor


def _validar_placa_unica(
    db: Session, placa: str, ignorar_id: int | None = None
) -> None:
    stmt = select(models.Veiculo).where(models.Veiculo.placa == placa)
    if ignorar_id is not None:
        stmt = stmt.where(models.Veiculo.id != ignorar_id)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Placa já cadastrada")


@router.get("", response_model=list[VeiculoOut])
def listar(
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(get_current_user),
) -> list[models.Veiculo]:
    """Lista os veículos."""
    return list(db.scalars(select(models.Veiculo).order_by(models.Veiculo.id)))


@router.get("/{veiculo_id}", response_model=VeiculoOut)
def obter(
    veiculo_id: int,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(get_current_user),
) -> models.Veiculo:
    """Retorna um veículo pelo id."""
    return _obter_ou_404(db, veiculo_id)


@router.post("", response_model=VeiculoOut, status_code=201)
def criar(
    body: VeiculoIn,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("admin")),
) -> models.Veiculo:
    """Cria um veículo."""
    placa = _validar_placa(body.placa)
    _validar_placa_unica(db, placa)
    veiculo = models.Veiculo(placa=placa)
    db.add(veiculo)
    db.commit()
    db.refresh(veiculo)
    return veiculo


@router.put("/{veiculo_id}", response_model=VeiculoOut)
def atualizar(
    veiculo_id: int,
    body: VeiculoIn,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("admin")),
) -> models.Veiculo:
    """Atualiza a placa de um veículo."""
    veiculo = _obter_ou_404(db, veiculo_id)
    placa = _validar_placa(body.placa)
    _validar_placa_unica(db, placa, ignorar_id=veiculo_id)
    veiculo.placa = placa
    db.commit()
    db.refresh(veiculo)
    return veiculo


@router.delete("/{veiculo_id}", status_code=204)
def excluir(
    veiculo_id: int,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("admin")),
) -> None:
    """Remove um veículo."""
    db.delete(_obter_ou_404(db, veiculo_id))
    db.commit()
