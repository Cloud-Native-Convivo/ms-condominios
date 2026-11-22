from collections.abc import Sequence

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import obtener_sesion
from app.dto.alerta_espacio_dto import AlertaRespuesta
from app.middleware.auth_roles import requiere_roles
from app.model.alerta_espacio import AlertaEspacio
from app.repository.alerta_espacio_repository import AlertaEspacioRepository
from app.service.alerta_espacio_service import AlertaEspacioService

router = APIRouter(prefix="/condominios/{id_condominio}/alertas", tags=["Alertas"])


def get_alerta_service(db: AsyncSession = Depends(obtener_sesion)) -> AlertaEspacioService:
    return AlertaEspacioService(AlertaEspacioRepository(db))


# Las alertas incluyen el sub del residente afectado: solo administración y conserjería.
@router.get(
    "/",
    response_model=list[AlertaRespuesta],
    dependencies=[Depends(requiere_roles(["ADMIN", "CONSERJE"]))],
)
async def listar_alertas(
    id_condominio: int = Path(gt=0),
    limite: int = Query(50, ge=1, le=200),
    service: AlertaEspacioService = Depends(get_alerta_service),
) -> Sequence[AlertaEspacio]:
    return await service.listar_alertas(id_condominio, limite)
