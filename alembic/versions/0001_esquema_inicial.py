"""esquema inicial

Revision ID: 0001
Revises:
Create Date: 2026-10-07

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "condominios",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("direccion", sa.String(255), nullable=False),
        sa.Column("tipo", sa.String(1), nullable=False),
        sa.Column("cantidad_sectores", sa.Integer(), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False),
        sa.Column("registro_minvu", sa.String(255), nullable=True),
        sa.Column("seguro_incendio", sa.Boolean(), nullable=False),
        sa.Column("plan_emergencia", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "outbox",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("aggregate_type", sa.String(255), nullable=False),
        sa.Column("aggregate_id", sa.String(255), nullable=False),
        sa.Column("type", sa.String(255), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("SYS_EXTRACT_UTC(SYSTIMESTAMP)")),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_outbox_processed_id", "outbox", ["processed", "id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_outbox_processed_id", table_name="outbox")
    op.drop_table("outbox")
    op.drop_table("condominios")
