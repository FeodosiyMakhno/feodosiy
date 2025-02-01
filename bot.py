import asyncio
import logging
import sqlite3
import sys
import os
import pickle
import datetime
from aiogram import Bot
from aiogram.dispatcher.dispatcher import Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Загружаем переменные окружения из файла .env
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Подключение к базе данных SQLite
DB_PATH = "family_users.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Создаём таблицы, если их нет
cursor.execute("""
CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_email TEXT,
    name TEXT,
    email TEXT,
    FOREIGN KEY (group_email) REFERENCES groups (email)
)
""")
conn.commit()

# Инициализация диспетчера
dp = Dispatcher()
TOKEN = os.getenv("TOKEN")
COOKIES_DIR = "cookies"
os.makedirs(COOKIES_DIR, exist_ok=True)

# Список с одной группой для проверки
ACCOUNTS = [
    {"email": "ytubegroups3@gmail.com"},  # Используем одну группу
]

# Кнопки главного меню
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Пропарсить систему")],
        [KeyboardButton(text="📂 Показать группы")]
    ],
    resize_keyboard=True
)

def get_group_buttons():
    """Создаёт кнопки для выбора группы."""
    cursor.execute("SELECT email FROM groups")
    groups = cursor.fetchall()

    if not groups:
        return None  # ❗ Возвращаем None, если групп нет (не создаём пустую клавиатуру)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{idx}. {email}", callback_data=f"group_{email}")]
        for idx, (email,) in enumerate(groups, start=1)
    ])

    return keyboard

@dp.message()
async def button_handler(message: Message) -> None:
    """Обрабатывает кнопки и игнорирует старые сообщения после перезапуска."""
    now = datetime.datetime.now(datetime.timezone.utc)

    # ❗ Игнорируем старые сообщения
    if (now - message.date).total_seconds() > 5:
        return  

    if message.text == "📂 Показать группы":
        cursor.execute("SELECT email FROM groups")
        groups = cursor.fetchall()

        if not groups:
            await message.answer("⚠️ В базе пока нет данных. Сначала пропарсьте систему!")
            return

        keyboard = get_group_buttons()
        if keyboard:
            await message.answer("📂 Выберите группу:", reply_markup=keyboard)
        else:
            await message.answer("⚠️ Ошибка загрузки групп. Попробуйте снова.")

    elif message.text == "🔍 Пропарсить систему":
        await message.answer("⏳ Парсер запущен. Пожалуйста, подождите...")
        asyncio.create_task(run_parser(message.chat.id))

# Словарь для хранения последнего сообщения с пользователями
user_last_message = {}

@dp.callback_query()
async def group_selected_callback(call: CallbackQuery):
    """Обрабатывает выбор группы, удаляет предыдущее сообщение только при выборе другой группы."""
    group_email = call.data.replace("group_", "")

    try:
        chat_id = call.message.chat.id

        # ✅ Удаляем предыдущее сообщение, если выбрана ДРУГАЯ группа
        if chat_id in user_last_message and user_last_message[chat_id]["group"] != group_email:
            last_message_id = user_last_message[chat_id]["message_id"]
            try:
                await call.bot.delete_message(chat_id, last_message_id)
            except Exception:
                pass  # Игнорируем ошибку, если сообщение уже удалено

        # Получаем пользователей группы
        cursor.execute("SELECT name, email FROM users WHERE group_email=?", (group_email,))
        users = cursor.fetchall()

        if not users:
            msg = await call.message.answer(f"⚠️ В группе {group_email} нет пользователей.")
            user_last_message[chat_id] = {"group": group_email, "message_id": msg.message_id}
            return

        # Формируем список пользователей
        user_list = "\n".join([f"👤 {name} - {email}" for name, email in users])

        # ✅ Отправляем список пользователей и сохраняем ID нового сообщения
        msg = await call.message.answer(f"📋 **Пользователи группы {group_email}:**\n{user_list}")
        user_last_message[chat_id] = {"group": group_email, "message_id": msg.message_id}

    except Exception as e:
        logging.error(f"Ошибка при обработке выбора группы: {e}")
        await call.message.answer("❌ Произошла ошибка при загрузке пользователей.")

# Параллельная обработка аккаунтов с ограничением
async def parse_account(account):
    """Парсит один аккаунт."""
    logging.info(f"Начинаем парсинг аккаунта {account['email']}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Запускаем браузер в headless режиме
        context = await browser.new_context()

        try:
            cookies_path = os.path.join(COOKIES_DIR, f"{account['email']}.pkl")
            if os.path.exists(cookies_path):
                with open(cookies_path, "rb") as f:
                    cookies = pickle.load(f)
                await context.add_cookies(cookies)

            page = await context.new_page()
            await page.goto("https://myaccount.google.com/family/details", wait_until="domcontentloaded")

            members_links = await page.query_selector_all("a[href^='family/member/g/']")
            if not members_links:
                return

            cursor.execute("INSERT OR IGNORE INTO groups (email) VALUES (?)", (account["email"],))
            cursor.execute("DELETE FROM users WHERE group_email=?", (account["email"],))

            for i in range(len(members_links)):
                members_links = await page.query_selector_all("a[href^='family/member/g/']")
                await members_links[i].click(click_count=2)
                await asyncio.sleep(2)

                name_element = await page.query_selector("h2.f0YdKf")
                name = await name_element.inner_text() if name_element else "Неизвестный"

                email_elements = await page.query_selector_all("p.hX6Oo")
                email_text = await email_elements[0].inner_text() if email_elements else "Нет email"

                if name:
                    cursor.execute("INSERT INTO users (group_email, name, email) VALUES (?, ?, ?)", (account["email"], name, email_text))

                await page.go_back()
                await asyncio.sleep(2)

            conn.commit()

        except Exception as e:
            logging.error(f"Ошибка при парсинге {account['email']}: {e}")

        finally:
            await browser.close()

async def run_parser(chat_id):
    """Запускает парсер для одного аккаунта."""
    await parse_account(ACCOUNTS[0])  # Парсим только первый аккаунт из списка

    # ✅ Сообщаем пользователю, что парсинг завершён
    bot = Bot(token=TOKEN)
    await bot.send_message(chat_id, "✅ Парсинг завершён. Данные обновлены.")

async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
