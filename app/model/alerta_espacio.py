from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text

from app.config.database import Base


def _ahora_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class AlertaEspacio(Base):
    """Alerta recibida de espacios.alertas.v1.

    event_id es la clave primaria: un mensaje repetido choca en el insert y
    eso es la idempotencia del consumidor.
    """

    __tablename__ = "alertas_espacio"
    # El listado filtra por condominio y ordena por fecha.
    __table_args__ = (Index("ix_alertas_espacio_condominio_fecha", "condominio_id", "ocurrido_en"),)

    event_id = Column(String(36), primary_key=True)
    tipo = Column(String(50), nullable=False)
    severidad = Column(String(20), nullable=False)
    condominio_id = Column(Integer, nullable=False)
    espacio_id = Column(Integer, nullable=False)
    reserva_id = Column(Integer, nullable=True)
    destinatario_sub = Column(String(255), nullable=True)
    # Text: el contrato no limita el largo y un insert fallido bloquearía la partición.
    mensaje = Column(Text, nullable=False)
    origen_event_id = Column(String(36), nullable=True)
    # Fechas en UTC sin zona, como created_at de outbox.
    ocurrido_en = Column(DateTime, nullable=False)
    recibido_en = Column(DateTime, nullable=False, default=_ahora_utc)
