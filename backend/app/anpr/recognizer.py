"""Reconhecimento de placas via PaddleOCR (ANPR offline).

O import do PaddleOCR é feito sob demanda (dentro do construtor), pois é um
carregamento pesado e deve ficar fora do caminho de testes que informam a
placa explicitamente no corpo da requisição.
"""

import os
from dataclasses import dataclass

import numpy as np

from .plate import Placa, normalizar_placa


@dataclass(frozen=True)
class CandidatoPlaca:
    placa: Placa
    confianca: float
    raw: str


class PlacaRecognizer:
    def __init__(self, lang: str = "en") -> None:
        # Definidas antes do import do paddleocr para evitar falhas de
        # oneDNN/MKLDNN em algumas CPUs.
        os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "False")
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        from paddleocr import PaddleOCR

        self._ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            lang=lang,
        )

    def reconhecer(self, imagem: np.ndarray) -> list[CandidatoPlaca]:
        """Retorna os candidatos a placa em uma imagem.

        Args:
            imagem: Array numpy (BGR, como lido pelo OpenCV).

        Returns:
            Lista de candidatos normalizados, cada um com placa, confiança e raw.
        """
        resultado = self._ocr.predict(imagem)
        candidatos: list[CandidatoPlaca] = []
        for pagina in resultado:
            for texto, score in zip(
                pagina["rec_texts"], pagina["rec_scores"], strict=False
            ):
                placa = normalizar_placa(texto)
                if placa is not None:
                    candidatos.append(
                        CandidatoPlaca(placa=placa, confianca=float(score), raw=texto)
                    )
        return candidatos

    def reconhecer_melhor(self, imagem: np.ndarray) -> CandidatoPlaca | None:
        """Retorna apenas o candidato de maior confiança (ou None)."""
        candidatos = self.reconhecer(imagem)
        if not candidatos:
            return None
        return max(candidatos, key=lambda c: c.confianca)


_recognizer: PlacaRecognizer | None = None


def get_recognizer() -> PlacaRecognizer:
    """Retorna a instância única do reconhecedor, criando-a sob demanda."""
    global _recognizer
    if _recognizer is None:
        from ..config import settings

        _recognizer = PlacaRecognizer(lang=settings.anpr_lang)
    return _recognizer
