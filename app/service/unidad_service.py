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

    async def listar_unidades(self, condominio_id: int, incluir_inactivas: bool = False) -> Sequence[Unidad]:
        await self.condominio_service.obtener_condominio(condominio_id)
        return await self.repository.get_by_condominio(condominio_id, incluir_inactivas=incluir_inactivas)

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
        # exclude_none=True: todos los campos de Unidad son NOT NULL en Oracle, asi
        # que un null explicito en el body no debe intentar aplicarse (eso rompia
        # con 500 por ORA-01407 en vez de dejar el campo sin cambios).
        for campo, valor in dto.model_dump(exclude_unset=True, exclude_none=True).items():
            setattr(unidad, campo, valor)
        return await self.repository.actualizar(unidad)

    async def eliminar_unidad(self, id_unidad: int, condominio_id: int) -> None:
        unidad = await self.obtener_unidad(id_unidad, condominio_id)
        unidad.activa = False
        await self.repository.actualizar(unidad)
