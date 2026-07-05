"""
=====================================================================
webhook/payment_webhook.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
Это отдельный маленький веб-сервер (не Telegram-бот!), который
слушает HTTP-запросы. Tribute.tg, когда пользователь успешно платит,
отправляет POST-запрос на наш сервер — это и называется "вебхук"
(webhook = "веб-крючок", на который вешается уведомление о событии).

Мы используем aiohttp.web — лёгкий встроенный веб-фреймворк, который
отлично уживается в одном asyncio-цикле вместе с aiogram-ботом (см.
main.py, где мы запускаем и бота, и этот веб-сервер одновременно).

ЧТО НУЖНО НАСТРОИТЬ В КАБИНЕТЕ TRIBUTE.TG:
Указать URL вебхука вида: https://ТВОЙ_ДОМЕН:8080/webhook/tribute
(порт и путь можно поменять — просто используй тот же и там, и тут).

ФОРМАТ ТЕЛА ЗАПРОСА:
Ожидаем примерно такой JSON (уточни точный формат в документации
Tribute.tg личном кабинете — там будет actual payload example):
{
  "event": "payment.success",
  "transaction_id": "abc123",
  "telegram_user_id": 123456789,
  "plan": "monthly",
  "status": "success"
}
Если у Tribute другие названия полей — поменяй их ТОЛЬКО в функции
`handle_tribute_webhook` ниже, в блоке "# <-- парсинг полей".
=====================================================================
"""

import logging
from aiohttp import web
from aiogram import Bot

from core.db import get_session
from core.i18n import t
from bot.services.payment_service import verify_webhook_signature, activate_subscription

logger = logging.getLogger(__name__)


def create_webhook_app(bot: Bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_post("/webhook/tribute", handle_tribute_webhook)
    app.router.add_get("/health", handle_health_check)
    return app


async def handle_health_check(request: web.Request) -> web.Response:
    """Простой эндпоинт для проверки, что сервер жив (полезно для Railway healthcheck)."""
    return web.json_response({"status": "ok"})


async def handle_tribute_webhook(request: web.Request) -> web.Response:
    raw_body = await request.read()
    signature = request.headers.get("X-Tribute-Signature", "")

    if not verify_webhook_signature(raw_body, signature):
        logger.warning("Invalid Tribute webhook signature — request rejected")
        return web.json_response({"error": "invalid signature"}, status=403)

    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)

    # <-- парсинг полей: поменяй ключи здесь, если у Tribute другие названия
    event = payload.get("event")
    status = payload.get("status")
    transaction_id = payload.get("transaction_id")
    telegram_user_id = payload.get("telegram_user_id")
    plan = payload.get("plan")

    if status != "success" or not all([transaction_id, telegram_user_id, plan]):
        logger.info(f"Tribute webhook ignored (status={status}, event={event})")
        return web.json_response({"status": "ignored"})

    async with get_session() as session:
        user = await activate_subscription(
            session,
            telegram_id=int(telegram_user_id),
            plan=plan,
            transaction_id=transaction_id,
        )

    if user is not None:
        bot: Bot = request.app["bot"]
        end_date_str = user.subscription_end.strftime("%d.%m.%Y")
        try:
            await bot.send_message(
                user.telegram_id,
                t("subscription_activated", user.language, end_date=end_date_str),
            )
        except Exception as e:
            logger.warning(f"Could not notify user {user.telegram_id} about subscription: {e}")

    return web.json_response({"status": "ok"})
