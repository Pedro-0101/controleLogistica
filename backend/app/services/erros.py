"""Exceções de domínio mapeadas para respostas HTTP nos routers."""


class PlacaNaoReconhecidaError(Exception):
    """Placa não foi reconhecida pelo OCR nem informada no corpo."""


class VisitaAbertaNaoEncontradaError(Exception):
    """Não há visita aberta para a placa informada."""
