"""Simulador de balança para testar parser + estabilização sem hardware.

Gera linhas no mesmo formato que uma balança em modo contínuo enviaria,
com ruído gaussiano e picos ocasionais (outliers) para validar a mediana.
"""

import random


class SimuladorBalanca:
    def __init__(
        self,
        peso_alvo: float = 15480.0,
        ruido: float = 1.5,
        pico_prob: float = 0.06,
        pico_magnitude: float = 80.0,
    ) -> None:
        self.peso_alvo = peso_alvo
        self.ruido = ruido
        self.pico_prob = pico_prob
        self.pico_magnitude = pico_magnitude

    def proxima_linha(self) -> str:
        peso = self.peso_alvo + random.gauss(0, self.ruido)
        if random.random() < self.pico_prob:
            peso += random.choice([-1, 1]) * self.pico_magnitude
        return f"+ {peso:.1f} kg"
