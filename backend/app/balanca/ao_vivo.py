"""Balança "ao vivo": simula leituras contínuas e mantém o peso estabilizado.

Para testes sem hardware, usa o SimuladorBalanca. Quando houver balança real,
este módulo é o ponto único a trocar por leitura serial.
"""

import threading

from .estabilizador import EstabilizadorPeso
from .parser import extrair_peso
from .simulador import SimuladorBalanca


class BalancaAoVivo:
    def __init__(self, peso_alvo: float = 15480.0) -> None:
        self._sim = SimuladorBalanca(peso_alvo=peso_alvo)
        self._estab = EstabilizadorPeso(
            tamanho_janela=25, tolerancia=5.0, peso_minimo=100.0
        )
        self._lock = threading.Lock()
        self._ultimo = 0.0
        self._estavel = None

    def tick(self) -> float:
        peso = extrair_peso(self._sim.proxima_linha())
        with self._lock:
            self._ultimo = peso
            estavel = self._estab.adicionar(peso)
            if estavel is not None:
                self._estavel = estavel
        return peso

    def estado(self) -> dict:
        with self._lock:
            return {
                "peso_atual": round(self._ultimo, 1),
                "peso_estavel": self._estavel.peso if self._estavel else None,
                "desvio": self._estavel.desvio if self._estavel else None,
            }
