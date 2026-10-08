import asyncio
import logging

import aio_pika
from sqlalchemy import false
from sqlalchemy.future import select

from app.config.database import fabrica_sesiones
from app.config.settings import settings
from app.model.outbox import Outbox

logger = logging.getLogger(__name__)

ESPERA_POLL_SEGUNDOS = 5
ESPERA_REINTENTO_SEGUNDOS = 10

# SKIP LOCKED: con varias réplicas cada fila la publica una sola.
# == false() y no is_(False): este último genera "IS 0", inválido en Oracle.
CONSULTA_PENDIENTES = (
    select(Outbox)
    .where(Outbox.processed == false())
    .order_by(Outbox.id)
    .with_for_update(skip_locked=True)
)

async def relay_outbox() -> None:
    """Publica en RabbitMQ los eventos pendientes de outbox. Ante cualquier fallo reintenta sin límite."""
    while True:
        try:
            await _publicar_pendientes()
        except Exception:
            # CancelledError no hereda de Exception: el shutdown sigue cortando el bucle
            logger.exception("Relay outbox caído; reintento en %s s", ESPERA_REINTENTO_SEGUNDOS)
            await asyncio.sleep(ESPERA_REINTENTO_SEGUNDOS)

async def _publicar_pendientes() -> None:
    """Abre una conexión y publica pendientes cada ESPERA_POLL_SEGUNDOS hasta que algo falle."""
    async with await aio_pika.connect_robust(
        host=settings.rabbitmq_host,
        port=settings.rabbitmq_port,
        login=settings.rabbitmq_usuario,
        password=settings.rabbitmq_contrasena,
    ) as conexion:
        canal = await conexion.channel()
        exchange = await canal.declare_exchange(
            "condominios_events", aio_pika.ExchangeType.TOPIC, durable=True
        )
        while True:
            async with fabrica_sesiones() as sesion:
                eventos = (await sesion.execute(CONSULTA_PENDIENTES)).scalars().all()
                for evento in eventos:
                    mensaje = aio_pika.Message(body=evento.payload.encode(), content_type="application/json")
                    await exchange.publish(mensaje, routing_key=evento.type)
                    evento.processed = True
                if eventos:
                    await sesion.commit()
            await asyncio.sleep(ESPERA_POLL_SEGUNDOS)
