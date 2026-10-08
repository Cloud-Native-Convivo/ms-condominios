"""Integración contra Oracle real. Requiere una BD vacía y ORACLE_INTEGRACION=1.

Ejemplo (Oracle desechable, sin tocar el volumen del compose):
    docker run -d --name oracle-condominios-it -p 1533:1521 \
        -e ORACLE_PASSWORD=<admin> -e APP_USER=condominios_it -e APP_USER_PASSWORD=<pass> \
        gvenzl/oracle-free:23.5-slim
    ORACLE_INTEGRACION=1 DB_PORT=1533 DB_USERNAME=condominios_it DB_PASSWORD=<pass> \
        PYTHONPATH=. pytest tests/integration -v
"""
import json
import os

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.future import select

from app.config.database import fabrica_sesiones, motor, obtener_sesion
from app.events.outbox_event import CONSULTA_PENDIENTES
from app.model.condominio import Condominio
from app.model.outbox import Outbox
from app.repository.condominio_repository import CondominioRepository

pytestmark = [
    pytest.mark.skipif(os.getenv("ORACLE_INTEGRACION") != "1", reason="requiere Oracle real: ORACLE_INTEGRACION=1"),
    pytest.mark.asyncio(loop_scope="module"),
]


@pytest.fixture(scope="module")
def esquema_migrado():
    """Aplica la migración real de Alembic y la revierte al terminar."""
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    yield
    command.downgrade(config, "base")


@pytest_asyncio.fixture(scope="module", loop_scope="module", autouse=True)
async def bd(esquema_migrado):
    yield
    await motor.dispose()  # antes del downgrade: libera conexiones del pool


async def _crear_por_ruta_del_router(nombre: str) -> Condominio:
    """Usa obtener_sesion igual que la dependencia del router (el path que fallaba con .begin())."""
    generador = obtener_sesion()
    sesion = await anext(generador)
    try:
        return await CondominioRepository(sesion).create(
            Condominio(nombre=nombre, direccion="Calle 1", seguro_incendio=True), "CondominioCreado"
        )
    finally:
        await generador.aclose()


async def test_crear_condominio_asigna_id_y_persiste_evento_con_ese_id():
    condominio = await _crear_por_ruta_del_router("Condominio IT")

    assert condominio.id is not None
    assert condominio.seguro_incendio is True
    async with fabrica_sesiones() as sesion:
        evento = (await sesion.execute(
            select(Outbox).where(Outbox.aggregate_id == str(condominio.id))
        )).scalar_one()
    assert evento.type == "CondominioCreado"
    assert evento.processed is False
    assert evento.created_at is not None
    assert json.loads(evento.payload)["id"] == condominio.id


async def test_ids_consecutivos_no_colisionan():
    primero = await _crear_por_ruta_del_router("A")
    segundo = await _crear_por_ruta_del_router("B")

    assert segundo.id != primero.id


async def test_consulta_del_relay_salta_filas_bloqueadas_por_otra_replica():
    await _crear_por_ruta_del_router("Pendiente")

    async with fabrica_sesiones() as replica_a, fabrica_sesiones() as replica_b:
        tomados_por_a = (await replica_a.execute(CONSULTA_PENDIENTES)).scalars().all()
        tomados_por_b = (await replica_b.execute(CONSULTA_PENDIENTES)).scalars().all()
        await replica_a.rollback()
        await replica_b.rollback()

    assert tomados_por_a, "la consulta debe devolver los pendientes"
    assert tomados_por_b == []
