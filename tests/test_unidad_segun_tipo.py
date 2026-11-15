import pytest

from app.dto.condominio_dto import CondominioActualizar
from app.dto.unidad_dto import UnidadActualizar, UnidadCrear
from app.exception.condominio_exception import CondominioConUnidadesException
from app.exception.unidad_exception import UnidadIncompatibleConTipoException
from app.model.condominio import Condominio
from app.model.unidad import Unidad
from app.service.condominio_service import CondominioService
from app.service.unidad_service import (
    UnidadService,
    describir_unidad,
    normalizar_segun_tipo,
)


@pytest.mark.parametrize(
    ("tipo", "torre", "piso", "esperado"),
    [
        ("B", "UNICA", None, ("UNICA", "0")),
        ("B", "UNICA", "0", ("UNICA", "0")),
        ("A", "UNICA", "3", ("UNICA", "3")),
        ("A", "B", "5", ("B", "5")),
    ],
)
def test_normalizar_segun_tipo_acepta(tipo, torre, piso, esperado):
    assert normalizar_segun_tipo(tipo, torre, piso) == esperado


@pytest.mark.parametrize(
    ("tipo", "torre", "piso"),
    [("B", "A", None), ("B", "UNICA", "2"), ("A", "UNICA", None), ("A", "B", "")],
    ids=["casa-con-torre", "casa-con-piso", "depto-sin-piso", "depto-piso-vacio"],
)
def test_normalizar_segun_tipo_rechaza(tipo, torre, piso):
    with pytest.raises(UnidadIncompatibleConTipoException):
        normalizar_segun_tipo(tipo, torre, piso)


def test_describir_unidad():
    assert describir_unidad("B", "UNICA", "0", "24") == "Casa 24"
    assert describir_unidad("A", "UNICA", "5", "504") == "Piso 5 · Unidad 504"
    assert describir_unidad("A", "B", "5", "504") == "Torre B · Piso 5 · Unidad 504"


@pytest.mark.asyncio
async def test_crear_casa_fija_torre_y_piso(mock_unidad_repo, mock_condominio_service):
    mock_condominio_service.obtener_condominio.return_value = Condominio(id=1, tipo="B")
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    await service.crear_unidad(1, UnidadCrear(numero="24"))

    unidad = mock_unidad_repo.create.call_args.args[0]
    assert (unidad.torre, unidad.piso, unidad.numero) == ("UNICA", "0", "24")


@pytest.mark.asyncio
async def test_crear_depto_sin_piso_no_persiste(mock_unidad_repo, mock_condominio_service):
    mock_condominio_service.obtener_condominio.return_value = Condominio(id=1, tipo="A")
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    with pytest.raises(UnidadIncompatibleConTipoException):
        await service.crear_unidad(1, UnidadCrear(torre="A", numero="101"))

    mock_unidad_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_actualizar_casa_con_piso_se_rechaza_sobre_valores_fusionados(mock_unidad_repo, mock_condominio_service):
    mock_condominio_service.obtener_condominio.return_value = Condominio(id=1, tipo="B")
    mock_unidad_repo.get_by_id_y_condominio.return_value = Unidad(id=1, condominio_id=1, torre="UNICA", piso="0", numero="24")
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    with pytest.raises(UnidadIncompatibleConTipoException):
        await service.actualizar_unidad(1, 1, UnidadActualizar(piso="3"))

    mock_unidad_repo.actualizar.assert_not_called()


@pytest.mark.asyncio
async def test_actualizar_parcial_conserva_piso_de_la_fila(mock_unidad_repo, mock_condominio_service):
    mock_condominio_service.obtener_condominio.return_value = Condominio(id=1, tipo="A")
    unidad = Unidad(id=1, condominio_id=1, torre="A", piso="2", numero="201")
    mock_unidad_repo.get_by_id_y_condominio.return_value = unidad
    mock_unidad_repo.actualizar.return_value = unidad
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    resultado = await service.actualizar_unidad(1, 1, UnidadActualizar(numero="202"))

    assert (resultado.torre, resultado.piso, resultado.numero) == ("A", "2", "202")


@pytest.mark.asyncio
async def test_cambiar_tipo_con_unidades_se_bloquea(mock_repo):
    mock_repo.get_by_id.return_value = Condominio(id=1, nombre="C", direccion="D", tipo="A")
    mock_repo.tiene_unidades.return_value = True
    service = CondominioService(mock_repo)

    with pytest.raises(CondominioConUnidadesException):
        await service.actualizar_condominio(1, CondominioActualizar(tipo="B"))

    mock_repo.actualizar.assert_not_called()


@pytest.mark.asyncio
async def test_cambiar_tipo_sin_unidades_se_permite(mock_repo):
    condominio = Condominio(id=1, nombre="C", direccion="D", tipo="A")
    mock_repo.get_by_id.return_value = condominio
    mock_repo.tiene_unidades.return_value = False
    mock_repo.actualizar.return_value = condominio
    service = CondominioService(mock_repo)

    resultado = await service.actualizar_condominio(1, CondominioActualizar(tipo="B"))

    assert resultado.tipo == "B"


@pytest.mark.asyncio
async def test_reenviar_el_mismo_tipo_no_consulta_unidades(mock_repo):
    condominio = Condominio(id=1, nombre="C", direccion="D", tipo="A")
    mock_repo.get_by_id.return_value = condominio
    mock_repo.actualizar.return_value = condominio
    service = CondominioService(mock_repo)

    await service.actualizar_condominio(1, CondominioActualizar(tipo="A", nombre="Nuevo"))

    mock_repo.tiene_unidades.assert_not_called()


def test_put_condominio_con_unidades_responde_409(client, mock_service):
    mock_service.actualizar_condominio.side_effect = CondominioConUnidadesException(1)

    respuesta = client.put("/condominios/1", json={"tipo": "B"}, headers={"X-Usuario-Roles": "ADMIN"})

    assert respuesta.status_code == 409


def test_post_unidad_incompatible_con_tipo_responde_422(client_unidad, mock_unidad_service):
    mock_unidad_service.crear_unidad.side_effect = UnidadIncompatibleConTipoException("sin piso")

    respuesta = client_unidad.post(
        "/condominios/1/unidades/", json={"numero": "101"}, headers={"X-Usuario-Roles": "ADMIN"}
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["message"] == "sin piso"
