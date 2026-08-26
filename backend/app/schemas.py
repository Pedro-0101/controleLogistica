"""Schemas Pydantic para a API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class PlacaCameraIn(BaseModel):
    host: str = Field(
        ..., description="IP da câmera", examples=["192.168.11.241"]
    )
    port: int = Field(80, description="Porta HTTP da câmera", examples=[80])
    user: str = Field(
        ..., description="Usuário da câmera", examples=["admin"]
    )
    password: str = Field(..., description="Senha da câmera")
    auth: str = Field(
        "digest",
        description="Tipo de autenticação: 'digest' ou 'basic'",
        examples=["digest"],
    )
    camera_url: str | None = Field(
        None,
        description=(
            "URL completa do snapshot (opcional). "
            "Se omitida, o sistema tenta descobrir automaticamente."
        ),
        examples=["http://192.168.11.241/ISAPI/Streaming/channels/101/picture"],
    )


class PlacaCameraOut(BaseModel):
    placa: str = Field(..., description="Placa normalizada (ex: ABC1D23)")
    formato: str = Field(
        ..., description="Formato da placa: 'mercosul' ou 'antiga'"
    )
    confianca: float = Field(
        ..., description="Score de confiança do OCR (0-1)"
    )
    raw: str = Field(..., description="Texto bruto capturado pelo OCR")
    camera_url_encontrada: str | None = Field(
        None, description="URL de snapshot que retornou imagem válida"
    )
    foto_path: str | None = Field(
        None, description="Caminho da imagem salva em disco"
    )
