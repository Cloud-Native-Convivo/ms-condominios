import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import py_eureka_client.eureka_client as eureka_client
from fastapi import FastAPI

from app.api.alerta_router import router as alerta_router
from app.api.condominio_router import router as condominio_router
from app.api.solicitud_router import router as solicitud_router
from app.api.unidad_router import router as unidad_router
from app.config.settings import settings
from app.events.kafka_alertas import consumidor_alertas
from app.events.outbox_event import relay_outbox
from app.exception.condominio_exception import (
    CondominioConUnidadesException,
    CondominioNoEncontradoException,
)
from app.exception.unidad_exception import (
    UnidadDuplicadaException,
    UnidadIncompatibleConTipoException,
    UnidadInexistenteException,
    UnidadNoEncontradaException,
)
from app.handler.exception_handler import (
    condominio_con_unidades_handler,
    condominio_no_encontrado_handler,
    unidad_duplicada_handler,
    unidad_invalida_handler,
    unidad_no_encontrada_handler,
)
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.security_middleware import SecurityMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# El esquema lo crea `alembic upgrade head` antes de arrancar (ver Dockerfile), no create_all.
# Sin CORS acá: lo resuelve el BFF, este servicio no se expone al navegador.

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if settings.eureka_url:
        try:
            await eureka_client.init_async(
                eureka_server=settings.eureka_url,
                app_name="ms-condominios",
                instance_port=settings.puerto,
                instance_ip=settings.eureka_ip,
                instance_host="ms-condominios"
            )
            logger.info("Registrado en Eureka")
        except Exception as error:
            logger.warning("Eureka no disponible (%s) — continuando", error)

    tarea_outbox = asyncio.create_task(relay_outbox())
    logger.info("Tarea outbox iniciada")
    # Kafka caído no bloquea el arranque: el consumidor reintenta cada 10 s.
    tarea_alertas = asyncio.create_task(consumidor_alertas())
    logger.info("Consumidor de alertas Kafka iniciado")

    try:
        yield
    finally:
        logger.info("Deteniendo tareas...")
        tarea_outbox.cancel()
        tarea_alertas.cancel()
        await asyncio.gather(tarea_outbox, tarea_alertas, return_exceptions=True)
        if settings.eureka_url:
            try:
                await eureka_client.stop_async()
            except Exception as error:
                logger.warning("Error al desregistrar de Eureka: %s", error)

app = FastAPI(title="MS Condominios", lifespan=lifespan)

app.add_middleware(SecurityMiddleware)
app.add_middleware(LoggingMiddleware)

app.add_exception_handler(CondominioNoEncontradoException, condominio_no_encontrado_handler)
app.add_exception_handler(UnidadNoEncontradaException, unidad_no_encontrada_handler)
app.add_exception_handler(UnidadDuplicadaException, unidad_duplicada_handler)
app.add_exception_handler(CondominioConUnidadesException, condominio_con_unidades_handler)
app.add_exception_handler(UnidadIncompatibleConTipoException, unidad_invalida_handler)
app.add_exception_handler(UnidadInexistenteException, unidad_invalida_handler)
app.include_router(solicitud_router)
app.include_router(condominio_router)
app.include_router(unidad_router)
app.include_router(alerta_router)
