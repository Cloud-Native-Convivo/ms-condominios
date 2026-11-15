from collections.abc import Sequence

from app.dto.unidad_dto import UnidadActualizar, UnidadCrear
from app.exception.unidad_exception import (
    UnidadIncompatibleConTipoException,
    UnidadNoEncontradaException,
)
from app.model.unidad import Unidad
from app.repository.unidad_repository import UnidadRepository
from app.service.condominio_service import CondominioService

TORRE_UNICA = "UNICA"
# Las casas (tipo B) no tienen piso propio, pero la columna es NOT NULL:
# el servidor guarda este valor fijo en vez de pedirlo al cliente.
PISO_CASA = "0"


def normalizar_segun_tipo(tipo: str, torre: str, piso: str | None) -> tuple[str, str]:
    """Aplica la regla de Ley 21.442: tipo B solo casas, tipo A solo departamentos.

    Recibe torre y piso ya normalizados (strip/upper) y devuelve los valores a
    persistir. Lanza UnidadIncompatibleConTipoException si no cuadran con el tipo.
    """
    if tipo == "B":
        if torre != TORRE_UNICA:
            raise UnidadIncompatibleConTipoException(
                "En un condominio de casas (tipo B) la unidad no lleva torre"
            )
        if piso not in (None, PISO_CASA):
            raise UnidadIncompatibleConTipoException(
                "En un condominio de casas (tipo B) la unidad no lleva piso"
            )
        return TORRE_UNICA, PISO_CASA
    if not piso:
        raise UnidadIncompatibleConTipoException(
            "En un condominio de torres (tipo A) el piso es obligatorio"
        )
    return torre, piso


def describir_unidad(tipo: str, torre: str, piso: str, numero: str) -> str:
    """Texto legible de la unidad, el que muestran el panel y el portal de residentes."""
    if tipo == "B":
        return f"Casa {numero}"
    partes = [] if torre == TORRE_UNICA else [f"Torre {torre}"]
    return " · ".join([*partes, f"Piso {piso}", f"Unidad {numero}"])


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
        condominio = await self.condominio_service.obtener_condominio(condominio_id)
        torre, piso = normalizar_segun_tipo(condominio.tipo, dto.torre, dto.piso)
        unidad = Unidad(condominio_id=condominio_id, torre=torre, piso=piso, numero=dto.numero)
        return await self.repository.create(unidad)

    async def actualizar_unidad(self, id_unidad: int, condominio_id: int, dto: UnidadActualizar) -> Unidad:
        condominio = await self.condominio_service.obtener_condominio(condominio_id)
        unidad = await self.obtener_unidad(id_unidad, condominio_id)
        # exclude_none=True: todos los campos de Unidad son NOT NULL en Oracle, asi
        # que un null explicito en el body no debe intentar aplicarse (eso rompia
        # con 500 por ORA-01407 en vez de dejar el campo sin cambios).
        cambios = dto.model_dump(exclude_unset=True, exclude_none=True)
        # La regla por tipo se valida sobre el resultado final (fila + cambios),
        # no solo sobre lo enviado: un cambio parcial no puede dejarla incoherente.
        torre, piso = normalizar_segun_tipo(
            condominio.tipo, cambios.get("torre", unidad.torre), cambios.get("piso", unidad.piso)
        )
        cambios.update(torre=torre, piso=piso)
        for campo, valor in cambios.items():
            setattr(unidad, campo, valor)
        return await self.repository.actualizar(unidad)

    async def eliminar_unidad(self, id_unidad: int, condominio_id: int) -> None:
        unidad = await self.obtener_unidad(id_unidad, condominio_id)
        unidad.activa = False
        await self.repository.actualizar(unidad)
