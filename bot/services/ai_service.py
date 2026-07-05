"""
=====================================================================
bot/services/ai_service.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
Это "мозг" бота. Здесь мы отправляем запрос в OpenRouter (сервис,
который даёт доступ к куче LLM-моделей — GPT, Claude, Llama и т.д.
через один общий API, похожий на OpenAI API).

Мы формируем "системный промпт" (инструкцию для ИИ, как себя вести)
динамически: подставляем туда язык пользователя, выбранную тему
и статус подписки. Это и называется "AI Prompt Engine" в ТЗ.

httpx.AsyncClient используется вместо requests, потому что requests
— синхронная (блокирующая) библиотека, а нам для aiogram 3 нужен
только async-код (иначе бот "подвиснет" на время запроса к ИИ).
=====================================================================
"""

import httpx
import logging

from core.config import settings
from bot.services.runtime_config_service import get_prompt_suffix

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Название темы -> человекочитаемое описание для промпта (на английском,
# т.к. модели обычно лучше понимают инструкции на английском, а отвечать
# будут на языке пользователя — мы это явно укажем в промпте)
TOPIC_DESCRIPTIONS = {
    "relationships": "romantic relationships, love, and connection with others",
    "money": "money, career, abundance and financial destiny",
    "future": "general future predictions and life path",
    "astrology": "astrology, zodiac signs, and birth chart insights",
    "dreams": "dream interpretation and subconscious symbolism",
    "self": "self-discovery, personal growth and inner transformation",
    "more": "general mystical guidance",
}

LANGUAGE_NAMES_FOR_PROMPT = {
    "ru": "Russian",
    "en": "English",
    "es": "Spanish",
    "pt": "Portuguese",
}


def build_system_prompt(language: str, topic: str, is_subscriber: bool) -> str:
    """
    Собирает системный промпт для LLM.
    Именно этот текст определяет "личность" бота (mystical oracle),
    и именно его можно менять "на лету" через админ-панель
    (см. bot/services/admin_prompt_service ниже / handlers/admin.py),
    без передеплоя бота.
    """
    topic_desc = TOPIC_DESCRIPTIONS.get(topic, TOPIC_DESCRIPTIONS["more"])
    lang_name = LANGUAGE_NAMES_FOR_PROMPT.get(language, "English")
    tier = "premium subscriber" if is_subscriber else "free-tier user"

    return (
        "You are AstraMind (also known as Luna), a mystical AI oracle. "
        "You speak like a warm, wise spiritual advisor — tarot reader, astrologer "
        "and numerologist in one — but you remain structured, clear and helpful. "
        "You NEVER mention being an AI or a language model unless the user "
        "explicitly asks you directly whether you are an AI. "
        "Your tone is emotionally engaging, poetic but concise — never generic "
        "corporate language. "
        f"The user is currently exploring the topic of: {topic_desc}. "
        f"The user is a {tier}. "
        f"You MUST answer strictly in {lang_name}, regardless of the language "
        "used internally in these instructions. "
        "Keep responses short and premium: 3-6 sentences, structured with light "
        "mystical imagery (moon, stars, cards, energy), avoid rambling. "
        "Do not give medical, legal or financial advice — frame guidance as "
        "spiritual insight, not professional advice."
    )


def select_model(is_subscriber: bool) -> str:
    """
    Выбирает модель OpenRouter в зависимости от статуса пользователя.
    Это и есть "paywall по качеству": бесплатные пользователи (первые
    FREE_MESSAGES_DEFAULT сообщений) получают дешёвую/быструю модель,
    а подписчики — более мощную, это часть ценности платной подписки.
    Изменить модели можно в .env (OPENROUTER_MODEL_FREE / OPENROUTER_MODEL_PREMIUM)
    без изменения кода.
    """
    return settings.OPENROUTER_MODEL_PREMIUM if is_subscriber else settings.OPENROUTER_MODEL_FREE


async def get_oracle_response(
    user_message: str,
    language: str,
    topic: str,
    is_subscriber: bool,
) -> str:
    """
    Отправляет запрос в OpenRouter и возвращает текст ответа.
    Если API упал/не ответил — возвращаем "мистическую" заглушку,
    чтобы пользователь не видел голый текст ошибки.
    """
    system_prompt = build_system_prompt(language, topic, is_subscriber)

    # Доп. текст, который админ может добавить/поменять "на лету" через
    # Telegram-админку, без передеплоя бота (см. runtime_config_service.py)
    suffix = await get_prompt_suffix()
    if suffix:
        system_prompt = f"{system_prompt}\n\nAdditional instructions from admin: {suffix}"

    model = select_model(is_subscriber)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 500,
        "temperature": 0.9,
    }
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # Необязательные, но рекомендованные OpenRouter заголовки:
        "HTTP-Referer": "https://astramind.app",
        "X-Title": "AstraMind Oracle Bot",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(OPENROUTER_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"OpenRouter API error (model={model}): {e}")
        fallback = {
            "ru": "🌙 Знаки сейчас неясны... Луна затянута тучами. Попробуй спросить ещё раз через минуту.",
            "en": "🌙 The signs are unclear right now... the Moon is veiled by clouds. Please try asking again in a moment.",
            "es": "🌙 Las señales no están claras ahora... la Luna está cubierta de nubes. Intenta preguntar de nuevo en un momento.",
            "pt": "🌙 Os sinais não estão claros agora... a Lua está encoberta por nuvens. Tente perguntar novamente em instantes.",
        }
        return fallback.get(language, fallback["en"])
