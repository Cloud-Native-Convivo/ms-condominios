from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.exception.unidad_exception import UnidadDuplicadaException
from app.model.unidad import Unidad
from app.repository.unidad_repository import UnidadRepository


def _integrity_error(mensaje_oracle: str) -> IntegrityError:
    return IntegrityError("stmt", {}, Exception(mensaje_oracle))


@pytest.mark.asyncio
async def test_get_by_condominio_filtra_solo_activas_por_defecto(mock_session):
    unidad_activa = Unidad(id=1, condominio_id=5, torre="A", piso="1", numero="1", activa=True)
    resultado = MagicMock()
    resultado.scalars.return_value.all.return_value = [unidad_activa]
    mock_session.execute = AsyncMock(return_value=resultado)
    repo = UnidadRepository(mock_session)

    unidades = await repo.get_by_condominio(5)

    assert unidades == [unidad_activa]
    mock_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_by_condominio_incluir_inactivas_omite_el_filtro(mock_session):
    resultado = MagicMock()
    resultado.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=resultado)
    repo = UnidadRepository(mock_session)

    await repo.get_by_condominio(5, incluir_inactivas=True)

    stmt_ejecutado = mock_session.execute.call_args.args[0]
    # Sin incluir_inactivas=True el stmt tendria 2 clausulas WHERE (condominio_id Y activa);
    # con incluir_inactivas=True solo se agrega la de condominio_id.
    assert len(stmt_ejecutado._where_criteria) == 1

@pytest.mark.asyncio
async def test_get_by_id_y_condominio_filtra_por_ambos(mock_session):
    resultado = MagicMock()
    resultado.scalars.return_value.first.return_value = None
    mock_session.execute = AsyncMock(return_value=resultado)
    repo = UnidadRepository(mock_session)

    await repo.get_by_id_y_condominio(1, 5)

    mock_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_create_persiste_y_hace_flush(mock_session):
    repo = UnidadRepository(mock_session)
    unidad = Unidad(condominio_id=1, torre="A", piso="1", numero="101")

    resultado = await repo.create(unidad)

    mock_session.add.assert_called_once_with(unidad)
    mock_session.flush.assert_awaited_once()
    mock_session.commit.assert_awaited_once()
    assert resultado is unidad

@pytest.mark.asyncio
async def test_create_traduce_violacion_de_unicidad_oracle_a_excepcion_de_dominio(mock_session):
    unidad = Unidad(condominio_id=1, torre="A", piso="1", numero="101")
    mock_session.flush.side_effect = _integrity_error(
        "ORA-00001: unique constraint (CONVIVO.UQ_UNIDAD_DIRECCION) violated"
    )
    repo = UnidadRepository(mock_session)

    with pytest.raises(UnidadDuplicadaException):
        await repo.create(unidad)

    mock_session.rollback.assert_awaited_once()

@pytest.mark.asyncio
async def test_create_propaga_otros_integrity_error_sin_traducir(mock_session):
    unidad = Unidad(condominio_id=1, torre="A", piso="1", numero="101")
    mock_session.flush.side_effect = _integrity_error(
        "ORA-02291: integrity constraint violated - parent key not found"
    )
    repo = UnidadRepository(mock_session)

    with pytest.raises(IntegrityError):
        await repo.create(unidad)

    mock_session.rollback.assert_awaited_once()

@pytest.mark.asyncio
async def test_actualizar_persiste_y_refresca(mock_session):
    unidad = Unidad(id=1, condominio_id=1, torre="A", piso="1", numero="101")
    repo = UnidadRepository(mock_session)

    resultado = await repo.actualizar(unidad)

    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(unidad)
    assert resultado is unidad

@pytest.mark.asyncio
async def test_actualizar_traduce_violacion_de_unicidad_oracle(mock_session):
    unidad = Unidad(id=1, condominio_id=1, torre="A", piso="1", numero="101")
    mock_session.commit.side_effect = _integrity_error(
        "ORA-00001: unique constraint (CONVIVO.UQ_UNIDAD_DIRECCION) violated"
    )
    repo = UnidadRepository(mock_session)

    with pytest.raises(UnidadDuplicadaException):
        await repo.actualizar(unidad)

    mock_session.rollback.assert_awaited_once()

@pytest.mark.asyncio
async def test_actualizar_propaga_otros_integrity_error_sin_traducir(mock_session):
    unidad = Unidad(id=1, condominio_id=1, torre="A", piso="1", numero="101")
    mock_session.commit.side_effect = _integrity_error(
        "ORA-02291: integrity constraint violated - parent key not found"
    )
    repo = UnidadRepository(mock_session)

    with pytest.raises(IntegrityError):
        await repo.actualizar(unidad)

    mock_session.rollback.assert_awaited_once()

@pytest.mark.asyncio
async def test_actualizar_duplicado_usa_valores_capturados_antes_del_rollback(mock_session):
    # SQLAlchemy real expira los atributos del objeto tras rollback() (incluso con
    # expire_on_commit=False); leerlos despues de eso en un AsyncSession dispara
    # IO y revienta con MissingGreenlet. El repo debe capturar los valores ANTES
    # de intentar el commit, no leerlos del objeto despues del rollback.
    unidad = Unidad(id=1, condominio_id=1, torre="A", piso="1", numero="101")
    mock_session.commit.side_effect = _integrity_error(
        "ORA-00001: unique constraint (CONVIVO.UQ_UNIDAD_DIRECCION) violated"
    )

    async def rollback_que_expira():
        # Simula la expiracion real: el objeto queda sin los valores que tenia.
        unidad.torre = None
        unidad.piso = None
        unidad.numero = None
    mock_session.rollback = AsyncMock(side_effect=rollback_que_expira)

    repo = UnidadRepository(mock_session)

    with pytest.raises(UnidadDuplicadaException) as error:
        await repo.actualizar(unidad)

    assert "A-1-101" in str(error.value)
