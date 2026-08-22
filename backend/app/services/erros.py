"""Exceções de domínio mapeadas para respostas HTTP nos routers."""


class PlacaNaoReconhecidaError(Exception):
    """Placa não foi reconhecida pelo OCR nem informada no corpo."""


class VisitaAbertaNaoEncontradaError(Exception):
    """Não há visita aberta para a placa informada."""


class CameraNaoConfiguradaError(Exception):
    """O ponto de coleta não possui URL de câmera (snapshot) configurada."""


class CameraSnapshotError(Exception):
    """Falha ao obter o snapshot da câmera (rede, autenticação ou resposta inválida)."""
