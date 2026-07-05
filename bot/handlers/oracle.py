"""
=====================================================================
bot/handlers/oracle.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
Это ГЛАВНЫЙ файл продукта — тут происходит:
1. Выбор темы (Отношения / Деньги / Будущее / Астрология / Сны / ...)
2. Сам AI-чат: пользователь пишет текст → мы проверяем лимит
   бесплатных сообщений → если лимит не исчерпан (или есть подписка) —
   отправляем запрос в OpenRouter (ai_service.py) → показываем ответ.
3. Если лимит исчерпан — показываем пейволл (paywall) вместо ответа.

Порядок действий внутри `handle_oracle_message` важен:
сначала проверяем ЛИМИТ, потом (если есть доступ) СПИСЫВАЕМ
сообщение, потом уже идём в AI. Если бы мы списывали after — можно
было бы "проспамить" запросы, пока идёт ответ от AI (двойное
списание/обход лимита через параллельные запросы). Плюс throttling
middleware (bot/middlewares/throttling.py) уже защищает от спама
кнопками/сообщениями на уровне "не чаще 1 раза в N секунд".
=====================================================================
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from core.db import get_session
from core.i18n import t
from bot.services.user_service import (
    get_user_by_telegram_id,
    has_messages_available,
    consume_message,
)
from bot.services.ai_service import get_oracle_response
from bot.keyboards.keyboards import paywall_keyboard, more_menu_keyboard
from bot.states.states import OracleStates

router = Router(name="oracle")

TOPIC_CODES = {"relationships", "money", "future", "astrology", "dreams", "self", "more"}


@router.callback_query(F.data.startswith("topic:"))
async def on_topic_selected(callback: CallbackQuery, state: FSMContext, user_language: str):
    """Пользователь выбрал тему из главного меню."""
    topic = callback.data.split(":")[1]

    if topic == "more":
        await callback.message.edit_text(t("choose_topic", user_language))
        await callback.message.edit_reply_markup(reply_markup=more_menu_keyboard(user_language))
        await callback.answer()
        return

    # Запоминаем выбранную тему в данных состояния (FSM data),
    # чтобы потом использовать её при формировании AI-промпта.
    await state.update_data(topic=topic)
    await state.set_state(OracleStates.chatting)

    await callback.message.edit_text(t("topic_selected", user_language))
    await callback.answer()


@router.message(OracleStates.chatting, F.text)
async def handle_oracle_message(message: Message, state: FSMContext, user_language: str):
    """
    Пользователь написал текстовый вопрос оракулу.
    Это основной "монетизируемый" путь в боте.
    """
    data = await state.get_data()
    topic = data.get("topic", "more")

    async with get_session() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if user is None:
            return  # защита от гонки состояний; обычно недостижимо

        if not await has_messages_available(user):
            # Лимит исчерпан и подписки нет -> показываем пейволл вместо ответа
            await message.answer(
                t("paywall", user_language),
                reply_markup=paywall_keyboard(user_language),
            )
            return

        # Списываем сообщение ДО обращения к AI (см. объяснение в шапке файла)
        await consume_message(session, user)
        is_subscriber = user.has_active_subscription
        free_left = user.free_messages_left

    thinking_msg = await message.answer(t("ai_thinking", user_language))

    ai_answer = await get_oracle_response(
        user_message=message.text,
        language=user_language,
        topic=topic,
        is_subscriber=is_subscriber,
    )

    footer = "" if is_subscriber else t("messages_left", user_language, left=free_left)
    await thinking_msg.edit_text(f"{ai_answer}{footer}")


@router.message(OracleStates.choosing_topic, F.text)
@router.message(OracleStates.choosing_language, F.text)
async def prompt_to_use_buttons(message: Message, user_language: str):
    """
    Если пользователь пишет текст, находясь не в режиме чата (например,
    ещё не выбрал тему) — вежливо просим воспользоваться кнопками.
    Это защищает от "потерянных" сообщений без ответа.
    """
    await message.answer(t("choose_topic", user_language))
