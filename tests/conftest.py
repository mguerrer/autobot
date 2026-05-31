import pytest
import pytest_asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.services.rule_engine import (
    cargar_reglas_generales,
    cargar_reglas_negocio,
    cargar_negocios,
    cargar_rubros,
    buscar_negocio_por_whatsapp,
    construir_prompt_sistema,
)

TEST_DB_URL = "sqlite+aiosqlite://"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = async_sessionmaker(engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def datos_dir(tmp_path):
    d = tmp_path / "datos"
    d.mkdir()
    return d


@pytest.fixture(autouse=True)
def setup_datos_dir(monkeypatch, datos_dir):
    src = Path(__file__).resolve().parent.parent / "datos"
    TEXT_EXTENSIONS = {".json", ".md", ".txt", ".yaml", ".yml", ".env"}
    for f in src.iterdir():
        if f.is_file() and f.suffix in TEXT_EXTENSIONS:
            content = f.read_text(encoding="utf-8")
            (datos_dir / f.name).write_text(content, encoding="utf-8")
    from app.services import rule_engine
    monkeypatch.setattr(rule_engine, "DATOS_DIR", datos_dir)
    return datos_dir
