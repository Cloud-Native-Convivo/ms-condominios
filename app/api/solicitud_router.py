from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import obtener_sesion
from app.config.security_config import UsuarioContexto, obtener_contexto_usuario
from app.middleware.auth_roles import requiere_roles
from app.model.condominio import Condominio
from app.model.solicitud_asignacion import SolicitudAsignacion

router = APIRouter(prefix="/condominios/solicitudes", tags=["Solicitudes de asignación"])


class SolicitudCrear(BaseModel):
    condominio_id: int = Field(gt=0)
    unidad: str = Field(min_length=1, max_length=100)


class SolicitudRespuesta(BaseModel):
    id: int
    usuario_sub: str
    condominio_id: int
    unidad: str
    estado: str

    model_config = {"from_attributes": True}


@router.get("/me", response_model=SolicitudRespuesta | None, dependencies=[Depends(requiere_roles(["RESIDENTE"]))])
async def solicitud_propia(
    usuario: UsuarioContexto = Depends(obtener_contexto_usuario),
    sesion: AsyncSession = Depends(obtener_sesion),
):
    resultado = await sesion.execute(select(SolicitudAsignacion).where(SolicitudAsignacion.usuario_sub == usuario.usuario_sub))
    return resultado.scalar_one_or_none()


@router.post("", response_model=SolicitudRespuesta, status_code=201, dependencies=[Depends(requiere_roles(["RESIDENTE"]))])
async def solicitar_asignacion(
    datos: SolicitudCrear,
    usuario: UsuarioContexto = Depends(obtener_contexto_usuario),
    sesion: AsyncSession = Depends(obtener_sesion),
):
    if not await sesion.get(Condominio, datos.condominio_id):
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    resultado = await sesion.execute(select(SolicitudAsignacion).where(SolicitudAsignacion.usuario_sub == usuario.usuario_sub))
    solicitud = resultado.scalar_one_or_none()
    if solicitud and solicitud.estado == "aprobada":
        raise HTTPException(status_code=409, detail="Asignación ya aprobada")
    if solicitud:
        solicitud.condominio_id = datos.condominio_id
        solicitud.unidad = datos.unidad
        solicitud.estado = "pendiente"
    else:
        solicitud = SolicitudAsignacion(usuario_sub=usuario.usuario_sub, condominio_id=datos.condominio_id, unidad=datos.unidad, estado="pendiente")
        sesion.add(solicitud)
    await sesion.commit()
    await sesion.refresh(solicitud)
    return solicitud


@router.get("", response_model=list[SolicitudRespuesta], dependencies=[Depends(requiere_roles(["ADMIN"]))])
async def listar_solicitudes(sesion: AsyncSession = Depends(obtener_sesion)):
    resultado = await sesion.execute(select(SolicitudAsignacion).where(SolicitudAsignacion.estado == "pendiente"))
    return resultado.scalars().all()


@router.post("/{id_solicitud}/aprobar", response_model=SolicitudRespuesta, dependencies=[Depends(requiere_roles(["ADMIN"]))])
async def aprobar_solicitud(id_solicitud: int, sesion: AsyncSession = Depends(obtener_sesion)):
    solicitud = await sesion.get(SolicitudAsignacion, id_solicitud)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if solicitud.estado != "pendiente":
        raise HTTPException(status_code=409, detail="La solicitud ya fue procesada")
    solicitud.estado = "aprobada"
    await sesion.commit()
    await sesion.refresh(solicitud)
    return solicitud
