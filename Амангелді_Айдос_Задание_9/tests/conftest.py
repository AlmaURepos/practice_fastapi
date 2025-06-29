import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from Амангелді_Айдос_Задание_9.app import app
from database import Base, get_session

TEST_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost/test_notes_db"

test_engine = create_async_engine(TEST_DB_URL, echo=True, future=True)
test_async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_session():
    async with test_async_session() as session:
        try:
            yield session
        finally:
            await session.close()

app.dependency_overrides[get_session] = override_get_session

@pytest_asyncio.fixture(scope='session')
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client(setup_db):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
