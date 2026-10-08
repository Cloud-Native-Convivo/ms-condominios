import pytest

from app.dto.condominio_dto import CondominioRespuesta


def test_crear_condominio_requiere_rol_admin(client, mock_service):
    # Sin el rol ADMIN debería fallar por protección de roles
    response = client.post("/condominios/", json={
        "nombre": "Prueba", "direccion": "Dir", "cantidad_sectores": 1, "plan": "basico"
    }, headers={"X-Usuario-Roles": "RESIDENTE"})
    
    assert response.status_code == 403
    assert response.json() == {"detail": "Permisos insuficientes"}

def test_crear_condominio_con_rol_admin_exitoso(client, mock_service):
    # Con el rol ADMIN debe inyectar dependencias y tener éxito
    mock_service.crear_condominio.return_value = CondominioRespuesta(
        id=1, nombre="Prueba", direccion="Dir", cantidad_sectores=1, plan="basico"
    )
    
    response = client.post("/condominios/", json={
        "nombre": "Prueba", "direccion": "Dir", "cantidad_sectores": 1, "plan": "basico"
    }, headers={"X-Usuario-Roles": "ADMIN"})
    
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["nombre"] == "Prueba"
    mock_service.crear_condominio.assert_called_once()

def test_obtener_condominios_permite_residente(client, mock_service):
    mock_service.obtener_condominio.return_value = CondominioRespuesta(
        id=1, nombre="Prueba", direccion="Dir", cantidad_sectores=1, plan="basico"
    )
    
    # El endpoint GET /{id} requiere ADMIN o RESIDENTE
    response = client.get("/condominios/1", headers={"X-Usuario-Roles": "RESIDENTE"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    mock_service.obtener_condominio.assert_called_once_with(1)

@pytest.mark.parametrize("cambio", [
    {"nombre": ""},
    {"nombre": "x" * 256},
    {"tipo": "AB"},
    {"cantidad_sectores": 0},
])
def test_crear_condominio_rechaza_entrada_invalida_con_422(client, mock_service, cambio):
    cuerpo = {"nombre": "Prueba", "direccion": "Dir"} | cambio
    response = client.post("/condominios/", json=cuerpo, headers={"X-Usuario-Roles": "ADMIN"})

    assert response.status_code == 422
    mock_service.crear_condominio.assert_not_called()

def test_respuestas_llevan_headers_de_seguridad_y_sin_cors(client, mock_service):
    mock_service.obtener_condominio.return_value = CondominioRespuesta(id=1, nombre="Prueba", direccion="Dir")

    response = client.get("/condominios/1", headers={"X-Usuario-Roles": "ADMIN", "Origin": "https://evil.example"})

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-XSS-Protection"] == "0"
    assert "access-control-allow-origin" not in response.headers
