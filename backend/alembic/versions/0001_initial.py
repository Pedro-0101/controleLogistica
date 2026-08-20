"""Esquema inicial da API de operação.

Substitui as tabelas legadas do sistema de teste por duas tabelas operacionais
(``portaria_movimentacoes`` e ``pesagens``) e adiciona ``usuarios``. As tabelas
``plantas``, ``pontos`` e ``veiculos`` são preservadas.

Observação sobre a unidade de peso: o legado armazenava o peso em **kg**
(ex.: ``15480.0``); a nova API usa **toneladas**. As tabelas legadas são
descartadas (é um sistema de teste); qualquer importação manual de pesos legados
deve dividir o valor por 1000.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-20
"""

from alembic import op

from app import models  # noqa: F401
from app.db import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _dropar_tabelas_legadas() -> None:
    op.execute("DROP TABLE IF EXISTS pesagens CASCADE")
    op.execute("DROP TABLE IF EXISTS movimentacoes CASCADE")
    op.execute("DROP TABLE IF EXISTS eventos_placa CASCADE")


def upgrade() -> None:
    _dropar_tabelas_legadas()
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
