"""CRUD de usuários."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..auth.deps import require_roles
from ..auth.security import hash_senha
from ..db import get_db
from ..schemas import UsuarioIn, UsuarioOut, UsuarioUpdate

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

ROLES_VALIDOS = {"admin", "portaria", "balanca"}


def _obter_ou_404(db: Session, usuario_id: int) -> models.Usuario:
    usuario = db.get(models.Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return usuario


def _validar_role(role: str) -> None:
    if role not in ROLES_VALIDOS:
        raise HTTPException(status_code=422, detail=f"Role inválida: {role}")


def _validar_email_unico(db: Session, email: str, ignorar_id: int | None = None) -> str:
    email = email.lower()
    stmt = select(models.Usuario).where(models.Usuario.email == email)
    if ignorar_id is not None:
        stmt = stmt.where(models.Usuario.id != ignorar_id)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")
    return email


@router.get("", response_model=list[UsuarioOut])
def listar(
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("admin")),
) -> list[models.Usuario]:
    """Lista os usuários."""
    return list(db.scalars(select(models.Usuario).order_by(models.Usuario.id)))


@router.get("/{usuario_id}", response_model=UsuarioOut)
def obter(
    usuario_id: int,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("admin")),
) -> models.Usuario:
    """Retorna um usuário pelo id."""
    return _obter_ou_404(db, usuario_id)


@router.post("", response_model=UsuarioOut, status_code=201)
def criar(
    body: UsuarioIn,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("admin")),
) -> models.Usuario:
    """Cria um usuário."""
    _validar_role(body.role)
    email = _validar_email_unico(db, body.email)
    usuario = models.Usuario(
        nome=body.nome,
        email=email,
        senha_hash=hash_senha(body.senha),
        role=body.role,
        ativo=body.ativo,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.put("/{usuario_id}", response_model=UsuarioOut)
def atualizar(
    usuario_id: int,
    body: UsuarioUpdate,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("admin")),
) -> models.Usuario:
    """Atualiza um usuário (campos informados apenas)."""
    usuario = _obter_ou_404(db, usuario_id)
    dados = body.model_dump(exclude_unset=True)
    if "role" in dados and dados["role"] is not None:
        _validar_role(dados["role"])
    if "email" in dados and dados["email"] is not None:
        dados["email"] = _validar_email_unico(db, dados["email"], ignorar_id=usuario_id)
    if "senha" in dados and dados["senha"] is not None:
        dados["senha_hash"] = hash_senha(dados.pop("senha"))
    for campo, valor in dados.items():
        setattr(usuario, campo, valor)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.delete("/{usuario_id}", status_code=204)
def excluir(
    usuario_id: int,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(require_roles("admin")),
) -> None:
    """Remove um usuário."""
    db.delete(_obter_ou_404(db, usuario_id))
    db.commit()
