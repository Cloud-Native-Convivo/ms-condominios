from collections.abc import Sequence

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import obtener_sesion
from app.dto.condominio_dto import CondominioCrear, CondominioRespuesta
from app.middleware.auth_roles import requiere_roles
from app.model.condominio import Condominio
from app.repository.condominio_repository import CondominioRepository
from app.service.condominio_service import CondominioService

router = APIRouter(prefix="/condominios", tags=["Condominios"])

def get_condominio_service(db: AsyncSession = Depends(obtener_sesion)) -> CondominioService:
    repo = CondominioRepository(db)
    return CondominioService(repo)

@router.get("/", response_model=list[CondominioRespuesta], dependencies=[Depends(requiere_roles(["ADMIN"]))])
async def listar_condominios(service: CondominioService = Depends(get_condominio_service)) -> Sequence[Condominio]:
    return await service.listar_condominios()

@router.post("/", response_model=CondominioRespuesta, status_code=status.HTTP_201_CREATED, dependencies=[Depends(requiere_roles(["ADMIN"]))])
async def crear_condominio(condominio: CondominioCrear, service: CondominioService = Depends(get_condominio_service)) -> Condominio:
    return await service.crear_condominio(condominio)

@router.get("/{id_condominio}", response_model=CondominioRespuesta, dependencies=[Depends(requiere_roles(["ADMIN", "RESIDENTE"]))])
async def obtener_condominio(id_condominio: int, service: CondominioService = Depends(get_condominio_service)) -> Condominio:
    return await service.obtener_condominio(id_condominio)
