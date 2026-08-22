"""Adiciona o tipo (tara/bruto) às pesagens.

A coluna ``tipo`` indica se a pesagem é de tara (caminhão vazio) ou bruto
(caminhão cheio), pois o sistema não consegue inferir isso automaticamente.
A coluna é adicionada de forma idempotente porque a migração inicial cria o
esquema via ``Base.metadata.create_all``.

Revision ID: 0003_pesagem_tipo
Revises: 0002_ponto_nome
Create Date: 2026-08-21
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_pesagem_tipo"
down_revision = "0002_ponto_nome"
branch_labels = None
depends_on = None


def _colunas_existentes() -> list[str]:
    inspetor = sa.inspect(op.get_bind())
    return [c["name"] for c in inspetor.get_columns("pesagens")]


def upgrade() -> None:
    if "tipo" not in _colunas_existentes():
        op.add_column(
            "pesagens",
            sa.Column("tipo", sa.String(10), nullable=True),
        )


def downgrade() -> None:
    if "tipo" in _colunas_existentes():
        op.drop_column("pesagens", "tipo")
