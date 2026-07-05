"""
=====================================================================
bot/services/analytics_service.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
Все SQL-запросы для админ-дашборда собраны здесь в одном месте.
Хендлер admin.py просто вызывает эти функции и красиво форматирует
результат в текст сообщения.

DAU  = Daily Active Users  (сколько разных людей писали боту сегодня)
WAU  = Weekly Active Users (сколько разных людей писали боту за 7 дней)
Conversion rate = % пользователей, которые стали платными подписчиками
=====================================================================
"""

from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import User, Payment


async def get_dashboard_stats(session: AsyncSession) -> dict:
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_ago = now - timedelta(days=7)

    total_users = (await session.execute(select(func.count(User.id)))).scalar_one()

    dau = (
        await session.execute(
            select(func.count(User.id)).where(User.last_active_at >= today_start)
        )
    ).scalar_one()

    wau = (
        await session.execute(
            select(func.count(User.id)).where(User.last_active_at >= week_ago)
        )
    ).scalar_one()

    active_subs = (
        await session.execute(
            select(func.count(User.id)).where(User.subscription_status == "active")
        )
    ).scalar_one()

    total_paid_users = (
        await session.execute(
            select(func.count(func.distinct(Payment.user_id))).where(Payment.status == "success")
        )
    ).scalar_one()

    total_revenue = (
        await session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0.0)).where(Payment.status == "success")
        )
    ).scalar_one()

    conversion_rate = (total_paid_users / total_users * 100) if total_users else 0.0

    # Простая оценка churn: истёкшие подписки / (истёкшие + активные)
    expired_subs = (
        await session.execute(
            select(func.count(User.id)).where(User.subscription_status == "expired")
        )
    ).scalar_one()
    denom = expired_subs + active_subs
    churn_estimate = (expired_subs / denom * 100) if denom else 0.0

    new_users_today = (
        await session.execute(
            select(func.count(User.id)).where(User.created_at >= today_start)
        )
    ).scalar_one()

    return {
        "total_users": total_users,
        "new_users_today": new_users_today,
        "dau": dau,
        "wau": wau,
        "active_subscribers": active_subs,
        "total_paid_users": total_paid_users,
        "total_revenue": round(float(total_revenue), 2),
        "conversion_rate": round(conversion_rate, 2),
        "churn_estimate": round(churn_estimate, 2),
    }


async def find_user_details(session: AsyncSession, telegram_id: int) -> dict | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        return None
    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "language": user.language,
        "free_messages_left": user.free_messages_left,
        "subscription_status": user.subscription_status,
        "plan_type": user.plan_type,
        "subscription_end": user.subscription_end,
        "referrals_count": user.referrals_count,
        "referrals_converted": user.referrals_converted,
        "is_banned": user.is_banned,
        "created_at": user.created_at,
    }


async def get_all_active_telegram_ids(session: AsyncSession) -> list[int]:
    """Для рассылки (broadcast) — список всех telegram_id, кто не забанен."""
    result = await session.execute(select(User.telegram_id).where(User.is_banned == False))  # noqa: E712
    return [row[0] for row in result.all()]
