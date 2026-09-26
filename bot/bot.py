"""DoriIshonch Telegram boti (aiogram 3).

Ishga tushirish:
    TELEGRAM_BOT_TOKEN=... API_URL=http://localhost:8000 WEB_URL=https://....trycloudflare.com python bot.py

WEB_URL https boʻlsa, bot Telegram Mini App tugmasini koʻrsatadi: veb-skaner Telegram ichida ochiladi.
Butun mantiq core.py da (testlanadi), bu fayl faqat Telegram bilan bogʻlaydi.
"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (BotCommand, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
                           Message, ReplyKeyboardMarkup, WebAppInfo)

from core import BTN_NEAR, MENU, Brain, Reply

API_URL = os.getenv("API_URL", "http://localhost:8000")
WEB_URL = os.getenv("WEB_URL", "")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

log = logging.getLogger("doriishonch.bot")
dp = Dispatcher()
brain = Brain(httpx.AsyncClient(base_url=API_URL, timeout=60), WEB_URL)

COMMANDS = [
    BotCommand(command="start", description="Boshlash"),
    BotCommand(command="demo", description="Demo stsenariylar"),
    BotCommand(command="zanjir", description="DoriIshonch zanjiri holati"),
    BotCommand(command="yordam", description="Yordam"),
    BotCommand(command="stop", description="AI suhbatni tugatish"),
]


def menu_keyboard() -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=t, request_location=(t == BTN_NEAR)) for t in row] for row in MENU]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)


def location_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True)],
                                         [KeyboardButton(text="❓ Yordam")]], resize_keyboard=True, one_time_keyboard=True)


def inline(rows) -> InlineKeyboardMarkup | None:
    if not rows:
        return None
    out = []
    for row in rows:
        btns = []
        for b in row:
            if b.webapp:
                btns.append(InlineKeyboardButton(text=b.text, web_app=WebAppInfo(url=b.webapp)))
            elif b.url:
                btns.append(InlineKeyboardButton(text=b.text, url=b.url))
            else:
                btns.append(InlineKeyboardButton(text=b.text, callback_data=b.data))
        out.append(btns)
    return InlineKeyboardMarkup(inline_keyboard=out)


async def send(m: Message, replies: list[Reply], user_msg: Message | None = None):
    for r in replies:
        if r.delete_user_message and user_msg:
            try:
                await user_msg.delete()
            except Exception:  # noqa: BLE001 — guruhda huquq boʻlmasligi mumkin
                pass
        markup = inline(r.buttons) or (location_keyboard() if r.location_request else
                                       menu_keyboard() if r.menu else None)
        await m.answer(r.text, reply_markup=markup, disable_web_page_preview=True)


def backend_down() -> list[Reply]:
    return [Reply("⚠️ Server bilan aloqa yoʻq. Birozdan keyin urinib koʻring.")]


@dp.message(F.location)
async def on_location(m: Message):
    try:
        await send(m, await brain.on_location(m.from_user.id, m.location.latitude, m.location.longitude))
    except httpx.HTTPError:
        await send(m, backend_down())


@dp.message(F.photo | F.document.mime_type.startswith("image/"))
async def on_photo(m: Message, bot: Bot):
    await bot.send_chat_action(m.chat.id, "typing")
    file_id = m.photo[-1].file_id if m.photo else m.document.file_id
    f = await bot.get_file(file_id)
    data = (await bot.download_file(f.file_path)).read()
    try:
        await send(m, await brain.on_photo(m.from_user.id, data))
    except httpx.HTTPError:
        await send(m, backend_down())


@dp.message(F.text)
async def on_text(m: Message, bot: Bot):
    await bot.send_chat_action(m.chat.id, "typing")
    try:
        await send(m, await brain.on_text(m.from_user.id, m.text), user_msg=m)
    except httpx.HTTPError:
        await send(m, backend_down())


@dp.message(F.web_app_data)
async def on_webapp(m: Message):
    # Mini App skanerlagan kodni yuborishi mumkin
    try:
        await send(m, await brain.verify(m.from_user.id, code=m.web_app_data.data))
    except httpx.HTTPError:
        await send(m, backend_down())


@dp.callback_query()
async def on_callback(c: CallbackQuery, bot: Bot):
    try:
        replies, alert = await brain.on_callback(c.from_user.id, c.data or "")
    except httpx.HTTPError:
        replies, alert = [], "Server bilan aloqa yoʻq"
    await c.answer(alert or None, show_alert=bool(alert))
    if replies:
        await bot.send_chat_action(c.message.chat.id, "typing")
        await send(c.message, replies)


async def main():
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN oʻrnatilmagan. @BotFather dan token oling va .env ga yozing.")
    logging.basicConfig(level=logging.INFO)
    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    await bot.set_my_commands(COMMANDS)
    me = await bot.get_me()
    log.info("Bot ishga tushdi: @%s → %s", me.username, API_URL)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
