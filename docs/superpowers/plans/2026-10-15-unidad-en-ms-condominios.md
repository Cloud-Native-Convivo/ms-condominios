# Unidad en ms-condominios Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** agregar el recurso `Unidad` como sub-recurso de `Condominio` en `ms-condominios` (modelo, migración, DTOs, repositorio, servicio, router, tests), sin tocar ningún otro microservicio.

**Architecture:** mismo patrón Router→Service→Repository que `Condominio`. `UnidadService` depende de `CondominioService` para validar que el condominio padre existe. Borrado lógico (`activa`), sin eventos Outbox, autorización ADMIN-only en los 5 endpoints.

**Tech Stack:** FastAPI 0.115+, SQLAlchemy 2.0 async, Oracle Database Free 23ai (oracledb thin), Alembic, Pydantic v2, pytest + pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-10-15-unidad-en-ms-condominios-design.md`

## Global Constraints

- Todo en español (funciones, variables, archivos, mensajes de error) — excepto los métodos de repositorio en inglés (`get_by_id`, `create`), convención existente que se replica en `UnidadRepository` sin mezclar estilos.
- Sin eventos Outbox para `Unidad`. No tocar `app/model/outbox.py`, `app/events/outbox_event.py` ni `CondominioRepository`.
- Sin cambios en `ms-gastos-comunes`, `ms-espacios-comunes`, BFF ni frontends.
- Sin cambios al mecanismo de autorización (`app/middleware/auth_roles.py`) — el riesgo de suplantación vía header `X-Usuario-Roles` es heredado y queda documentado en el spec (sección 3), no corregido acá.
- Cobertura de ramas ≥80% en la lógica nueva (convención `AGENTS.md` §7), `ruff check .` limpio.
- Normalización: solo `torre` tiene valor por defecto (`"UNICA"`). `piso`/`numero` vacíos se rechazan con 422, nunca caen a un default.
- `IntegrityError` se traduce a `UnidadDuplicadaException` únicamente cuando el mensaje contiene `"ORA-00001"` (unique constraint de Oracle); cualquier otro `IntegrityError` se re-lanza sin traducir.

## Review Focus

1. `piso`/`numero` vacíos o solo espacios → 422, nunca `"UNICA"` ni ningún otro valor por defecto (a diferencia de `torre`).
2. Crear una unidad bajo un `id_condominio` inexistente → 404 del condominio, no 500 por FK rota.
3. `GET`/`PUT`/`DELETE /unidades/{id_unidad}` con una unidad que existe pero pertenece a OTRO condominio → 404, nunca confirma su existencia ahí.
4. Un `IntegrityError` que NO es por unique constraint (ej. FK rota, `ORA-02291`) → se propaga tal cual, nunca se disfraza de `UnidadDuplicadaException` (409 falso).
5. Reactivar (`PUT activa=true`) una unidad desactivada cuya dirección ya no choca con nada activo → debe funcionar; crear una unidad nueva con la misma dirección mientras la vieja sigue inactiva → debe fallar con 409 (limitación aceptada, documentada en el spec §4).

---

### Task 1: Modelo `Unidad` + migración Alembic + registro en `env.py`

**Files:**
- Create: `app/model/unidad.py`
- Create: `alembic/versions/0002_unidad.py`
- Modify: `alembic/env.py` (agregar `import app.model.unidad` junto a las líneas 24-25 existentes)

**Interfaces:**
- Produce: clase `Unidad` con columnas `id, condominio_id, torre, piso, numero, activa`.

- [ ] **Paso 1 — Escribir el modelo**

```python
# app/model/unidad.py
from sqlalchemy import Boolean, Column, ForeignKey, Identity, Index, Integer, String, UniqueConstraint

from app.config.database import Base


class Unidad(Base):
    __tablename__ = "unidades"
    __table_args__ = (
        Index("ix_unidades_condominio_id", "condominio_id"),
        UniqueConstraint("condominio_id", "torre", "piso", "numero", name="uq_unidad_direccion"),
    )

    id = Column(Integer, Identity(), primary_key=True)
    condominio_id = Column(Integer, ForeignKey("condominios.id", ondelete="CASCADE"), nullable=False)
    torre = Column(String(50), nullable=False, default="UNICA")
    piso = Column(String(10), nullable=False)
    numero = Column(String(20), nullable=False)
    activa = Column(Boolean, nullable=False, default=True)
```

- [ ] **Paso 2 — Escribir la migración**

```python
# alembic/versions/0002_unidad.py
"""agrega tabla unidades

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-15

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "unidades",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("condominio_id", sa.Integer(), sa.ForeignKey("condominios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("torre", sa.String(50), nullable=False, server_default="UNICA"),
        sa.Column("piso", sa.String(10), nullable=False),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_unidades_condominio_id", "unidades", ["condominio_id"])
    op.create_unique_constraint("uq_unidad_direccion", "unidades", ["condominio_id", "torre", "piso", "numero"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_unidad_direccion", "unidades", type_="unique")
    op.drop_index("ix_unidades_condominio_id", table_name="unidades")
    op.drop_table("unidades")
```

- [ ] **Paso 3 — Registrar el modelo en `alembic/env.py`**

```python
# alembic/env.py — agregar junto a las líneas 24-25 existentes
import app.model.condominio
import app.model.outbox
import app.model.unidad  # noqa: necesario para que Base.metadata conozca la tabla en autogenerate
```

- [ ] **Paso 4 — Verificar que la migración aplica en limpio (requiere Oracle corriendo)**

```bash
docker compose up -d oracle-condominios
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```
Criterio de aceptación: los tres comandos corren sin error; `alembic downgrade -1` seguido de `upgrade head` deja el esquema idéntico (verificable con `alembic current` mostrando `0002`).

- [ ] **Paso 5 — Commit**

```bash
git add app/model/unidad.py alembic/versions/0002_unidad.py alembic/env.py
git commit -m ":sparkles: feat(condominios): agrega modelo y migracion de Unidad"
```

---

### Task 2: Excepciones y handlers

**Files:**
- Create: `app/exception/unidad_exception.py`
- Modify: `app/handler/exception_handler.py`

**Interfaces:**
- Produce: `UnidadNoEncontradaException(id_unidad)`, `UnidadDuplicadaException(condominio_id, torre, piso, numero)`.
- Consumido por: `UnidadRepository`/`UnidadService` (Tasks 4-5), registrado en `app/main.py` (Task 6).

- [ ] **Paso 1 — Escribir las excepciones**

```python
# app/exception/unidad_exception.py
class UnidadException(Exception):
    pass

class UnidadNoEncontradaException(UnidadException):
    def __init__(self, id_unidad: int):
        self.id_unidad = id_unidad
        super().__init__(f"Unidad {id_unidad} no encontrada")

class UnidadDuplicadaException(UnidadException):
    def __init__(self, condominio_id: int, torre: str, piso: str, numero: str):
        self.condominio_id = condominio_id
        super().__init__(
            f"Ya existe una unidad {torre}-{piso}-{numero} en el condominio {condominio_id}"
        )
```

- [ ] **Paso 2 — Agregar los handlers**

```python
# app/handler/exception_handler.py — agregar al final del archivo
from app.exception.unidad_exception import UnidadDuplicadaException, UnidadNoEncontradaException


def unidad_no_encontrada_handler(_request: Request, exc: UnidadNoEncontradaException):
    return JSONResponse(status_code=404, content={"message": str(exc)})


def unidad_duplicada_handler(_request: Request, exc: UnidadDuplicadaException):
    return JSONResponse(status_code=409, content={"message": str(exc)})
```

Criterio de aceptación: `python -c "from app.handler.exception_handler import unidad_no_encontrada_handler, unidad_duplicada_handler"` no lanza `ImportError`.

- [ ] **Paso 3 — Commit**

```bash
git add app/exception/unidad_exception.py app/handler/exception_handler.py
git commit -m ":sparkles: feat(condominios): agrega excepciones de Unidad"
```

---

### Task 3: DTOs con normalización (corregida: default solo en `torre`)

**Files:**
- Create: `app/dto/unidad_dto.py`
- Test: `tests/test_unidad_dto.py`

**Interfaces:**
- Produce: `UnidadCrear(condominio_id: int, torre: str, piso: str, numero: str)`, `UnidadRespuesta(..., id: int, activa: bool)`, `UnidadActualizar(torre|piso|numero|activa opcionales)`.
- Consume: nada externo.

- [ ] **Paso 1 — Escribir los tests que fallan**

```python
# tests/test_unidad_dto.py
import pytest
from pydantic import ValidationError

from app.dto.unidad_dto import UnidadActualizar, UnidadCrear


def test_normaliza_torre_piso_numero_a_mayuscula_sin_espacios():
    dto = UnidadCrear(condominio_id=1, torre=" a ", piso=" 3 ", numero=" 101 ")
    assert dto.torre == "A"
    assert dto.piso == "3"
    assert dto.numero == "101"

def test_torre_vacia_cae_a_unica():
    dto = UnidadCrear(condominio_id=1, torre="   ", piso="1", numero="1")
    assert dto.torre == "UNICA"

def test_torre_omitida_usa_default_unica():
    dto = UnidadCrear(condominio_id=1, piso="1", numero="1")
    assert dto.torre == "UNICA"

def test_piso_vacio_no_cae_a_unica_sino_que_falla_422():
    with pytest.raises(ValidationError):
        UnidadCrear(condominio_id=1, torre="A", piso="   ", numero="1")

def test_numero_vacio_no_cae_a_unica_sino_que_falla_422():
    with pytest.raises(ValidationError):
        UnidadCrear(condominio_id=1, torre="A", piso="1", numero="   ")

def test_actualizar_normaliza_solo_campos_enviados():
    dto = UnidadActualizar(numero=" 205b ")
    assert dto.numero == "205B"
    assert dto.torre is None

def test_actualizar_piso_vacio_falla_422():
    with pytest.raises(ValidationError):
        UnidadActualizar(piso="   ")
```

- [ ] **Paso 2 — Correr y verificar que falla**

```bash
pytest tests/test_unidad_dto.py -v
```
Esperado: FAIL — `No module named 'app.dto.unidad_dto'`.

- [ ] **Paso 3 — Implementación mínima**

```python
# app/dto/unidad_dto.py
from pydantic import BaseModel, ConfigDict, Field, field_validator


def _limpiar(v: str) -> str:
    return v.strip().upper()


def _torre_o_unica(v: str | None) -> str:
    """Unico campo con valor por defecto: torre vacia/ausente cae a 'UNICA'."""
    if v is None:
        return "UNICA"
    limpio = _limpiar(v)
    return limpio if limpio else "UNICA"


class UnidadCrear(BaseModel):
    condominio_id: int
    torre: str = Field(default="UNICA", max_length=50)
    piso: str = Field(min_length=1, max_length=10)
    numero: str = Field(min_length=1, max_length=20)

    @field_validator("torre", mode="before")
    @classmethod
    def normalizar_torre(cls, v: str | None) -> str:
        return _torre_o_unica(v)

    @field_validator("piso", "numero", mode="before")
    @classmethod
    def normalizar_piso_numero(cls, v: str) -> str:
        # Solo limpia formato; NO aplica ningun valor por defecto.
        # Si queda vacio tras el strip, Field(min_length=1) lo rechaza con 422.
        return _limpiar(v) if isinstance(v, str) else v


class UnidadRespuesta(UnidadCrear):
    id: int
    activa: bool
    model_config = ConfigDict(from_attributes=True)


class UnidadActualizar(BaseModel):
    torre: str | None = Field(default=None, max_length=50)
    piso: str | None = Field(default=None, min_length=1, max_length=10)
    numero: str | None = Field(default=None, min_length=1, max_length=20)
    activa: bool | None = None

    @field_validator("torre", mode="before")
    @classmethod
    def normalizar_torre(cls, v: str | None) -> str | None:
        return _torre_o_unica(v) if v is not None else None

    @field_validator("piso", "numero", mode="before")
    @classmethod
    def normalizar_piso_numero(cls, v: str | None) -> str | None:
        return _limpiar(v) if isinstance(v, str) else v
```

- [ ] **Paso 4 — Correr y verificar que pasa**

```bash
pytest tests/test_unidad_dto.py -v
```
Criterio de aceptación: 7 passed.

- [ ] **Paso 5 — Commit**

```bash
git add app/dto/unidad_dto.py tests/test_unidad_dto.py
git commit -m ":sparkles: feat(condominios): agrega DTOs de Unidad con normalizacion"
```

---

### Task 4: `UnidadRepository` (corregida: distingue tipo de `IntegrityError`)

**Files:**
- Create: `app/repository/unidad_repository.py`
- Test: `tests/test_unidad_repository.py`

**Interfaces:**
- Consume: `Unidad` (Task 1), `UnidadDuplicadaException` (Task 2), `sqlalchemy.exc.IntegrityError`.
- Produce: `UnidadRepository(session).get_by_condominio(condominio_id, incluir_inactivas=False) -> Sequence[Unidad]`, `.get_by_id_y_condominio(id_unidad, condominio_id) -> Unidad | None`, `.create(unidad: Unidad) -> Unidad`, `.actualizar(unidad: Unidad) -> Unidad`.

- [ ] **Paso 1 — Escribir los tests que fallan**

```python
# tests/test_unidad_repository.py
import pytest
from sqlalchemy.exc import IntegrityError

from app.exception.unidad_exception import UnidadDuplicadaException
from app.model.unidad import Unidad
from app.repository.unidad_repository import UnidadRepository


def _integrity_error(mensaje_oracle: str) -> IntegrityError:
    return IntegrityError("stmt", {}, Exception(mensaje_oracle))


@pytest.mark.asyncio
async def test_get_by_id_y_condominio_filtra_por_ambos(mock_session):
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
async def test_actualizar_traduce_violacion_de_unicidad_oracle(mock_session):
    unidad = Unidad(id=1, condominio_id=1, torre="A", piso="1", numero="101")
    mock_session.commit.side_effect = _integrity_error(
        "ORA-00001: unique constraint (CONVIVO.UQ_UNIDAD_DIRECCION) violated"
    )
    repo = UnidadRepository(mock_session)

    with pytest.raises(UnidadDuplicadaException):
        await repo.actualizar(unidad)

    mock_session.rollback.assert_awaited_once()
```

- [ ] **Paso 2 — Correr y verificar que falla**

```bash
pytest tests/test_unidad_repository.py -v
```
Esperado: FAIL — módulo no existe.

- [ ] **Paso 3 — Implementación**

```python
# app/repository/unidad_repository.py
from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.exception.unidad_exception import UnidadDuplicadaException
from app.model.unidad import Unidad

VIOLACION_UNIQUE_ORACLE = "ORA-00001"


class UnidadRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_condominio(self, condominio_id: int, incluir_inactivas: bool = False) -> Sequence[Unidad]:
        stmt = select(Unidad).where(Unidad.condominio_id == condominio_id)
        if not incluir_inactivas:
            stmt = stmt.where(Unidad.activa == True)  # noqa: E712 — comparacion explicita, estilo SQLAlchemy
        resultado = await self.session.execute(stmt)
        return resultado.scalars().all()

    async def get_by_id_y_condominio(self, id_unidad: int, condominio_id: int) -> Unidad | None:
        stmt = select(Unidad).where(Unidad.id == id_unidad, Unidad.condominio_id == condominio_id)
        resultado = await self.session.execute(stmt)
        return resultado.scalars().first()

    async def create(self, unidad: Unidad) -> Unidad:
        """Persiste la unidad; traduce SOLO violacion de unicidad (ORA-00001) a excepcion de dominio."""
        self.session.add(unidad)
        try:
            await self.session.flush()
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            self._relanzar_o_traducir(exc, unidad)
        await self.session.refresh(unidad)
        return unidad

    async def actualizar(self, unidad: Unidad) -> Unidad:
        """Persiste cambios sobre una unidad ya cargada; misma distincion de excepcion."""
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            self._relanzar_o_traducir(exc, unidad)
        await self.session.refresh(unidad)
        return unidad

    @staticmethod
    def _relanzar_o_traducir(exc: IntegrityError, unidad: Unidad) -> None:
        if VIOLACION_UNIQUE_ORACLE in str(exc.orig):
            raise UnidadDuplicadaException(unidad.condominio_id, unidad.torre, unidad.piso, unidad.numero) from exc
        raise exc
```

- [ ] **Paso 4 — Correr y verificar que pasa**

```bash
pytest tests/test_unidad_repository.py -v
```
Criterio de aceptación: 5 passed.

- [ ] **Paso 5 — Commit**

```bash
git add app/repository/unidad_repository.py tests/test_unidad_repository.py
git commit -m ":sparkles: feat(condominios): agrega UnidadRepository"
```

---

### Task 5: `UnidadService`

**Files:**
- Create: `app/service/unidad_service.py`
- Test: `tests/test_unidad_service.py`

**Interfaces:**
- Consume: `UnidadRepository` (Task 4), `CondominioService.obtener_condominio` (existente, sin modificar), `UnidadCrear/Actualizar` (Task 3), `UnidadNoEncontradaException` (Task 2).
- Produce: `UnidadService(unidad_repo, condominio_service)` con `listar_unidades`, `obtener_unidad`, `crear_unidad`, `actualizar_unidad`, `eliminar_unidad`.

- [ ] **Paso 1 — Escribir los tests que fallan**

```python
# tests/test_unidad_service.py
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
        await service.crear_unidad(99, UnidadCrear(condominio_id=99, piso="1", numero="1"))

    mock_unidad_repo.create.assert_not_called()

@pytest.mark.asyncio
async def test_crear_unidad_exitosa(mock_unidad_repo, mock_condominio_service):
    mock_unidad_repo.create.return_value = Unidad(id=1, condominio_id=1, torre="UNICA", piso="1", numero="1")
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    resultado = await service.crear_unidad(1, UnidadCrear(condominio_id=1, piso="1", numero="1"))

    assert resultado.id == 1
    mock_condominio_service.obtener_condominio.assert_called_once_with(1)

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
async def test_actualizar_unidad_aplica_solo_campos_enviados(mock_unidad_repo, mock_condominio_service):
    unidad = Unidad(id=1, condominio_id=1, torre="UNICA", piso="1", numero="1")
    mock_unidad_repo.get_by_id_y_condominio.return_value = unidad
    mock_unidad_repo.actualizar.return_value = unidad
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    resultado = await service.actualizar_unidad(1, 1, UnidadActualizar(numero="205"))

    assert resultado.numero == "205"
    assert resultado.piso == "1"  # no enviado, no cambia

@pytest.mark.asyncio
async def test_reactivar_unidad_via_actualizar(mock_unidad_repo, mock_condominio_service):
    unidad = Unidad(id=1, condominio_id=1, torre="UNICA", piso="1", numero="1", activa=False)
    mock_unidad_repo.get_by_id_y_condominio.return_value = unidad
    mock_unidad_repo.actualizar.return_value = unidad
    service = UnidadService(mock_unidad_repo, mock_condominio_service)

    resultado = await service.actualizar_unidad(1, 1, UnidadActualizar(activa=True))

    assert resultado.activa is True
```

- [ ] **Paso 2 — Correr y verificar que falla**

```bash
pytest tests/test_unidad_service.py -v
```
Esperado: FAIL — módulo y fixtures (`mock_unidad_repo`, `mock_condominio_service`) no existen todavía (se agregan en Task 6).

- [ ] **Paso 3 — Implementación**

```python
# app/service/unidad_service.py
from collections.abc import Sequence

from app.dto.unidad_dto import UnidadActualizar, UnidadCrear
from app.exception.unidad_exception import UnidadNoEncontradaException
from app.model.unidad import Unidad
from app.repository.unidad_repository import UnidadRepository
from app.service.condominio_service import CondominioService


class UnidadService:
    def __init__(self, repository: UnidadRepository, condominio_service: CondominioService):
        self.repository = repository
        self.condominio_service = condominio_service

    async def listar_unidades(self, condominio_id: int) -> Sequence[Unidad]:
        await self.condominio_service.obtener_condominio(condominio_id)
        return await self.repository.get_by_condominio(condominio_id)

    async def obtener_unidad(self, id_unidad: int, condominio_id: int) -> Unidad:
        unidad = await self.repository.get_by_id_y_condominio(id_unidad, condominio_id)
        if not unidad:
            raise UnidadNoEncontradaException(id_unidad)
        return unidad

    async def crear_unidad(self, condominio_id: int, dto: UnidadCrear) -> Unidad:
        await self.condominio_service.obtener_condominio(condominio_id)
        unidad = Unidad(condominio_id=condominio_id, torre=dto.torre, piso=dto.piso, numero=dto.numero)
        return await self.repository.create(unidad)

    async def actualizar_unidad(self, id_unidad: int, condominio_id: int, dto: UnidadActualizar) -> Unidad:
        unidad = await self.obtener_unidad(id_unidad, condominio_id)
        for campo, valor in dto.model_dump(exclude_unset=True).items():
            setattr(unidad, campo, valor)
        return await self.repository.actualizar(unidad)

    async def eliminar_unidad(self, id_unidad: int, condominio_id: int) -> None:
        unidad = await self.obtener_unidad(id_unidad, condominio_id)
        unidad.activa = False
        await self.repository.actualizar(unidad)
```

- [ ] **Paso 4 — Correr y verificar que pasa (tras Task 6, que agrega las fixtures)**

```bash
pytest tests/test_unidad_service.py -v
```
Criterio de aceptación: 6 passed.

- [ ] **Paso 5 — Commit**

```bash
git add app/service/unidad_service.py tests/test_unidad_service.py
git commit -m ":sparkles: feat(condominios): agrega UnidadService con eliminacion logica"
```

---

### Task 6: Router, fixtures de test y registro en `main.py`

**Files:**
- Create: `app/api/unidad_router.py`
- Modify: `app/main.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_unidad_router.py`

**Interfaces:**
- Consume: `UnidadService` (Task 5), `UnidadCrear/Actualizar/Respuesta` (Task 3), `requiere_roles` (existente, sin modificar — ver riesgo documentado en el spec §3).
- Produce: `router` con prefix `/condominios/{id_condominio}/unidades`, función `get_unidad_service`, fixtures `mock_unidad_repo`, `mock_condominio_service`, `mock_unidad_service`, `client_unidad`.

- [ ] **Paso 1 — Agregar fixtures a `tests/conftest.py`**

```python
# tests/conftest.py — agregar imports y fixtures, sin tocar lo existente
from app.api.unidad_router import get_unidad_service
from app.repository.unidad_repository import UnidadRepository
from app.service.unidad_service import UnidadService

@pytest.fixture
def mock_unidad_repo():
    return AsyncMock(spec=UnidadRepository)

@pytest.fixture
def mock_condominio_service():
    return AsyncMock(spec=CondominioService)

@pytest.fixture
def mock_unidad_service():
    return AsyncMock(spec=UnidadService)

@pytest.fixture
def client_unidad(mock_unidad_service):
    app.dependency_overrides[get_unidad_service] = lambda: mock_unidad_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
```

- [ ] **Paso 2 — Escribir los tests de router que fallan**

```python
# tests/test_unidad_router.py
from app.dto.unidad_dto import UnidadRespuesta
from app.exception.condominio_exception import CondominioNoEncontradoException
from app.exception.unidad_exception import UnidadDuplicadaException, UnidadNoEncontradaException


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
```

- [ ] **Paso 3 — Correr y verificar que falla**

```bash
pytest tests/test_unidad_router.py -v
```
Esperado: FAIL — `app.api.unidad_router` no existe.

- [ ] **Paso 4 — Implementar el router**

```python
# app/api/unidad_router.py
from collections.abc import Sequence

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import obtener_sesion
from app.dto.unidad_dto import UnidadActualizar, UnidadCrear, UnidadRespuesta
from app.middleware.auth_roles import requiere_roles
from app.model.unidad import Unidad
from app.repository.condominio_repository import CondominioRepository
from app.repository.unidad_repository import UnidadRepository
from app.service.condominio_service import CondominioService
from app.service.unidad_service import UnidadService

router = APIRouter(prefix="/condominios/{id_condominio}/unidades", tags=["Unidades"])

def get_unidad_service(db: AsyncSession = Depends(obtener_sesion)) -> UnidadService:
    condominio_service = CondominioService(CondominioRepository(db))
    return UnidadService(UnidadRepository(db), condominio_service)

@router.get("/", response_model=list[UnidadRespuesta], dependencies=[Depends(requiere_roles(["ADMIN"]))])
async def listar_unidades(
    id_condominio: int, service: UnidadService = Depends(get_unidad_service)
) -> Sequence[Unidad]:
    return await service.listar_unidades(id_condominio)

@router.post("/", response_model=UnidadRespuesta, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(requiere_roles(["ADMIN"]))])
async def crear_unidad(
    id_condominio: int, dto: UnidadCrear, service: UnidadService = Depends(get_unidad_service)
) -> Unidad:
    return await service.crear_unidad(id_condominio, dto)

@router.get("/{id_unidad}", response_model=UnidadRespuesta, dependencies=[Depends(requiere_roles(["ADMIN"]))])
async def obtener_unidad(
    id_condominio: int, id_unidad: int, service: UnidadService = Depends(get_unidad_service)
) -> Unidad:
    return await service.obtener_unidad(id_unidad, id_condominio)

@router.put("/{id_unidad}", response_model=UnidadRespuesta, dependencies=[Depends(requiere_roles(["ADMIN"]))])
async def actualizar_unidad(
    id_condominio: int, id_unidad: int, dto: UnidadActualizar, service: UnidadService = Depends(get_unidad_service)
) -> Unidad:
    return await service.actualizar_unidad(id_unidad, id_condominio, dto)

@router.delete("/{id_unidad}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(requiere_roles(["ADMIN"]))])
async def eliminar_unidad(
    id_condominio: int, id_unidad: int, service: UnidadService = Depends(get_unidad_service)
) -> None:
    await service.eliminar_unidad(id_unidad, id_condominio)
```

- [ ] **Paso 5 — Registrar router y handlers en `app/main.py`**

```python
# app/main.py — agregar junto a los imports/registros existentes de Condominio
from app.api.unidad_router import router as unidad_router
from app.exception.unidad_exception import UnidadDuplicadaException, UnidadNoEncontradaException
from app.handler.exception_handler import unidad_duplicada_handler, unidad_no_encontrada_handler

# ... junto a las lineas 58-59 existentes:
app.add_exception_handler(UnidadNoEncontradaException, unidad_no_encontrada_handler)
app.add_exception_handler(UnidadDuplicadaException, unidad_duplicada_handler)
app.include_router(unidad_router)
```

- [ ] **Paso 6 — Correr y verificar que pasa**

```bash
pytest tests/ -v --ignore=tests/integration
```
Criterio de aceptación: los tests existentes de `Condominio` siguen en verde + los 7 nuevos de `test_unidad_router.py` pasan (ningún test preexistente se rompe).

- [ ] **Paso 7 — Commit**

```bash
git add app/api/unidad_router.py app/main.py tests/conftest.py tests/test_unidad_router.py
git commit -m ":sparkles: feat(condominios): expone endpoints REST de Unidad"
```

---

### Task 7: Test de integración contra Oracle real (requiere Oracle levantado)

**Files:**
- Modify: `tests/integration/test_oracle.py`

**Interfaces:**
- Consume: `Unidad`, `UnidadRepository`, motor Oracle real vía `docker compose up`.

- [ ] **Paso 1 — Agregar los tests de integración**

```python
# tests/integration/test_oracle.py — agregar junto a los tests existentes
@pytest.mark.asyncio
async def test_unidad_respeta_unique_constraint_en_oracle_real(session):
    from app.exception.unidad_exception import UnidadDuplicadaException
    from app.model.condominio import Condominio
    from app.model.unidad import Unidad
    from app.repository.unidad_repository import UnidadRepository

    condominio = Condominio(nombre="Test Oracle", direccion="Dir", cantidad_sectores=1, plan="basico")
    session.add(condominio)
    await session.flush()

    repo = UnidadRepository(session)
    await repo.create(Unidad(condominio_id=condominio.id, torre="A", piso="1", numero="101"))

    with pytest.raises(UnidadDuplicadaException):
        await repo.create(Unidad(condominio_id=condominio.id, torre="A", piso="1", numero="101"))

@pytest.mark.asyncio
async def test_unidad_boolean_activa_persiste_correctamente_en_oracle(session):
    from app.model.condominio import Condominio
    from app.model.unidad import Unidad
    from app.repository.unidad_repository import UnidadRepository

    condominio = Condominio(nombre="Test Oracle 2", direccion="Dir", cantidad_sectores=1, plan="basico")
    session.add(condominio)
    await session.flush()

    repo = UnidadRepository(session)
    unidad = await repo.create(Unidad(condominio_id=condominio.id, torre="B", piso="2", numero="202"))
    assert unidad.activa is True

    unidad.activa = False
    actualizada = await repo.actualizar(unidad)
    assert actualizada.activa is False
```

- [ ] **Paso 2 — Correr contra Oracle real**

```bash
docker compose up -d oracle-condominios
alembic upgrade head
pytest tests/integration -v
```
Criterio de aceptación: ambos tests PASS contra Oracle real — confirma que Oracle rechaza el duplicado de verdad (no solo el mock) y que `Boolean`/`ON DELETE CASCADE` funcionan tal como se verificó en la sección de compatibilidad del spec.

- [ ] **Paso 3 — Commit**

```bash
git add tests/integration/test_oracle.py
git commit -m ":white_check_mark: test(condominios): valida unique constraint y boolean de Unidad contra Oracle real"
```

---

### Task 8: Verificación final

- [ ] `pytest tests/ -v --ignore=tests/integration` — todo en verde, incluidos los tests preexistentes de `Condominio` sin regresión.
- [ ] `ruff check .` — limpio.
- [ ] `pytest tests/ --ignore=tests/integration --cov=app --cov-report=term-missing` — cobertura de ramas en `unidad_service.py`/`unidad_repository.py`/`unidad_router.py`/`unidad_dto.py` en línea con el resto del servicio (≥80%, convención `AGENTS.md` §7).
- [ ] `git status` desde la raíz del workspace — confirmar que ningún archivo fuera de `ms-condominios/` quedó modificado.
- [ ] Revisar manualmente que `app/middleware/auth_roles.py` no fue tocado (el riesgo de suplantación documentado en el spec se queda exactamente como estaba).

## Riesgos conocidos

- **Constraint único + reactivación:** reactivar una unidad inactiva es el único camino para recuperar un `torre+piso+numero`; no se puede crear una fila nueva con la misma dirección mientras la vieja siga inactiva. Aceptado, documentado en el spec §4.
- **Suplantación vía `X-Usuario-Roles`:** riesgo heredado de `Condominio`, no corregido en este sub-proyecto por decisión explícita de alcance. Documentado en el spec §3.
- **Autorización ADMIN-only:** si se necesita que un residente consulte su propia unidad antes de que exista `ms-usuario`, este diseño lo bloquea a propósito — decisión explícita de esta etapa, a revisar en la etapa 2.
- **Sin cross-validation:** `ms-gastos-comunes`/`ms-espacios-comunes` no se tocan; su `unidadId` sigue siendo un string libre hasta que `ms-usuario` u otro trabajo posterior cierre ese gap.
- **Asimetría frente a `CondominioRepository`:** `UnidadRepository.actualizar`/`.create` no aceptan `tipo_evento` (sin Outbox para `Unidad`, por diseño) — quien implemente debe notar que es intencional, no un olvido.
