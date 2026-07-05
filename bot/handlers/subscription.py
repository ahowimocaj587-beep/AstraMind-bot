"""
=====================================================================
bot/handlers/subscription.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
Здесь обрабатываются:
- нажатие на "Weekly plan" / "Monthly plan" на пейволле →
  генерируем transaction_id и создаём "pending" платёж → показываем
  кнопку-ссылку на реальную оплату в Tribute.tg
- команда "Моя подписка" (menu:subscription) — просто показывает
  статус: активна/нет и до какой даты.

ВАЖНО: сама активация подписки происходит НЕ здесь, а в
webhook/payment_webhook.py — когда Tribute.tg подтвердит, что
деньги реально получены. Здесь мы только "открываем дверь" к оплате.
=====================================================================
"""

import uuid

from aiogram import Router, F
from aiogram.types import CallbackQuery

from core.db import get_session
from core.i18n import t
from bot.services.user_service import get_user_by_telegram_id
from bot.services.payment_service import get_payment_url, create_pending_payment
from bot.keyboards.keyboards import payment_link_keyboard

router = Router(name="subscription")


@router.callback_query(F.data.startswith("plan:"))
async def on_plan_selected(callback: CallbackQuery, user_language: str):
    """Пользователь выбрал тариф (weekly/monthly) на пейволле."""
    plan = callback.data.split(":")[1]  # "weekly" или "monthly"
    payment_url = get_payment_url(plan)

    if not payment_url:
        await callback.answer("Payment temporarily unavailable", show_alert=True)
        return

    # Генерируем собственный уникальный ID транзакции. Это позволяет
    # заранее создать в базе "pending" запись, а когда придёт вебхук
    # от Tribute.tg — сматчить его с этим платежом.
    # ВАЖНО: если Tribute.tg сам присылает свой transaction_id в ответе
    # на переход по ссылке (через deep-link параметр) — лучше
    # использовать именно его. Уточни в документации Tribute, как
    # они это передают, и подставь сюда вместо uuid4().
    transaction_id = f"tribute_{uuid.uuid4().hex}"

    async with get_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if user is None:
            await callback.answer()
            return
        await create_pending_payment(session, user, plan, transaction_id)

    await callback.message.answer(
        t("go_to_payment", user_language),
        reply_markup=payment_link_keyboard(user_language, payment_url),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:subscription")
async def show_subscription_status(callback: CallbackQuery, user_language: str):
    """Показывает текущий статус подписки пользователя."""
    async with get_session() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)

    if user is None or not user.has_active_subscription:
        await callback.message.answer(t("no_subscription", user_language))
        await callback.answer()
        return

    end_date_str = user.subscription_end.strftime("%d.%m.%Y")
    await callback.message.answer(
        t(
            "my_subscription",
            user_language,
            status=user.plan_type or "active",
            end_date=end_date_str,
        )
    )
    await callback.answer()
