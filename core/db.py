"""
=====================================================================
core/db.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
Здесь мы один раз создаём "движок" (engine) подключения к PostgreSQL
и фабрику сессий (session maker). Сессия — это как "рабочий блокнот"
для одного запроса к базе: открыли сессию → сделали запросы →
закрыли (commit или rollback).

Функция `init_models()` создаёт таблицы в базе при первом запуске
(если их ещё нет) — аналог "миграции", но максимально простой.
Для более серьёзного продакшена лучше использовать Alembic,
но для MVP этого достаточно.

Использование в других файлах:
    from core.db import get_session
    async with get_session() as session:
        ...
=====================================================================
"""

from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from core.config import settings
from core.models import Base

# Асинхронный движок — умеет работать через asyncio, не блокируя бота
engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)

# Фабрика сессий — каждый раз создаёт новую сессию для работы с БД
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def get_session():
    """
    Удобный способ получить сессию базы данных через `async with`.
    Автоматически коммитит изменения, если всё прошло без ошибок,
    и откатывает (rollback), если была ошибка.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_models():
    """Создаёт все таблицы, описанные в core/models.py, если их ещё нет."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
