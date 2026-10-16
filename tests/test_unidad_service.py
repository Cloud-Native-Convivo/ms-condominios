import pytest

from app.dto.unidad_dto import UnidadActualizar, UnidadCrear
from app.exception.condominio_exception import CondominioNoEncontradoException
from app.exception.unidad_exception import UnidadNoEncontradaException
from app.model.unidad import Unidad
from app.service.unidad_service import UnidadService


@pytest.mark.asyncio
async def test_crear_unidad_valida_que_el_condominio_exista(mock_unidad_repo, mock_condominio_service):
    mock_condominio_service.obtener_condominio.side_effect = CondominioNoEncontradoException(99)
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    with pytest.raises(CondominioNoEncontradoException):
        await service.crear_unidad(99, UnidadCrear(piso="1", numero="1"))

    mock_unidad_repo.create.assert_not_called()

@pytest.mark.asyncio
async def test_crear_unidad_exitosa(mock_unidad_repo, mock_condominio_service):
    mock_unidad_repo.create.return_value = Unidad(id=1, condominio_id=1, torre="UNICA", piso="1", numero="1")
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    resultado = await service.crear_unidad(1, UnidadCrear(piso="1", numero="1"))

    assert resultado.id == 1
    mock_condominio_service.obtener_condominio.assert_called_once_with(1)

@pytest.mark.asyncio
async def test_listar_unidades_valida_que_el_condominio_exista(mock_unidad_repo, mock_condominio_service):
    mock_condominio_service.obtener_condominio.side_effect = CondominioNoEncontradoException(99)
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    with pytest.raises(CondominioNoEncontradoException):
        await service.listar_unidades(99)

    mock_unidad_repo.get_by_condominio.assert_not_called()

@pytest.mark.asyncio
async def test_listar_unidades_delega_al_repositorio(mock_unidad_repo, mock_condominio_service):
    unidad = Unidad(id=1, condominio_id=1, torre="UNICA", piso="1", numero="1")
    mock_unidad_repo.get_by_condominio.return_value = [unidad]
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    resultado = await service.listar_unidades(1)

    assert resultado == [unidad]
    mock_condominio_service.obtener_condominio.assert_called_once_with(1)
    mock_unidad_repo.get_by_condominio.assert_called_once_with(1, incluir_inactivas=False)

@pytest.mark.asyncio
async def test_listar_unidades_puede_incluir_inactivas(mock_unidad_repo, mock_condominio_service):
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    await service.listar_unidades(1, incluir_inactivas=True)

    mock_unidad_repo.get_by_condominio.assert_called_once_with(1, incluir_inactivas=True)

@pytest.mark.asyncio
async def test_obtener_unidad_de_otro_condominio_lanza_no_encontrada(mock_unidad_repo, mock_condominio_service):
    mock_unidad_repo.get_by_id_y_condominio.return_value = None
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    with pytest.raises(UnidadNoEncontradaException):
        await service.obtener_unidad(5, condominio_id=1)

@pytest.mark.asyncio
async def test_eliminar_unidad_es_logico_no_fisico(mock_unidad_repo, mock_condominio_service):
    unidad = Unidad(id=1, condominio_id=1, torre="UNICA", piso="1", numero="1", activa=True)
    mock_unidad_repo.get_by_id_y_condominio.return_value = unidad
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    await service.eliminar_unidad(1, condominio_id=1)

    assert unidad.activa is False
    mock_unidad_repo.actualizar.assert_called_once_with(unidad)

@pytest.mark.asyncio
async def test_actualizar_unidad_de_otro_condominio_lanza_no_encontrada(mock_unidad_repo, mock_condominio_service):
    mock_unidad_repo.get_by_id_y_condominio.return_value = None
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    with pytest.raises(UnidadNoEncontradaException):
        await service.actualizar_unidad(5, condominio_id=1, dto=UnidadActualizar(numero="999"))

    mock_unidad_repo.actualizar.assert_not_called()

@pytest.mark.asyncio
async def test_eliminar_unidad_de_otro_condominio_lanza_no_encontrada(mock_unidad_repo, mock_condominio_service):
    mock_unidad_repo.get_by_id_y_condominio.return_value = None
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    with pytest.raises(UnidadNoEncontradaException):
        await service.eliminar_unidad(5, condominio_id=1)

    mock_unidad_repo.actualizar.assert_not_called()

@pytest.mark.asyncio
async def test_actualizar_unidad_aplica_solo_campos_enviados(mock_unidad_repo, mock_condominio_service):
    unidad = Unidad(id=1, condominio_id=1, torre="UNICA", piso="1", numero="1")
    mock_unidad_repo.get_by_id_y_condominio.return_value = unidad
    mock_unidad_repo.actualizar.return_value = unidad
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    resultado = await service.actualizar_unidad(1, 1, UnidadActualizar(numero="205"))

    assert resultado.numero == "205"
    assert resultado.piso == "1"  # no enviado, no cambia

@pytest.mark.asyncio
async def test_actualizar_con_null_explicito_no_lo_aplica(mock_unidad_repo, mock_condominio_service):
    unidad = Unidad(id=1, condominio_id=1, torre="UNICA", piso="1", numero="1")
    mock_unidad_repo.get_by_id_y_condominio.return_value = unidad
    mock_unidad_repo.actualizar.return_value = unidad
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    resultado = await service.actualizar_unidad(1, 1, UnidadActualizar(piso=None))

    # piso es NOT NULL en Oracle: un null explicito no debe intentar aplicarse
    # (eso rompia con 500 por violacion de NOT NULL, ORA-01407).
    assert resultado.piso == "1"

@pytest.mark.asyncio
async def test_reactivar_unidad_via_actualizar(mock_unidad_repo, mock_condominio_service):
    unidad = Unidad(id=1, condominio_id=1, torre="UNICA", piso="1", numero="1", activa=False)
    mock_unidad_repo.get_by_id_y_condominio.return_value = unidad
    mock_unidad_repo.actualizar.return_value = unidad
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    resultado = await service.actualizar_unidad(1, 1, UnidadActualizar(activa=True))

    assert resultado.activa is True
