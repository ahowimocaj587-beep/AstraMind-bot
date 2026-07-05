"""
=====================================================================
bot/services/user_service.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
"Сервис" — это слой кода, который занимается ОДНОЙ областью логики
и не знает ничего про Telegram/кнопки. Хендлеры (handlers) вызывают
сервисы, а не лезут в базу данных напрямую — так код проще
поддерживать и тестировать.

Этот файл отвечает за всё, что связано с пользователями:
- найти или создать пользователя при первом /start
- обновить язык
- списать/начислить бесплатные сообщения
- проверить бан
=====================================================================
"""

from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import User
from core.config import settings


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    referred_by: int | None = None,
) -> tuple[User, bool]:
    """
    Возвращает (user, is_new).
    Если пользователя нет в базе — создаёт его с дефолтными
    бесплатными сообщениями (settings.FREE_MESSAGES_DEFAULT).
    """
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if user is not None:
        # Обновляем "последнюю активность" для DAU/WAU статистики
        user.last_active_at = datetime.utcnow()
        return user, False

    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        free_messages_left=settings.FREE_MESSAGES_DEFAULT,
        referred_by=referred_by,
    )
    session.add(user)
    await session.flush()  # чтобы у user появился id сразу, без отдельного commit
    return user, True


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def set_language(session: AsyncSession, user: User, language: str) -> None:
    user.language = language


async def has_messages_available(user: User) -> bool:
    """True, если у пользователя есть подписка ИЛИ остались бесплатные сообщения."""
    if user.has_active_subscription:
        return True
    return user.free_messages_left > 0


async def consume_message(session: AsyncSession, user: User) -> None:
    """
    Списывает одно бесплатное сообщение, если у пользователя нет подписки.
    Если подписка активна — ничего не списываем (безлимит).
    """
    if user.has_active_subscription:
        return
    if user.free_messages_left > 0:
        user.free_messages_left -= 1


async def add_bonus_messages(session: AsyncSession, user: User, amount: int) -> None:
    """Начисляет бонусные бесплатные сообщения (например, за реферала)."""
    user.free_messages_left += amount
    user.bonus_messages_earned += amount


async def ban_user(session: AsyncSession, telegram_id: int) -> bool:
    result = await session.execute(
        update(User).where(User.telegram_id == telegram_id).values(is_banned=True)
    )
    return result.rowcount > 0


async def unban_user(session: AsyncSession, telegram_id: int) -> bool:
    result = await session.execute(
        update(User).where(User.telegram_id == telegram_id).values(is_banned=False)
    )
    return result.rowcount > 0
