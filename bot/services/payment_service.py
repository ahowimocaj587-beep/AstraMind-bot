"""
=====================================================================
bot/services/payment_service.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
Здесь вся логика подписок: создание "ожидающего" платежа, активация
подписки после успешной оплаты, продление и т.д.

ВАЖНО про Tribute.tg:
Tribute.tg — сервис приёма платежей внутри Telegram. У него два
основных сценария интеграции:
  1) Ты создаёшь тарифы (подписки) в личном кабинете Tribute и
     получаешь на каждый тариф персональную ссылку оплаты
     (TRIBUTE_WEEKLY_PAYMENT_URL / TRIBUTE_MONTHLY_PAYMENT_URL в .env).
     Пользователь просто нажимает кнопку и платит внутри Telegram.
  2) Tribute шлёт вебхук (HTTP POST) на твой сервер, когда платёж
     прошёл — и ты активируешь подписку у себя в базе.

Так как формат вебхука может отличаться в зависимости от версии
API Tribute (это описано у них в личном кабинете разработчика),
здесь сделана ГИБКАЯ обработка: мы читаем `event`, `status`,
`transaction_id`, `telegram_user_id`, `plan` из JSON тела запроса.
Если у тебя другие названия полей — поправь их в
`webhook/payment_webhook.py`, в месте, где парсится JSON (там всё
подписано, где именно менять).

Проверка подписи (signature) реализована через HMAC-SHA256 —
это стандартный способ, которым большинство платёжных провайдеров
(включая Tribute) подписывают вебхуки, чтобы никто посторонний не
мог просто отправить fake-запрос "оплата прошла".
=====================================================================
"""

import hmac
import hashlib
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import User, Payment
from core.config import settings
from bot.services.referral_service import register_referral_conversion

logger = logging.getLogger(__name__)

PLAN_DURATIONS = {
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
}

PLAN_PRICES_USD = {
    "weekly": 4.99,
    "monthly": 14.99,
}


def get_payment_url(plan: str) -> str | None:
    """Возвращает ссылку на оплату для выбранного тарифа."""
    if plan == "weekly":
        return settings.TRIBUTE_WEEKLY_PAYMENT_URL
    if plan == "monthly":
        return settings.TRIBUTE_MONTHLY_PAYMENT_URL
    return None


def verify_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
    """
    Проверяет, что вебхук действительно прислан Tribute.tg, а не кем-то
    посторонним. Используем HMAC-SHA256 с секретом TRIBUTE_WEBHOOK_SECRET.

    Если Tribute.tg в реальном личном кабинете использует другой алгоритм
    подписи (например, просто сверку заголовка с секретом, или другой хэш) —
    достаточно поменять реализацию только этой функции, остальной код
    трогать не нужно.
    """
    if not settings.TRIBUTE_WEBHOOK_SECRET:
        # Секрет не настроен — в деве можно пропустить, но в проде это ОПАСНО.
        logger.warning("TRIBUTE_WEBHOOK_SECRET is empty — skipping signature check (DEV ONLY)")
        return True

    expected = hmac.new(
        settings.TRIBUTE_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header or "")


async def create_pending_payment(
    session: AsyncSession,
    user: User,
    plan: str,
    transaction_id: str,
) -> Payment:
    """Создаёт запись о платеже со статусом 'pending' (до подтверждения вебхуком)."""
    payment = Payment(
        user_id=user.id,
        plan=plan,
        status="pending",
        amount=PLAN_PRICES_USD.get(plan, 0.0),
        currency="USD",
        transaction_id=transaction_id,
    )
    session.add(payment)
    await session.flush()
    return payment


async def activate_subscription(
    session: AsyncSession,
    telegram_id: int,
    plan: str,
    transaction_id: str,
) -> User | None:
    """
    Активирует (или продлевает) подписку пользователя.
    Вызывается из webhook/payment_webhook.py после успешной оплаты.

    Если платёж с таким transaction_id уже был обработан — не делаем
    ничего повторно (защита от повторных вебхуков — Tribute, как и
    большинство провайдеров, может присылать один и тот же вебхук
    несколько раз).
    """
    result = await session.execute(
        select(Payment).where(Payment.transaction_id == transaction_id)
    )
    existing_payment = result.scalar_one_or_none()
    if existing_payment is not None and existing_payment.status == "success":
        logger.info(f"Payment {transaction_id} already processed, skipping")
        result_user = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result_user.scalar_one_or_none()

    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        logger.error(f"Payment webhook for unknown user telegram_id={telegram_id}")
        return None

    duration = PLAN_DURATIONS.get(plan, timedelta(days=30))
    is_first_subscription = user.subscription_status != "active"

    # Если подписка ещё активна — продлеваем от даты окончания,
    # а не от "сейчас" (чтобы не терять оплаченное время).
    base_date = user.subscription_end if user.has_active_subscription else datetime.utcnow()
    user.subscription_status = "active"
    user.plan_type = plan
    user.subscription_end = base_date + duration

    if existing_payment is not None:
        existing_payment.status = "success"
    else:
        payment = Payment(
            user_id=user.id,
            plan=plan,
            status="success",
            amount=PLAN_PRICES_USD.get(plan, 0.0),
            currency="USD",
            transaction_id=transaction_id,
        )
        session.add(payment)

    if is_first_subscription:
        await register_referral_conversion(session, user)

    return user


async def check_and_expire_subscriptions(session: AsyncSession) -> int:
    """
    Проверяет все "active" подписки и переводит просроченные в "expired".
    Эту функцию удобно вызывать по расписанию (cron / APScheduler) —
    например, раз в час. В MVP её также можно дёргать вручную из админки.
    """
    result = await session.execute(
        select(User).where(User.subscription_status == "active")
    )
    users = result.scalars().all()
    expired_count = 0
    now = datetime.utcnow()
    for user in users:
        if user.subscription_end and user.subscription_end < now:
            user.subscription_status = "expired"
            expired_count += 1
    return expired_count
