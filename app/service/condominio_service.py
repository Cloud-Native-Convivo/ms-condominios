from collections.abc import Sequence

from app.dto.condominio_dto import CondominioActualizar, CondominioCrear
from app.exception.condominio_exception import (
    CondominioConUnidadesException,
    CondominioNoEncontradoException,
)
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
        cambios = dto.model_dump(exclude_unset=True)
        # El tipo define que unidades caben (A torres, B casas): cambiarlo con
        # unidades creadas las dejaria incoherentes con la regla.
        nuevo_tipo = cambios.get("tipo")
        if (
            nuevo_tipo is not None
            and nuevo_tipo != condominio.tipo
            and await self.repository.tiene_unidades(id_condominio)
        ):
            raise CondominioConUnidadesException(id_condominio)
        for campo, valor in cambios.items():
            setattr(condominio, campo, valor)
        return await self.repository.actualizar(condominio, "CondominioActualizado")

    async def eliminar_condominio(self, id_condominio: int) -> None:
        condominio = await self.obtener_condominio(id_condominio)
        await self.repository.eliminar(condominio, "CondominioEliminado")
