"""
Бот для сбора и подтверждения заказов.
"""

import asyncio
import logging
import sys
import json
from datetime import datetime
from os import getenv
from typing import Dict, Optional, List
from pathlib import Path

from aiogram import Bot, Dispatcher, F, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    InputRichMessage,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

# === НАСТРОЙКИ ===
TOKEN = getenv("BOT_TOKEN")
if not TOKEN:
    print("❌ Не найден токен бота")
    sys.exit(1)

# === ИНИЦИАЛИЗАЦИЯ ===
storage = MemoryStorage()
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

# === БАЗА ДАННЫХ ===
DB_FILE = "orders.json"

class OrderDatabase:
    def __init__(self):
        self.orders: Dict[str, List[Dict]] = {}
        self.load()

    def load(self):
        if Path(DB_FILE).exists():
            try:
                with open(DB_FILE, 'r', encoding='utf-8') as f:
                    self.orders = json.load(f)
                print(f"✅ Загружено заказов: {sum(len(v) for v in self.orders.values())}")
            except Exception as e:
                print(f"⚠️ Ошибка загрузки БД: {e}")
                self.orders = {}
        else:
            self.orders = {}
            self.save()

    def save(self):
        try:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.orders, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Ошибка сохранения БД: {e}")

    def get_user_orders(self, user_id: int) -> List[Dict]:
        return self.orders.get(str(user_id), [])

    def add_order(self, user_id: int, chat_id: int, order_data: Dict) -> int:
        user_id_str = str(user_id)
        if user_id_str not in self.orders:
            self.orders[user_id_str] = []

        order_id = len(self.orders[user_id_str]) + 1
        order_data['order_id'] = order_id
        order_data['user_id'] = user_id
        order_data['chat_id'] = chat_id
        order_data['created_at'] = datetime.now().isoformat()
        order_data['status'] = 'Новый'
        order_data['message_id'] = None
        order_data['temp_messages'] = []

        self.orders[user_id_str].append(order_data)
        self.save()
        return order_id

    def update_order_status(self, user_id: int, order_id: int, status: str):
        user_id_str = str(user_id)
        if user_id_str in self.orders:
            for order in self.orders[user_id_str]:
                if order.get('order_id') == order_id:
                    order['status'] = status
                    order['updated_at'] = datetime.now().isoformat()
                    self.save()
                    return True
        return False

    def delete_order(self, user_id: int, order_number: str):
        user_id_str = str(user_id)
        if user_id_str in self.orders:
            self.orders[user_id_str] = [
                order for order in self.orders[user_id_str]
                if order.get('order_number') != order_number
            ]
            self.save()
            return True
        return False

    def delete_all_orders(self, user_id: int):
        user_id_str = str(user_id)
        if user_id_str in self.orders:
            self.orders[user_id_str] = []
            self.save()
            return True
        return False

    def get_order_by_number(self, user_id: int, order_number: str) -> Optional[Dict]:
        for order in self.get_user_orders(user_id):
            if order.get('order_number') == order_number:
                return order
        return None

    def update_order_field(self, user_id: int, order_number: str, field: str, value: str):
        user_id_str = str(user_id)
        if user_id_str in self.orders:
            for order in self.orders[user_id_str]:
                if order.get('order_number') == order_number:
                    order[field] = value
                    self.save()
                    return True
        return False

    def update_message_id(self, user_id: int, order_number: str, message_id: int):
        user_id_str = str(user_id)
        if user_id_str in self.orders:
            for order in self.orders[user_id_str]:
                if order.get('order_number') == order_number:
                    order['message_id'] = message_id
                    self.save()
                    return True
        return False

    def get_message_id(self, user_id: int, order_number: str) -> Optional[int]:
        order = self.get_order_by_number(user_id, order_number)
        if order:
            return order.get('message_id')
        return None

    def get_chat_id(self, user_id: int, order_number: str) -> Optional[int]:
        order = self.get_order_by_number(user_id, order_number)
        if order:
            return order.get('chat_id')
        return None

    def add_temp_message(self, user_id: int, order_number: str, message_id: int):
        user_id_str = str(user_id)
        if user_id_str in self.orders:
            for order in self.orders[user_id_str]:
                if order.get('order_number') == order_number:
                    if 'temp_messages' not in order:
                        order['temp_messages'] = []
                    order['temp_messages'].append(message_id)
                    self.save()
                    return True
        return False

    def clear_temp_messages(self, user_id: int, order_number: str):
        user_id_str = str(user_id)
        if user_id_str in self.orders:
            for order in self.orders[user_id_str]:
                if order.get('order_number') == order_number:
                    order['temp_messages'] = []
                    self.save()
                    return True
        return False

    def get_temp_messages(self, user_id: int, order_number: str) -> List[int]:
        order = self.get_order_by_number(user_id, order_number)
        if order:
            return order.get('temp_messages', [])
        return []

db = OrderDatabase()

# === FSM СОСТОЯНИЯ ===
class OrderStates(StatesGroup):
    waiting_for_order_number = State()
    waiting_for_address = State()
    waiting_for_time_interval = State()
    waiting_for_phone = State()
    waiting_for_amount = State()
    waiting_for_comment = State()
    editing_field = State()

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def create_order_table(order_data: Dict, status: str = "Новый") -> str:
    status_emoji = {
        'Новый': '🟡',
        'Подтверждён': '🟢',
        'Доставлен': '✅',
    }.get(status, '📋')

    return f"""
<table>
  <tr>
    <td colspan="2" style="text-align:center;"><b>📦 ЗАКАЗ #{order_data.get('order_number', '—')}</b></td>
  </tr>
  <tr>
    <td><b>📍 Адрес доставки</b></td>
    <td>{order_data.get('address', '—')}</td>
  </tr>
  <tr>
    <td><b>🕐 Интервал времени</b></td>
    <td>{order_data.get('time_interval', '—')}</td>
  </tr>
  <tr>
    <td><b>📱 Номер телефона</b></td>
    <td>{order_data.get('phone', '—')}</td>
  </tr>
  <tr>
    <td><b>💰 Сумма</b></td>
    <td>{order_data.get('amount', '—')}</td>
  </tr>
  <tr>
    <td><b>📝 Комментарий</b></td>
    <td>{order_data.get('comment', '—')}</td>
  </tr>
  <tr>
    <td colspan="2"><b>Статус:</b> {status_emoji} {status}</td>
  </tr>
</table>
"""

# === КЛАВИАТУРЫ ===

def create_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🆕 Новый заказ", callback_data="new_order"),
                InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders")
            ]
        ]
    )

def create_order_actions_keyboard(order_number: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{order_number}"),
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{order_number}")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
            ]
        ]
    )

def create_edit_fields_keyboard(order_number: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📍 Адрес", callback_data=f"edit_field_address_{order_number}"),
                InlineKeyboardButton(text="🕐 Время", callback_data=f"edit_field_interval_{order_number}")
            ],
            [
                InlineKeyboardButton(text="📱 Телефон", callback_data=f"edit_field_phone_{order_number}"),
                InlineKeyboardButton(text="💰 Сумма", callback_data=f"edit_field_amount_{order_number}")
            ],
            [
                InlineKeyboardButton(text="📝 Комментарий", callback_data=f"edit_field_comment_{order_number}"),
                InlineKeyboardButton(text="❌ Отменить", callback_data=f"edit_cancel_{order_number}")
            ]
        ]
    )

def create_view_order_keyboard(order_number: str, status: str) -> InlineKeyboardMarkup:
    buttons = []

    if status == 'Новый':
        buttons.append([
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{order_number}")
        ])
    elif status == 'Подтверждён':
        buttons.append([
            InlineKeyboardButton(text="🚚 Доставлен", callback_data=f"deliver_{order_number}")
        ])

    buttons.append([
        InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{order_number}"),
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_from_list_{order_number}")
    ])

    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_orders")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_confirmed_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")
            ]
        ]
    )

def create_orders_list_keyboard(user_orders: List[Dict]) -> InlineKeyboardMarkup:
    buttons = []

    for order in user_orders[-10:]:
        number = order.get('order_number', '—')
        status = order.get('status', 'Новый')
        emoji = {'Новый': '🟡', 'Подтверждён': '🟢', 'Доставлен': '✅'}.get(status, '📋')
        buttons.append([
            InlineKeyboardButton(text=f"{emoji} Заказ #{number}", callback_data=f"view_order_{number}")
        ])

    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
            ]
        ]
    )

# === ОСНОВНАЯ ФУНКЦИЯ ОТПРАВКИ ===

async def send_order_message(target, order_data: Dict, status: str = "Новый", keyboard=None):
    html_content = create_order_table(order_data, status)
    rich_message = InputRichMessage(html=html_content)

    if isinstance(target, CallbackQuery):
        chat_id = target.message.chat.id
        user_id = target.from_user.id
    else:
        chat_id = target.chat.id
        user_id = target.from_user.id

    order_number = order_data.get('order_number')
    existing_message_id = db.get_message_id(user_id, order_number)

    try:
        if existing_message_id:
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=existing_message_id,
                    text=html_content,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                return existing_message_id
            except Exception as e:
                print(f"Ошибка редактирования: {e}")
                existing_message_id = None

        sent_msg = await bot.send_rich_message(
            chat_id=chat_id,
            rich_message=rich_message,
            reply_markup=keyboard,
        )

        if sent_msg:
            db.update_message_id(user_id, order_number, sent_msg.message_id)
            return sent_msg.message_id

    except TelegramForbiddenError as e:
        print(f"Ошибка отправки: {e}")
        if isinstance(target, CallbackQuery):
            await target.message.answer("⚠️ Не удалось отправить сообщение.")
        else:
            await target.answer("⚠️ Не удалось отправить сообщение.")
        return None
    except TelegramBadRequest as e:
        error_text = f"⚠️ Ошибка: {e}"
        if isinstance(target, CallbackQuery):
            await target.message.answer(error_text)
        else:
            await target.answer(error_text)
        return None

async def delete_temp_messages(user_id: int, order_number: str):
    temp_messages = db.get_temp_messages(user_id, order_number)
    chat_id = db.get_chat_id(user_id, order_number)

    for msg_id in temp_messages:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception as e:
            print(f"Ошибка удаления временного сообщения {msg_id}: {e}")

    db.clear_temp_messages(user_id, order_number)

# === КОМАНДЫ ===

@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"👋 Привет, {html.bold(message.from_user.full_name)}!\n\n"
        "Выберите действие:",
        reply_markup=create_main_menu()
    )

@dp.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    if await state.get_state():
        await state.clear()
        await message.answer("❌ Заказ отменён.")
    else:
        await message.answer("Нет активного заказа.")

# === СБОР ЗАКАЗА ===

@dp.callback_query(F.data == "new_order")
async def new_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()

    try:
        await callback.message.delete()
    except:
        pass

    msg = await callback.message.answer("🆕 Введите номер заказа:")
    await state.set_state(OrderStates.waiting_for_order_number)
    await state.update_data(temp_messages=[msg.message_id])

@dp.message(OrderStates.waiting_for_order_number)
async def get_order_number(message: Message, state: FSMContext):
    data = await state.get_data()
    temp_messages = data.get('temp_messages', [])
    temp_messages.append(message.message_id)
    await state.update_data(order_number=message.text.strip(), temp_messages=temp_messages)

    msg = await message.answer("📍 Введите адрес доставки:")
    temp_messages.append(msg.message_id)
    await state.update_data(temp_messages=temp_messages)
    await state.set_state(OrderStates.waiting_for_address)

@dp.message(OrderStates.waiting_for_address)
async def get_address(message: Message, state: FSMContext):
    data = await state.get_data()
    temp_messages = data.get('temp_messages', [])
    temp_messages.append(message.message_id)
    await state.update_data(address=message.text.strip(), temp_messages=temp_messages)

    msg = await message.answer("🕐 Введите интервал времени (14:00-18:00):")
    temp_messages.append(msg.message_id)
    await state.update_data(temp_messages=temp_messages)
    await state.set_state(OrderStates.waiting_for_time_interval)

@dp.message(OrderStates.waiting_for_time_interval)
async def get_time(message: Message, state: FSMContext):
    data = await state.get_data()
    temp_messages = data.get('temp_messages', [])
    temp_messages.append(message.message_id)
    await state.update_data(time_interval=message.text.strip(), temp_messages=temp_messages)

    msg = await message.answer("📱 Введите номер телефона:")
    temp_messages.append(msg.message_id)
    await state.update_data(temp_messages=temp_messages)
    await state.set_state(OrderStates.waiting_for_phone)

@dp.message(OrderStates.waiting_for_phone)
async def get_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    temp_messages = data.get('temp_messages', [])
    temp_messages.append(message.message_id)
    await state.update_data(phone=message.text.strip(), temp_messages=temp_messages)

    msg = await message.answer("💰 Введите сумму заказа:")
    temp_messages.append(msg.message_id)
    await state.update_data(temp_messages=temp_messages)
    await state.set_state(OrderStates.waiting_for_amount)

@dp.message(OrderStates.waiting_for_amount)
async def get_amount(message: Message, state: FSMContext):
    data = await state.get_data()
    temp_messages = data.get('temp_messages', [])
    temp_messages.append(message.message_id)
    await state.update_data(amount=message.text.strip(), temp_messages=temp_messages)

    msg = await message.answer("📝 Введите комментарий (или '-'):")
    temp_messages.append(msg.message_id)
    await state.update_data(temp_messages=temp_messages)
    await state.set_state(OrderStates.waiting_for_comment)

@dp.message(OrderStates.waiting_for_comment)
async def get_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    temp_messages = data.get('temp_messages', [])
    temp_messages.append(message.message_id)
    await state.update_data(comment=message.text.strip() or "—", temp_messages=temp_messages)

    order_data = await state.get_data()
    user_id = message.from_user.id
    chat_id = message.chat.id

    temp_msgs = order_data.get('temp_messages', [])

    db.add_order(user_id, chat_id, order_data)
    order_number = order_data['order_number']

    for msg_id in temp_msgs:
        db.add_temp_message(user_id, order_number, msg_id)

    await delete_temp_messages(user_id, order_number)

    order_data = db.get_order_by_number(user_id, order_number)
    await send_order_message(
        target=message,
        order_data=order_data,
        status="Новый",
        keyboard=create_order_actions_keyboard(order_number)
    )

    await state.clear()

# === ОБРАБОТЧИКИ РЕДАКТИРОВАНИЯ ===

@dp.callback_query(F.data.startswith("edit_"))
async def edit_order(callback: CallbackQuery, state: FSMContext):
    """Редактирование заказа (из меню действий или из списка)."""
    parts = callback.data.split("_")

    # Определяем откуда пришёл вызов
    if len(parts) == 2:  # edit_{number}
        order_number = parts[1]
    elif len(parts) == 4:  # edit_from_list_{number}
        order_number = parts[3]
    else:
        await callback.answer("❌ Ошибка!", show_alert=True)
        return

    user_id = callback.from_user.id

    print(f"📝 Редактирование заказа: order_number={order_number}")

    order_data = db.get_order_by_number(user_id, order_number)
    if not order_data:
        await callback.answer("❌ Заказ не найден!", show_alert=True)
        return

    await callback.answer("✏️ Выберите поле для редактирования")

    # Сохраняем номер заказа в состояние
    await state.update_data(editing_order_number=order_number)

    # Показываем заказ с клавиатурой редактирования
    await send_order_message(
        target=callback,
        order_data=order_data,
        status=order_data.get('status', 'Новый'),
        keyboard=create_edit_fields_keyboard(order_number)
    )

@dp.callback_query(F.data.startswith("edit_field_"))
async def edit_field(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    field = parts[2]  # address, interval, phone, amount, comment
    order_number = parts[3]

    field_names = {
        "address": "адрес доставки",
        "interval": "интервал времени",
        "phone": "номер телефона",
        "amount": "сумму",
        "comment": "комментарий"
    }

    field_name = field_names.get(field, field)

    print(f"✏️ Выбрано поле для редактирования: {field} -> {field_name}")

    await callback.answer(f"Редактируем {field_name}")

    # Сохраняем в состояние
    await state.update_data(
        editing_order_number=order_number,
        editing_field=field,
        editing_field_name=field_name,
        editing_waiting_for_input=True
    )

    await state.set_state(OrderStates.editing_field)

    # Удаляем сообщение с клавиатурой редактирования
    try:
        await callback.message.delete()
    except Exception as e:
        print(f"Ошибка удаления сообщения: {e}")

    # Отправляем сообщение с запросом ввода
    await callback.message.answer(f"✏️ Введите новый {field_name}:")

@dp.message(OrderStates.editing_field)
async def process_edit_field(message: Message, state: FSMContext):
    """Обработка ввода нового значения для поля."""
    print("📩 Получено сообщение в состоянии editing_field")

    data = await state.get_data()
    print(f"📊 Данные состояния: {data}")

    order_number = data.get("editing_order_number")
    field = data.get("editing_field")
    field_name = data.get("editing_field_name", "поля")

    if not order_number or not field:
        print("❌ Ошибка: нет данных в состоянии")
        await message.answer("❌ Ошибка: данные для редактирования не найдены. Попробуйте заново.")
        await state.clear()
        return

    user_id = message.from_user.id
    new_value = message.text.strip()

    if not new_value:
        await message.answer("❌ Значение не может быть пустым. Попробуйте снова:")
        return

    print(f"✅ Обновляем поле {field} -> '{new_value}' для заказа {order_number}")

    # Обновляем поле в БД
    if db.update_order_field(user_id, order_number, field, new_value):
        # Получаем обновлённые данные заказа
        order_data = db.get_order_by_number(user_id, order_number)

        if not order_data:
            await message.answer("❌ Заказ не найден")
            await state.clear()
            return

        await state.clear()

        # Удаляем сообщение с запросом ввода
        try:
            await message.delete()
        except Exception as e:
            print(f"Ошибка удаления сообщения: {e}")

        # Показываем обновлённый заказ с клавиатурой редактирования
        await send_order_message(
            target=message,
            order_data=order_data,
            status=order_data.get('status', 'Новый'),
            keyboard=create_edit_fields_keyboard(order_number)
        )

        await message.answer(f"✅ {field_name.capitalize()} обновлено на: {new_value}")
        print(f"✅ Поле {field} успешно обновлено")
    else:
        print(f"❌ Ошибка при обновлении поля {field}")
        await message.answer("❌ Ошибка при обновлении заказа")
        await state.clear()

@dp.callback_query(F.data.startswith("edit_cancel_"))
async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    print("❌ Отмена редактирования")
    await callback.answer("Редактирование отменено")

    order_number = callback.data.split("_")[2]
    user_id = callback.from_user.id

    await state.clear()

    order_data = db.get_order_by_number(user_id, order_number)
    if order_data:
        await send_order_message(
            target=callback,
            order_data=order_data,
            status=order_data.get('status', 'Новый'),
            keyboard=create_order_actions_keyboard(order_number)
        )

# === ОСТАЛЬНЫЕ ОБРАБОТЧИКИ ===

@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_order(callback: CallbackQuery):
    order_number = callback.data.split("_")[1]
    user_id = callback.from_user.id

    order_data = db.get_order_by_number(user_id, order_number)
    if not order_data:
        await callback.answer("❌ Заказ не найден!", show_alert=True)
        return

    db.update_order_status(user_id, order_data['order_id'], "Подтверждён")
    order_data['status'] = "Подтверждён"

    await callback.answer("✅ Заказ подтверждён!")

    await send_order_message(
        target=callback,
        order_data=order_data,
        status="Подтверждён",
        keyboard=create_confirmed_keyboard()
    )

@dp.callback_query(F.data.startswith("delete_"))
async def delete_order(callback: CallbackQuery):
    order_number = callback.data.split("_")[1]
    user_id = callback.from_user.id

    order_data = db.get_order_by_number(user_id, order_number)
    if not order_data:
        await callback.answer("❌ Заказ не найден!", show_alert=True)
        return

    await callback.answer("🗑️ Заказ удаляется...")

    message_id = db.get_message_id(user_id, order_number)
    chat_id = db.get_chat_id(user_id, order_number)
    if message_id and chat_id:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except:
            pass

    db.delete_order(user_id, order_number)

    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer(f"🗑️ Заказ #{order_number} удалён")

@dp.callback_query(F.data.startswith("deliver_"))
async def deliver_order(callback: CallbackQuery):
    order_number = callback.data.split("_")[1]
    user_id = callback.from_user.id

    order_data = db.get_order_by_number(user_id, order_number)
    if not order_data:
        await callback.answer("❌ Заказ не найден!", show_alert=True)
        return

    db.update_order_status(user_id, order_data['order_id'], "Доставлен")
    order_data['status'] = "Доставлен"

    await callback.answer("🚚 Заказ доставлен!")

    await send_order_message(
        target=callback,
        order_data=order_data,
        status="Доставлен",
        keyboard=create_view_order_keyboard(order_number, "Доставлен")
    )

# === ПРОСМОТР ЗАКАЗОВ ===

@dp.callback_query(F.data == "my_orders")
async def my_orders(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_orders = db.get_user_orders(user_id)

    try:
        await callback.message.delete()
    except:
        pass

    if not user_orders:
        await callback.message.answer(
            "📭 У вас нет заказов.",
            reply_markup=create_back_menu()
        )
        await callback.answer()
        return

    text = "📋 <b>Ваши заказы:</b>\n\n"

    for order in user_orders[-10:]:
        status = order.get('status', 'Новый')
        emoji = {'Новый': '🟡', 'Подтверждён': '🟢', 'Доставлен': '✅'}.get(status, '📋')
        number = order.get('order_number', '—')
        text += f"{emoji} Заказ #{number} - {status}\n"

    text += f"\nВсего: {len(user_orders)}"

    await callback.message.answer(
        text,
        reply_markup=create_orders_list_keyboard(user_orders)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("view_order_"))
async def view_order(callback: CallbackQuery):
    order_number = callback.data.split("_")[2]
    user_id = callback.from_user.id

    order_data = db.get_order_by_number(user_id, order_number)
    if not order_data:
        await callback.answer("❌ Заказ не найден!", show_alert=True)
        return

    await callback.answer()

    status = order_data.get('status', 'Новый')
    keyboard = create_view_order_keyboard(order_number, status)

    await send_order_message(
        target=callback,
        order_data=order_data,
        status=status,
        keyboard=keyboard
    )

# === КНОПКИ НАЗАД ===

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()

    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer(
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите действие:",
        reply_markup=create_main_menu()
    )

@dp.callback_query(F.data == "back_to_orders")
async def back_to_orders(callback: CallbackQuery):
    await callback.answer()
    await my_orders(callback)

# === ОБРАБОТЧИК ВСЕХ СООБЩЕНИЙ ===

@dp.message()
async def echo(message: Message):
    await message.answer(
        "🤖 Я не понимаю это сообщение.\n\n"
        "Используйте /start для начала работы"
    )

# === ЗАПУСК ===

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🚀 Бот для заказов запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())