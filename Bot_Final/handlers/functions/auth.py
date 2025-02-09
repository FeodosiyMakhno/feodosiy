import os
import json
import pickle
import asyncio
from playwright.async_api import async_playwright

COOKIES_DIR = "cookies"
os.makedirs(COOKIES_DIR, exist_ok=True)

async def login_youtube(email: str, password: str):
    """Логин в Google, обход проверки браузера и сохранение куки."""
    print(f"🚀 {email}: Запуск авторизации...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-gpu",
                "--start-maximized",
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            locale="ru-RU",
            timezone_id="Europe/Moscow"
        )

        # Загружаем куки, если есть
        cookies_path = os.path.join(COOKIES_DIR, f"{email}.pkl")
        if os.path.exists(cookies_path):
            with open(cookies_path, "rb") as f:
                cookies = pickle.load(f)
            await context.add_cookies(cookies)
            print(f"🍪 Куки загружены для {email}")

        page = await context.new_page()
        await page.goto("https://accounts.google.com/signin")

        # Ввод email
        await page.fill('input[type="email"]', email)
        await page.click('button:has-text("Далее")')
        await page.wait_for_selector('input[type="password"]', timeout=10000)

        # Ввод пароля
        await page.fill('input[type="password"]', password)
        await page.click('button:has-text("Далее")')
        await page.wait_for_timeout(5000)

        # Проверка успешного входа
        if "myaccount.google.com" in page.url:
            print(f"✅ Успешный вход: {email}")

            # **Сохраняем куки**
            cookies = await context.cookies()
            with open(cookies_path, "wb") as f:
                pickle.dump(cookies, f)

            print(f"🍪 Куки сохранены: {cookies_path}")
        else:
            print(f"❌ Ошибка входа: {email}")

        await browser.close()


async def login_all_accounts():
    """Авторизация всех аккаунтов одновременно."""
    with open("accounts.json", "r", encoding="utf-8") as f:
        accounts = json.load(f)

    tasks = [login_youtube(acc["email"], acc["password"]) for acc in accounts]
    await asyncio.gather(*tasks)  # Запускаем все задачи одновременно


