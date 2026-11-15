from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import obtener_sesion
from app.config.security_config import UsuarioContexto, obtener_contexto_usuario
from app.dto.unidad_dto import UnidadCrear
from app.exception.unidad_exception import UnidadInexistenteException
from app.middleware.auth_roles import requiere_roles
from app.model.condominio import Condominio
from app.model.solicitud_asignacion import SolicitudAsignacion
from app.model.unidad import Unidad
from app.repository.unidad_repository import UnidadRepository
from app.service.unidad_service import describir_unidad, normalizar_segun_tipo

router = APIRouter(prefix="/condominios/solicitudes", tags=["Solicitudes de asignación"])


class SolicitudCrear(UnidadCrear):
    # Hereda torre/piso/numero con la misma normalizacion que UnidadCrear,
    # asi la busqueda calza con lo que el admin guardo al crear la unidad.
    condominio_id: int = Field(gt=0)


class SolicitudRespuesta(BaseModel):
    id: int
    usuario_sub: str
    usuario_email: str | None = None
    condominio_id: int
    unidad: str
    unidad_id: int | None = None
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
    # Header de identidad que fija el bff, como X-Usuario-Sub: no viene del cliente.
    x_usuario_email: str | None = Header(default=None, max_length=255),
):
    usuario_email = x_usuario_email.strip() if x_usuario_email and x_usuario_email.strip() else None
    condominio = await sesion.get(Condominio, datos.condominio_id)
    if not condominio:
        raise HTTPException(status_code=404, detail="Condominio no encontrado")
    torre, piso = normalizar_segun_tipo(condominio.tipo, datos.torre, datos.piso)
    unidad = await UnidadRepository(sesion).get_activa_por_direccion(condominio.id, torre, piso, datos.numero)
    if not unidad:
        raise UnidadInexistenteException()
    texto = describir_unidad(condominio.tipo, torre, piso, datos.numero)

    resultado = await sesion.execute(select(SolicitudAsignacion).where(SolicitudAsignacion.usuario_sub == usuario.usuario_sub))
    solicitud = resultado.scalar_one_or_none()
    if solicitud and solicitud.estado == "aprobada":
        raise HTTPException(status_code=409, detail="Asignación ya aprobada")
    if solicitud:
        solicitud.condominio_id = datos.condominio_id
        solicitud.unidad = texto
        solicitud.unidad_id = unidad.id
        solicitud.estado = "pendiente"
        if usuario_email:
            solicitud.usuario_email = usuario_email
    else:
        solicitud = SolicitudAsignacion(
            usuario_sub=usuario.usuario_sub, usuario_email=usuario_email, condominio_id=datos.condominio_id,
            unidad=texto, unidad_id=unidad.id, estado="pendiente",
        )
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
    # Se revalida: la unidad pudo desactivarse entre la solicitud y la aprobacion.
    # Una solicitud sin unidad_id (anterior a la migracion 0004) no se aprueba:
    # el residente debe enviarla de nuevo para vincularla a una unidad real.
    unidad = await sesion.get(Unidad, solicitud.unidad_id) if solicitud.unidad_id else None
    if not unidad or not unidad.activa or unidad.condominio_id != solicitud.condominio_id:
        raise UnidadInexistenteException()
    solicitud.estado = "aprobada"
    await sesion.commit()
    await sesion.refresh(solicitud)
    return solicitud
