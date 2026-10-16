from app.dto.unidad_dto import UnidadRespuesta
from app.exception.condominio_exception import CondominioNoEncontradoException
from app.exception.unidad_exception import (
    UnidadDuplicadaException,
    UnidadNoEncontradaException,
)


def test_listar_unidades_requiere_admin(client_unidad, mock_unidad_service):
    response = client_unidad.get("/condominios/1/unidades/", headers={"X-Usuario-Roles": "RESIDENTE"})
    assert response.status_code == 403
    mock_unidad_service.listar_unidades.assert_not_called()

def test_listar_unidades_con_admin_exitoso(client_unidad, mock_unidad_service):
    mock_unidad_service.listar_unidades.return_value = [
        UnidadRespuesta(id=1, condominio_id=1, torre="UNICA", piso="1", numero="101", activa=True)
    ]
    response = client_unidad.get("/condominios/1/unidades/", headers={"X-Usuario-Roles": "ADMIN"})
    assert response.status_code == 200
    assert response.json()[0]["numero"] == "101"
    mock_unidad_service.listar_unidades.assert_called_once_with(1, incluir_inactivas=False)

def test_listar_unidades_puede_pedir_incluir_inactivas(client_unidad, mock_unidad_service):
    mock_unidad_service.listar_unidades.return_value = []
    response = client_unidad.get(
        "/condominios/1/unidades/?incluir_inactivas=true", headers={"X-Usuario-Roles": "ADMIN"}
    )
    assert response.status_code == 200
    mock_unidad_service.listar_unidades.assert_called_once_with(1, incluir_inactivas=True)

def test_crear_unidad_con_condominio_inexistente_da_404(client_unidad, mock_unidad_service):
    mock_unidad_service.crear_unidad.side_effect = CondominioNoEncontradoException(99)
    response = client_unidad.post(
        "/condominios/99/unidades/", json={"piso": "1", "numero": "1"}, headers={"X-Usuario-Roles": "ADMIN"}
    )
    assert response.status_code == 404

def test_crear_unidad_duplicada_da_409(client_unidad, mock_unidad_service):
    mock_unidad_service.crear_unidad.side_effect = UnidadDuplicadaException(1, "A", "1", "101")
    response = client_unidad.post(
        "/condominios/1/unidades/", json={"torre": "A", "piso": "1", "numero": "101"},
        headers={"X-Usuario-Roles": "ADMIN"},
    )
    assert response.status_code == 409

def test_crear_unidad_con_piso_vacio_da_422(client_unidad, mock_unidad_service):
    response = client_unidad.post(
        "/condominios/1/unidades/", json={"piso": "   ", "numero": "1"}, headers={"X-Usuario-Roles": "ADMIN"}
    )
    assert response.status_code == 422
    mock_unidad_service.crear_unidad.assert_not_called()

def test_obtener_unidad_de_otro_condominio_da_404(client_unidad, mock_unidad_service):
    mock_unidad_service.obtener_unidad.side_effect = UnidadNoEncontradaException(5)
    response = client_unidad.get("/condominios/1/unidades/5", headers={"X-Usuario-Roles": "ADMIN"})
    assert response.status_code == 404

def test_eliminar_unidad_requiere_admin_y_responde_204(client_unidad, mock_unidad_service):
    response = client_unidad.delete("/condominios/1/unidades/1", headers={"X-Usuario-Roles": "ADMIN"})
    assert response.status_code == 204
    mock_unidad_service.eliminar_unidad.assert_called_once_with(1, 1)
