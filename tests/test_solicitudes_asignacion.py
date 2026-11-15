from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.config.database import obtener_sesion
from app.main import app
from app.model.condominio import Condominio
from app.model.solicitud_asignacion import SolicitudAsignacion
from app.model.unidad import Unidad
from app.repository.unidad_repository import UnidadRepository

RESIDENTE = {"X-Usuario-Sub": "usuario-real", "X-Usuario-Roles": "RESIDENTE"}
ADMIN = {"X-Usuario-Sub": "admin", "X-Usuario-Roles": "ADMIN"}


@pytest.fixture
def con_sesion(mock_session):
    async def sesion():
        yield mock_session

    app.dependency_overrides[obtener_sesion] = sesion
    yield mock_session
    app.dependency_overrides.clear()


@pytest.fixture
def buscar_unidad(monkeypatch):
    buscar = AsyncMock(return_value=None)
    monkeypatch.setattr(UnidadRepository, "get_activa_por_direccion", buscar)
    return buscar


def _preparar_creacion(mock_session, tipo: str):
    mock_session.get.return_value = Condominio(id=42, nombre="Parque", direccion="Calle 1", tipo=tipo)
    mock_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

    async def refrescar(solicitud):
        solicitud.id = 1
    mock_session.refresh.side_effect = refrescar


def test_solicitud_vincula_unidad_existente_con_identidad_verificada(con_sesion, buscar_unidad):
    _preparar_creacion(con_sesion, "A")
    buscar_unidad.return_value = Unidad(id=9, condominio_id=42, torre="B", piso="5", numero="504", activa=True)

    with TestClient(app) as client:
        respuesta = client.post(
            "/condominios/solicitudes",
            json={"condominio_id": 42, "torre": " b ", "piso": "5", "numero": "504", "usuario_sub": "falso"},
            headers=RESIDENTE,
        )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "pendiente"
    assert cuerpo["unidad"] == "Torre B · Piso 5 · Unidad 504"
    assert cuerpo["unidad_id"] == 9
    # La busqueda usa los valores normalizados, igual que al crear la unidad.
    assert buscar_unidad.await_args.args == (42, "B", "5", "504")
    solicitud = con_sesion.add.call_args.args[0]
    assert solicitud.usuario_sub == "usuario-real"


def test_solicitud_en_condominio_de_casas_usa_torre_y_piso_fijos(con_sesion, buscar_unidad):
    _preparar_creacion(con_sesion, "B")
    buscar_unidad.return_value = Unidad(id=3, condominio_id=42, torre="UNICA", piso="0", numero="24", activa=True)

    with TestClient(app) as client:
        respuesta = client.post("/condominios/solicitudes", json={"condominio_id": 42, "numero": "24"}, headers=RESIDENTE)

    assert respuesta.status_code == 201
    assert respuesta.json()["unidad"] == "Casa 24"
    assert buscar_unidad.await_args.args == (42, "UNICA", "0", "24")


def test_solicitud_con_unidad_inexistente_da_422(con_sesion, buscar_unidad):
    _preparar_creacion(con_sesion, "A")

    with TestClient(app) as client:
        respuesta = client.post(
            "/condominios/solicitudes", json={"condominio_id": 42, "piso": "9", "numero": "999"}, headers=RESIDENTE
        )

    assert respuesta.status_code == 422
    assert respuesta.json()["message"] == "La unidad no existe en este condominio"
    con_sesion.add.assert_not_called()
    con_sesion.commit.assert_not_awaited()


def test_solicitud_con_torre_en_condominio_de_casas_da_422(con_sesion, buscar_unidad):
    _preparar_creacion(con_sesion, "B")

    with TestClient(app) as client:
        respuesta = client.post(
            "/condominios/solicitudes", json={"condominio_id": 42, "torre": "A", "numero": "24"}, headers=RESIDENTE
        )

    assert respuesta.status_code == 422
    buscar_unidad.assert_not_awaited()


def test_residente_no_puede_aprobar_solicitud():
    with TestClient(app) as client:
        respuesta = client.post("/condominios/solicitudes/1/aprobar", headers=RESIDENTE)
    assert respuesta.status_code == 403


def _solicitud_pendiente(unidad_id: int | None) -> SolicitudAsignacion:
    return SolicitudAsignacion(
        id=7, usuario_sub="residente", condominio_id=42, unidad="Piso 2 · Unidad 201", unidad_id=unidad_id, estado="pendiente"
    )


def test_admin_aprueba_solicitud_con_unidad_activa(con_sesion):
    unidad = Unidad(id=9, condominio_id=42, torre="UNICA", piso="2", numero="201", activa=True)
    con_sesion.get.side_effect = [_solicitud_pendiente(9), unidad]

    with TestClient(app) as client:
        respuesta = client.post("/condominios/solicitudes/7/aprobar", headers=ADMIN)

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "aprobada"
    con_sesion.commit.assert_awaited_once()


@pytest.mark.parametrize(
    ("unidad_id", "unidad"),
    [
        (None, None),  # solicitud anterior a la migracion 0004
        (9, None),
        (9, Unidad(id=9, condominio_id=42, torre="UNICA", piso="2", numero="201", activa=False)),
        (9, Unidad(id=9, condominio_id=77, torre="UNICA", piso="2", numero="201", activa=True)),
    ],
    ids=["sin-unidad-id", "unidad-borrada", "unidad-inactiva", "otro-condominio"],
)
def test_aprobar_revalida_la_unidad(con_sesion, unidad_id, unidad):
    con_sesion.get.side_effect = [_solicitud_pendiente(unidad_id), unidad]

    with TestClient(app) as client:
        respuesta = client.post("/condominios/solicitudes/7/aprobar", headers=ADMIN)

    assert respuesta.status_code == 422
    con_sesion.commit.assert_not_awaited()
