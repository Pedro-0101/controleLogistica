"""Hash de senha e criação/validação de tokens JWT."""

from datetime import UTC, datetime, timedelta
from typing import cast

import bcrypt
import jwt

from .. import models
from ..config import settings


class TokenInvalidoError(Exception):
    """Token JWT inválido, expirado ou malformado."""


def hash_senha(senha: str) -> str:
    """Gera o hash bcrypt de uma senha em texto plano."""
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Verifica se a senha em texto plano corresponde ao hash armazenado."""
    try:
        return bcrypt.checkpw(senha.encode(), senha_hash.encode())
    except ValueError:
        return False


def _criar_token(*, sub: str, tipo: str, role: str | None, expira_minutos: int) -> str:
    agora = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": sub,
        "type": tipo,
        "iat": agora,
        "exp": agora + timedelta(minutes=expira_minutos),
    }
    if role is not None:
        payload["role"] = role
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def criar_access_token(usuario: models.Usuario) -> str:
    """Gera o token de acesso (curto, carrega o role)."""
    return _criar_token(
        sub=str(usuario.id),
        tipo="access",
        role=usuario.role,
        expira_minutos=settings.access_token_expire_minutes,
    )


def criar_refresh_token(usuario: models.Usuario) -> str:
    """Gera o token de refresh (longo, sem role)."""
    return _criar_token(
        sub=str(usuario.id),
        tipo="refresh",
        role=None,
        expira_minutos=settings.refresh_token_expire_minutes,
    )


def decodificar_token(token: str) -> dict[str, object]:
    """Decodifica e valida a assinatura e a expiração de um token.

    Raises:
        TokenInvalidoError: Se o token for inválido, expirado ou malformado.
    """
    try:
        return cast(
            dict[str, object],
            jwt.decode(token, settings.secret_key, algorithms=["HS256"]),
        )
    except jwt.PyJWTError as exc:
        raise TokenInvalidoError from exc
