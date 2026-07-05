"""
=====================================================================
core/i18n.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
i18n = "internationalization" (между 'i' и 'n' — 18 букв, отсюда
сокращение). Это система переводов бота на разные языки.

Как это работает:
1. Все тексты бота хранятся в одном большом словаре TRANSLATIONS.
2. У каждого текста есть "ключ" (например "welcome") и 4 варианта:
   ru / en / es / pt.
3. Функция `t(key, lang, **kwargs)` достаёт нужный перевод по ключу
   и языку, и подставляет туда переменные (например, имя юзера).

Пример использования в хендлере:
    from core.i18n import t
    text = t("welcome", user.language, name=message.from_user.first_name)

Если каких-то языков не хватает или нужно добавить новый текст —
просто добавляешь новый ключ в словарь ниже, для всех 4 языков сразу.
=====================================================================
"""

SUPPORTED_LANGUAGES = ["ru", "en", "es", "pt"]

LANGUAGE_NAMES = {
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "es": "🇪🇸 Español",
    "pt": "🇵🇹 Português",
}

TRANSLATIONS: dict[str, dict[str, str]] = {

    "choose_language": {
        "ru": "🌙 Выбери язык общения:",
        "en": "🌙 Choose your language:",
        "es": "🌙 Elige tu idioma:",
        "pt": "🌙 Escolha seu idioma:",
    },

    "welcome": {
        "ru": (
            "✨ <b>Добро пожаловать в AstraMind</b> ✨\n\n"
            "Я — Luna, твой личный AI-оракул. Я вижу то, что скрыто:\n"
            "любовь, деньги, судьбу, звёзды над твоей головой.\n\n"
            "Задай мне вопрос, и вселенная ответит через меня.\n\n"
            "🔮 У тебя есть <b>{free_left}</b> бесплатных посланий."
        ),
        "en": (
            "✨ <b>Welcome to AstraMind</b> ✨\n\n"
            "I am Luna, your personal AI oracle. I see what is hidden:\n"
            "love, money, destiny, the stars above you.\n\n"
            "Ask me anything, and the universe will answer through me.\n\n"
            "🔮 You have <b>{free_left}</b> free messages."
        ),
        "es": (
            "✨ <b>Bienvenido a AstraMind</b> ✨\n\n"
            "Soy Luna, tu oráculo de IA personal. Veo lo que está oculto:\n"
            "amor, dinero, destino, las estrellas sobre ti.\n\n"
            "Pregúntame lo que quieras y el universo responderá a través de mí.\n\n"
            "🔮 Tienes <b>{free_left}</b> mensajes gratis."
        ),
        "pt": (
            "✨ <b>Bem-vindo ao AstraMind</b> ✨\n\n"
            "Eu sou Luna, seu oráculo de IA pessoal. Eu vejo o que está oculto:\n"
            "amor, dinheiro, destino, as estrelas acima de você.\n\n"
            "Pergunte-me qualquer coisa, e o universo responderá através de mim.\n\n"
            "🔮 Você tem <b>{free_left}</b> mensagens grátis."
        ),
    },

    "choose_topic": {
        "ru": "Выбери тему, в которую хочешь заглянуть:",
        "en": "Choose a topic you'd like to explore:",
        "es": "Elige un tema que quieras explorar:",
        "pt": "Escolha um tema que deseja explorar:",
    },

    "topic_relationships": {"ru": "❤️ Отношения", "en": "❤️ Relationships", "es": "❤️ Relaciones", "pt": "❤️ Relacionamentos"},
    "topic_money": {"ru": "💰 Деньги", "en": "💰 Money", "es": "💰 Dinero", "pt": "💰 Dinheiro"},
    "topic_future": {"ru": "🔮 Будущее", "en": "🔮 Future", "es": "🔮 Futuro", "pt": "🔮 Futuro"},
    "topic_astrology": {"ru": "🪐 Астрология", "en": "🪐 Astrology", "es": "🪐 Astrología", "pt": "🪐 Astrologia"},
    "topic_dreams": {"ru": "🌙 Сны", "en": "🌙 Dreams", "es": "🌙 Sueños", "pt": "🌙 Sonhos"},
    "topic_self": {"ru": "✨ Саморазвитие", "en": "✨ Self-discovery", "es": "✨ Autoconocimiento", "pt": "✨ Autoconhecimento"},
    "topic_more": {"ru": "⚙️ Ещё", "en": "⚙️ More", "es": "⚙️ Más", "pt": "⚙️ Mais"},

    "topic_selected": {
        "ru": "🔮 Хорошо. Задай свой вопрос, и я загляну за завесу...",
        "en": "🔮 Very well. Ask your question, and I shall look beyond the veil...",
        "es": "🔮 Muy bien. Haz tu pregunta, y miraré más allá del velo...",
        "pt": "🔮 Muito bem. Faça sua pergunta, e olharei além do véu...",
    },

    "ai_thinking": {
        "ru": "🌙 Читаю знаки...",
        "en": "🌙 Reading the signs...",
        "es": "🌙 Leyendo las señales...",
        "pt": "🌙 Lendo os sinais...",
    },

    "messages_left": {
        "ru": "\n\n<i>Осталось бесплатных посланий: {left}</i>",
        "en": "\n\n<i>Free messages left: {left}</i>",
        "es": "\n\n<i>Mensajes gratis restantes: {left}</i>",
        "pt": "\n\n<i>Mensagens grátis restantes: {left}</i>",
    },

    "paywall": {
        "ru": (
            "🌌 Твои бесплатные послания закончились.\n\n"
            "Чтобы продолжить путь с Luna и получить безлимитный доступ "
            "к оракулу, выбери план ниже:"
        ),
        "en": (
            "🌌 Your free messages have run out.\n\n"
            "To continue your journey with Luna and unlock unlimited access "
            "to the oracle, choose a plan below:"
        ),
        "es": (
            "🌌 Tus mensajes gratis se han agotado.\n\n"
            "Para continuar tu viaje con Luna y desbloquear acceso ilimitado "
            "al oráculo, elige un plan a continuación:"
        ),
        "pt": (
            "🌌 Suas mensagens grátis acabaram.\n\n"
            "Para continuar sua jornada com Luna e desbloquear acesso ilimitado "
            "ao oráculo, escolha um plano abaixo:"
        ),
    },

    "plan_weekly": {"ru": "📅 Недельный — {price}", "en": "📅 Weekly — {price}", "es": "📅 Semanal — {price}", "pt": "📅 Semanal — {price}"},
    "plan_monthly": {"ru": "🗓️ Месячный — {price}", "en": "🗓️ Monthly — {price}", "es": "🗓️ Mensual — {price}", "pt": "🗓️ Mensal — {price}"},

    "pay_button": {"ru": "💳 Оплатить", "en": "💳 Pay now", "es": "💳 Pagar", "pt": "💳 Pagar"},

    "go_to_payment": {
        "ru": "Нажми кнопку ниже, чтобы перейти к оплате. После оплаты подписка активируется автоматически ✨",
        "en": "Tap the button below to proceed to payment. Your subscription will activate automatically after payment ✨",
        "es": "Toca el botón de abajo para proceder al pago. Tu suscripción se activará automáticamente ✨",
        "pt": "Toque no botão abaixo para prosseguir com o pagamento. Sua assinatura será ativada automaticamente ✨",
    },

    "subscription_activated": {
        "ru": "🎉 Подписка активирована! Теперь у тебя безлимитный доступ к Luna до {end_date}.",
        "en": "🎉 Subscription activated! You now have unlimited access to Luna until {end_date}.",
        "es": "🎉 ¡Suscripción activada! Ahora tienes acceso ilimitado a Luna hasta {end_date}.",
        "pt": "🎉 Assinatura ativada! Agora você tem acesso ilimitado à Luna até {end_date}.",
    },

    "rate_limited": {
        "ru": "⏳ Не спеши... вселенная не любит спешки. Подожди пару секунд.",
        "en": "⏳ Slow down... the universe dislikes haste. Wait a couple of seconds.",
        "es": "⏳ Despacio... al universo no le gusta la prisa. Espera unos segundos.",
        "pt": "⏳ Devagar... o universo não gosta de pressa. Espere alguns segundos.",
    },

    "banned": {
        "ru": "🚫 Твой доступ к оракулу ограничен.",
        "en": "🚫 Your access to the oracle has been restricted.",
        "es": "🚫 Tu acceso al oráculo ha sido restringido.",
        "pt": "🚫 Seu acesso ao oráculo foi restrito.",
    },

    "referral_info": {
        "ru": (
            "🔗 <b>Твоя реферальная ссылка:</b>\n{link}\n\n"
            "👥 Приглашено: <b>{count}</b>\n"
            "💎 Из них оформили подписку: <b>{converted}</b>\n"
            "🎁 Заработано бонусных сообщений: <b>{bonus}</b>\n\n"
            "За каждого друга, который перейдёт по твоей ссылке, "
            "ты получишь +{reward} бесплатных посланий!"
        ),
        "en": (
            "🔗 <b>Your referral link:</b>\n{link}\n\n"
            "👥 Invited: <b>{count}</b>\n"
            "💎 Of which subscribed: <b>{converted}</b>\n"
            "🎁 Bonus messages earned: <b>{bonus}</b>\n\n"
            "For every friend who joins via your link, "
            "you get +{reward} free messages!"
        ),
        "es": (
            "🔗 <b>Tu enlace de referido:</b>\n{link}\n\n"
            "👥 Invitados: <b>{count}</b>\n"
            "💎 De los cuales se suscribieron: <b>{converted}</b>\n"
            "🎁 Mensajes bonus ganados: <b>{bonus}</b>\n\n"
            "¡Por cada amigo que se una con tu enlace, "
            "obtienes +{reward} mensajes gratis!"
        ),
        "pt": (
            "🔗 <b>Seu link de indicação:</b>\n{link}\n\n"
            "👥 Convidados: <b>{count}</b>\n"
            "💎 Dos quais assinaram: <b>{converted}</b>\n"
            "🎁 Mensagens bônus ganhas: <b>{bonus}</b>\n\n"
            "Para cada amigo que entrar pelo seu link, "
            "você ganha +{reward} mensagens grátis!"
        ),
    },

    "menu_button": {"ru": "🏠 Меню", "en": "🏠 Menu", "es": "🏠 Menú", "pt": "🏠 Menu"},
    "referral_button": {"ru": "🔗 Пригласить друга", "en": "🔗 Invite a friend", "es": "🔗 Invitar amigo", "pt": "🔗 Convidar amigo"},
    "subscription_button": {"ru": "💎 Подписка", "en": "💎 Subscription", "es": "💎 Suscripción", "pt": "💎 Assinatura"},

    "my_subscription": {
        "ru": "💎 Статус подписки: <b>{status}</b>\nДействует до: <b>{end_date}</b>",
        "en": "💎 Subscription status: <b>{status}</b>\nActive until: <b>{end_date}</b>",
        "es": "💎 Estado de suscripción: <b>{status}</b>\nActiva hasta: <b>{end_date}</b>",
        "pt": "💎 Status da assinatura: <b>{status}</b>\nAtiva até: <b>{end_date}</b>",
    },

    "no_subscription": {
        "ru": "У тебя пока нет активной подписки.",
        "en": "You don't have an active subscription yet.",
        "es": "Aún no tienes una suscripción activa.",
        "pt": "Você ainda não tem uma assinatura ativa.",
    },
}


def t(key: str, lang: str, **kwargs) -> str:
    """
    Достаёт перевод по ключу и языку.
    Если языка нет в словаре — берёт английский по умолчанию.
    Если ключа вообще нет — возвращает сам ключ (чтобы сразу было видно
    в чате, что перевод забыли добавить, а не молча падать с ошибкой).
    """
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    text = entry.get(lang) or entry.get("en") or key
    if kwargs:
        text = text.format(**kwargs)
    return text
