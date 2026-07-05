"""
=====================================================================
bot/middlewares/user_context_middleware.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
Этот middleware выполняется ПЕРЕД каждым хендлером и делает 3 вещи:

1. Достаёт пользователя из базы данных (или ничего не делает, если
   его там ещё нет — тогда это сделает handlers/start.py при /start).
2. Кладёт язык пользователя в `data["user_language"]`, чтобы
   ThrottlingMiddleware и другие места могли сразу показывать текст
   на нужном языке, не лазив в базу самостоятельно.
3. Проверяет бан: если пользователь забанен — просто не пропускает
   запрос дальше (кроме команды /start, чтобы не путать пользователя
   полной тишиной).

Благодаря этому в самих хендлерах (handlers/oracle.py и т.д.) НЕ
нужно каждый раз писать "проверь бан" — это уже сделано один раз тут.
=====================================================================
"""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from core.db import get_session
from bot.services.user_service import get_user_by_telegram_id
from core.i18n import t


class UserContextMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        async with get_session() as session:
            db_user = await get_user_by_telegram_id(session, user.id)

        if db_user is not None:
            data["db_user"] = db_user
            data["user_language"] = db_user.language

            if db_user.is_banned:
                lang = db_user.language
                if isinstance(event, Message):
                    await event.answer(t("banned", lang))
                elif isinstance(event, CallbackQuery):
                    await event.answer(t("banned", lang), show_alert=True)
                return None
        else:
            data["db_user"] = None
            data["user_language"] = "en"

        return await handler(event, data)
