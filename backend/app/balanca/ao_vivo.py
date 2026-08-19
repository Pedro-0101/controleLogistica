"""Balança "ao vivo": fonte simulada ou serial, mantendo o peso estabilizado.

Mantém leituras contínuas e expõe o estado atual (peso corrente e estabilizado).
A fonte pode alternar entre simulador e porta serial em tempo de execução.
"""

import threading

from serial import SerialException

from .estabilizador import EstabilizadorPeso, PesoEstavel
from .leitor import BalancaSerial
from .parser import extrair_peso
from .simulador import SimuladorBalanca


class BalancaAoVivo:
    def __init__(self, peso_alvo: float = 15480.0) -> None:
        self._lock = threading.Lock()
        self._sim = SimuladorBalanca(peso_alvo=peso_alvo)
        self._serial: BalancaSerial | None = None
        self._porta: str | None = None
        self._fonte = "simulador"
        self._estab = EstabilizadorPeso(
            tamanho_janela=25, tolerancia=5.0, peso_minimo=100.0
        )
        self._ultimo = 0.0
        self._ultima_linha = ""
        self._estavel: PesoEstavel | None = None

    def _ler(self) -> str | None:
        if self._serial is not None:
            return self._serial.ler_linha()
        return self._sim.proxima_linha()

    def _reset(self) -> None:
        self._estab = EstabilizadorPeso(
            tamanho_janela=25, tolerancia=5.0, peso_minimo=100.0
        )
        self._estavel = None
        self._ultimo = 0.0

    def usar_simulador(self) -> None:
        with self._lock:
            if self._serial is not None:
                self._serial.fechar()
                self._serial = None
            self._porta = None
            self._fonte = "simulador"
            self._reset()

    def conectar_serial(self, porta: str, baudrate: int = 9600) -> None:
        with self._lock:
            if self._serial is not None:
                self._serial.fechar()
            self._serial = BalancaSerial(porta, baudrate=baudrate)
            self._porta = porta
            self._fonte = "serial"
            self._reset()

    def tick(self) -> float:
        try:
            linha = self._ler()
        except SerialException:
            linha = None
        peso = extrair_peso(linha) if linha else None
        with self._lock:
            self._ultima_linha = linha or ""
            if peso is not None:
                self._ultimo = peso
                estavel = self._estab.adicionar(peso)
                if estavel is not None:
                    self._estavel = estavel
            return self._ultimo

    def estado(self) -> dict:
        with self._lock:
            return {
                "peso_atual": round(self._ultimo, 1),
                "peso_estavel": self._estavel.peso if self._estavel else None,
                "desvio": self._estavel.desvio if self._estavel else None,
                "fonte": self._fonte,
                "porta": self._porta,
                "ultima_linha": self._ultima_linha or None,
            }
