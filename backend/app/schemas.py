"""Schemas Pydantic para a API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshIn(BaseModel):
    refresh_token: str


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    role: str
    ativo: bool
    criado_em: datetime


class UsuarioIn(BaseModel):
    nome: str
    email: str
    senha: str
    role: str
    ativo: bool = True


class UsuarioUpdate(BaseModel):
    nome: str | None = None
    email: str | None = None
    senha: str | None = None
    role: str | None = None
    ativo: bool | None = None


class PlantaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nome: str
    cidade: str | None
    uf: str | None
    criado_em: datetime


class PlantaIn(BaseModel):
    codigo: str
    nome: str
    cidade: str | None = None
    uf: str | None = None


class VeiculoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    placa: str
    criado_em: datetime
    atualizado_em: datetime


class VeiculoIn(BaseModel):
    placa: str


class PontoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    planta_id: int
    codigo: str
    nome: str
    tipo: str
    descricao: str | None
    camera_url: str | None
    criado_em: datetime


class PontoIn(BaseModel):
    planta_id: int
    codigo: str
    nome: str
    tipo: str
    descricao: str | None = None
    camera_url: str | None = None


class PortariaEventoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visita_id: uuid.UUID
    placa: str
    placa_raw: str | None
    formato: str | None
    confianca: float | None
    operacao: str
    status_visita: str | None
    foto_frontal_path: str | None
    capturado_em: datetime


class PesagemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visita_id: uuid.UUID
    placa: str
    peso: float
    ordem: int
    tipo: str | None
    peso_entrada: float | None
    peso_saida: float | None
    peso_liquido: float | None
    tipo_carregamento: str | None
    capturado_em: datetime


class CarregamentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visita_id: uuid.UUID
    placa: str
    peso_entrada: float | None
    peso_saida: float | None
    peso_liquido: float | None
    tipo_carregamento: str
    capturado_em: datetime
