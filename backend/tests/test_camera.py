"""Testes unitários do serviço de captura de snapshot."""

import asyncio

import pytest

from app.services.camera import capturar_snapshot
from app.services.erros import CameraNaoConfiguradaError


def test_capturar_snapshot_sem_url_levanta_erro() -> None:
    with pytest.raises(CameraNaoConfiguradaError):
        asyncio.run(capturar_snapshot(None))
