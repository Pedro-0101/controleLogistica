"""Schemas Pydantic para a API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EventoPlacaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    placa: str
    placa_raw: str | None
    formato: str | None
    confianca: float | None
    planta_id: int
    ponto_id: int
    veiculo_id: int | None
    imagem_path: str | None
    capturado_em: datetime


class ReconhecimentoOut(BaseModel):
    placa: str
    formato: str
    confianca: float
    raw: str
    evento_id: int | None = None


class ReconhecerResponse(BaseModel):
    candidatos: list[ReconhecimentoOut]
    total: int


class PesagemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    planta_id: int
    ponto_id: int
    veiculo_id: int | None
    movimentacao_id: int | None
    peso: float
    desvio: float | None
    amostras: int | None
    capturado_em: datetime


class PesagemIn(BaseModel):
    placa: str
    peso: float
    ponto_codigo: str = "BALANCA"


class MovimentacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    planta_id: int
    veiculo_id: int
    placa: str | None
    status: str
    tipo: str | None
    peso_entrada: float | None
    peso_saida: float | None
    peso_liquido: float | None
    criado_em: datetime
    fechado_em: datetime | None


class BalancaEstado(BaseModel):
    peso_atual: float
    peso_estavel: float | None
    desvio: float | None
    fonte: str = "simulador"
    porta: str | None = None
    ultima_linha: str | None = None


class BalancaPortaOut(BaseModel):
    porta: str
    descricao: str | None
    fabricante: str | None
    serial: str | None
    hwid: str | None


class BalancaConectarIn(BaseModel):
    porta: str | None = None
    baudrate: int = 9600


class BalancaDetectarOut(BaseModel):
    porta: str | None


class BalancaPesarOut(BaseModel):
    placa: str | None
    formato: str | None
    confianca: float | None
    peso: float
    desvio: float | None
    pesagem_id: int | None
    movimentacao_id: int | None
    movimentacao_status: str | None
    movimentacao_tipo: str | None
