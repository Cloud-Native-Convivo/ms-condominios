from sqlalchemy import Column, ForeignKey, Identity, Integer, String, UniqueConstraint

from app.config.database import Base


class SolicitudAsignacion(Base):
    __tablename__ = "solicitudes_asignacion"
    __table_args__ = (UniqueConstraint("usuario_sub", name="uq_solicitud_usuario"),)

    id = Column(Integer, Identity(), primary_key=True)
    usuario_sub = Column(String(255), nullable=False)
    condominio_id = Column(Integer, ForeignKey("condominios.id"), nullable=False)
    # Texto legible armado por el servidor; unidad_id es la referencia real.
    # Nullable: las solicitudes anteriores a 0004 solo guardaban el texto.
    unidad = Column(String(100), nullable=False)
    unidad_id = Column(Integer, ForeignKey("unidades.id", name="fk_solicitud_unidad"), nullable=True)
    estado = Column(String(20), nullable=False, default="pendiente")
