"""
=====================================================================
core/config.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
Это "пульт управления" всем проектом. Вместо того чтобы разбрасывать
токены и пароли по всему коду, мы один раз читаем их из файла .env
и складываем в один объект `settings`. Дальше в любом файле проекта
пишем: `from core.config import settings` и берём `settings.BOT_TOKEN`
и т.д. Это удобно и безопасно (секреты не попадают в git).

pydantic-settings сам умеет читать .env файл и проверяет типы
(например, что ADMIN_IDS — это список чисел, а не текст).
=====================================================================
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    # --- Telegram ---
    BOT_TOKEN: str
    ADMIN_IDS: str = ""  # строка вида "111,222", распарсим ниже в свойстве

    # --- База данных ---
    DATABASE_URL: str

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- OpenRouter (LLM) ---
    OPENROUTER_API_KEY: str
    # Модель для бесплатных пользователей (первые FREE_MESSAGES_DEFAULT сообщений) —
    # берём дешёвую и быструю модель, чтобы не сжигать бюджет на пробный период
    OPENROUTER_MODEL_FREE: str = "anthropic/claude-3-5-haiku"
    # Модель для подписчиков — более мощная/качественная, это часть ценности подписки
    OPENROUTER_MODEL_PREMIUM: str = "anthropic/claude-sonnet-4"

    # --- Tribute.tg ---
    TRIBUTE_API_KEY: str = ""
    TRIBUTE_WEBHOOK_SECRET: str = ""
    TRIBUTE_WEEKLY_PAYMENT_URL: str = ""
    TRIBUTE_MONTHLY_PAYMENT_URL: str = ""

    # --- Продукт ---
    FREE_MESSAGES_DEFAULT: int = 10
    REFERRAL_BONUS_MESSAGES: int = 5
    WEEKLY_PRICE_TEXT: str = "$4.99 / week"
    MONTHLY_PRICE_TEXT: str = "$14.99 / month"

    # --- Rate limit ---
    THROTTLE_RATE_LIMIT: float = 3.0

    # --- Webhook сервер ---
    WEBHOOK_SERVER_HOST: str = "0.0.0.0"
    WEBHOOK_SERVER_PORT: int = 8080

    # --- Прочее ---
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def admin_ids_list(self) -> List[int]:
        """Превращает строку '111,222' в список [111, 222]."""
        if not self.ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip()]


# Один общий объект настроек на весь проект (создаётся один раз при импорте)
settings = Settings()
