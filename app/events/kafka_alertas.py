"""Consumidor de espacios.alertas.v1 (grupo condominios-alertas).

Entrega at-least-once: el offset se confirma recién después del commit en
Oracle. Si el proceso cae entre ambos, el mensaje vuelve a llegar y el insert
choca con la clave primaria event_id, así que no se duplica.
"""

import logging

from aiokafka import AIOKafkaConsumer
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import before_sleep_log, retry, wait_fixed

from app.config.database import fabrica_sesiones
from app.config.settings import settings
from app.dto.alerta_espacio_dto import TOPICO_ALERTAS, AlertaEspacioV1
from app.model.alerta_espacio import AlertaEspacio

logger = logging.getLogger(__name__)

GRUPO_ALERTAS = "condominios-alertas"


def _a_modelo(alerta: AlertaEspacioV1) -> AlertaEspacio:
    return AlertaEspacio(
        event_id=str(alerta.event_id),
        tipo=alerta.tipo,
        severidad=alerta.severidad,
        condominio_id=alerta.condominio_id,
        espacio_id=alerta.espacio_id,
        reserva_id=alerta.reserva_id,
        destinatario_sub=alerta.destinatario_sub,
        mensaje=alerta.mensaje,
        origen_event_id=str(alerta.origen_event_id) if alerta.origen_event_id else None,
        ocurrido_en=alerta.ocurrido_en.replace(tzinfo=None),
    )


async def procesar_valor(sesion: AsyncSession, valor: bytes | None) -> bool:
    """Guarda una alerta; False si es inválida o repetida (igual se confirma el offset).

    Un error de base de datos distinto de la clave repetida se propaga: el
    offset no se confirma y el mensaje se vuelve a leer al reconectar.
    """
    try:
        alerta = AlertaEspacioV1.model_validate_json(valor or b"")
    except ValidationError as error:
        # Sin DLQ nativa en Kafka: se registra y se salta para no bloquear la partición.
        logger.error("Mensaje fuera de contrato en %s, se omite: %s", TOPICO_ALERTAS, error)
        return False

    sesion.add(_a_modelo(alerta))
    try:
        await sesion.commit()
    except IntegrityError:
        await sesion.rollback()
        logger.info("Alerta %s ya registrada, se omite", alerta.event_id)
        return False
    logger.info(
        "Alerta %s %s guardada (condominio %s)", alerta.tipo, alerta.event_id, alerta.condominio_id
    )
    return True


@retry(wait=wait_fixed(10), before_sleep=before_sleep_log(logger, logging.ERROR))
async def consumidor_alertas() -> None:
    """Consume alertas y confirma el offset tras cada commit en la base."""
    consumidor = AIOKafkaConsumer(
        TOPICO_ALERTAS,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        client_id=f"{settings.kafka_client_id}-alertas",
        group_id=GRUPO_ALERTAS,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    await consumidor.start()
    try:
        async for mensaje in consumidor:
            async with fabrica_sesiones() as sesion:
                await procesar_valor(sesion, mensaje.value)
            await consumidor.commit()
    finally:
        await consumidor.stop()
