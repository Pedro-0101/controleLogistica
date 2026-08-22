"""Adiciona nome aos pontos de coleta.

O campo ``nome`` é o rótulo de exibição do ponto. A coluna é adicionada de
forma idempotente porque a migração inicial cria o esquema inteiro via
``Base.metadata.create_all`` (que, após esta mudança, já inclui a coluna).

Revision ID: 0002_ponto_nome
Revises: 0001_initial
Create Date: 2026-08-21
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_ponto_nome"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _colunas_existentes() -> list[str]:
    inspetor = sa.inspect(op.get_bind())
    return [c["name"] for c in inspetor.get_columns("pontos")]


def upgrade() -> None:
    if "nome" not in _colunas_existentes():
        op.add_column(
            "pontos",
            sa.Column("nome", sa.String(120), nullable=False, server_default=""),
        )


def downgrade() -> None:
    if "nome" in _colunas_existentes():
        op.drop_column("pontos", "nome")
