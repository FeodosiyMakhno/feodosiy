import json  # Импортируем json
import asyncio
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from handlers.functions.auth import login_all_accounts  # Используем функцию для входа во все аккаунты
from keyboards.inline_keyboard import auth_keyboard 

admin_router = Router()

@admin_router.message(Command("admin"))
async def admin_panel(message: Message):
    """Главное админ-меню с кнопкой авторизации."""
    await message.answer("⚙️ Панель управления:", reply_markup=auth_keyboard)

@admin_router.callback_query(lambda call: call.data == "auth_youtube")
async def handle_auth_callback(call: CallbackQuery):
    """Обработчик кнопки авторизации YouTube."""
    await call.message.answer("🔑 Запуск авторизации для всех аккаунтов...")
    
    await login_all_accounts()  # Запускаем авторизацию для всех почт
    
    await call.message.answer("✅ Авторизация завершена.")
