"""
=====================================================================
main.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
Это ТОЧКА ВХОДА в приложение — файл, который запускается командой
`python main.py`. Он:

1. Создаёт объект Bot (подключение к Telegram API по токену).
2. Создаёт Dispatcher (диспетчер) — "мозг", который решает, какой
   хендлер вызвать на каждое сообщение/кнопку.
3. Подключает Redis-хранилище состояний (FSM) — чтобы бот помнил
   "на каком шаге" пользователь, даже если бот перезапустится.
4. Подключает все middlewares (троттлинг, проверка юзера/бана).
5. Подключает все роутеры (хендлеры) из bot/handlers/__init__.py.
6. Запускает ОДНОВРЕМЕННО:
   - long polling бота (бот сам спрашивает у Telegram "есть новые
     сообщения?" — не нужен публичный домен/SSL для этого)
   - aiohttp веб-сервер для приёма вебхуков платежей (для него
     публичный домен как раз нужен — см. README.md, раздел деплоя)

Оба процесса живут в одном asyncio event loop — это стандартный
способ для aiogram 3 + aiohttp внутри одного контейнера Docker.
=====================================================================
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiohttp import web
import redis.asyncio as redis

from core.config import settings
from core.db import init_models
from bot.handlers import get_main_router
from bot.middlewares.throttling import ThrottlingMiddleware
from bot.middlewares.user_context_middleware import UserContextMiddleware
from webhook.payment_webhook import create_webhook_app

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,  # логи в stdout, как требуется для Railway/Docker
)
logger = logging.getLogger(__name__)


async def main():
    # --- 1. Бот и его глобальные настройки ---
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    me = await bot.get_me()
    bot_username = me.username
    logger.info(f"Bot started as @{bot_username}")

    # --- 2. Redis для FSM-состояний и троттлинга ---
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    storage = RedisStorage(redis=redis.from_url(settings.REDIS_URL))  # своё соединение под FSM

    dp = Dispatcher(storage=storage)

    # Кладём общие данные, которые понадобятся хендлерам (referral.py и т.д.)
    dp["bot_username"] = bot_username

    # --- 3. Middlewares (порядок важен: сначала контекст юзера, потом троттлинг) ---
    dp.message.middleware(UserContextMiddleware())
    dp.callback_query.middleware(UserContextMiddleware())
    dp.message.middleware(ThrottlingMiddleware(redis_client))
    dp.callback_query.middleware(ThrottlingMiddleware(redis_client))

    # --- 4. Роутеры (все хендлеры бота) ---
    dp.include_router(get_main_router())

    # --- 5. База данных: создаём таблицы, если их ещё нет ---
    await init_models()
    logger.info("Database models initialized")

    # --- 6. Запускаем веб-сервер для вебхуков платежей ---
    webhook_app = create_webhook_app(bot)
    runner = web.AppRunner(webhook_app)
    await runner.setup()
    site = web.TCPSite(runner, settings.WEBHOOK_SERVER_HOST, settings.WEBHOOK_SERVER_PORT)
    await site.start()
    logger.info(
        f"Payment webhook server started on "
        f"{settings.WEBHOOK_SERVER_HOST}:{settings.WEBHOOK_SERVER_PORT}"
    )

    # --- 7. Запускаем бота (long polling) ---
    # На всякий случай удаляем возможный старый webhook Telegram-бота
    # (если раньше кто-то настраивал бота через setWebhook) — иначе
    # long polling и webhook будут конфликтовать.
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
