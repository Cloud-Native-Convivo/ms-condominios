from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.condominio_router import get_condominio_service
from app.config import database
from app.exception.condominio_exception import CondominioNoEncontradoException
from app.handler.exception_handler import condominio_no_encontrado_handler
from app.model.condominio import Condominio
from app.repository.condominio_repository import CondominioRepository
from app.service.condominio_service import CondominioService


@pytest.mark.asyncio
async def test_servicio_lista_y_obtiene(mock_repo):
    condominio = Condominio(id=1, nombre="A", direccion="B")
    mock_repo.get_all.return_value = [condominio]
    mock_repo.get_by_id.return_value = condominio
    servicio = CondominioService(mock_repo)
    assert await servicio.listar_condominios() == [condominio]
    assert await servicio.obtener_condominio(1) is condominio


@pytest.mark.asyncio
async def test_servicio_condominio_inexistente_lanza_excepcion(mock_repo):
    mock_repo.get_by_id.return_value = None
    servicio = CondominioService(mock_repo)
    with pytest.raises(CondominioNoEncontradoException) as error:
        await servicio.obtener_condominio(99)
    assert error.value.id_condominio == 99
    assert "99" in str(error.value)


def test_handler_responde_404_con_mensaje():
    respuesta = condominio_no_encontrado_handler(MagicMock(), CondominioNoEncontradoException(5))
    assert respuesta.status_code == 404
    assert b"Condominio 5 no encontrado" in respuesta.body


@pytest.mark.asyncio
async def test_repositorio_consultas(mock_session):
    condominio = Condominio(id=3, nombre="C", direccion="D")
    resultado = MagicMock()
    resultado.scalars.return_value.all.return_value = [condominio]
    resultado.scalars.return_value.first.return_value = condominio
    mock_session.execute = AsyncMock(return_value=resultado)
    repo = CondominioRepository(mock_session)
    assert await repo.get_all() == [condominio]
    assert await repo.get_by_id(3) is condominio
    assert mock_session.execute.await_count == 2


def test_dependencia_arma_servicio_con_repositorio(mock_session):
    servicio = get_condominio_service(mock_session)
    assert isinstance(servicio, CondominioService)
    assert servicio.repository.session is mock_session


@pytest.mark.asyncio
async def test_obtener_sesion_entrega_y_cierra_sesion():
    sesion = AsyncMock()
    contexto = MagicMock()
    contexto.__aenter__ = AsyncMock(return_value=sesion)
    contexto.__aexit__ = AsyncMock(return_value=False)
    with patch.object(database, "fabrica_sesiones", MagicMock(return_value=contexto)):
        generador = database.obtener_sesion()
        assert await generador.__anext__() is sesion
        with pytest.raises(StopAsyncIteration):
            await generador.__anext__()
    contexto.__aexit__.assert_awaited_once()
