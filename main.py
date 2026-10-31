"""Telegram complaint-drafting bot (aiogram 3).

Install: pip install -r requirements.txt
Set BOT_TOKEN and ADMIN_CODE environment variables before running.
"""
import asyncio
import html
import logging
import os
import re
import time
import secrets
from aiohttp import web

try:
    import aiosqlite
    from aiogram import Bot, Dispatcher, F, Router
    from aiogram.filters import Command, CommandStart
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.types import Message, CallbackQuery
    from aiogram.utils.keyboard import InlineKeyboardBuilder
except ImportError as exc:
    raise SystemExit(
        "Не установлены зависимости. Выполни: pip install -r requirements.txt"
    ) from exc

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CODE = os.getenv("ADMIN_CODE", "").strip()
DB_PATH = os.getenv("DB_PATH", "complaints_bot.db")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("complaint_bot")
router = Router()
admin_sessions: set[int] = set()


class ReportForm(StatesGroup):
    username = State()
    reason = State()
    details = State()
    evidence = State()


class AdminForm(StatesGroup):
    code = State()


def main_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Подготовить обращение", callback_data="new_case")
    kb.button(text="📚 Мои обращения", callback_data="my_cases")
    kb.button(text="ℹ️ Как отправить", callback_data="howto")
    kb.adjust(1)
    return kb.as_markup()


def reasons_keyboard():
    kb = InlineKeyboardBuilder()
    options = [
        ("Мошенничество", "fraud"),
        ("Спам", "spam"),
        ("Выдаёт себя за другого", "impersonation"),
        ("Угрозы или преследование", "threats"),
        ("Другое нарушение", "other"),
    ]
    for label, value in options:
        kb.button(text=label, callback_data=f"reason:{value}")
    kb.adjust(1)
    return kb.as_markup()


REASONS = {
    "fraud": "Мошенничество",
    "spam": "Спам",
    "impersonation": "Выдаёт себя за другого",
    "threats": "Угрозы или преследование",
    "other": "Другое нарушение",
}


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🛡️ Помощник по оформлению обращения в Telegram\n\n"
        "Бот собирает факты и формирует черновик обращения. Он не рассылает "
        "массовые жалобы и не пытается автоматически блокировать аккаунты.",
        reply_markup=main_keyboard(),
    )


@router.callback_query(F.data == "new_case")
async def new_case(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(ReportForm.username)
    await call.message.answer("Укажи username аккаунта (например, @example):")
    await call.answer()


@router.message(ReportForm.username)
async def get_username(message: Message, state: FSMContext):
    username = (message.text or "").strip()
    if not re.fullmatch(r"@[A-Za-z0-9_]{5,32}", username):
        await message.answer("Введи корректный username в формате @example (5–32 символа после @).")
        return
    await state.update_data(username=username)
    await state.set_state(ReportForm.reason)
    await message.answer("Выбери причину обращения:", reply_markup=reasons_keyboard())


@router.callback_query(ReportForm.reason, F.data.startswith("reason:"))
async def get_reason(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":", 1)[1]
    if key not in REASONS:
        await call.answer("Неизвестная причина", show_alert=True)
        return
    await state.update_data(reason=REASONS[key])
    await state.set_state(ReportForm.details)
    await call.message.answer(
        "Опиши конкретные факты: что произошло, когда и где. "
        "Не добавляй догадки или посторонние личные данные."
    )
    await call.answer()


@router.message(ReportForm.details)
async def get_details(message: Message, state: FSMContext):
    details = (message.text or "").strip()
    if len(details) < 20:
        await message.answer("Добавь конкретики (минимум 20 символов).")
        return
    if len(details) > 3000:
        await message.answer("Слишком длинное описание. Максимум 3000 символов.")
        return
    await state.update_data(details=details)
    await state.set_state(ReportForm.evidence)
    await message.answer(
        "Пришли ссылки на публичные материалы или напиши «нет». "
        "Не отправляй пароли и коды входа."
    )


@router.message(ReportForm.evidence)
async def finish_case(message: Message, state: FSMContext):
    data = await state.get_data()
    evidence = (message.text or "Не указаны").strip()
    if len(evidence) > 2000:
        await message.answer("Слишком длинный текст. Максимум 2000 символов.")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO cases(user_id, username, reason, details, evidence, created_at) "
            "VALUES(?,?,?,?,?,?)",
            (message.from_user.id, data["username"], data["reason"],
             data["details"], evidence, int(time.time())),
        )
        case_id = cur.lastrowid
        await db.commit()

    await state.clear()
    draft = (
        f"Обращение по аккаунту {data['username']}\n"
        f"Причина: {data['reason']}\n\n"
        f"Описание фактов:\n{data['details']}\n\n"
        f"Материалы: {evidence}"
    )
    safe_draft = html.escape(draft)
    await message.answer(
        f"✅ Черновик обращения №{case_id} сохранён.\n\n"
        f"<b>Проверь перед отправкой:</b>\n<pre>{safe_draft}</pre>\n\n"
        "Самостоятельно отправь достоверное обращение через официальные "
        "средства Telegram. Решение принимает Telegram.",
        reply_markup=main_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "my_cases")
async def my_cases(call: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, username, reason, created_at FROM cases "
            "WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (call.from_user.id,),
        )
        rows = await cur.fetchall()

    if not rows:
        result = "У тебя пока нет сохранённых обращений."
    else:
        lines = ["📚 Последние обращения:"]
        for row in rows:
            date = time.strftime("%d.%m.%Y", time.localtime(row[3]))
            lines.append(f"№{row[0]} — {row[1]} — {row[2]} — {date}")
        result = "\n".join(lines)
    await call.message.answer(result, reply_markup=main_keyboard())
    await call.answer()


@router.callback_query(F.data == "howto")
async def howto(call: CallbackQuery):
    await call.message.answer(
        "Как действовать:\n"
        "1. Убедись, что описание основано на реальных фактах.\n"
        "2. Сохрани ссылки и исходные материалы.\n"
        "3. Используй встроенную функцию Telegram «Пожаловаться» или "
        "официальную поддержку.\n"
        "4. Не отправляй ложные и массовые повторные обращения."
    )
    await call.answer()


@router.message(Command("admin"))
async def admin_login(message: Message, state: FSMContext):
    if not ADMIN_CODE:
        await message.answer("Админ-код не настроен. Укажи переменную ADMIN_CODE на сервере.")
        return
    await state.set_state(AdminForm.code)
    await message.answer("Введи код доступа администратора:")


@router.message(AdminForm.code)
async def admin_code(message: Message, state: FSMContext):
    supplied = (message.text or "").strip()
    if not ADMIN_CODE or supplied != ADMIN_CODE:
        await state.clear()
        await message.answer("Неверный код.")
        return
    admin_sessions.add(message.from_user.id)
    await state.clear()
    kb = InlineKeyboardBuilder()
    kb.button(text="📥 Последние обращения", callback_data="admin_cases")
    kb.button(text="🚪 Выйти", callback_data="admin_logout")
    kb.adjust(1)
    await message.answer("🔐 Панель администратора", reply_markup=kb.as_markup())


@router.callback_query(F.data == "admin_logout")
async def admin_logout(call: CallbackQuery):
    admin_sessions.discard(call.from_user.id)
    await call.message.answer("Сессия администратора завершена.")
    await call.answer()


@router.callback_query(F.data == "admin_cases")
async def admin_cases(call: CallbackQuery):
    if call.from_user.id not in admin_sessions:
        await call.answer("Сначала войди через /admin", show_alert=True)
        return

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, user_id, username, reason, details, evidence, created_at "
            "FROM cases ORDER BY id DESC LIMIT 10"
        )
        rows = await cur.fetchall()

    if not rows:
        await call.message.answer("Обращений пока нет.")
    else:
        for row in rows:
            case_id, user_id, username, reason, details, evidence, created = row
            date = time.strftime("%d.%m.%Y %H:%M", time.localtime(created))
            report = (
                f"Обращение №{case_id}\nОт: {user_id}\nАккаунт: {username}\n"
                f"Причина: {reason}\nДата: {date}\n\n{details}\n\nМатериалы: {evidence}"
            )
            await call.message.answer(report[:4000])
    await call.answer()


async def main():
    if not BOT_TOKEN or ":" not in BOT_TOKEN:
        raise SystemExit("Добавь корректный BOT_TOKEN в переменные окружения Render.")
    render_url = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    port = int(os.getenv("PORT", "10000"))
    webhook_secret = os.getenv("WEBHOOK_SECRET", "").strip()
    if not render_url.startswith("https://"):
        raise SystemExit("RENDER_EXTERNAL_URL не задан. Запусти сервис как Render Web Service.")
    if not webhook_secret or not re.fullmatch(r"[A-Za-z0-9_-]{16,256}", webhook_secret):
        raise SystemExit("Задай WEBHOOK_SECRET: 16–256 символов, латинские буквы, цифры, _ или -.")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS cases ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "user_id INTEGER NOT NULL, username TEXT NOT NULL, reason TEXT NOT NULL, "
            "details TEXT NOT NULL, evidence TEXT NOT NULL, created_at INTEGER NOT NULL)"
        )
        await db.commit()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    webhook_path = "/" + secrets.token_urlsafe(24)
    webhook_url = render_url + webhook_path

    async def health(_request):
        return web.Response(text="Bot service is running.")

    async def telegram_webhook(request):
        if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != webhook_secret:
            raise web.HTTPUnauthorized()
        try:
            update = await request.json()
            from aiogram.types import Update
            telegram_update = Update.model_validate(update, context={"bot": bot})
            await dp.feed_update(bot, telegram_update)
        except Exception:
            log.exception("Не удалось обработать Telegram update")
            raise web.HTTPBadRequest(text="Invalid update")
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_post(webhook_path, telegram_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    try:
        await site.start()
        await bot.set_webhook(
            webhook_url,
            secret_token=webhook_secret,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
        )
        log.info("Webhook установлен; сервис слушает порт %s", port)
        # Keep the aiohttp server alive.
        await asyncio.Event().wait()
    finally:
        await bot.delete_webhook()
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        log.exception("Критическая ошибка при запуске бота")
        raise
