import os

# Secretos sin default en Settings: valores de prueba antes de importar app
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("RABBITMQ_CONTRASENA", "test")

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.service.condominio_service import CondominioService
from app.repository.condominio_repository import CondominioRepository
from app.api.condominio_router import get_condominio_service

@pytest.fixture
def mock_repo():
    return AsyncMock(spec=CondominioRepository)

@pytest.fixture
def mock_service(mock_repo):
    return AsyncMock(spec=CondominioService)

@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)

from contextlib import asynccontextmanager

@pytest.fixture(autouse=True)
def override_lifespan():
    @asynccontextmanager
    async def dummy_lifespan(app):
        yield
    
    old_lifespan = app.router.lifespan_context
    app.router.lifespan_context = dummy_lifespan
    yield
    app.router.lifespan_context = old_lifespan

@pytest.fixture
def client(mock_service):
    app.dependency_overrides[get_condominio_service] = lambda: mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
