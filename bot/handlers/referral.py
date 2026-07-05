"""
=====================================================================
bot/handlers/referral.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
Простой хендлер: показывает пользователю его персональную
реферальную ссылку и статистику (сколько друзей пригласил, сколько
из них оформили подписку, сколько бонусных сообщений заработано).

Username бота (bot_username) мы передаём через data — его один раз
получают в main.py при старте (bot.get_me()) и кладут в Dispatcher,
чтобы не запрашивать это у Telegram при каждом клике.
=====================================================================
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from core.db import get_session
from core.i18n import t
from core.config import settings
from bot.services.user_service import get_user_by_telegram_id
from bot.services.referral_service import build_referral_link

router = Router(name="referral")


@router.callback_query(F.data == "menu:referral")
async def show_referral_info(callback: CallbackQuery, user_language: str, bot_username: str):
    async with get_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)

    if user is None:
        await callback.answer()
        return

    link = build_referral_link(bot_username, user.telegram_id)

    await callback.message.answer(
        t(
            "referral_info",
            user_language,
            link=link,
            count=user.referrals_count,
            converted=user.referrals_converted,
            bonus=user.bonus_messages_earned,
            reward=settings.REFERRAL_BONUS_MESSAGES,
        )
    )
    await callback.answer()
