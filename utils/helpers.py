from typing import Dict
from config import ADMIN_URL


def create_order_table(order_data: Dict) -> str:
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
</table>
<a href="{ADMIN_URL}/courier/order/{order_data.get('order_number', '—')}">🔗 Ссылка на заказ</a>
"""
