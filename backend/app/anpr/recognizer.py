"""Reconhecimento de placas via PaddleOCR (ANPR offline).

Importante: as variáveis de ambiente abaixo DEVEM ser definidas antes do
import do paddleocr, caso contrário o PaddleOCR 3.x tenta usar oneDNN/MKLDNN
e pode falhar em algumas CPUs (NotImplementedError em onednn_instruction.cc).
"""

import os

os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "False")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

from paddleocr import PaddleOCR  # noqa: E402

from .plate import Placa, normalizar_placa


class PlacaRecognizer:
    def __init__(self, lang: str = "en") -> None:
        self._ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            lang=lang,
        )

    def reconhecer(self, imagem) -> list[dict]:
        """Retorna os candidatos a placa em uma imagem.

        `imagem` pode ser um caminho de arquivo (str/Path) ou um array numpy
        (BGR, como lido pelo OpenCV). Cada candidato é um dict com as chaves
        `placa` (Placa), `confianca` (float) e `raw` (texto bruto do OCR).
        """
        resultado = self._ocr.predict(imagem)
        candidatos: list[dict] = []
        for pagina in resultado:
            for texto, score in zip(pagina["rec_texts"], pagina["rec_scores"]):
                placa = normalizar_placa(texto)
                if placa is not None:
                    candidatos.append(
                        {"placa": placa, "confianca": float(score), "raw": texto}
                    )
        return candidatos

    def reconhecer_melhor(self, imagem) -> dict | None:
        """Retorna apenas o candidato de maior confiança (ou None)."""
        candidatos = self.reconhecer(imagem)
        if not candidatos:
            return None
        return max(candidatos, key=lambda c: c["confianca"])


_recognizer: PlacaRecognizer | None = None


def get_recognizer() -> PlacaRecognizer:
    global _recognizer
    if _recognizer is None:
        from ..config import settings

        _recognizer = PlacaRecognizer(lang=settings.anpr_lang)
    return _recognizer
