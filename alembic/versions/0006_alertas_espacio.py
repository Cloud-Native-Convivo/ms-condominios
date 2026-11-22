"""guarda las alertas recibidas de espacios.alertas.v1

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alertas_espacio",
        # event_id como PK: un mensaje repetido choca en el insert (idempotencia).
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("severidad", sa.String(20), nullable=False),
        sa.Column("condominio_id", sa.Integer(), nullable=False),
        sa.Column("espacio_id", sa.Integer(), nullable=False),
        sa.Column("reserva_id", sa.Integer(), nullable=True),
        sa.Column("destinatario_sub", sa.String(255), nullable=True),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("origen_event_id", sa.String(36), nullable=True),
        sa.Column("ocurrido_en", sa.DateTime(), nullable=False),
        sa.Column("recibido_en", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_alertas_espacio_condominio_fecha", "alertas_espacio", ["condominio_id", "ocurrido_en"]
    )


def downgrade() -> None:
    op.drop_index("ix_alertas_espacio_condominio_fecha", table_name="alertas_espacio")
    op.drop_table("alertas_espacio")
