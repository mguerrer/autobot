import re
import pytest
import pytest_asyncio
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.auth import hash_password, create_session

TEST_DB_URL = "sqlite+aiosqlite://"


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()


@pytest_asyncio.fixture
async def client(session_factory):
    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_client(client, session_factory):
    """Authenticated client with admin session."""
    from app.models import Usuario
    async with session_factory() as session:
        result = await session.execute(select(Usuario).where(Usuario.username == "admin"))
        user = result.scalar_one()
    token = create_session(user)
    client.cookies.set("autobot_session", token)
    return client


@pytest_asyncio.fixture
async def cliente_client(client, session_factory):
    """Authenticated client with cliente1 session (Pizzería Napoli)."""
    from app.models import Usuario
    async with session_factory() as session:
        result = await session.execute(select(Usuario).where(Usuario.username == "cliente1"))
        user = result.scalar_one()
    token = create_session(user)
    client.cookies.set("autobot_session", token)
    return client


async def _seed_db(session_factory, datos_dir):
    import json
    from app.models import ReglaGeneral, ReglaNegocio, Usuario, Negocio, NumeroWhatsApp

    async with session_factory() as session:
        reglas_gral_path = datos_dir / "reglas_generales.md"
        reglas_neg_path = datos_dir / "reglas_negocio.md"

        if reglas_gral_path.exists():
            contenido = reglas_gral_path.read_text(encoding="utf-8")
            session.add(ReglaGeneral(contenido=contenido))

        if reglas_neg_path.exists():
            contenido = reglas_neg_path.read_text(encoding="utf-8")
            patron = r"## negocio:\s*([^\n]+)\s*\n(.*?)(?=\n## negocio:|\Z)"
            for match in re.finditer(patron, contenido, re.DOTALL):
                rut = match.group(1).strip()
                texto = match.group(2).strip()
                session.add(ReglaNegocio(negocio_rut=rut, contenido=texto))

        users = [
            ("admin", "admin123", "admin", None),
            ("cliente1", "cliente123", "cliente", "76.123.456-7"),
            ("cliente2", "cliente123", "cliente", "77.789.012-3"),
            ("cliente3", "cliente123", "cliente", "7688844-2"),
        ]
        for username, pwd, role, negocio_rut in users:
            exists = await session.execute(select(Usuario).where(Usuario.username == username))
            if not exists.scalar_one_or_none():
                session.add(Usuario(
                    username=username,
                    password_hash=hash_password(pwd),
                    role=role,
                    negocio_rut=negocio_rut,
                ))

        negocios_path = datos_dir / "negocios.json"
        if negocios_path.exists():
            negocios_data = json.loads(negocios_path.read_text(encoding="utf-8"))
            for nd in negocios_data:
                exists = await session.execute(select(Negocio).where(Negocio.rut == nd["rut"]))
                if exists.scalar_one_or_none():
                    continue
                neg = Negocio(
                    rut=nd["rut"],
                    nombre=nd.get("nombre", ""),
                    rubro_id=nd.get("rubro_id", 0),
                    dueno_nombre=nd.get("dueno_nombre", ""),
                    dueno_telefono=nd.get("dueno_telefono", ""),
                    activo=nd.get("activo", True),
                )
                session.add(neg)
                await session.flush()
                num_exists = await session.execute(
                    select(NumeroWhatsApp).where(
                        NumeroWhatsApp.negocio_rut == nd["rut"],
                        NumeroWhatsApp.numero == nd.get("bot_whatsapp", ""),
                    )
                )
                if nd.get("bot_whatsapp") and not num_exists.scalar_one_or_none():
                    session.add(NumeroWhatsApp(
                        negocio_rut=nd["rut"],
                        numero=nd["bot_whatsapp"],
                        tipo_cuenta="personal",
                        phone_number_id=nd.get("phone_number_id", ""),
                        verify_token=nd.get("verify_token", ""),
                    ))
        await session.commit()


@pytest.fixture
def datos_dir(tmp_path):
    d = tmp_path / "datos"
    d.mkdir()
    return d


@pytest_asyncio.fixture(autouse=True)
async def setup_test_env(monkeypatch, datos_dir, session_factory):
    src = Path(__file__).resolve().parent.parent / "datos"
    TEXT_EXTENSIONS = {".json", ".md", ".txt", ".yaml", ".yml", ".env"}
    for f in src.iterdir():
        if f.is_file() and f.suffix in TEXT_EXTENSIONS:
            content = f.read_text(encoding="utf-8")
            (datos_dir / f.name).write_text(content, encoding="utf-8")
    from app.services import rule_engine
    monkeypatch.setattr(rule_engine, "DATOS_DIR", datos_dir)
    monkeypatch.setattr(rule_engine, "async_session", session_factory)

    await _seed_db(session_factory, datos_dir)
    return datos_dir
