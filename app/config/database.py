from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config.settings import settings

motor = create_async_engine(settings.url_base_datos, echo=False)
fabrica_sesiones = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def obtener_sesion() -> AsyncGenerator[AsyncSession, None]:
    # Sin .begin(): el repositorio hace commit; al cerrar, lo no confirmado hace rollback
    async with fabrica_sesiones() as sesion:
        yield sesion
