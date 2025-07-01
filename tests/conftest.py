import os
import sys
import pytest_asyncio
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from database import Base, get_session

TEST_DB_URL = os.getenv("DATABASE_URL")

@pytest_asyncio.fixture(scope="function")
async def engine_and_session():
    test_engine = create_async_engine(TEST_DB_URL, future=True, echo=False)
    test_sessionmaker = sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine, test_sessionmaker

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def client(engine_and_session):
    engine, session_maker = engine_and_session

    async def override_get_session():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
