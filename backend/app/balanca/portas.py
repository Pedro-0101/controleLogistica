"""Listagem e detecção automática de portas seriais (balança)."""

import re
import time

from serial import SerialException
from serial.tools import list_ports
from serial.tools.list_ports_common import ListPortInfo

from .leitor import BalancaSerial
from .parser import extrair_peso

_CONTROLE = re.compile(r"[\x00-\x1f]")
TEMPO_VARREDURA = 2.0


def listar_portas() -> list[ListPortInfo]:
    """Retorna as portas seriais disponíveis, ordenadas pelo nome do dispositivo."""
    return sorted(list_ports.comports(), key=lambda p: p.device)


def limpar(linha: str) -> str:
    """Remove caracteres de controle para exibição segura."""
    return _CONTROLE.sub(" ", linha).strip()


def testar_porta(
    info: ListPortInfo,
    baudrate: int = 9600,
    regex: str | None = None,
    tempo: float = TEMPO_VARREDURA,
) -> list[float]:
    """Lê `info` por `tempo` segundos e retorna os pesos válidos encontrados."""
    pesos: list[float] = []
    try:
        serial = BalancaSerial(info.device, baudrate=baudrate)
    except SerialException:
        return pesos
    try:
        inicio = time.monotonic()
        while time.monotonic() - inicio < tempo:
            linha = serial.ler_linha()
            if linha is None:
                continue
            peso = extrair_peso(linha, padrao=regex)
            if peso is not None:
                pesos.append(peso)
    except SerialException:
        pass
    finally:
        serial.fechar()
    return pesos


def detectar(
    baudrate: int = 9600,
    regex: str | None = None,
    tempo: float = TEMPO_VARREDURA,
) -> str | None:
    """Varre as portas e retorna a primeira que enviou pesos válidos."""
    for info in listar_portas():
        if testar_porta(info, baudrate, regex, tempo):
            return info.device
    return None
