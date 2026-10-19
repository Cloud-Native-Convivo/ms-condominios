"""registra solicitudes de asignación de residentes

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "solicitudes_asignacion",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("usuario_sub", sa.String(255), nullable=False),
        sa.Column("condominio_id", sa.Integer(), sa.ForeignKey("condominios.id"), nullable=False),
        sa.Column("unidad", sa.String(100), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.UniqueConstraint("usuario_sub", name="uq_solicitud_usuario"),
    )


def downgrade() -> None:
    op.drop_table("solicitudes_asignacion")
