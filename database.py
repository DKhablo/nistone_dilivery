import json
from datetime import datetime
from typing import Dict, Optional, List
from config import DB_PATH


class OrderDatabase:
    def __init__(self):
        self.orders: Dict[str, List[Dict]] = {}
        self.load()

    def load(self):
        """Загружает данные из файла."""
        if DB_PATH.exists():
            try:
                with open(DB_PATH, 'r', encoding='utf-8') as f:
                    self.orders = json.load(f)
                print(f"✅ Загружено заказов: {sum(len(v) for v in self.orders.values())}")
            except Exception as e:
                print(f"⚠️ Ошибка загрузки БД: {e}")
                self.orders = {}
        else:
            self.orders = {}
            self.save()

    def save(self):
        """Сохраняет данные в файл."""
        try:
            with open(DB_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.orders, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Ошибка сохранения БД: {e}")

    def get_user_orders(self, user_id: int) -> List[Dict]:
        """Получает заказы пользователя, всегда читая свежие данные из файла."""
        self.load()
        return self.orders.get(str(user_id), [])

    def add_order(self, user_id: int, chat_id: int, order_data: Dict) -> int:
        """Добавляет новый заказ."""
        self.load()

        user_id_str = str(user_id)
        if user_id_str not in self.orders:
            self.orders[user_id_str] = []

        order_id = len(self.orders[user_id_str]) + 1
        order_data['order_id'] = order_id
        order_data['user_id'] = user_id
        order_data['chat_id'] = chat_id
        order_data['created_at'] = datetime.now().isoformat()
        order_data['status'] = 'new'
        order_data['message_id'] = None
        order_data['temp_messages'] = []

        self.orders[user_id_str].append(order_data)
        self.save()
        return order_id

    def delete_order(self, user_id: int, order_number: str):
        """Удаляет заказ."""
        self.load()

        user_id_str = str(user_id)
        if user_id_str in self.orders:
            self.orders[user_id_str] = [
                order for order in self.orders[user_id_str]
                if order.get('order_number') != order_number
            ]
            self.save()
            return True
        return False

    def get_order_by_number(self, user_id: int, order_number: str) -> Optional[Dict]:
        """Получает заказ по номеру, всегда читая свежие данные из файла."""
        self.load()
        for order in self.get_user_orders(user_id):
            if order.get('order_number') == order_number:
                return order
        return None

    def update_message_id(self, user_id: int, order_number: str, message_id: int):
        """Обновляет ID сообщения в заказе."""
        self.load()

        user_id_str = str(user_id)
        if user_id_str in self.orders:
            for order in self.orders[user_id_str]:
                if order.get('order_number') == order_number:
                    order['message_id'] = message_id
                    self.save()
                    return True
        return False

    def get_message_id(self, user_id: int, order_number: str) -> Optional[int]:
        """Получает ID сообщения из заказа."""
        self.load()
        order = self.get_order_by_number(user_id, order_number)
        if order:
            return order.get('message_id')
        return None

    def get_chat_id(self, user_id: int, order_number: str) -> Optional[int]:
        """Получает chat_id из заказа."""
        self.load()
        order = self.get_order_by_number(user_id, order_number)
        if order:
            return order.get('chat_id')
        return None

    def add_temp_message(self, user_id: int, order_number: str, message_id: int):
        """Добавляет временное сообщение."""
        self.load()

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
        """Очищает временные сообщения."""
        self.load()

        user_id_str = str(user_id)
        if user_id_str in self.orders:
            for order in self.orders[user_id_str]:
                if order.get('order_number') == order_number:
                    order['temp_messages'] = []
                    self.save()
                    return True
        return False

    def get_temp_messages(self, user_id: int, order_number: str) -> List[int]:
        """Получает список временных сообщений."""
        self.load()
        order = self.get_order_by_number(user_id, order_number)
        if order:
            return order.get('temp_messages', [])
        return []


db = OrderDatabase()