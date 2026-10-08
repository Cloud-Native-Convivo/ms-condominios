import json
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.condominio import Condominio
from app.model.outbox import Outbox
from app.repository.condominio_repository import CondominioRepository


@pytest.mark.asyncio
async def test_create_condominio_con_outbox_transaction():
    mock_session = AsyncMock(spec=AsyncSession)
    repo = CondominioRepository(mock_session)
    
    condominio = Condominio(nombre="Prueba", direccion="Dir", cantidad_sectores=1, plan="basico")

    # Simula la BD: el id recién existe después del flush
    async def mock_flush():
        condominio.id = 7
    mock_session.flush = AsyncMock(side_effect=mock_flush)

    await repo.create(condominio, "CondominioCreado")

    mock_session.flush.assert_called_once()

    # Se debe haber agregado tanto condominio como outbox a la sesion
    assert mock_session.add.call_count == 2
    mock_session.add.assert_any_call(condominio)
    outbox = mock_session.add.call_args_list[1].args[0]
    assert isinstance(outbox, Outbox)
    assert outbox.type == "CondominioCreado"
    # El evento lleva el id asignado en el flush, no un placeholder
    assert outbox.aggregate_id == "7"
    payload = json.loads(outbox.payload)
    assert payload["id"] == 7
    assert payload["nombre"] == "Prueba"
    
    # Se debe hacer un unico commit para evitar escrituras parciales
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once_with(condominio)

@pytest.mark.asyncio
async def test_create_condominio_rollback_on_error():
    mock_session = AsyncMock(spec=AsyncSession)
    repo = CondominioRepository(mock_session)
    
    condominio = Condominio(id=1, nombre="Prueba")
    
    mock_session.commit.side_effect = Exception("Database error")
    
    with pytest.raises(Exception, match="Database error"):
        await repo.create(condominio)
    
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_not_called()
