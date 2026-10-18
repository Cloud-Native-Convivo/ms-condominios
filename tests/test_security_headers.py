from app.dto.condominio_dto import CondominioRespuesta


def test_cabeceras_de_seguridad_completas(client):
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains; preload"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert resp.headers.get("server") == "convivo"
    assert "Content-Security-Policy" in resp.headers

def test_csp_estricto_en_api_condominios(client, mock_service):
    mock_service.obtener_condominio.return_value = CondominioRespuesta(
        id=1, nombre="Prueba", direccion="Dir", cantidad_sectores=1, plan="basico"
    )
    resp = client.get("/condominios/1", headers={"X-Usuario-Roles": "RESIDENTE"})
    assert resp.status_code == 200
    assert resp.headers.get("Content-Security-Policy") == "default-src 'self'"
    assert resp.headers.get("server") == "convivo"
