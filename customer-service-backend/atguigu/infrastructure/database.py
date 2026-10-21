from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from atguigu.conf.config import settings


engine: AsyncEngine | None = None
async_session: async_sessionmaker[AsyncSession] | None = None


def init_db_engine() -> None:
    global engine, async_session
    if engine is not None:
        return
    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        echo=False,
    )
    async_session = async_sessionmaker(engine, expire_on_commit=False)


async def close_db_engine() -> None:
    global engine, async_session
    if engine is not None:
        await engine.dispose()
    engine = None
    async_session = None
