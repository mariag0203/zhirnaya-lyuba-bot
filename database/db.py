"""
Управление подключением к базе данных
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from config.settings import settings
from database.models import Base
import logging

logger = logging.getLogger(__name__)

# Создание async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Выводить SQL запросы в консоль (для отладки)
    poolclass=NullPool  # Для SQLite
)

# Создание фабрики сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """Инициализация базы данных (создание таблиц)"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ База данных инициализирована успешно")
    except Exception as e:
        logger.error(f"✗ Ошибка инициализации БД: {e}")
        raise


async def get_session() -> AsyncSession:
    """Получить сессию БД"""
    async with async_session_maker() as session:
        yield session


async def close_db():
    """Закрыть соединение с БД"""
    await engine.dispose()
    logger.info("✓ Соединение с БД закрыто")
