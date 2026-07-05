"""
=====================================================================
bot/handlers/start.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
Хендлер (handler) — это функция, которая обрабатывает конкретное
событие: команду, нажатие кнопки, текстовое сообщение.

Этот файл отвечает за самый первый контакт пользователя с ботом:
- команда /start (в том числе с реферальным параметром ?start=ref_123)
- выбор языка (кнопки от language_keyboard())
- показ приветствия и главного меню тем

Router — это "мини-приложение" внутри aiogram, группа хендлеров.
Все роутеры потом собираются вместе в bot/handlers/__init__.py и
подключаются к главному Dispatcher в main.py.
=====================================================================
"""

from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from core.db import get_session
from core.i18n import t
from bot.services.user_service import get_or_create_user, set_language
from bot.services.referral_service import parse_referral_payload, register_referral, build_referral_link
from bot.keyboards.keyboards import language_keyboard, topics_keyboard
from bot.states.states import OracleStates

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    """
    Обрабатывает /start.
    command.args содержит то, что идёт после /start, например
    "ref_123456789" — это и есть реферальный параметр.
    """
    referrer_telegram_id = parse_referral_payload(command.args)

    async with get_session() as session:
        user, is_new = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            referred_by=referrer_telegram_id if referrer_telegram_id else None,
        )

        # Начисляем бонус пригласившему ТОЛЬКО если это реально новый юзер
        # (иначе пользователь мог бы много раз слать /start ref_ и фармить бонусы)
        if is_new and referrer_telegram_id:
            await register_referral(session, message.from_user.id, referrer_telegram_id)

    if is_new:
        # Новый пользователь — сначала спрашиваем язык
        await state.set_state(OracleStates.choosing_language)
        await message.answer(
            t("choose_language", "en"),  # показываем на английском, т.к. язык ещё не выбран
            reply_markup=language_keyboard(),
        )
    else:
        # Уже существующий пользователь — сразу в меню тем на его языке
        await state.set_state(OracleStates.choosing_topic)
        await message.answer(
            t("welcome", user.language, free_left=user.free_messages_left),
            reply_markup=topics_keyboard(user.language),
        )


@router.callback_query(F.data.startswith("lang:"))
async def on_language_selected(callback: CallbackQuery, state: FSMContext):
    """Пользователь нажал на одну из кнопок выбора языка."""
    lang_code = callback.data.split(":")[1]

    async with get_session() as session:
        from bot.services.user_service import get_user_by_telegram_id
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if user is None:
            await callback.answer()
            return
        await set_language(session, user, lang_code)
        free_left = user.free_messages_left

    await state.set_state(OracleStates.choosing_topic)
    await callback.message.edit_text(
        t("welcome", lang_code, free_left=free_left),
    )
    await callback.message.answer(
        t("choose_topic", lang_code),
        reply_markup=topics_keyboard(lang_code),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:topics")
async def back_to_topics(callback: CallbackQuery, state: FSMContext, user_language: str):
    """Кнопка 'назад в меню' — возвращает к выбору темы."""
    await state.set_state(OracleStates.choosing_topic)
    await callback.message.edit_text(t("choose_topic", user_language))
    await callback.message.edit_reply_markup(reply_markup=topics_keyboard(user_language))
    await callback.answer()
