"""Dependências de autenticação e autorização."""

from collections.abc import Callable
from typing import cast

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from .security import TokenInvalidoError, decodificar_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _credenciais_invalidas() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Usuario:
    """Resolve o usuário autenticado a partir do bearer token."""
    try:
        payload = decodificar_token(token)
    except TokenInvalidoError as exc:
        raise _credenciais_invalidas() from exc
    if payload.get("type") != "access" or payload.get("sub") is None:
        raise _credenciais_invalidas()
    usuario = db.get(models.Usuario, int(cast(str, payload["sub"])))
    if usuario is None or not usuario.ativo:
        raise _credenciais_invalidas()
    return usuario


def require_roles(*roles: str) -> Callable[..., models.Usuario]:
    """Fábrica de dependência que exige um dos papéis informados."""

    def _dependencia(
        usuario: models.Usuario = Depends(get_current_user),
    ) -> models.Usuario:
        if usuario.role not in roles:
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        return usuario

    return _dependencia
