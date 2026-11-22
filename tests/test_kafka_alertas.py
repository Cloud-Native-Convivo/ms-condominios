"""Consumidor de espacios.alertas.v1 y listado de alertas por condominio.

Técnica: partición de equivalencia por mensaje (válido, repetido, fuera de
contrato, error de base de datos), tabla de decisión de roles por endpoint y
valores límite para `limite` (1 y 200 válidos, 0 y 201 no).
"""

import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, OperationalError

from app.api.alerta_router import get_alerta_service
from app.events import kafka_alertas
from app.main import app
from app.model.alerta_espacio import AlertaEspacio
from app.repository.alerta_espacio_repository import AlertaEspacioRepository
from app.service.alerta_espacio_service import AlertaEspacioService


def _alerta(**cambios) -> dict:
    base = {
        "event_id": str(uuid4()),
        "version": 1,
        "ocurrido_en": "2026-11-22T11:00:00-03:00",
        "tipo": "RESERVA_CANCELADA_POR_ADMIN",
        "severidad": "advertencia",
        "condominio_id": 1,
        "espacio_id": 45,
        "reserva_id": 46,
        "destinatario_sub": "residente-2",
        "mensaje": "Tu reserva #46 en Sala E2E fue cancelada por la administración.",
        "origen_event_id": str(uuid4()),
    }
    return base | cambios


def _bytes(datos: dict) -> bytes:
    return json.dumps(datos).encode()


# --- procesar_valor -----------------------------------------------------------


@pytest.mark.asyncio
async def test_guarda_alerta_valida_con_fecha_en_utc(mock_session):
    datos = _alerta()

    assert await kafka_alertas.procesar_valor(mock_session, _bytes(datos)) is True

    guardada = mock_session.add.call_args.args[0]
    assert isinstance(guardada, AlertaEspacio)
    assert guardada.event_id == datos["event_id"]
    assert guardada.origen_event_id == datos["origen_event_id"]
    assert (guardada.condominio_id, guardada.reserva_id) == (1, 46)
    # 11:00 en Chile (-03:00) = 14:00 UTC, guardada sin zona.
    assert guardada.ocurrido_en == datetime(2026, 11, 22, 14, 0)
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_alerta_sin_reserva_ni_origen(mock_session):
    datos = _alerta(reserva_id=None, destinatario_sub=None, origen_event_id=None)
    assert await kafka_alertas.procesar_valor(mock_session, _bytes(datos)) is True
    guardada = mock_session.add.call_args.args[0]
    assert (guardada.reserva_id, guardada.origen_event_id) == (None, None)


@pytest.mark.asyncio
async def test_alerta_repetida_se_omite(mock_session):
    mock_session.commit.side_effect = IntegrityError("INSERT", {}, Exception("ORA-00001"))

    assert await kafka_alertas.procesar_valor(mock_session, _bytes(_alerta())) is False

    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "valor",
    [
        b"no es json",
        None,
        _bytes(_alerta(tipo="TIPO_DESCONOCIDO")),
        _bytes(_alerta(version=2)),
        _bytes(_alerta(mensaje="")),
        _bytes(_alerta(campo_extra=1)),
        _bytes(_alerta(ocurrido_en="2026-11-22T11:00:00")),  # sin zona horaria
    ],
)
async def test_mensaje_fuera_de_contrato_se_registra_y_se_salta(mock_session, valor, caplog):
    assert await kafka_alertas.procesar_valor(mock_session, valor) is False
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_awaited()
    assert "fuera de contrato" in caplog.text


@pytest.mark.asyncio
async def test_otro_error_de_base_de_datos_se_propaga(mock_session):
    # El consumidor no confirma el offset y el mensaje se relee al reconectar.
    mock_session.commit.side_effect = OperationalError("INSERT", {}, Exception("ORA-03113"))
    with pytest.raises(OperationalError):
        await kafka_alertas.procesar_valor(mock_session, _bytes(_alerta()))
    mock_session.rollback.assert_not_awaited()


# --- Bucle del consumidor -----------------------------------------------------


class _ConsumidorFalso:
    def __init__(self, valores):
        self._valores = valores
        self.start = AsyncMock()
        self.stop = AsyncMock()
        self.commit = AsyncMock()

    def __aiter__(self):
        return self._generar()

    async def _generar(self):
        for valor in self._valores:
            yield SimpleNamespace(value=valor)


def _fabrica(sesion):
    contexto = MagicMock()
    contexto.__aenter__ = AsyncMock(return_value=sesion)
    contexto.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=contexto)


@pytest.mark.asyncio
async def test_consumidor_confirma_offset_tras_cada_mensaje_con_commit_manual(mock_session):
    falso = _ConsumidorFalso([_bytes(_alerta()), b"invalido"])
    with (
        patch.object(kafka_alertas, "AIOKafkaConsumer", return_value=falso) as clase,
        patch.object(kafka_alertas, "fabrica_sesiones", _fabrica(mock_session)),
    ):
        await kafka_alertas.consumidor_alertas.retry_with(stop=lambda _: True)()

    argumentos = clase.call_args
    assert argumentos.args == ("espacios.alertas.v1",)
    assert argumentos.kwargs["group_id"] == "condominios-alertas"
    assert argumentos.kwargs["enable_auto_commit"] is False
    assert argumentos.kwargs["auto_offset_reset"] == "earliest"
    # Válido e inválido confirman offset: el inválido se salta para no bloquear la partición.
    assert falso.commit.await_count == 2
    falso.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_consumidor_no_confirma_offset_si_falla_la_base(mock_session):
    mock_session.commit.side_effect = OperationalError("INSERT", {}, Exception("ORA-03113"))
    falso = _ConsumidorFalso([_bytes(_alerta())])
    with (
        patch.object(kafka_alertas, "AIOKafkaConsumer", return_value=falso),
        patch.object(kafka_alertas, "fabrica_sesiones", _fabrica(mock_session)),
    ):
        with pytest.raises(OperationalError):
            await kafka_alertas.consumidor_alertas.retry_with(stop=lambda _: True, reraise=True)()
    falso.commit.assert_not_awaited()
    falso.stop.assert_awaited_once()


# --- Repositorio y servicio ---------------------------------------------------


@pytest.mark.asyncio
async def test_repositorio_filtra_por_condominio_y_ordena_reciente_primero(mock_session):
    resultado = MagicMock()
    resultado.scalars.return_value.all.return_value = ["a"]
    mock_session.execute.return_value = resultado

    assert await AlertaEspacioRepository(mock_session).listar_por_condominio(7, 20) == ["a"]

    sql = str(mock_session.execute.await_args.args[0].compile(compile_kwargs={"literal_binds": True}))
    assert "alertas_espacio.condominio_id = 7" in sql
    assert "ORDER BY alertas_espacio.ocurrido_en DESC" in sql
    assert "20" in sql


@pytest.mark.asyncio
async def test_servicio_delega_en_el_repositorio():
    repo = AsyncMock(spec=AlertaEspacioRepository)
    repo.listar_por_condominio.return_value = []
    assert await AlertaEspacioService(repo).listar_alertas(3, 10) == []
    repo.listar_por_condominio.assert_awaited_once_with(3, 10)


# --- Endpoint -----------------------------------------------------------------


@pytest.fixture
def cliente_alertas():
    servicio = AsyncMock(spec=AlertaEspacioService)
    servicio.listar_alertas.return_value = [
        AlertaEspacio(
            event_id="9b2f0c1e-0000-4000-8000-000000000001",
            tipo="RESERVA_POR_EXPIRAR",
            severidad="info",
            condominio_id=1,
            espacio_id=45,
            reserva_id=48,
            destinatario_sub="residente-3",
            mensaje="Tu reserva #48 expira en 3 min si no se confirma el pago.",
            origen_event_id=None,
            ocurrido_en=datetime(2026, 11, 22, 14, 0),
            recibido_en=datetime(2026, 11, 22, 14, 0, 1),
        )
    ]
    app.dependency_overrides[get_alerta_service] = lambda: servicio
    with TestClient(app) as c:
        yield c, servicio
    app.dependency_overrides.clear()


@pytest.mark.parametrize("rol", ["admin", "administrador", "conserje"])
def test_listar_alertas_admin_y_conserje(cliente_alertas, rol):
    c, servicio = cliente_alertas
    r = c.get("/condominios/1/alertas/", headers={"X-Usuario-Roles": rol})
    assert r.status_code == 200
    assert r.json()[0]["tipo"] == "RESERVA_POR_EXPIRAR"
    assert r.json()[0]["reserva_id"] == 48
    servicio.listar_alertas.assert_awaited_once_with(1, 50)


@pytest.mark.parametrize("rol", ["residente", ""])
def test_listar_alertas_otros_roles_es_403(cliente_alertas, rol):
    c, servicio = cliente_alertas
    r = c.get("/condominios/1/alertas/", headers={"X-Usuario-Roles": rol})
    assert r.status_code == 403
    servicio.listar_alertas.assert_not_awaited()


@pytest.mark.parametrize(
    ("ruta", "codigo"),
    [
        ("/condominios/1/alertas/?limite=1", 200),
        ("/condominios/1/alertas/?limite=200", 200),
        ("/condominios/1/alertas/?limite=0", 422),
        ("/condominios/1/alertas/?limite=201", 422),
        ("/condominios/0/alertas/", 422),
    ],
)
def test_listar_alertas_limites(cliente_alertas, ruta, codigo):
    c, _ = cliente_alertas
    assert c.get(ruta, headers={"X-Usuario-Roles": "admin"}).status_code == codigo
