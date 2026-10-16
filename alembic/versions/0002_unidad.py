"""agrega tabla unidades

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-15

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "unidades",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("condominio_id", sa.Integer(), sa.ForeignKey("condominios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("torre", sa.String(50), nullable=False, server_default="UNICA"),
        sa.Column("piso", sa.String(10), nullable=False),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_unidades_condominio_id", "unidades", ["condominio_id"])
    op.create_unique_constraint("uq_unidad_direccion", "unidades", ["condominio_id", "torre", "piso", "numero"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_unidad_direccion", "unidades", type_="unique")
    op.drop_index("ix_unidades_condominio_id", table_name="unidades")
    op.drop_table("unidades")
