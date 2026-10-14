from collections.abc import Sequence

from app.dto.condominio_dto import CondominioActualizar, CondominioCrear
from app.exception.condominio_exception import CondominioNoEncontradoException
from app.model.condominio import Condominio
from app.repository.condominio_repository import CondominioRepository


class CondominioService:
    def __init__(self, repository: CondominioRepository):
        self.repository = repository

    async def listar_condominios(self) -> Sequence[Condominio]:
        return await self.repository.get_all()

    async def obtener_condominio(self, id_condominio: int) -> Condominio:
        condominio = await self.repository.get_by_id(id_condominio)
        if not condominio:
            raise CondominioNoEncontradoException(id_condominio)
        return condominio

    async def crear_condominio(self, dto: CondominioCrear) -> Condominio:
        return await self.repository.create(Condominio(**dto.model_dump()), "CondominioCreado")

    async def actualizar_condominio(self, id_condominio: int, dto: CondominioActualizar) -> Condominio:
        condominio = await self.obtener_condominio(id_condominio)
        for campo, valor in dto.model_dump(exclude_unset=True).items():
            setattr(condominio, campo, valor)
        return await self.repository.actualizar(condominio, "CondominioActualizado")

    async def eliminar_condominio(self, id_condominio: int) -> None:
        condominio = await self.obtener_condominio(id_condominio)
        await self.repository.eliminar(condominio, "CondominioEliminado")
