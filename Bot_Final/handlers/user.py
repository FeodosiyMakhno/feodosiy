from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

user_router = Router()

@user_router.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("👋 Привет! Я ваш бот.")
