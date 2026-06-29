from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        from app.models import Base
        await conn.run_sync(Base.metadata.create_all)
    from app.auth import seed_default_users
    await seed_default_users()
    from app.services.rule_engine import migrar_reglas_de_archivos_a_db
    await migrar_reglas_de_archivos_a_db()
    from app.services.rule_engine import migrar_negocios_de_json_a_db
    await migrar_negocios_de_json_a_db()
