"""
=====================================================================
bot/keyboards/keyboards.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
Здесь собраны ВСЕ inline-кнопки (клавиатуры), которые показывает бот.
Каждая функция возвращает объект InlineKeyboardMarkup — это и есть
"кнопки под сообщением".

У каждой кнопки есть `callback_data` — это скрытый "код команды",
который бот получает, когда пользователь нажимает на кнопку.
Например: callback_data="lang:ru" → в хендлере мы проверяем, что
пользователь выбрал русский язык.
=====================================================================
"""

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

from core.i18n import t, LANGUAGE_NAMES, SUPPORTED_LANGUAGES
from core.config import settings


def language_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора языка (показывается при первом /start)."""
    builder = InlineKeyboardBuilder()
    for lang_code in SUPPORTED_LANGUAGES:
        builder.button(text=LANGUAGE_NAMES[lang_code], callback_data=f"lang:{lang_code}")
    builder.adjust(2)  # по 2 кнопки в ряд
    return builder.as_markup()


def topics_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Главное меню тем оракула (после выбора языка / по команде /menu)."""
    builder = InlineKeyboardBuilder()
    topics = [
        ("topic_relationships", "topic:relationships"),
        ("topic_money", "topic:money"),
        ("topic_future", "topic:future"),
        ("topic_astrology", "topic:astrology"),
        ("topic_dreams", "topic:dreams"),
        ("topic_self", "topic:self"),
        ("topic_more", "topic:more"),
    ]
    for key, callback in topics:
        builder.button(text=t(key, lang), callback_data=callback)
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


def more_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Доп. меню: подписка / рефералка / назад к темам."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("subscription_button", lang), callback_data="menu:subscription")
    builder.button(text=t("referral_button", lang), callback_data="menu:referral")
    builder.button(text=t("menu_button", lang), callback_data="menu:topics")
    builder.adjust(1)
    return builder.as_markup()


def paywall_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Клавиатура пейволла: выбор тарифа (Weekly / Monthly)."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=t("plan_weekly", lang, price=settings.WEEKLY_PRICE_TEXT),
        callback_data="plan:weekly",
    )
    builder.button(
        text=t("plan_monthly", lang, price=settings.MONTHLY_PRICE_TEXT),
        callback_data="plan:monthly",
    )
    builder.adjust(1)
    return builder.as_markup()


def payment_link_keyboard(lang: str, payment_url: str) -> InlineKeyboardMarkup:
    """Кнопка-ссылка на реальную страницу оплаты Tribute.tg."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("pay_button", lang), url=payment_url)
    return builder.as_markup()
