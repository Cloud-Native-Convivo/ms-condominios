from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    UniqueConstraint,
)

from app.config.database import Base


class Unidad(Base):
    __tablename__ = "unidades"
    __table_args__ = (
        Index("ix_unidades_condominio_id", "condominio_id"),
        UniqueConstraint("condominio_id", "torre", "piso", "numero", name="uq_unidad_direccion"),
    )

    id = Column(Integer, Identity(), primary_key=True)
    condominio_id = Column(Integer, ForeignKey("condominios.id", ondelete="CASCADE"), nullable=False)
    torre = Column(String(50), nullable=False, default="UNICA")
    piso = Column(String(10), nullable=False)
    numero = Column(String(20), nullable=False)
    activa = Column(Boolean, nullable=False, default=True)
