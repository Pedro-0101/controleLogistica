"""Estabilização de peso: mediana + desvio mediano absoluto (MAD).

O leitor entrega pesos contínuos (com ruído e eventuais picos). Para
considerar um peso "estável", acumulamos uma janela de leituras e exigimos
que a dispersão (MAD) fique abaixo da tolerância; o valor representativo é a
mediana (robusta a picos).
"""

import statistics
from dataclasses import dataclass


@dataclass(frozen=True)
class PesoEstavel:
    peso: float  # mediana da janela (kg)
    desvio: float  # MAD da janela (kg)
    amostras: int


class EstabilizadorPeso:
    def __init__(
        self,
        tamanho_janela: int = 25,
        tolerancia: float = 5.0,
        peso_minimo: float = 100.0,
    ) -> None:
        self.tamanho_janela = tamanho_janela
        self.tolerancia = tolerancia
        self.peso_minimo = peso_minimo
        self._amostras: list[float] = []

    def adicionar(self, peso: float) -> PesoEstavel | None:
        """Adiciona uma leitura; retorna PesoEstavel quando a janela estabiliza."""
        self._amostras.append(peso)
        if len(self._amostras) < self.tamanho_janela:
            return None

        amostras = self._amostras
        self._amostras = []

        mediana = statistics.median(amostras)
        desvio = statistics.median([abs(x - mediana) for x in amostras])

        if mediana < self.peso_minimo:
            return None
        if desvio > self.tolerancia:
            return None

        return PesoEstavel(
            peso=round(mediana, 1),
            desvio=round(desvio, 2),
            amostras=len(amostras),
        )
