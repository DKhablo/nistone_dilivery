from typing import List, Dict
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_URL, ADMIN_IDS


def main_menu(user_id: int = None) -> InlineKeyboardMarkup:
    """Главное меню с учётом роли пользователя."""
    buttons = [
        [
            InlineKeyboardButton(text="🆕 Новый заказ", callback_data="new_order"),
            InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders")
        ]
    ]

    if user_id and user_id in ADMIN_IDS:
        buttons.append([
            InlineKeyboardButton(
                text="👨‍💼 Админ-панель",
                url=f"{ADMIN_URL}/admin"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def orders_list(user_orders: List[Dict], user_id: int = None) -> InlineKeyboardMarkup:
    """Клавиатура со списком заказов."""
    buttons = []

    for order in user_orders[-10:]:
        number = order.get('order_number', '—')
        status = order.get('status', 'new')
        status_emoji = {'new': '🟡', 'collecting': '🔵', 'ready': '🟢', 'delivering': '🟠', 'delivered': '✅'}.get(status, '📋')
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_emoji} Заказ #{number}",
                callback_data=f"view_order_{number}"
            )
        ])

    if user_id and user_id in ADMIN_IDS:
        buttons.append([
            InlineKeyboardButton(
                text="🌐 Открыть все в админке",
                url=f"{ADMIN_URL}/admin"
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_menu() -> InlineKeyboardMarkup:
    """Кнопка назад."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
            ]
        ]
    )