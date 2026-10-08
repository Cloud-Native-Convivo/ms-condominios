import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app import main
from app.events import outbox_event


def _contexto_async(valor):
    contexto = MagicMock()
    contexto.__aenter__ = AsyncMock(return_value=valor)
    contexto.__aexit__ = AsyncMock(return_value=False)
    return contexto


@pytest.mark.asyncio
@pytest.mark.parametrize("hay_eventos", [True, False])
async def test_publicar_pendientes_publica_marca_y_hace_commit(hay_eventos):
    exchange = AsyncMock()
    canal = AsyncMock()
    canal.declare_exchange = AsyncMock(return_value=exchange)
    conexion = AsyncMock()
    conexion.channel = AsyncMock(return_value=canal)
    evento = MagicMock(payload='{"id": 7}', type="CondominioCreado", processed=False)
    sesion = AsyncMock()
    resultado = MagicMock()
    resultado.scalars.return_value.all.return_value = [evento] if hay_eventos else []
    sesion.execute = AsyncMock(return_value=resultado)

    with (
        patch.object(outbox_event.aio_pika, "connect_robust", AsyncMock(return_value=_contexto_async(conexion))),
        patch.object(outbox_event, "fabrica_sesiones", MagicMock(return_value=_contexto_async(sesion))),
        patch.object(outbox_event.asyncio, "sleep", AsyncMock(side_effect=asyncio.CancelledError)),
    ):
        with pytest.raises(asyncio.CancelledError):
            await outbox_event._publicar_pendientes()

    if hay_eventos:
        assert exchange.publish.await_args.kwargs["routing_key"] == "CondominioCreado"
        assert evento.processed is True
        sesion.commit.assert_awaited_once()
    else:
        exchange.publish.assert_not_awaited()
        sesion.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_relay_reintenta_tras_fallo_y_corta_con_cancelacion():
    publicar = AsyncMock(side_effect=[RuntimeError("rabbit caido"), asyncio.CancelledError()])
    dormir = AsyncMock()
    with (
        patch.object(outbox_event, "_publicar_pendientes", publicar),
        patch.object(outbox_event.asyncio, "sleep", dormir),
    ):
        with pytest.raises(asyncio.CancelledError):
            await outbox_event.relay_outbox()
    dormir.assert_awaited_once_with(outbox_event.ESPERA_REINTENTO_SEGUNDOS)
    assert publicar.await_count == 2


async def _tarea_inmediata():
    return None


@pytest.mark.asyncio
@pytest.mark.parametrize("eureka_falla", [False, True])
async def test_lifespan_con_eureka(eureka_falla):
    eureka = MagicMock()
    eureka.init_async = AsyncMock(side_effect=RuntimeError("sin eureka") if eureka_falla else None)
    eureka.stop_async = AsyncMock(side_effect=RuntimeError("ya detenido") if eureka_falla else None)
    with (
        patch.object(main.settings, "eureka_url", "http://eureka"),
        patch.object(main, "eureka_client", eureka),
        patch.object(main, "relay_outbox", _tarea_inmediata),
    ):
        async with main.lifespan(main.app):
            pass
    eureka.init_async.assert_awaited_once()
    eureka.stop_async.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_sin_eureka():
    eureka = MagicMock()
    with (
        patch.object(main.settings, "eureka_url", ""),
        patch.object(main, "eureka_client", eureka),
        patch.object(main, "relay_outbox", _tarea_inmediata),
    ):
        async with main.lifespan(main.app):
            pass
    eureka.init_async.assert_not_called()
