import pytest

from app.dto.condominio_dto import CondominioActualizar, CondominioCrear
from app.exception.condominio_exception import CondominioNoEncontradoException
from app.model.condominio import Condominio
from app.service.condominio_service import CondominioService


@pytest.mark.asyncio
async def test_crear_condominio_emits_outbox_event(mock_repo):
    service = CondominioService(mock_repo)
    dto = CondominioCrear(nombre="Condominio A", direccion="Calle 123", cantidad_sectores=2, plan="basico")

    mock_condominio = Condominio(id=1, nombre="Condominio A", direccion="Calle 123", cantidad_sectores=2, plan="basico")
    mock_repo.create.return_value = mock_condominio

    resultado = await service.crear_condominio(dto)

    assert resultado.id == 1
    mock_repo.create.assert_called_once()

    condominio_arg, tipo_evento = mock_repo.create.call_args.args

    assert isinstance(condominio_arg, Condominio)
    assert condominio_arg.nombre == "Condominio A"
    assert condominio_arg.cantidad_sectores == 2
    assert tipo_evento == "CondominioCreado"


@pytest.mark.asyncio
async def test_actualizar_condominio_aplica_solo_campos_enviados(mock_repo):
    service = CondominioService(mock_repo)
    condominio = Condominio(id=1, nombre="Viejo", direccion="Calle 123", cantidad_sectores=2, plan="basico")
    mock_repo.get_by_id.return_value = condominio
    mock_repo.actualizar.return_value = condominio

    resultado = await service.actualizar_condominio(1, CondominioActualizar(nombre="Nuevo"))

    assert resultado.nombre == "Nuevo"
    assert resultado.direccion == "Calle 123"  # no enviado, no cambia
    condominio_arg, tipo_evento = mock_repo.actualizar.call_args.args
    assert condominio_arg is condominio
    assert tipo_evento == "CondominioActualizado"


@pytest.mark.asyncio
async def test_actualizar_condominio_inexistente_lanza_excepcion(mock_repo):
    mock_repo.get_by_id.return_value = None
    service = CondominioService(mock_repo)

    with pytest.raises(CondominioNoEncontradoException):
        await service.actualizar_condominio(99, CondominioActualizar(nombre="Nuevo"))

    mock_repo.actualizar.assert_not_called()


@pytest.mark.asyncio
async def test_eliminar_condominio_delega_al_repositorio(mock_repo):
    condominio = Condominio(id=1, nombre="A borrar", direccion="Dir")
    mock_repo.get_by_id.return_value = condominio
    service = CondominioService(mock_repo)

    await service.eliminar_condominio(1)

    mock_repo.eliminar.assert_called_once_with(condominio, "CondominioEliminado")


@pytest.mark.asyncio
async def test_eliminar_condominio_inexistente_lanza_excepcion(mock_repo):
    mock_repo.get_by_id.return_value = None
    service = CondominioService(mock_repo)

    with pytest.raises(CondominioNoEncontradoException):
        await service.eliminar_condominio(99)

    mock_repo.eliminar.assert_not_called()
