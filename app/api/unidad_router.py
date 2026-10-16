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
    id_condominio: int, incluir_inactivas: bool = False, service: UnidadService = Depends(get_unidad_service)
) -> Sequence[Unidad]:
    return await service.listar_unidades(id_condominio, incluir_inactivas=incluir_inactivas)

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
