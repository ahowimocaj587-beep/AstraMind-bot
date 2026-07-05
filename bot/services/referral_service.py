"""
=====================================================================
bot/services/referral_service.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
Реферальная система — это "приведи друга и получи бонус".

Как это работает у нас:
1. У каждого пользователя есть персональная ссылка вида
   https://t.me/<имя_бота>?start=ref_<его_telegram_id>
2. Когда новый человек переходит по ссылке, Telegram передаёт боту
   команду /start с параметром "ref_12345" — это как раз telegram_id
   пригласившего. Мы парсим этот параметр в handlers/start.py.
3. Как только новый пользователь регистрируется (и это НЕ он сам,
   т.е. защита от само-рефералки), пригласившему начисляется бонус.
4. Если приглашённый позже покупает подписку — мы также увеличиваем
   счётчик "converted" (конвертированных рефералов) у пригласившего.
=====================================================================
"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import User
from core.config import settings
from bot.services.user_service import add_bonus_messages

logger = logging.getLogger(__name__)


def parse_referral_payload(start_param: str | None) -> int | None:
    """
    Парсит параметр из команды /start.
    Ожидаемый формат: "ref_123456789" -> возвращает 123456789.
    Если формат неверный — возвращает None (это НЕ реферальный запуск).
    """
    if not start_param:
        return None
    if not start_param.startswith("ref_"):
        return None
    raw_id = start_param.removeprefix("ref_")
    try:
        return int(raw_id)
    except ValueError:
        return None


async def register_referral(
    session: AsyncSession,
    new_user_telegram_id: int,
    referrer_telegram_id: int,
) -> bool:
    """
    Начисляет бонус пригласившему, когда регистрируется новый пользователь.
    Возвращает True, если бонус успешно начислен.

    Анти-абуз правила:
    - нельзя пригласить самого себя (referrer == new_user)
    - пригласивший должен реально существовать в базе
    """
    if new_user_telegram_id == referrer_telegram_id:
        logger.warning(f"Self-referral attempt blocked: {new_user_telegram_id}")
        return False

    result = await session.execute(
        select(User).where(User.telegram_id == referrer_telegram_id)
    )
    referrer = result.scalar_one_or_none()
    if referrer is None:
        return False

    referrer.referrals_count += 1
    await add_bonus_messages(session, referrer, settings.REFERRAL_BONUS_MESSAGES)
    return True


async def register_referral_conversion(session: AsyncSession, converted_user: User) -> None:
    """
    Вызывается, когда приглашённый пользователь оформляет ПЕРВУЮ подписку.
    Увеличивает счётчик "конвертированных" рефералов у того, кто его пригласил.
    """
    if converted_user.referred_by is None:
        return
    result = await session.execute(
        select(User).where(User.telegram_id == converted_user.referred_by)
    )
    referrer = result.scalar_one_or_none()
    if referrer is not None:
        referrer.referrals_converted += 1


def build_referral_link(bot_username: str, telegram_id: int) -> str:
    return f"https://t.me/{bot_username}?start=ref_{telegram_id}"
