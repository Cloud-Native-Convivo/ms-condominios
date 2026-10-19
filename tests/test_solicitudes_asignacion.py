from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.config.database import obtener_sesion
from app.main import app
from app.model.condominio import Condominio
from app.model.solicitud_asignacion import SolicitudAsignacion


def test_solicitud_usa_identidad_verificada_y_no_aprueba_automaticamente(mock_session):
    mock_session.get.return_value = Condominio(id=42, nombre="Parque", direccion="Calle 1")
    mock_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)
    async def refrescar(solicitud):
        solicitud.id = 1
    mock_session.refresh.side_effect = refrescar

    async def sesion():
        yield mock_session

    app.dependency_overrides[obtener_sesion] = sesion
    try:
        with TestClient(app) as client:
            respuesta = client.post(
                "/condominios/solicitudes",
                json={"condominio_id": 42, "unidad": "Torre A · Piso 2 · Unidad 201", "usuario_sub": "falso"},
                headers={"X-Usuario-Sub": "usuario-real", "X-Usuario-Roles": "RESIDENTE"},
            )
        assert respuesta.status_code == 201
        assert respuesta.json()["estado"] == "pendiente"
        solicitud = mock_session.add.call_args.args[0]
        assert solicitud.usuario_sub == "usuario-real"
        assert solicitud.condominio_id == 42
    finally:
        app.dependency_overrides.clear()


def test_residente_no_puede_aprobar_solicitud():
    with TestClient(app) as client:
        respuesta = client.post(
            "/condominios/solicitudes/1/aprobar",
            headers={"X-Usuario-Sub": "residente", "X-Usuario-Roles": "RESIDENTE"},
        )
    assert respuesta.status_code == 403


def test_admin_aprueba_solicitud_pendiente(mock_session):
    solicitud = SolicitudAsignacion(id=7, usuario_sub="residente", condominio_id=42, unidad="201", estado="pendiente")
    mock_session.get.return_value = solicitud

    async def sesion():
        yield mock_session

    app.dependency_overrides[obtener_sesion] = sesion
    try:
        with TestClient(app) as client:
            respuesta = client.post(
                "/condominios/solicitudes/7/aprobar",
                headers={"X-Usuario-Sub": "admin", "X-Usuario-Roles": "ADMIN"},
            )
        assert respuesta.status_code == 200
        assert respuesta.json()["estado"] == "aprobada"
        mock_session.commit.assert_awaited_once()
    finally:
        app.dependency_overrides.clear()
