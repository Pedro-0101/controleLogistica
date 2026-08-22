"""Captura de snapshot das câmeras IP Intelbras.

As câmeras usam firmwares de OEMs diferentes (Dahua, Hikvision/ISAPI etc.),
então o endpoint de snapshot varia por modelo. A URL completa do snapshot de
cada câmera fica em ``Ponto.camera_url`` e é chamada diretamente.

Exemplos:
- Hikvision/ISAPI: http://IP/ISAPI/Streaming/channels/101/picture
- Dahua:           http://IP/cgi-bin/snapshot.cgi
"""

import httpx

from ..config import settings
from .erros import CameraNaoConfiguradaError, CameraSnapshotError


def _auth() -> httpx.Auth:
    if settings.dvr_auth.lower() == "basic":
        return httpx.BasicAuth(settings.dvr_user, settings.dvr_password)
    return httpx.DigestAuth(settings.dvr_user, settings.dvr_password)


async def capturar_snapshot(camera_url: str | None) -> bytes:
    """Baixa o snapshot JPEG a partir da URL completa configurada no ponto.

    Args:
        camera_url: URL completa do snapshot (ex.: ``http://IP/ISAPI/Streaming/channels/101/picture``).

    Returns:
        Os bytes do JPEG capturado.

    Raises:
        CameraNaoConfiguradaError: Se a URL não estiver configurada.
        CameraSnapshotError: Se a captura falhar (rede, autenticação ou resposta vazia).
    """
    if not camera_url:
        raise CameraNaoConfiguradaError
    try:
        async with httpx.AsyncClient(
            auth=_auth(), timeout=settings.dvr_timeout
        ) as client:
            resp = await client.get(camera_url)
            resp.raise_for_status()
            conteudo = resp.content
    except httpx.HTTPError as exc:
        raise CameraSnapshotError(f"falha ao capturar snapshot: {exc}") from exc
    if not conteudo:
        raise CameraSnapshotError("snapshot vazio")
    return conteudo
