"""
=====================================================================
bot/middlewares/throttling.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
Middleware — это код, который выполняется "перед" каждым хендлером
(перед обработкой сообщения/кнопки). Это удобное место для общих
проверок, которые нужны везде: антиспам, проверка бана, язык и т.д.

Этот конкретный middleware — троттлинг (throttling), то есть
ограничение частоты запросов одного пользователя. Задача:
- защитить бота от спама кнопками/сообщениями
- защитить наш кошелёк от резких счетов за OpenRouter API
  (каждое сообщение = деньги за токены)

Как работает:
1. При каждом сообщении/клике смотрим в Redis: "когда этот
   пользователь последний раз писал?"
2. Если прошло меньше settings.THROTTLE_RATE_LIMIT секунд —
   блокируем обработку и показываем "не спеши" на нужном языке.
3. Иначе — обновляем время последнего действия и пропускаем
   запрос дальше, к хендлеру.

Используем Redis (а не просто Python-словарь в памяти), потому что
если бот будет запущен в нескольких процессах/контейнерах —
словарь в памяти не будет общим. Redis — общее хранилище для всех.
=====================================================================
"""

import time
from typing import Any, Awaitable, Callable

import redis.asyncio as redis
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

from core.config import settings
from core.i18n import t


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.rate_limit = settings.THROTTLE_RATE_LIMIT
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        key = f"throttle:{user.id}"
        # NX=True -> установить ключ, только если его ещё нет.
        # Если ключ уже есть — значит пользователь недавно писал.
        is_new = await self.redis.set(key, "1", nx=True, ex=int(self.rate_limit) or 1)

        if not is_new:
            # Пользователь превысил лимит — молча блокируем, либо
            # показываем предупреждение (только для обычных сообщений,
            # чтобы не спамить алертами на каждый лишний клик).
            lang = data.get("user_language", "en")
            if isinstance(event, Message):
                try:
                    await event.answer(t("rate_limited", lang))
                except Exception:
                    pass
            return None  # не пропускаем запрос дальше к хендлеру

        return await handler(event, data)
