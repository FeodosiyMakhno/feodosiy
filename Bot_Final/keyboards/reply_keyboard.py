from aiogram import Router
from aiogram.types import Message
from keyboards.reply_keyboard import admin_keyboard
from handlers.functions.auth import login_all_accounts
import asyncio

admin_router = Router()

@admin_router.message()
async def admin_panel(message: Message):
    if message.text == "🔑 Авторизовать все аккаунты":
        await message.answer("⏳ Авторизация всех аккаунтов...")
        await asyncio.create_task(login_all_accounts())
        await message.answer("✅ Все аккаунты авторизованы!")
