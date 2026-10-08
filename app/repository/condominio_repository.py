import json
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.model.condominio import Condominio
from app.model.outbox import Outbox


class CondominioRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> Sequence[Condominio]:
        result = await self.session.execute(select(Condominio))
        return result.scalars().all()

    async def get_by_id(self, id_condominio: int) -> Condominio | None:
        result = await self.session.execute(select(Condominio).where(Condominio.id == id_condominio))
        return result.scalars().first()

    async def create(self, condominio: Condominio, tipo_evento: str | None = None) -> Condominio:
        """Persiste el condominio y, si se indica, su evento outbox en la misma transacción."""
        self.session.add(condominio)
        await self.session.flush()  # asigna el id antes de armar el evento
        if tipo_evento:
            payload = {c.name: getattr(condominio, c.name) for c in Condominio.__table__.columns}
            self.session.add(Outbox(
                aggregate_type="Condominio",
                aggregate_id=str(condominio.id),
                type=tipo_evento,
                payload=json.dumps(payload),
            ))
        await self.session.commit()
        await self.session.refresh(condominio)
        return condominio
