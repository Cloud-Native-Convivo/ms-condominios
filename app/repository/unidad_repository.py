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
        # Capturado ANTES del commit: tras un rollback() real, SQLAlchemy expira
        # los atributos del objeto incluso con expire_on_commit=False, y leerlos
        # despues en un AsyncSession dispara IO y revienta con MissingGreenlet.
        valores = (unidad.condominio_id, unidad.torre, unidad.piso, unidad.numero)
        try:
            await self.session.flush()
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            self._relanzar_o_traducir(exc, *valores)
        await self.session.refresh(unidad)
        return unidad

    async def actualizar(self, unidad: Unidad) -> Unidad:
        """Persiste cambios sobre una unidad ya cargada; misma distincion de excepcion."""
        valores = (unidad.condominio_id, unidad.torre, unidad.piso, unidad.numero)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            self._relanzar_o_traducir(exc, *valores)
        await self.session.refresh(unidad)
        return unidad

    @staticmethod
    def _relanzar_o_traducir(exc: IntegrityError, condominio_id: int, torre: str, piso: str, numero: str) -> None:
        if VIOLACION_UNIQUE_ORACLE in str(exc.orig):
            raise UnidadDuplicadaException(condominio_id, torre, piso, numero) from exc
        raise exc
