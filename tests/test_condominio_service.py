import pytest

from app.dto.condominio_dto import CondominioCrear
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
