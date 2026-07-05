"""
=====================================================================
bot/handlers/admin.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
Это админ-панель ПРЯМО ВНУТРИ Telegram (проще и быстрее в разработке,
чем отдельная веб-панель, и админу не нужно никуда заходить кроме
самого Telegram).

Доступ есть только у telegram_id, перечисленных в .env -> ADMIN_IDS.
Проверка происходит через фильтр `AdminFilter` — это класс-фильтр
aiogram, который просто возвращает True/False: "разрешить ли
обработку этого сообщения дальше".

Команды админа:
  /admin            — показать меню админки
  /stats            — аналитика (DAU/WAU/конверсия/доход)
  /find <id>        — найти пользователя по telegram_id
  /ban <id>         — забанить пользователя
  /unban <id>       — разбанить пользователя
  /broadcast        — начать рассылку всем пользователям (спросит текст)
  /setprompt        — изменить AI-промпт "на лету" без передеплоя
  /features         — включить/выключить фичи (рефералка, подписки и т.д.)
=====================================================================
"""

import asyncio
import logging

from aiogram import Router, F, Bot
from aiogram.filters import Command, BaseFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from core.config import settings
from core.db import get_session
from bot.services.analytics_service import get_dashboard_stats, find_user_details, get_all_active_telegram_ids
from bot.services.user_service import ban_user, unban_user
from bot.services.runtime_config_service import (
    set_prompt_suffix, get_prompt_suffix, is_feature_enabled, set_feature_enabled, DEFAULT_FEATURES
)
from bot.states.states import AdminStates
from core.models import BroadcastLog

logger = logging.getLogger(__name__)
router = Router(name="admin")


class AdminFilter(BaseFilter):
    """Пропускает дальше только сообщения от telegram_id из ADMIN_IDS."""

    async def __call__(self, message: Message) -> bool:
        return message.from_user is not None and message.from_user.id in settings.admin_ids_list


# Применяем фильтр АДМИНА сразу ко всему роутеру — так каждый хендлер
# ниже автоматически защищён, не нужно дублировать проверку в каждом.
router.message.filter(AdminFilter())


@router.message(Command("admin"))
async def admin_menu(message: Message):
    await message.answer(
        "🛠 <b>AstraMind Admin Panel</b>\n\n"
        "/stats — analytics dashboard\n"
        "/find <code>&lt;telegram_id&gt;</code> — find user\n"
        "/ban <code>&lt;telegram_id&gt;</code> — ban user\n"
        "/unban <code>&lt;telegram_id&gt;</code> — unban user\n"
        "/broadcast — send message to all users\n"
        "/setprompt — change AI prompt suffix (no redeploy)\n"
        "/features — toggle features on/off"
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    async with get_session() as session:
        stats = await get_dashboard_stats(session)

    text = (
        "📊 <b>Analytics Dashboard</b>\n\n"
        f"👥 Total users: <b>{stats['total_users']}</b>\n"
        f"🆕 New today: <b>{stats['new_users_today']}</b>\n"
        f"🔥 DAU: <b>{stats['dau']}</b>\n"
        f"📅 WAU: <b>{stats['wau']}</b>\n\n"
        f"💎 Active subscribers: <b>{stats['active_subscribers']}</b>\n"
        f"💰 Total paid users: <b>{stats['total_paid_users']}</b>\n"
        f"📈 Conversion rate: <b>{stats['conversion_rate']}%</b>\n"
        f"📉 Churn estimate: <b>{stats['churn_estimate']}%</b>\n\n"
        f"💵 Total revenue: <b>${stats['total_revenue']}</b>"
    )
    await message.answer(text)


@router.message(Command("find"))
async def cmd_find_user(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer("Usage: <code>/find 123456789</code>")
        return

    telegram_id = int(parts[1].strip())
    async with get_session() as session:
        details = await find_user_details(session, telegram_id)

    if details is None:
        await message.answer("User not found.")
        return

    end_date = details["subscription_end"].strftime("%d.%m.%Y") if details["subscription_end"] else "—"
    text = (
        f"👤 <b>User {details['telegram_id']}</b>\n"
        f"Username: @{details['username'] or '—'}\n"
        f"Language: {details['language']}\n"
        f"Free messages left: {details['free_messages_left']}\n"
        f"Subscription: {details['subscription_status']} ({details['plan_type'] or '—'})\n"
        f"Subscription ends: {end_date}\n"
        f"Referrals: {details['referrals_count']} (converted: {details['referrals_converted']})\n"
        f"Banned: {'yes' if details['is_banned'] else 'no'}\n"
        f"Joined: {details['created_at'].strftime('%d.%m.%Y')}"
    )
    await message.answer(text)


@router.message(Command("ban"))
async def cmd_ban_user(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer("Usage: <code>/ban 123456789</code>")
        return
    telegram_id = int(parts[1].strip())
    async with get_session() as session:
        success = await ban_user(session, telegram_id)
    await message.answer("✅ User banned." if success else "User not found.")


@router.message(Command("unban"))
async def cmd_unban_user(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer("Usage: <code>/unban 123456789</code>")
        return
    telegram_id = int(parts[1].strip())
    async with get_session() as session:
        success = await unban_user(session, telegram_id)
    await message.answer("✅ User unbanned." if success else "User not found.")


# --- Рассылка (broadcast) ---

@router.message(Command("broadcast"))
async def cmd_broadcast_start(message: Message, state: FSMContext):
    await state.set_state(AdminStates.waiting_broadcast_text)
    await message.answer("✍️ Send me the text you want to broadcast to ALL users (HTML formatting allowed).")


@router.message(AdminStates.waiting_broadcast_text, F.text)
async def cmd_broadcast_execute(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    broadcast_text = message.text

    async with get_session() as session:
        telegram_ids = await get_all_active_telegram_ids(session)

    sent, failed = 0, 0
    status_msg = await message.answer(f"📡 Sending to {len(telegram_ids)} users...")

    for tg_id in telegram_ids:
        try:
            await bot.send_message(tg_id, broadcast_text)
            sent += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Broadcast failed for {tg_id}: {e}")
        # Небольшая пауза, чтобы не упереться в лимиты Telegram (30 msg/sec)
        await asyncio.sleep(0.05)

    async with get_session() as session:
        session.add(
            BroadcastLog(
                admin_telegram_id=message.from_user.id,
                text=broadcast_text,
                sent_count=sent,
                failed_count=failed,
            )
        )

    await status_msg.edit_text(f"✅ Broadcast done. Sent: {sent}, failed: {failed}.")


# --- Изменение AI-промпта без передеплоя ---

@router.message(Command("setprompt"))
async def cmd_setprompt_start(message: Message, state: FSMContext):
    current = await get_prompt_suffix()
    await state.set_state(AdminStates.waiting_new_prompt)
    await message.answer(
        f"Current prompt suffix:\n<code>{current or '(empty)'}</code>\n\n"
        "Send new text to APPEND to the AI system prompt (applies instantly, no redeploy). "
        "Send \"-\" to clear it."
    )


@router.message(AdminStates.waiting_new_prompt, F.text)
async def cmd_setprompt_execute(message: Message, state: FSMContext):
    await state.clear()
    new_text = "" if message.text.strip() == "-" else message.text
    await set_prompt_suffix(new_text)
    await message.answer("✅ AI prompt suffix updated instantly.")


# --- Feature flags ---

@router.message(Command("features"))
async def cmd_features(message: Message):
    lines = ["⚙️ <b>Feature flags</b> (tap to toggle):\n"]
    for name in DEFAULT_FEATURES:
        enabled = await is_feature_enabled(name)
        lines.append(f"{'🟢' if enabled else '🔴'} {name} — /toggle_{name}")
    await message.answer("\n".join(lines))


@router.message(F.text.regexp(r"^/toggle_(\w+)$"))
async def cmd_toggle_feature(message: Message):
    feature_name = message.text.split("toggle_")[1]
    if feature_name not in DEFAULT_FEATURES:
        await message.answer("Unknown feature.")
        return
    current = await is_feature_enabled(feature_name)
    await set_feature_enabled(feature_name, not current)
    await message.answer(f"Feature '{feature_name}' is now {'🟢 ON' if not current else '🔴 OFF'}.")
