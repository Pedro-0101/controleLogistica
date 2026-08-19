"""Leitura de balança via porta serial (modo contínuo)."""

import serial


class BalancaSerial:
    def __init__(
        self,
        porta: str,
        baudrate: int = 9600,
        bytesize: int = serial.EIGHTBITS,
        paridade: str = serial.PARITY_NONE,
        stopbits: int = serial.STOPBITS_ONE,
        timeout: float = 1.0,
    ) -> None:
        self._ser = serial.Serial(
            port=porta,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=paridade,
            stopbits=stopbits,
            timeout=timeout,
        )

    def ler_linha(self) -> str | None:
        """Lê uma linha terminada por \\r ou \\n. Retorna None no timeout."""
        bruto = self._ser.readline()
        if not bruto:
            return None
        return bruto.decode("ascii", errors="ignore").strip()

    def fechar(self) -> None:
        self._ser.close()
