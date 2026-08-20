"""Rotas de autenticação (login, refresh, me)."""

from typing import cast

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..auth.deps import get_current_user
from ..auth.security import (
    TokenInvalidoError,
    criar_access_token,
    criar_refresh_token,
    decodificar_token,
    verificar_senha,
)
from ..config import settings
from ..db import get_db
from ..schemas import RefreshIn, TokenOut, UsuarioOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _autenticar(db: Session, email: str, senha: str) -> models.Usuario:
    usuario = db.execute(
        select(models.Usuario).where(models.Usuario.email == email)
    ).scalar_one_or_none()
    if usuario is None or not verificar_senha(senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Usuário inativo")
    return usuario


def _tokens(usuario: models.Usuario) -> TokenOut:
    return TokenOut(
        access_token=criar_access_token(usuario),
        refresh_token=criar_refresh_token(usuario),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/login", response_model=TokenOut)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenOut:
    """Autentica por usuário/senha e emite access + refresh tokens."""
    usuario = _autenticar(db, form.username, form.password)
    return _tokens(usuario)


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, db: Session = Depends(get_db)) -> TokenOut:
    """Emite um novo par de tokens a partir de um refresh token válido."""
    try:
        payload = decodificar_token(body.refresh_token)
    except TokenInvalidoError as exc:
        raise HTTPException(status_code=401, detail="Token inválido") from exc
    if payload.get("type") != "refresh" or payload.get("sub") is None:
        raise HTTPException(status_code=401, detail="Token inválido")
    usuario = db.get(models.Usuario, int(cast(str, payload["sub"])))
    if usuario is None or not usuario.ativo:
        raise HTTPException(status_code=401, detail="Usuário inativo")
    return _tokens(usuario)


@router.get("/me", response_model=UsuarioOut)
def me(usuario: models.Usuario = Depends(get_current_user)) -> models.Usuario:
    """Retorna os dados do usuário autenticado."""
    return usuario
