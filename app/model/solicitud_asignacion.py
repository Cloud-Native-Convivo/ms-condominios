from sqlalchemy import Column, ForeignKey, Identity, Integer, String, UniqueConstraint

from app.config.database import Base


class SolicitudAsignacion(Base):
    __tablename__ = "solicitudes_asignacion"
    __table_args__ = (UniqueConstraint("usuario_sub", name="uq_solicitud_usuario"),)

    id = Column(Integer, Identity(), primary_key=True)
    usuario_sub = Column(String(255), nullable=False)
    condominio_id = Column(Integer, ForeignKey("condominios.id"), nullable=False)
    unidad = Column(String(100), nullable=False)
    estado = Column(String(20), nullable=False, default="pendiente")
