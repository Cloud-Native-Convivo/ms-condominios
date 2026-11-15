"""guarda el correo del residente en la solicitud de asignacion

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable: las solicitudes existentes no tienen correo, y el bff no
    # siempre puede resolverlo (Cognito caido o token sin acceso a GetUser).
    op.add_column("solicitudes_asignacion", sa.Column("usuario_email", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("solicitudes_asignacion", "usuario_email")
