"""Modelos ORM do domínio de logística (portaria + balança)."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
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
    # portaria_entrada | portaria_saida | balanca
    tipo: Mapped[str] = mapped_column(String(30))
    descricao: Mapped[str | None] = mapped_column(String(200), nullable=True)
    camera_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    planta: Mapped["Planta"] = relationship(back_populates="pontos")
    eventos: Mapped[list["EventoPlaca"]] = relationship(back_populates="ponto")


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

    eventos: Mapped[list["EventoPlaca"]] = relationship(back_populates="veiculo")


class Pesagem(Base):
    __tablename__ = "pesagens"

    id: Mapped[int] = mapped_column(primary_key=True)
    planta_id: Mapped[int] = mapped_column(ForeignKey("plantas.id"), index=True)
    ponto_id: Mapped[int] = mapped_column(ForeignKey("pontos.id"), index=True)
    veiculo_id: Mapped[int | None] = mapped_column(ForeignKey("veiculos.id"), nullable=True)
    movimentacao_id: Mapped[int | None] = mapped_column(
        ForeignKey("movimentacoes.id"), nullable=True, index=True
    )

    peso: Mapped[float] = mapped_column(Float)
    desvio: Mapped[float | None] = mapped_column(Float, nullable=True)  # dispersão (MAD) ao estabilizar
    amostras: Mapped[int | None] = mapped_column(Integer, nullable=True)

    capturado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    planta: Mapped["Planta"] = relationship()
    ponto: Mapped["Ponto"] = relationship()
    veiculo: Mapped["Veiculo"] = relationship()
    movimentacao: Mapped["Movimentacao"] = relationship(back_populates="pesagens")


class EventoPlaca(Base):
    __tablename__ = "eventos_placa"

    id: Mapped[int] = mapped_column(primary_key=True)
    placa: Mapped[str] = mapped_column(String(8), index=True)
    placa_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)
    formato: Mapped[str | None] = mapped_column(String(10), nullable=True)  # mercosul | antiga
    confianca: Mapped[float | None] = mapped_column(Float, nullable=True)

    planta_id: Mapped[int] = mapped_column(ForeignKey("plantas.id"), index=True)
    ponto_id: Mapped[int] = mapped_column(ForeignKey("pontos.id"), index=True)
    veiculo_id: Mapped[int | None] = mapped_column(ForeignKey("veiculos.id"), nullable=True)

    imagem_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    capturado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    planta: Mapped["Planta"] = relationship()
    ponto: Mapped["Ponto"] = relationship(back_populates="eventos")
    veiculo: Mapped["Veiculo"] = relationship(back_populates="eventos")


class Movimentacao(Base):
    __tablename__ = "movimentacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    planta_id: Mapped[int] = mapped_column(ForeignKey("plantas.id"), index=True)
    veiculo_id: Mapped[int] = mapped_column(ForeignKey("veiculos.id"), index=True)

    status: Mapped[str] = mapped_column(String(20), default="aberta", index=True)  # aberta | fechada
    # carregamento | descarregamento | sem_pesagem | pesagem_parcial
    tipo: Mapped[str | None] = mapped_column(String(30), nullable=True)

    entrada_evento_id: Mapped[int | None] = mapped_column(
        ForeignKey("eventos_placa.id"), nullable=True
    )
    saida_evento_id: Mapped[int | None] = mapped_column(
        ForeignKey("eventos_placa.id"), nullable=True
    )

    peso_entrada: Mapped[float | None] = mapped_column(Float, nullable=True)
    peso_saida: Mapped[float | None] = mapped_column(Float, nullable=True)
    peso_liquido: Mapped[float | None] = mapped_column(Float, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    fechado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    planta: Mapped["Planta"] = relationship()
    veiculo: Mapped["Veiculo"] = relationship()
    entrada_evento: Mapped["EventoPlaca"] = relationship(foreign_keys=[entrada_evento_id])
    saida_evento: Mapped["EventoPlaca"] = relationship(foreign_keys=[saida_evento_id])
    pesagens: Mapped[list["Pesagem"]] = relationship(
        back_populates="movimentacao", order_by="Pesagem.id"
    )

    @property
    def placa(self) -> str | None:
        return self.veiculo.placa if self.veiculo else None
