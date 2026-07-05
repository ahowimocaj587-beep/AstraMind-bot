"""
=====================================================================
bot/services/runtime_config_service.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
В ТЗ есть требование: "change AI prompt without redeploy" и
"enable/disable features" из админки. Если хранить это в .env —
пришлось бы каждый раз пересобирать и перезапускать бота (redeploy).

Вместо этого мы храним такие "изменяемые на лету" настройки в Redis —
это быстрое хранилище ключ-значение, которое у нас и так подключено
для rate limiting. Админ меняет значение командой в боте →
мы пишем новое значение в Redis → все следующие запросы сразу видят
изменение, без перезапуска бота.

Что тут хранится:
- custom_system_prompt_suffix — доп. текст, который "приклеивается"
  к системному промпту оракула (см. ai_service.py)
- feature flags — вкл/выкл отдельных функций (например, реферальную
  программу можно временно отключить не трогая код)
=====================================================================
"""

import redis.asyncio as redis
from core.config import settings

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


PROMPT_SUFFIX_KEY = "config:ai_prompt_suffix"
FEATURE_FLAG_PREFIX = "config:feature:"

DEFAULT_FEATURES = {
    "referrals": True,
    "subscriptions": True,
    "daily_guidance": True,
}


async def get_prompt_suffix() -> str:
    """Возвращает дополнительный текст для системного промпта (или пустую строку)."""
    r = get_redis()
    value = await r.get(PROMPT_SUFFIX_KEY)
    return value or ""


async def set_prompt_suffix(text: str) -> None:
    """Админ меняет промпт 'на лету' через /admin -> изменить промпт."""
    r = get_redis()
    await r.set(PROMPT_SUFFIX_KEY, text)


async def is_feature_enabled(feature_name: str) -> bool:
    r = get_redis()
    value = await r.get(f"{FEATURE_FLAG_PREFIX}{feature_name}")
    if value is None:
        return DEFAULT_FEATURES.get(feature_name, True)
    return value == "1"


async def set_feature_enabled(feature_name: str, enabled: bool) -> None:
    r = get_redis()
    await r.set(f"{FEATURE_FLAG_PREFIX}{feature_name}", "1" if enabled else "0")
