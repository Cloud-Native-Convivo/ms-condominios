"""vincula la solicitud de asignacion con la unidad real

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable: las solicitudes existentes solo tienen el texto libre y no se
    # pueden vincular de forma confiable a una fila de unidades.
    op.add_column("solicitudes_asignacion", sa.Column("unidad_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_solicitud_unidad", "solicitudes_asignacion", "unidades", ["unidad_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_solicitud_unidad", "solicitudes_asignacion", type_="foreignkey")
    op.drop_column("solicitudes_asignacion", "unidad_id")
