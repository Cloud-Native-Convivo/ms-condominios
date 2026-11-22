"""Contrato de espacios.alertas.v1 y respuesta del listado de alertas.

AlertaEspacioV1 es copia del contrato publicado por ms-espacios-comunes
(app/dto/kafka_eventos.py). Un cambio incompatible allá exige tópico .v2,
así que esta copia solo cambia si cambia la versión.
"""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

TOPICO_ALERTAS = "espacios.alertas.v1"

TipoAlertaEspacio = Literal[
    "ESPACIO_EN_MANTENCION_CON_RESERVAS",
    "RESERVA_CANCELADA_POR_ADMIN",
    "RESERVA_POR_EXPIRAR",
]


class AlertaEspacioV1(BaseModel):
    """Alerta para residentes o administración (espacios.alertas.v1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: UUID
    version: Literal[1] = 1
    ocurrido_en: AwareDatetime
    tipo: TipoAlertaEspacio
    severidad: Literal["info", "advertencia"]
    condominio_id: int
    espacio_id: int
    reserva_id: int | None = None
    destinatario_sub: str | None = None
    mensaje: str = Field(min_length=1)
    origen_event_id: UUID | None = None

    @field_validator("ocurrido_en")
    @classmethod
    def _normalizar_utc(cls, valor: datetime) -> datetime:
        return valor.astimezone(UTC)


class AlertaRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    tipo: str
    severidad: str
    condominio_id: int
    espacio_id: int
    reserva_id: int | None
    destinatario_sub: str | None
    mensaje: str
    origen_event_id: str | None
    ocurrido_en: datetime
    recibido_en: datetime
