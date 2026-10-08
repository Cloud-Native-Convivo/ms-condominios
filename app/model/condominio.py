from sqlalchemy import Boolean, Column, Identity, Integer, String

from app.config.database import Base


class Condominio(Base):
    __tablename__ = "condominios"

    # Oracle no autoincrementa sin Identity; la PK ya trae índice propio
    id = Column(Integer, Identity(), primary_key=True)
    nombre = Column(String(255), nullable=False)
    direccion = Column(String(255), nullable=False)
    tipo = Column(String(1), nullable=False, default="A")
    cantidad_sectores = Column(Integer, nullable=False, default=1)
    plan = Column(String(50), nullable=False, default="basico")
    registro_minvu = Column(String(255), nullable=True)
    seguro_incendio = Column(Boolean, nullable=False, default=False)
    plan_emergencia = Column(Boolean, nullable=False, default=False)
