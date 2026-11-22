from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.model.alerta_espacio import AlertaEspacio


class AlertaEspacioRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def listar_por_condominio(self, condominio_id: int, limite: int) -> Sequence[AlertaEspacio]:
        """Alertas del condominio, la más reciente primero."""
        stmt = (
            select(AlertaEspacio)
            .where(AlertaEspacio.condominio_id == condominio_id)
            .order_by(AlertaEspacio.ocurrido_en.desc(), AlertaEspacio.event_id)
            .limit(limite)
        )
        resultado = await self.session.execute(stmt)
        return resultado.scalars().all()
