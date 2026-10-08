import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import py_eureka_client.eureka_client as eureka_client
from fastapi import FastAPI

from app.api.condominio_router import router as condominio_router
from app.config.settings import settings
from app.events.outbox_event import relay_outbox
from app.exception.condominio_exception import CondominioNoEncontradoException
from app.handler.exception_handler import condominio_no_encontrado_handler
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

    try:
        yield
    finally:
        logger.info("Deteniendo tareas...")
        tarea_outbox.cancel()
        await asyncio.gather(tarea_outbox, return_exceptions=True)
        if settings.eureka_url:
            try:
                await eureka_client.stop_async()
            except Exception as error:
                logger.warning("Error al desregistrar de Eureka: %s", error)

app = FastAPI(title="MS Condominios", lifespan=lifespan)

app.add_middleware(SecurityMiddleware)
app.add_middleware(LoggingMiddleware)

app.add_exception_handler(CondominioNoEncontradoException, condominio_no_encontrado_handler)
app.include_router(condominio_router)
