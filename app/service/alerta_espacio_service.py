from collections.abc import Sequence

from app.model.alerta_espacio import AlertaEspacio
from app.repository.alerta_espacio_repository import AlertaEspacioRepository


class AlertaEspacioService:
    def __init__(self, repository: AlertaEspacioRepository):
        self.repository = repository

    async def listar_alertas(self, condominio_id: int, limite: int) -> Sequence[AlertaEspacio]:
        """Últimas alertas de espacios comunes recibidas para el condominio."""
        return await self.repository.listar_por_condominio(condominio_id, limite)
