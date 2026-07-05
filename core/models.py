"""
=====================================================================
core/models.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
Здесь описаны таблицы базы данных в виде Python-классов
(это называется ORM — Object Relational Mapping).
Вместо того чтобы писать сырые SQL-запросы вроде
"CREATE TABLE users (...)", мы описываем класс `User`, а
SQLAlchemy сам превращает его в таблицу в PostgreSQL.

Таблицы:
- User        — все пользователи бота
- Payment     — все платежи (успешные и неуспешные)
- DailyStat   — агрегированная статистика по дням (для админ-дашборда)
- BroadcastLog— история рассылок (чтобы админ видел, что уже отправлял)
=====================================================================
"""

from datetime import datetime, date
from sqlalchemy import (
    BigInteger, String, Integer, Boolean, DateTime, Date,
    ForeignKey, Text, Float
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс, от которого наследуются все таблицы."""
    pass


class User(Base):
    __tablename__ = "users"

    # Внутренний ID записи в нашей базе (не путать с telegram_id!)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ID пользователя в Telegram (уникальный, по нему всегда ищем юзера)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)

    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Язык интерфейса: ru / en / es / pt
    language: Mapped[str] = mapped_column(String(5), default="en")

    # Сколько бесплатных AI-сообщений осталось у пользователя
    free_messages_left: Mapped[int] = mapped_column(Integer, default=10)

    # Статус подписки: "none" / "active" / "expired"
    subscription_status: Mapped[str] = mapped_column(String(20), default="none")
    # Тип тарифа: "weekly" / "monthly" / None
    plan_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Когда подписка заканчивается (если активна)
    subscription_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Реферальная система
    referred_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # telegram_id пригласившего
    referrals_count: Mapped[int] = mapped_column(Integer, default=0)
    referrals_converted: Mapped[int] = mapped_column(Integer, default=0)  # сколько рефералов стали платными
    bonus_messages_earned: Mapped[int] = mapped_column(Integer, default=0)

    # Бан пользователя администратором
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)

    # Служебные поля
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    payments: Mapped[list["Payment"]] = relationship(back_populates="user")

    @property
    def has_active_subscription(self) -> bool:
        """Удобное свойство: True, если подписка сейчас активна и не истекла."""
        if self.subscription_status != "active":
            return False
        if self.subscription_end is None:
            return False
        return self.subscription_end > datetime.utcnow()


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    plan: Mapped[str] = mapped_column(String(20))         # "weekly" / "monthly"
    status: Mapped[str] = mapped_column(String(20))       # "pending" / "success" / "failed"
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    # ID транзакции от Tribute.tg — по нему находим платёж при вебхуке
    transaction_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="payments")


class DailyStat(Base):
    """
    Одна строка = один день статистики.
    Обновляется каждый раз, когда пользователь пишет боту или платит.
    Нужно для быстрого построения графиков в админке (без тяжёлых SQL-запросов).
    """
    __tablename__ = "daily_stats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    day: Mapped[date] = mapped_column(Date, unique=True, index=True)

    new_users: Mapped[int] = mapped_column(Integer, default=0)
    active_users: Mapped[int] = mapped_column(Integer, default=0)
    ai_messages_sent: Mapped[int] = mapped_column(Integer, default=0)
    new_subscriptions: Mapped[int] = mapped_column(Integer, default=0)
    revenue: Mapped[float] = mapped_column(Float, default=0.0)


class BroadcastLog(Base):
    """История рассылок админа — просто для аудита/истории."""
    __tablename__ = "broadcast_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    admin_telegram_id: Mapped[int] = mapped_column(BigInteger)
    text: Mapped[str] = mapped_column(Text)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
