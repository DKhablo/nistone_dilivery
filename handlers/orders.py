from typing import Dict
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputRichMessage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from keyboards.menu import orders_list, back_menu
from utils.helpers import create_order_table

router = Router(name="orders")


class OrderStates(StatesGroup):
    waiting_for_order_number = State()
    waiting_for_address = State()
    waiting_for_time_interval = State()
    waiting_for_phone = State()
    waiting_for_amount = State()
    waiting_for_comment = State()


async def send_order_message(target, order_data: Dict, keyboard=None):
    """Отправляет сообщение с заказом."""
    html_content = create_order_table(order_data)
    rich_message = InputRichMessage(html=html_content)

    if isinstance(target, CallbackQuery):
        chat_id = target.message.chat.id
        user_id = target.from_user.id
    else:
        chat_id = target.chat.id
        user_id = target.from_user.id

    order_number = order_data.get('order_number')

    try:
        sent_msg = await target.bot.send_rich_message(
            chat_id=chat_id,
            rich_message=rich_message,
            reply_markup=keyboard,
        )

        if sent_msg:
            db.update_message_id(user_id, order_number, sent_msg.message_id)
            return sent_msg.message_id

    except Exception as e:
        print(f"Ошибка отправки: {e}")
        return None


async def delete_temp_messages(user_id: int, order_number: str):
    """Удаляет временные сообщения."""
    temp_messages = db.get_temp_messages(user_id, order_number)
    chat_id = db.get_chat_id(user_id, order_number)

    for msg_id in temp_messages:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception as e:
            print(f"Ошибка удаления временного сообщения {msg_id}: {e}")

    db.clear_temp_messages(user_id, order_number)


@router.callback_query(F.data == "new_order")
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


@router.message(OrderStates.waiting_for_order_number)
async def get_order_number(message: Message, state: FSMContext):
    data = await state.get_data()
    temp_messages = data.get('temp_messages', [])
    temp_messages.append(message.message_id)
    await state.update_data(order_number=message.text.strip(), temp_messages=temp_messages)

    msg = await message.answer("📍 Введите адрес доставки:")
    temp_messages.append(msg.message_id)
    await state.update_data(temp_messages=temp_messages)
    await state.set_state(OrderStates.waiting_for_address)


@router.message(OrderStates.waiting_for_address)
async def get_address(message: Message, state: FSMContext):
    data = await state.get_data()
    temp_messages = data.get('temp_messages', [])
    temp_messages.append(message.message_id)
    await state.update_data(address=message.text.strip(), temp_messages=temp_messages)

    msg = await message.answer("🕐 Введите интервал времени (14:00-18:00):")
    temp_messages.append(msg.message_id)
    await state.update_data(temp_messages=temp_messages)
    await state.set_state(OrderStates.waiting_for_time_interval)


@router.message(OrderStates.waiting_for_time_interval)
async def get_time(message: Message, state: FSMContext):
    data = await state.get_data()
    temp_messages = data.get('temp_messages', [])
    temp_messages.append(message.message_id)
    await state.update_data(time_interval=message.text.strip(), temp_messages=temp_messages)

    msg = await message.answer("📱 Введите номер телефона:")
    temp_messages.append(msg.message_id)
    await state.update_data(temp_messages=temp_messages)
    await state.set_state(OrderStates.waiting_for_phone)


@router.message(OrderStates.waiting_for_phone)
async def get_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    temp_messages = data.get('temp_messages', [])
    temp_messages.append(message.message_id)
    await state.update_data(phone=message.text.strip(), temp_messages=temp_messages)

    msg = await message.answer("💰 Введите сумму заказа:")
    temp_messages.append(msg.message_id)
    await state.update_data(temp_messages=temp_messages)
    await state.set_state(OrderStates.waiting_for_amount)


@router.message(OrderStates.waiting_for_amount)
async def get_amount(message: Message, state: FSMContext):
    data = await state.get_data()
    temp_messages = data.get('temp_messages', [])
    temp_messages.append(message.message_id)
    await state.update_data(amount=message.text.strip(), temp_messages=temp_messages)

    msg = await message.answer("📝 Введите комментарий (или '-'):")
    temp_messages.append(msg.message_id)
    await state.update_data(temp_messages=temp_messages)
    await state.set_state(OrderStates.waiting_for_comment)


@router.message(OrderStates.waiting_for_comment)
async def get_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    temp_messages = data.get('temp_messages', [])
    temp_messages.append(message.message_id)
    await state.update_data(comment=message.text.strip() or "—", temp_messages=temp_messages)

    order_data = await state.get_data()
    user_id = message.from_user.id
    chat_id = message.chat.id

    temp_msgs = order_data.get('temp_messages', [])

    # Сохраняем заказ в БД со статусом 'new'
    db.add_order(user_id, chat_id, order_data)
    order_number = order_data['order_number']

    for msg_id in temp_msgs:
        db.add_temp_message(user_id, order_number, msg_id)

    for msg_id in temp_msgs:
        try:
            await message.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except:
            pass

    db.clear_temp_messages(user_id, order_number)

    # Получаем свежие данные из БД
    order_data = db.get_order_by_number(user_id, order_number)

    # Отправляем заказ без кнопок (только просмотр)
    await send_order_message(
        target=message,
        order_data=order_data,
        keyboard=None
    )

    await state.clear()


@router.callback_query(F.data == "my_orders")
async def my_orders(callback: CallbackQuery):
    user_id = callback.from_user.id

    # ✅ Получаем актуальные данные из БД (всегда свежие)
    user_orders = db.get_user_orders(user_id)

    try:
        await callback.message.delete()
    except:
        pass

    if not user_orders:
        await callback.message.answer(
            "📭 У вас нет заказов.",
            reply_markup=back_menu()
        )
        await callback.answer()
        return

    text = "📋 <b>Ваши заказы:</b>\n\n"

    for order in user_orders[-10:]:
        status = order.get('status', 'new')
        status_emoji = {'new': '🟡', 'collecting': '🔵', 'ready': '🟢', 'delivering': '🟠', 'delivered': '✅'}.get(status, '📋')
        status_name = {'new': 'Новый', 'collecting': 'Собирается', 'ready': 'Готов', 'delivering': 'В доставке', 'delivered': 'Доставлен'}.get(status, status)
        number = order.get('order_number', '—')
        text += f"{status_emoji} Заказ #{number} - {status_name}\n"

    text += f"\nВсего: {len(user_orders)}"

    await callback.message.answer(
        text,
        reply_markup=orders_list(user_orders, user_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("view_order_"))
async def view_order(callback: CallbackQuery):
    order_number = callback.data.split("_")[2]
    user_id = callback.from_user.id

    # ✅ Получаем актуальные данные из БД (всегда свежие)
    order_data = db.get_order_by_number(user_id, order_number)

    if not order_data:
        await callback.answer("❌ Заказ не найден! Возможно, он был удалён.", show_alert=True)
        return

    await callback.answer()

    try:
        await callback.message.delete()
    except:
        pass

    # Отправляем заказ с актуальными данными из БД
    await send_order_message(
        target=callback,
        order_data=order_data,
        keyboard=None
    )


@router.callback_query(F.data == "back_to_orders")
async def back_to_orders(callback: CallbackQuery):
    await callback.answer()

    try:
        await callback.message.delete()
    except:
        pass

    # Перезагружаем список заказов из БД (всегда свежие)
    await my_orders(callback)