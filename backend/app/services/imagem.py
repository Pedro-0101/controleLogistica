"""Decodificação e persistência de imagens de captura."""

from datetime import UTC, datetime

import cv2
import numpy as np

from ..config import settings


def decodificar(conteudo: bytes) -> np.ndarray:
    """Decodifica bytes em uma imagem BGR.

    Raises:
        ValueError: Se o conteúdo não for uma imagem válida.
    """
    arr = np.frombuffer(conteudo, dtype=np.uint8)
    imagem = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if imagem is None:
        raise ValueError("imagem inválida")
    return imagem


def salvar(conteudo: bytes) -> str:
    """Grava a imagem em disco e retorna o caminho absoluto."""
    nome = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')}.jpg"
    caminho = settings.imagens_dir / nome
    caminho.write_bytes(conteudo)
    return str(caminho)
