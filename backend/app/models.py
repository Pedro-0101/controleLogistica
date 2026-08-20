"""Modelos ORM do domínio de logística (portaria + balança)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Planta(Base):
    __tablename__ = "plantas"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(120))
    cidade: Mapped[str | None] = mapped_column(String(80), nullable=True)
    uf: Mapped[str | None] = mapped_column(String(2), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    pontos: Mapped[list["Ponto"]] = relationship(
        back_populates="planta", cascade="all, delete-orphan"
    )


class Ponto(Base):
    __tablename__ = "pontos"

    id: Mapped[int] = mapped_column(primary_key=True)
    planta_id: Mapped[int] = mapped_column(ForeignKey("plantas.id"), index=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    tipo: Mapped[str] = mapped_column(
        String(30)
    )  # portaria_entrada | portaria_saida | balanca
    descricao: Mapped[str | None] = mapped_column(String(200), nullable=True)
    camera_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    planta: Mapped["Planta"] = relationship(back_populates="pontos")


class Veiculo(Base):
    __tablename__ = "veiculos"

    id: Mapped[int] = mapped_column(primary_key=True)
    placa: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))  # admin | portaria | balanca
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PortariaMovimentacao(Base):
    __tablename__ = "portaria_movimentacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    visita_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    planta_id: Mapped[int] = mapped_column(ForeignKey("plantas.id"), index=True)
    ponto_id: Mapped[int] = mapped_column(ForeignKey("pontos.id"), index=True)
    veiculo_id: Mapped[int | None] = mapped_column(
        ForeignKey("veiculos.id"), nullable=True, index=True
    )
    placa: Mapped[str] = mapped_column(String(8), index=True)
    placa_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)
    formato: Mapped[str | None] = mapped_column(String(10), nullable=True)
    confianca: Mapped[float | None] = mapped_column(Float, nullable=True)
    operacao: Mapped[str] = mapped_column(String(10))  # entrada | saida
    foto_frontal_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status_visita: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # aberta | fechada
    capturado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    planta: Mapped["Planta"] = relationship()
    ponto: Mapped["Ponto"] = relationship()
    veiculo: Mapped["Veiculo"] = relationship()


class Pesagem(Base):
    __tablename__ = "pesagens"

    id: Mapped[int] = mapped_column(primary_key=True)
    visita_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    planta_id: Mapped[int] = mapped_column(ForeignKey("plantas.id"), index=True)
    ponto_id: Mapped[int] = mapped_column(ForeignKey("pontos.id"), index=True)
    veiculo_id: Mapped[int | None] = mapped_column(
        ForeignKey("veiculos.id"), nullable=True, index=True
    )
    placa: Mapped[str] = mapped_column(String(8), index=True)
    foto_frontal_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    peso: Mapped[float] = mapped_column(Float)  # toneladas
    desvio: Mapped[float | None] = mapped_column(Float, nullable=True)
    amostras: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ordem: Mapped[int] = mapped_column(Integer)  # 1 = entrada, 2 = saida, ...
    peso_entrada: Mapped[float | None] = mapped_column(Float, nullable=True)
    peso_saida: Mapped[float | None] = mapped_column(Float, nullable=True)
    peso_liquido: Mapped[float | None] = mapped_column(Float, nullable=True)
    tipo_carregamento: Mapped[str | None] = mapped_column(String(20), nullable=True)
    capturado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    planta: Mapped["Planta"] = relationship()
    ponto: Mapped["Ponto"] = relationship()
    veiculo: Mapped["Veiculo"] = relationship()
