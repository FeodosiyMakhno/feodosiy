from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# 🔘 Кнопка для авторизации
auth_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Авторизовать YouTube", callback_data="auth_youtube")]
    ]
)

# 🔘 Кнопки для выбора групп
def get_group_buttons(groups):
    """Создаёт Inline-кнопки с группами."""
    if not groups:
        return None  # ❗ Если групп нет, возвращаем None
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{idx}. {email}", callback_data=f"group_{email}")]
            for idx, (email,) in enumerate(groups, start=1)
        ]
    )
    return keyboard
