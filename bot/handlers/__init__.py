"""
=====================================================================
bot/handlers/__init__.py
=====================================================================
ЗАЧЕМ ЭТОТ ФАЙЛ (для чайника):
aiogram 3 использует "роутеры" (Router) — это как отдельные папки
с обработчиками, которые потом подключаются к главному диспетчеру.

Здесь мы собираем все роутеры из папки handlers в один список и
экспортируем — main.py просто один раз это подключает.

ВАЖНО: порядок include_router имеет значение! Более специфичные
роутеры (admin — только для админов) стоит подключать раньше общих,
чтобы админские команды не перехватывались общими обработчиками текста.
=====================================================================
"""

from aiogram import Router

from bot.handlers import admin, start, oracle, subscription, referral


def get_main_router() -> Router:
    main_router = Router(name="main")
    main_router.include_router(admin.router)
    main_router.include_router(start.router)
    main_router.include_router(subscription.router)
    main_router.include_router(referral.router)
    main_router.include_router(oracle.router)
    return main_router
